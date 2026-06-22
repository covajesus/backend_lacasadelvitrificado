from datetime import datetime

from sqlalchemy import func

from app.backend.db.models import (
    ProductModel,
    PromotionModel,
    PromotionProductModel,
    PromotionUsageModel,
)
from app.backend.services.crud.base_domain_service import BaseDomainService
from app.backend.services.promotions.promotion_pricing_service import (
    PROMOTION_TYPE_COUPON,
    PROMOTION_TYPE_PRODUCT_DISCOUNT,
    PromotionPricingService,
)


def _parse_optional_date(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if len(text) >= 10:
        try:
            return datetime.strptime(text[:10], '%Y-%m-%d')
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace('Z', '')[:19])
    except ValueError:
        return None


class PromotionClass(BaseDomainService):
    PROMOTION_TYPE_LABELS = {
        PROMOTION_TYPE_PRODUCT_DISCOUNT: 'Descuento por producto',
        PROMOTION_TYPE_COUPON: 'Cupón',
    }

    def __init__(self, db):
        super().__init__(db)
        self.pricing = PromotionPricingService(db)

    def _type_label(self, promotion_type_id):
        return self.PROMOTION_TYPE_LABELS.get(int(promotion_type_id or 0), 'Desconocido')

    def _load_products(self, promotion_id):
        rows = (
            self.db.query(
                PromotionProductModel.id,
                PromotionProductModel.product_id,
                PromotionProductModel.original_price,
                PromotionProductModel.promotional_price,
                PromotionProductModel.discount_amount,
                ProductModel.product,
                ProductModel.code,
            )
            .join(ProductModel, ProductModel.id == PromotionProductModel.product_id, isouter=True)
            .filter(PromotionProductModel.promotion_id == promotion_id)
            .all()
        )
        return [
            {
                'id': row.id,
                'product_id': row.product_id,
                'product_name': row.product,
                'product_code': row.code,
                'original_price': float(row.original_price or 0),
                'promotional_price': float(row.promotional_price or 0),
                'discount_amount': float(row.discount_amount or 0),
            }
            for row in rows
        ]

    def _serialize_row(self, row):
        start = row.start_date.strftime('%Y-%m-%d') if row.start_date else None
        end = row.end_date.strftime('%Y-%m-%d') if row.end_date else None
        products = self._load_products(row.id)
        total_discount = sum(item['discount_amount'] for item in products)
        return {
            'id': row.id,
            'promotion_type_id': int(row.promotion_type_id or PROMOTION_TYPE_PRODUCT_DISCOUNT),
            'promotion_type_label': self._type_label(row.promotion_type_id),
            'product_id': row.product_id,
            'name': row.name,
            'description': row.description,
            'discount_percent': float(row.discount_percent or 0),
            'coupon_code': row.coupon_code,
            'minimum_purchase': float(row.minimum_purchase or 0),
            'start_date': start,
            'end_date': end,
            'is_active': int(row.is_active or 0),
            'products': products,
            'total_discount_per_unit': round(total_discount, 2),
        }

    def get_all(self, page=0, items_per_page=10):
        query = (
            self.db.query(
                PromotionModel.id,
                PromotionModel.promotion_type_id,
                PromotionModel.product_id,
                PromotionModel.name,
                PromotionModel.description,
                PromotionModel.discount_percent,
                PromotionModel.coupon_code,
                PromotionModel.minimum_purchase,
                PromotionModel.start_date,
                PromotionModel.end_date,
                PromotionModel.is_active,
            )
            .order_by(PromotionModel.id.desc())
        )
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get_list(self):
        query = (
            self.db.query(
                PromotionModel.id,
                PromotionModel.promotion_type_id,
                PromotionModel.product_id,
                PromotionModel.name,
                PromotionModel.description,
                PromotionModel.discount_percent,
                PromotionModel.coupon_code,
                PromotionModel.minimum_purchase,
                PromotionModel.start_date,
                PromotionModel.end_date,
                PromotionModel.is_active,
            )
            .filter(PromotionModel.is_active == 1)
            .order_by(PromotionModel.name)
        )
        return self.list_wrapped(query, self._serialize_row)

    def _validate_inputs(self, promotion_inputs, promotion_id=None):
        promotion_type_id = int(promotion_inputs.promotion_type_id or PROMOTION_TYPE_PRODUCT_DISCOUNT)
        if promotion_type_id not in (PROMOTION_TYPE_PRODUCT_DISCOUNT, PROMOTION_TYPE_COUPON):
            return 'Tipo de promoción no válido.'

        discount = float(promotion_inputs.discount_percent or 0)
        if discount < 0 or discount > 100:
            return 'El descuento debe estar entre 0 y 100.'

        product_ids = [int(pid) for pid in (promotion_inputs.product_ids or []) if pid]
        if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT:
            if promotion_inputs.product_id:
                product_ids = [int(promotion_inputs.product_id)]
            if len(product_ids) != 1:
                return 'Debe seleccionar un producto para el descuento.'

        if promotion_type_id == PROMOTION_TYPE_COUPON:
            coupon_code = (promotion_inputs.coupon_code or '').strip().upper()
            if not coupon_code:
                return 'Debe indicar el código del cupón.'
            if not product_ids:
                return 'Debe seleccionar al menos un producto para el cupón.'
            duplicate = (
                self.db.query(PromotionModel)
                .filter(func.upper(PromotionModel.coupon_code) == coupon_code)
                .filter(PromotionModel.id != (promotion_id or 0))
                .first()
            )
            if duplicate:
                return 'Ya existe un cupón con ese código.'

        return None

    def _replace_products(self, promotion_id, promotion_type_id, discount_percent, product_ids):
        self.db.query(PromotionProductModel).filter(
            PromotionProductModel.promotion_id == promotion_id
        ).delete(synchronize_session=False)

        for product_id in product_ids:
            base_price = self.pricing.get_product_public_price(product_id)
            pricing = self.pricing.calculate_promotional_price(base_price, discount_percent)
            self.db.add(
                PromotionProductModel(
                    promotion_id=promotion_id,
                    product_id=product_id,
                    original_price=pricing['original_price'],
                    promotional_price=pricing['promotional_price'],
                    discount_amount=pricing['discount_amount'],
                    added_date=datetime.utcnow(),
                )
            )

    def store(self, promotion_inputs):
        return self.safe(lambda: self._store_promotion(promotion_inputs), rollback=True)

    def _store_promotion(self, promotion_inputs):
        validation_error = self._validate_inputs(promotion_inputs)
        if validation_error:
            return validation_error

        promotion_type_id = int(promotion_inputs.promotion_type_id)
        product_ids = [int(pid) for pid in (promotion_inputs.product_ids or []) if pid]
        if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT and promotion_inputs.product_id:
            product_ids = [int(promotion_inputs.product_id)]

        coupon_code = None
        if promotion_type_id == PROMOTION_TYPE_COUPON:
            coupon_code = (promotion_inputs.coupon_code or '').strip().upper()

        new_row = PromotionModel(
            promotion_type_id=promotion_type_id,
            product_id=product_ids[0] if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT else None,
            name=promotion_inputs.name.strip(),
            description=(promotion_inputs.description or '').strip() or None,
            discount_percent=promotion_inputs.discount_percent,
            coupon_code=coupon_code,
            minimum_purchase=float(promotion_inputs.minimum_purchase or 0),
            start_date=_parse_optional_date(promotion_inputs.start_date),
            end_date=_parse_optional_date(promotion_inputs.end_date),
            is_active=1 if int(promotion_inputs.is_active or 0) else 0,
            added_date=datetime.utcnow(),
            updated_date=datetime.utcnow(),
        )
        self.db.add(new_row)
        self.db.flush()
        self._replace_products(new_row.id, promotion_type_id, promotion_inputs.discount_percent, product_ids)
        self.db.commit()
        self.db.refresh(new_row)
        return {
            'status': 'Promoción registrada exitosamente.',
            'promotion_id': new_row.id,
        }

    def update(self, id, promotion_inputs):
        existing = self.db.query(PromotionModel).filter(PromotionModel.id == id).one_or_none()
        if not existing:
            return 'No data found'
        return self.safe(lambda: self._update_promotion(existing, promotion_inputs), rollback=True)

    def _update_promotion(self, existing, promotion_inputs):
        validation_error = self._validate_inputs(promotion_inputs, promotion_id=existing.id)
        if validation_error:
            return validation_error

        promotion_type_id = int(promotion_inputs.promotion_type_id)
        product_ids = [int(pid) for pid in (promotion_inputs.product_ids or []) if pid]
        if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT and promotion_inputs.product_id:
            product_ids = [int(promotion_inputs.product_id)]

        existing.promotion_type_id = promotion_type_id
        existing.product_id = product_ids[0] if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT else None
        existing.name = promotion_inputs.name.strip()
        existing.description = (promotion_inputs.description or '').strip() or None
        existing.discount_percent = promotion_inputs.discount_percent
        existing.coupon_code = (
            (promotion_inputs.coupon_code or '').strip().upper()
            if promotion_type_id == PROMOTION_TYPE_COUPON
            else None
        )
        existing.minimum_purchase = float(promotion_inputs.minimum_purchase or 0)
        existing.start_date = _parse_optional_date(promotion_inputs.start_date)
        existing.end_date = _parse_optional_date(promotion_inputs.end_date)
        existing.is_active = 1 if int(promotion_inputs.is_active or 0) else 0
        existing.updated_date = datetime.utcnow()
        self._replace_products(existing.id, promotion_type_id, promotion_inputs.discount_percent, product_ids)
        self.db.commit()
        self.db.refresh(existing)
        return 'Promotion updated successfully'

    def get(self, id):
        return self.safe(
            lambda: self.get_or_error(
                self.db.query(PromotionModel).filter(PromotionModel.id == id).first(),
                data_key='promotion_data',
                serialize=lambda row: {
                    **self._serialize_row(row),
                    'added_date': row.added_date.strftime('%Y-%m-%d %H:%M:%S') if row.added_date else None,
                },
            )
        )

    def delete(self, id):
        self.db.query(PromotionProductModel).filter(PromotionProductModel.promotion_id == id).delete(
            synchronize_session=False
        )
        return self.delete_entity(PromotionModel, id)

    def validate_coupon(self, coupon_code, product_ids, subtotal):
        return self.pricing.validate_coupon(coupon_code, product_ids, subtotal)

    def get_usage_summary(self, promotion_id=None):
        query = self.db.query(
            PromotionUsageModel.promotion_id,
            func.sum(PromotionUsageModel.total_discount_lost).label('total_discount_lost'),
            func.count(PromotionUsageModel.id).label('usage_count'),
        )
        if promotion_id:
            query = query.filter(PromotionUsageModel.promotion_id == promotion_id)
        rows = query.group_by(PromotionUsageModel.promotion_id).all()
        return [
            {
                'promotion_id': row.promotion_id,
                'usage_count': int(row.usage_count or 0),
                'total_discount_lost': float(row.total_discount_lost or 0),
            }
            for row in rows
        ]
