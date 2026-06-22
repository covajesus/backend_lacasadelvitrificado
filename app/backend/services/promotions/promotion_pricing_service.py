from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.db.models import (
    LotItemModel,
    PromotionModel,
    PromotionProductModel,
    PromotionUsageModel,
)

PROMOTION_TYPE_PRODUCT_DISCOUNT = 1
PROMOTION_TYPE_COUPON = 2


def _to_float(value):
    if value is None:
        return 0.0
    return float(value)


def _round_price(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


class PromotionPricingService:
    def __init__(self, db: Session):
        self.db = db

    def is_promotion_active(self, promotion: PromotionModel, now: datetime | None = None) -> bool:
        if not promotion or int(promotion.is_active or 0) != 1:
            return False
        current = now or datetime.utcnow()
        if promotion.start_date and current < promotion.start_date:
            return False
        if promotion.end_date:
            end = promotion.end_date.replace(hour=23, minute=59, second=59)
            if current > end:
                return False
        return True

    def get_product_public_price(self, product_id: int) -> float:
        price = (
            self.db.query(func.max(LotItemModel.public_sale_price))
            .filter(LotItemModel.product_id == product_id)
            .scalar()
        )
        return _to_float(price)

    def calculate_promotional_price(self, base_price: float, discount_percent: float) -> dict:
        base = _to_float(base_price)
        percent = _to_float(discount_percent)
        promo = _round_price(base * (1 - percent / 100))
        discount_amount = _round_price(base - promo)
        return {
            'original_price': base,
            'promotional_price': promo,
            'discount_amount': discount_amount,
            'discount_percent': percent,
        }

    def get_active_product_discounts_map(self) -> dict[int, dict]:
        now = datetime.utcnow()
        rows = (
            self.db.query(PromotionModel, PromotionProductModel)
            .join(PromotionProductModel, PromotionProductModel.promotion_id == PromotionModel.id)
            .filter(PromotionModel.promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT)
            .filter(PromotionModel.is_active == 1)
            .all()
        )
        result: dict[int, dict] = {}
        for promotion, promo_product in rows:
            if not self.is_promotion_active(promotion, now):
                continue
            product_id = int(promo_product.product_id)
            if product_id in result:
                continue
            result[product_id] = {
                'promotion_id': promotion.id,
                'promotion_type_id': PROMOTION_TYPE_PRODUCT_DISCOUNT,
                'promotion_name': promotion.name,
                'discount_percent': _to_float(promotion.discount_percent),
                'original_price': _to_float(promo_product.original_price),
                'promotional_price': _to_float(promo_product.promotional_price),
                'discount_amount': _to_float(promo_product.discount_amount),
            }
        return result

    def enrich_product_dict(self, product_dict: dict) -> dict:
        product_id = product_dict.get('id')
        if not product_id:
            return product_dict
        discounts = self.get_active_product_discounts_map()
        promo = discounts.get(int(product_id))
        if not promo:
            return product_dict

        original = _to_float(product_dict.get('public_sale_price'))
        if original <= 0:
            original = promo['original_price']

        pricing = self.calculate_promotional_price(original, promo['discount_percent'])
        product_dict['public_sale_price_original'] = original
        product_dict['public_sale_price'] = pricing['promotional_price']
        product_dict['promotion_id'] = promo['promotion_id']
        product_dict['promotion_type_id'] = promo['promotion_type_id']
        product_dict['promotion_discount_percent'] = promo['discount_percent']
        product_dict['promotion_discount_amount'] = pricing['discount_amount']
        product_dict['has_product_promotion'] = True
        return product_dict

    def enrich_product_list(self, products: list[dict]) -> list[dict]:
        if not products:
            return products
        discounts = self.get_active_product_discounts_map()
        enriched = []
        for product in products:
            product_id = product.get('id')
            promo = discounts.get(int(product_id)) if product_id else None
            if not promo:
                enriched.append(product)
                continue
            item = dict(product)
            original = _to_float(item.get('public_sale_price'))
            if original <= 0:
                original = promo['original_price']
            pricing = self.calculate_promotional_price(original, promo['discount_percent'])
            item['public_sale_price_original'] = original
            item['public_sale_price'] = pricing['promotional_price']
            item['promotion_id'] = promo['promotion_id']
            item['promotion_type_id'] = promo['promotion_type_id']
            item['promotion_discount_percent'] = promo['discount_percent']
            item['promotion_discount_amount'] = pricing['discount_amount']
            item['has_product_promotion'] = True
            enriched.append(item)
        return enriched

    def validate_coupon(self, coupon_code: str, product_ids: list[int], subtotal: float) -> dict:
        code = (coupon_code or '').strip().upper()
        if not code:
            return {'status': 'error', 'message': 'Debe indicar el código del cupón.'}

        promotion = (
            self.db.query(PromotionModel)
            .filter(PromotionModel.promotion_type_id == PROMOTION_TYPE_COUPON)
            .filter(func.upper(PromotionModel.coupon_code) == code)
            .first()
        )
        if not promotion:
            return {'status': 'error', 'message': 'Cupón no encontrado.'}
        if not self.is_promotion_active(promotion):
            return {'status': 'error', 'message': 'El cupón no está vigente.'}

        minimum = _to_float(promotion.minimum_purchase)
        subtotal_value = _to_float(subtotal)
        if minimum > 0 and subtotal_value < minimum:
            return {
                'status': 'error',
                'message': f'La compra mínima para este cupón es ${int(minimum):,}'.replace(',', '.'),
            }

        promo_products = (
            self.db.query(PromotionProductModel)
            .filter(PromotionProductModel.promotion_id == promotion.id)
            .all()
        )
        allowed_ids = {int(row.product_id) for row in promo_products}
        if not allowed_ids:
            return {'status': 'error', 'message': 'El cupón no tiene productos asociados.'}

        matched_ids = [pid for pid in product_ids if int(pid) in allowed_ids]
        if not matched_ids:
            return {'status': 'error', 'message': 'Ningún producto del carrito aplica para este cupón.'}

        product_pricing = []
        total_discount = 0.0
        for row in promo_products:
            if int(row.product_id) not in matched_ids:
                continue
            product_pricing.append({
                'product_id': int(row.product_id),
                'original_price': _to_float(row.original_price),
                'promotional_price': _to_float(row.promotional_price),
                'discount_amount': _to_float(row.discount_amount),
            })
            total_discount += _to_float(row.discount_amount)

        return {
            'status': 'success',
            'message': 'Cupón válido.',
            'data': {
                'promotion_id': promotion.id,
                'promotion_type_id': PROMOTION_TYPE_COUPON,
                'coupon_code': promotion.coupon_code,
                'discount_percent': _to_float(promotion.discount_percent),
                'minimum_purchase': minimum,
                'product_ids': matched_ids,
                'products': product_pricing,
                'estimated_discount_total': _round_price(total_discount),
            },
        }

    def record_usage(
        self,
        promotion_id: int,
        promotion_type_id: int,
        product_id: int | None,
        quantity: int,
        original_unit_price: float,
        promotional_unit_price: float,
        sale_id: int | None = None,
        budget_id: int | None = None,
        coupon_code: str | None = None,
    ):
        discount_per_unit = _round_price(_to_float(original_unit_price) - _to_float(promotional_unit_price))
        total_lost = _round_price(discount_per_unit * max(int(quantity or 1), 1))
        row = PromotionUsageModel(
            promotion_id=promotion_id,
            promotion_type_id=promotion_type_id,
            product_id=product_id,
            sale_id=sale_id,
            budget_id=budget_id,
            coupon_code=coupon_code,
            quantity=max(int(quantity or 1), 1),
            original_unit_price=original_unit_price,
            promotional_unit_price=promotional_unit_price,
            discount_amount_per_unit=discount_per_unit,
            total_discount_lost=total_lost,
            applied_date=datetime.utcnow(),
        )
        self.db.add(row)
        return row

    def record_product_discount_usages(self, product_items, budget_id=None, sale_id=None):
        discounts = self.get_active_product_discounts_map()
        if not discounts:
            return
        for item in product_items:
            product_id = int(item.get('product_id') or item.get('id') or 0)
            if not product_id:
                continue
            promo = discounts.get(product_id)
            if not promo:
                continue
            quantity = max(int(item.get('quantity') or 1), 1)
            self.record_usage(
                promotion_id=promo['promotion_id'],
                promotion_type_id=PROMOTION_TYPE_PRODUCT_DISCOUNT,
                product_id=product_id,
                quantity=quantity,
                original_unit_price=promo['original_price'],
                promotional_unit_price=promo['promotional_price'],
                budget_id=budget_id,
                sale_id=sale_id,
            )
