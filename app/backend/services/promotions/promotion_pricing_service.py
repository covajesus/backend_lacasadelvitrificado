from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.backend.db.models import (
    CustomerModel,
    LotItemModel,
    ProductModel,
    PromotionModel,
    PromotionCustomerModel,
    PromotionProductModel,
    PromotionUsageModel,
    SaleModel,
    SaleProductModel,
)

PROMOTION_TYPE_PRODUCT_DISCOUNT = 1
PROMOTION_TYPE_COUPON = 2
PROMOTION_AUDIENCE_ALL = 1
PROMOTION_AUDIENCE_SELECTED = 2
ACCEPTED_SALE_STATUS_IDS = (2, 4)


def _to_float(value):
    if value is None:
        return 0.0
    return float(value)


def _round_price(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _normalize_rut(rut: str | None) -> str:
    if not rut:
        return ''
    return str(rut).strip().upper().replace('.', '').replace(' ', '').replace('-', '')


def _rollback_db(db: Session):
    try:
        db.rollback()
    except Exception:
        pass


class PromotionPricingService:
    def __init__(self, db: Session):
        self.db = db

    def _promotions_schema_missing(self, error: Exception) -> bool:
        message = str(getattr(error, 'orig', error)).lower()
        if "doesn't exist" in message or '1146' in message:
            return True
        if '1054' in message or 'unknown column' in message:
            return 'promotion' in message
        return False

    def is_promotion_active(self, promotion: PromotionModel, now: datetime | None = None) -> bool:
        if not promotion or int(getattr(promotion, 'status_id', 0) or 0) != 1:
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
        try:
            rows = (
                self.db.query(PromotionModel, PromotionProductModel)
                .join(PromotionProductModel, PromotionProductModel.promotion_id == PromotionModel.id)
                .filter(PromotionModel.promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT)
                .filter(PromotionModel.status_id == 1)
                .all()
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return {}
            raise

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

    def _get_product_names_map(self, product_ids: list[int]) -> dict[int, str]:
        if not product_ids:
            return {}
        rows = (
            self.db.query(ProductModel.id, ProductModel.product)
            .filter(ProductModel.id.in_(product_ids))
            .all()
        )
        return {int(row.id): str(row.product) for row in rows}

    def _split_coupon_eligible_products(self, product_ids: list[int]) -> tuple[list[int], list[dict]]:
        active_discounts = self.get_active_product_discounts_map()
        matched_ids = [int(pid) for pid in product_ids if int(pid)]
        excluded_ids = [pid for pid in matched_ids if pid in active_discounts]
        eligible_ids = [pid for pid in matched_ids if pid not in active_discounts]
        names_map = self._get_product_names_map(excluded_ids)
        excluded = [
            {
                'product_id': pid,
                'product_name': names_map.get(pid, f'Producto #{pid}'),
            }
            for pid in excluded_ids
        ]
        return eligible_ids, excluded

    def _customer_has_used_coupon(self, promotion_id: int, customer_rut: str | None) -> bool:
        normalized_rut = _normalize_rut(customer_rut)
        if not normalized_rut:
            return False
        try:
            rows = (
                self.db.query(CustomerModel.id, CustomerModel.identification_number)
                .join(SaleModel, SaleModel.customer_id == CustomerModel.id)
                .join(PromotionUsageModel, PromotionUsageModel.sale_id == SaleModel.id)
                .filter(PromotionUsageModel.promotion_id == promotion_id)
                .filter(PromotionUsageModel.promotion_type_id == PROMOTION_TYPE_COUPON)
                .filter(SaleModel.status_id.in_(ACCEPTED_SALE_STATUS_IDS))
                .all()
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return False
            raise

        seen_customer_ids: set[int] = set()
        for customer_id, identification_number in rows:
            if customer_id in seen_customer_ids:
                continue
            seen_customer_ids.add(int(customer_id))
            if _normalize_rut(identification_number) == normalized_rut:
                return True
        return False

    def _get_customer_id_by_rut(self, customer_rut: str | None) -> int | None:
        normalized_rut = _normalize_rut(customer_rut)
        if not normalized_rut:
            return None
        try:
            rows = self.db.query(CustomerModel.id, CustomerModel.identification_number).all()
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return None
            raise
        for customer_id, identification_number in rows:
            if _normalize_rut(identification_number) == normalized_rut:
                return int(customer_id)
        return None

    def _coupon_visible_to_customer(self, promotion: PromotionModel, customer_rut: str | None) -> bool:
        audience_type = int(getattr(promotion, 'audience_type', PROMOTION_AUDIENCE_ALL) or PROMOTION_AUDIENCE_ALL)
        if audience_type == PROMOTION_AUDIENCE_ALL:
            return True
        customer_id = self._get_customer_id_by_rut(customer_rut)
        if not customer_id:
            return False
        try:
            row = (
                self.db.query(PromotionCustomerModel.id)
                .filter(PromotionCustomerModel.promotion_id == promotion.id)
                .filter(PromotionCustomerModel.customer_id == customer_id)
                .first()
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return False
            raise
        return row is not None

    def get_visible_coupon_banners(self, customer_rut: str | None) -> list[dict]:
        now = datetime.utcnow()
        try:
            promotions = (
                self.db.query(PromotionModel)
                .filter(PromotionModel.promotion_type_id == PROMOTION_TYPE_COUPON)
                .filter(PromotionModel.status_id == 1)
                .order_by(PromotionModel.id.desc())
                .all()
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return []
            raise

        banners: list[dict] = []
        for promotion in promotions:
            if not self.is_promotion_active(promotion, now):
                continue
            if not self._coupon_visible_to_customer(promotion, customer_rut):
                continue
            if self._customer_has_used_coupon(promotion.id, customer_rut):
                continue
            end_date = promotion.end_date.strftime('%Y-%m-%d') if promotion.end_date else None
            banners.append({
                'id': promotion.id,
                'name': promotion.name,
                'coupon_code': promotion.coupon_code,
                'discount_percent': int(round(_to_float(promotion.discount_percent))),
                'minimum_purchase': _to_float(promotion.minimum_purchase),
                'end_date': end_date,
                'description': promotion.description,
            })
        return banners

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

    def validate_coupon(
        self,
        coupon_code: str,
        product_ids: list[int],
        subtotal: float,
        items: list[dict] | None = None,
        customer_rut: str | None = None,
    ) -> dict:
        code = (coupon_code or '').strip().upper()
        if not code:
            return {'status': 'error', 'message': 'Debe indicar el código del cupón.'}

        quantities: dict[int, int] = {}
        unit_prices: dict[int, float] = {}
        if items:
            for item in items:
                product_id = int(item.get('product_id') or item.get('id') or 0)
                if not product_id:
                    continue
                quantities[product_id] = max(int(item.get('quantity') or 1), 1)
                unit_prices[product_id] = _to_float(item.get('unit_price', 0))

        try:
            promotion = (
                self.db.query(PromotionModel)
                .filter(PromotionModel.promotion_type_id == PROMOTION_TYPE_COUPON)
                .filter(func.upper(PromotionModel.coupon_code) == code)
                .first()
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return {
                    'status': 'error',
                    'message': 'El módulo de promociones no está instalado en la base de datos.',
                }
            raise

        if not promotion:
            return {'status': 'error', 'message': 'Cupón no encontrado.'}
        if not self.is_promotion_active(promotion):
            return {'status': 'error', 'message': 'El cupón no está vigente.'}

        if not _normalize_rut(customer_rut):
            return {
                'status': 'error',
                'message': 'Debe iniciar sesión con su RUT para usar un cupón.',
            }
        if self._customer_has_used_coupon(promotion.id, customer_rut):
            return {
                'status': 'error',
                'message': 'Este cupón ya fue utilizado. No puede volver a aplicarlo.',
            }
        if not self._coupon_visible_to_customer(promotion, customer_rut):
            return {
                'status': 'error',
                'message': 'Este cupón no está disponible para su cuenta.',
            }

        minimum = _to_float(promotion.minimum_purchase)
        subtotal_value = _to_float(subtotal)
        if minimum <= 0:
            return {'status': 'error', 'message': 'Este cupón no tiene compra mínima configurada.'}
        if subtotal_value < minimum:
            return {
                'status': 'error',
                'message': f'La compra mínima para este cupón es ${int(minimum):,}'.replace(',', '.'),
            }

        try:
            promo_products = (
                self.db.query(PromotionProductModel)
                .filter(PromotionProductModel.promotion_id == promotion.id)
                .all()
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return {
                    'status': 'error',
                    'message': 'El módulo de promociones no está instalado en la base de datos.',
                }
            raise

        allowed_ids = {int(row.product_id) for row in promo_products}

        product_pricing = []
        total_discount = 0.0
        discount_percent = _to_float(promotion.discount_percent)
        excluded_products: list[dict] = []

        if not allowed_ids:
            cart_ids = [int(pid) for pid in product_ids if int(pid)]
            if not cart_ids:
                return {'status': 'error', 'message': 'El carrito está vacío.'}

            eligible_ids, excluded_products = self._split_coupon_eligible_products(cart_ids)
            if not eligible_ids:
                excluded_names = ', '.join(item['product_name'] for item in excluded_products)
                return {
                    'status': 'error',
                    'message': (
                        f'El cupón no aplica a productos con descuento activo: {excluded_names}. '
                        'Retírelos del carrito para usar el cupón.'
                    ),
                }

            for product_id in eligible_ids:
                quantity = quantities.get(product_id, 1)
                original = unit_prices.get(product_id, 0)
                if original <= 0:
                    original = self.get_product_public_price(product_id)
                pricing = self.calculate_promotional_price(original, discount_percent)
                line_discount = _round_price(pricing['discount_amount'] * quantity)
                product_pricing.append({
                    'product_id': product_id,
                    'original_price': pricing['original_price'],
                    'promotional_price': pricing['promotional_price'],
                    'discount_amount': pricing['discount_amount'],
                })
                total_discount += line_discount
            matched_ids = eligible_ids
        else:
            cart_matched_ids = [int(pid) for pid in product_ids if int(pid) in allowed_ids]
            if not cart_matched_ids:
                return {'status': 'error', 'message': 'Ningún producto del carrito aplica para este cupón.'}

            eligible_ids, excluded_products = self._split_coupon_eligible_products(cart_matched_ids)
            if not eligible_ids:
                excluded_names = ', '.join(item['product_name'] for item in excluded_products)
                return {
                    'status': 'error',
                    'message': (
                        f'El cupón no aplica a productos con descuento activo: {excluded_names}. '
                        'Retírelos del carrito para usar el cupón.'
                    ),
                }

            for row in promo_products:
                product_id = int(row.product_id)
                if product_id not in eligible_ids:
                    continue
                quantity = quantities.get(product_id, 1)
                original = _to_float(row.original_price)
                promotional = _to_float(row.promotional_price)
                discount_per_unit = _to_float(row.discount_amount)
                if discount_per_unit <= 0 and original > promotional:
                    discount_per_unit = _round_price(original - promotional)
                line_discount = _round_price(discount_per_unit * quantity)
                product_pricing.append({
                    'product_id': product_id,
                    'original_price': original,
                    'promotional_price': promotional,
                    'discount_amount': discount_per_unit,
                })
                total_discount += line_discount
            matched_ids = eligible_ids

        success_message = 'Cupón válido.'
        if excluded_products:
            excluded_names = ', '.join(item['product_name'] for item in excluded_products)
            success_message = (
                f'Cupón aplicado. No aplica a: {excluded_names} '
                '(tienen descuento activo).'
            )

        return {
            'status': 'success',
            'message': success_message,
            'data': {
                'promotion_id': promotion.id,
                'promotion_type_id': PROMOTION_TYPE_COUPON,
                'coupon_code': promotion.coupon_code,
                'discount_percent': discount_percent,
                'minimum_purchase': minimum,
                'product_ids': matched_ids,
                'products': product_pricing,
                'excluded_products': excluded_products,
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
        try:
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
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return None
            raise

    def record_coupon_usages(self, coupon_code: str, cart_items, sale_id=None, customer_rut: str | None = None):
        if not coupon_code:
            return
        product_ids = [int(item.get('product_id') or item.get('id') or 0) for item in cart_items]
        product_ids = [pid for pid in product_ids if pid]
        if not product_ids:
            return

        items = []
        for item in cart_items:
            product_id = int(item.get('product_id') or item.get('id') or 0)
            if not product_id:
                continue
            items.append({
                'product_id': product_id,
                'quantity': max(int(item.get('quantity') or 1), 1),
                'unit_price': _to_float(item.get('unit_price') or item.get('public_sale_price') or 0),
            })

        subtotal = sum(row['unit_price'] * row['quantity'] for row in items)
        validation = self.validate_coupon(
            coupon_code, product_ids, subtotal, items=items, customer_rut=customer_rut
        )
        if validation.get('status') != 'success':
            return

        promo_products = {
            int(row['product_id']): row
            for row in validation.get('data', {}).get('products', [])
        }
        promotion_id = validation['data']['promotion_id']
        for item in items:
            promo = promo_products.get(item['product_id'])
            if not promo:
                continue
            self.record_usage(
                promotion_id=promotion_id,
                promotion_type_id=PROMOTION_TYPE_COUPON,
                product_id=item['product_id'],
                quantity=item['quantity'],
                original_unit_price=promo['original_price'],
                promotional_unit_price=promo['promotional_price'],
                sale_id=sale_id,
                coupon_code=coupon_code.strip().upper(),
            )

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

    def remove_sale_promotion_usages(self, sale_id: int) -> None:
        try:
            (
                self.db.query(PromotionUsageModel)
                .filter(PromotionUsageModel.sale_id == int(sale_id))
                .delete(synchronize_session=False)
            )
            self.db.flush()
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return
            raise

    def record_sale_promotion_usages(self, sale_id: int) -> None:
        sale_id = int(sale_id)
        try:
            existing = (
                self.db.query(PromotionUsageModel.id)
                .filter(PromotionUsageModel.sale_id == sale_id)
                .first()
            )
            if existing:
                return

            sale = self.db.query(SaleModel).filter(SaleModel.id == sale_id).first()
            if not sale:
                return

            sale_products = (
                self.db.query(SaleProductModel)
                .filter(SaleProductModel.sale_id == sale_id)
                .all()
            )
            if not sale_products:
                return

            product_items = [
                {'product_id': sp.product_id, 'quantity': sp.quantity}
                for sp in sale_products
            ]
            self.record_product_discount_usages(product_items, sale_id=sale_id)

            coupon_code = (getattr(sale, 'coupon_code', None) or '').strip()
            if not coupon_code:
                return

            customer_rut = None
            if sale.customer_id:
                customer = (
                    self.db.query(CustomerModel)
                    .filter(CustomerModel.id == sale.customer_id)
                    .first()
                )
                if customer:
                    customer_rut = customer.identification_number

            coupon_items = []
            for sp in sale_products:
                unit_price = _to_float(sp.price)
                if unit_price <= 0:
                    unit_price = self.get_product_public_price(sp.product_id)
                coupon_items.append({
                    'product_id': sp.product_id,
                    'quantity': sp.quantity,
                    'unit_price': unit_price,
                    'public_sale_price': unit_price,
                })

            self.record_coupon_usages(
                coupon_code,
                coupon_items,
                sale_id=sale_id,
                customer_rut=customer_rut,
            )
        except (ProgrammingError, OperationalError) as error:
            _rollback_db(self.db)
            if self._promotions_schema_missing(error):
                return
            raise
