from datetime import datetime
import secrets

from sqlalchemy import func, or_
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.backend.db.models import (
    CustomerModel,
    ProductModel,
    PromotionCustomerModel,
    PromotionModel,
    PromotionProductModel,
    PromotionUsageModel,
)
from app.backend.services.crud.base_domain_service import BaseDomainService
from app.backend.services.promotions.promotion_pricing_service import (
    PROMOTION_AUDIENCE_ALL,
    PROMOTION_AUDIENCE_SELECTED,
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


_COUPON_PREFIX = 'LCV'
_COUPON_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def _build_coupon_code():
    suffix = ''.join(secrets.choice(_COUPON_ALPHABET) for _ in range(6))
    return f'{_COUPON_PREFIX}{suffix}'


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

    def _load_customers(self, promotion_id):
        rows = (
            self.db.query(
                PromotionCustomerModel.customer_id,
                CustomerModel.social_reason,
                CustomerModel.identification_number,
            )
            .join(CustomerModel, CustomerModel.id == PromotionCustomerModel.customer_id, isouter=True)
            .filter(PromotionCustomerModel.promotion_id == promotion_id)
            .all()
        )
        return [
            {
                'customer_id': row.customer_id,
                'social_reason': row.social_reason,
                'identification_number': row.identification_number,
            }
            for row in rows
        ]

    def _serialize_row(self, row):
        start = row.start_date.strftime('%Y-%m-%d') if row.start_date else None
        end = row.end_date.strftime('%Y-%m-%d') if row.end_date else None
        products = self._load_products(row.id)
        total_discount = sum(item['discount_amount'] for item in products)
        audience_type = int(getattr(row, 'audience_type', PROMOTION_AUDIENCE_ALL) or PROMOTION_AUDIENCE_ALL)
        customers = self._load_customers(row.id) if int(row.promotion_type_id or 0) == PROMOTION_TYPE_COUPON else []
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
            'status_id': int(row.status_id if row.status_id is not None else 1),
            'audience_type': audience_type,
            'customers': customers,
            'customer_ids': [int(item['customer_id']) for item in customers if item.get('customer_id')],
            'products': products,
            'total_discount_per_unit': round(total_discount, 2),
        }

    def get_all(
        self,
        page=0,
        items_per_page=10,
        q=None,
        promotion_type_id=None,
        status_id=None,
    ):
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
                PromotionModel.status_id,
                PromotionModel.audience_type,
            )
            .order_by(PromotionModel.id.desc())
        )

        if q and str(q).strip():
            term = f"%{str(q).strip()}%"
            product_promotion_ids = (
                self.db.query(PromotionProductModel.promotion_id)
                .join(ProductModel, ProductModel.id == PromotionProductModel.product_id)
                .filter(or_(ProductModel.product.ilike(term), ProductModel.code.ilike(term)))
            )
            query = query.filter(
                or_(
                    PromotionModel.name.ilike(term),
                    PromotionModel.description.ilike(term),
                    PromotionModel.coupon_code.ilike(term),
                    PromotionModel.id.in_(product_promotion_ids),
                )
            )

        if promotion_type_id is not None and int(promotion_type_id) > 0:
            query = query.filter(PromotionModel.promotion_type_id == int(promotion_type_id))

        if status_id is not None and int(status_id) >= 0:
            query = query.filter(PromotionModel.status_id == int(status_id))

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
                PromotionModel.status_id,
            )
            .filter(PromotionModel.status_id == 1)
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
            minimum = float(promotion_inputs.minimum_purchase or 0)
            if minimum <= 0:
                return 'Los cupones deben tener una compra mínima mayor a 0.'
            duplicate = (
                self.db.query(PromotionModel)
                .filter(func.upper(PromotionModel.coupon_code) == coupon_code)
                .filter(PromotionModel.id != (promotion_id or 0))
                .first()
            )
            if duplicate:
                return 'Ya existe un cupón con ese código.'
            audience_type = int(getattr(promotion_inputs, 'audience_type', PROMOTION_AUDIENCE_ALL) or PROMOTION_AUDIENCE_ALL)
            if audience_type not in (PROMOTION_AUDIENCE_ALL, PROMOTION_AUDIENCE_SELECTED):
                return 'Tipo de audiencia no válido.'
            customer_ids = [int(cid) for cid in (promotion_inputs.customer_ids or []) if cid]
            if audience_type == PROMOTION_AUDIENCE_SELECTED and not customer_ids:
                return 'Debe seleccionar al menos un cliente para el cupón.'

        return None

    def _replace_customers(self, promotion_id, audience_type, customer_ids):
        self.db.query(PromotionCustomerModel).filter(
            PromotionCustomerModel.promotion_id == promotion_id
        ).delete(synchronize_session=False)
        if int(audience_type or PROMOTION_AUDIENCE_ALL) != PROMOTION_AUDIENCE_SELECTED:
            return
        for customer_id in customer_ids:
            self.db.add(
                PromotionCustomerModel(
                    promotion_id=promotion_id,
                    customer_id=int(customer_id),
                    added_date=datetime.utcnow(),
                )
            )

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
        audience_type = PROMOTION_AUDIENCE_ALL
        customer_ids = []
        if promotion_type_id == PROMOTION_TYPE_COUPON:
            coupon_code = (promotion_inputs.coupon_code or '').strip().upper()
            audience_type = int(getattr(promotion_inputs, 'audience_type', PROMOTION_AUDIENCE_ALL) or PROMOTION_AUDIENCE_ALL)
            customer_ids = [int(cid) for cid in (promotion_inputs.customer_ids or []) if cid]

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
            status_id=1 if int(promotion_inputs.status_id or 0) == 1 else 0,
            audience_type=audience_type,
            added_date=datetime.utcnow(),
            updated_date=datetime.utcnow(),
        )
        self.db.add(new_row)
        self.db.flush()
        if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT:
            self._replace_products(new_row.id, promotion_type_id, promotion_inputs.discount_percent, product_ids)
            self._replace_customers(new_row.id, PROMOTION_AUDIENCE_ALL, [])
        else:
            self._replace_products(new_row.id, promotion_type_id, promotion_inputs.discount_percent, [])
            self._replace_customers(new_row.id, audience_type, customer_ids)
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

        existing_type = int(existing.promotion_type_id or PROMOTION_TYPE_PRODUCT_DISCOUNT)
        requested_type = int(promotion_inputs.promotion_type_id or existing_type)
        if requested_type != existing_type:
            return 'No se puede cambiar el tipo de promoción al editar.'

        promotion_type_id = existing_type
        product_ids = [int(pid) for pid in (promotion_inputs.product_ids or []) if pid]
        if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT and promotion_inputs.product_id:
            product_ids = [int(promotion_inputs.product_id)]

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
        existing.status_id = 1 if int(promotion_inputs.status_id or 0) == 1 else 0
        audience_type = int(getattr(promotion_inputs, 'audience_type', PROMOTION_AUDIENCE_ALL) or PROMOTION_AUDIENCE_ALL)
        customer_ids = [int(cid) for cid in (promotion_inputs.customer_ids or []) if cid]
        if promotion_type_id == PROMOTION_TYPE_COUPON:
            existing.audience_type = audience_type
        else:
            existing.audience_type = PROMOTION_AUDIENCE_ALL
        existing.updated_date = datetime.utcnow()
        if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT:
            self._replace_products(existing.id, promotion_type_id, promotion_inputs.discount_percent, product_ids)
            self._replace_customers(existing.id, PROMOTION_AUDIENCE_ALL, [])
        else:
            self._replace_products(existing.id, promotion_type_id, promotion_inputs.discount_percent, [])
            self._replace_customers(existing.id, audience_type, customer_ids)
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
        self.db.query(PromotionCustomerModel).filter(PromotionCustomerModel.promotion_id == id).delete(
            synchronize_session=False
        )
        self.db.query(PromotionProductModel).filter(PromotionProductModel.promotion_id == id).delete(
            synchronize_session=False
        )
        return self.delete_entity(PromotionModel, id)

    def validate_coupon(self, coupon_code, product_ids, subtotal, items=None, customer_rut=None):
        return self.pricing.validate_coupon(
            coupon_code, product_ids, subtotal, items=items, customer_rut=customer_rut
        )

    def get_visible_coupons(self, customer_rut=None):
        coupons = self.pricing.get_visible_coupon_banners(customer_rut)
        return {'status': 'success', 'data': coupons}

    def generate_coupon_code(self):
        for _ in range(25):
            code = _build_coupon_code()
            duplicate = (
                self.db.query(PromotionModel.id)
                .filter(func.upper(PromotionModel.coupon_code) == code)
                .first()
            )
            if not duplicate:
                return {'status': 'success', 'coupon_code': code}
        return {'status': 'error', 'message': 'No se pudo generar un código único.'}

    def get_usage_summary(self, promotion_id=None):
        if not promotion_id:
            query = self.db.query(
                PromotionUsageModel.promotion_id,
                func.sum(PromotionUsageModel.total_discount_lost).label('total_discount_lost'),
                func.count(PromotionUsageModel.id).label('usage_count'),
            )
            rows = query.group_by(PromotionUsageModel.promotion_id).all()
            return [
                {
                    'promotion_id': row.promotion_id,
                    'usage_count': int(row.usage_count or 0),
                    'total_discount_lost': float(row.total_discount_lost or 0),
                }
                for row in rows
            ]

        promotion = (
            self.db.query(PromotionModel).filter(PromotionModel.id == int(promotion_id)).first()
        )
        if not promotion:
            return {'status': 'error', 'message': 'Promoción no encontrada.'}

        usages = (
            self.db.query(PromotionUsageModel)
            .filter(PromotionUsageModel.promotion_id == int(promotion_id))
            .all()
        )

        total_original = 0.0
        total_paid = 0.0
        total_discount = 0.0
        for usage in usages:
            quantity = max(int(usage.quantity or 1), 1)
            original_unit = float(usage.original_unit_price or 0)
            promotional_unit = float(usage.promotional_unit_price or 0)
            line_discount = float(usage.total_discount_lost or 0)
            if line_discount <= 0 and original_unit > promotional_unit:
                line_discount = (original_unit - promotional_unit) * quantity
            total_original += original_unit * quantity
            total_paid += promotional_unit * quantity
            total_discount += line_discount

        total_original = round(total_original, 2)
        total_paid = round(total_paid, 2)
        total_discount = round(total_discount, 2)
        effective_percent = (
            round((total_discount / total_original) * 100, 2) if total_original > 0 else 0.0
        )

        return {
            'status': 'success',
            'data': {
                'promotion_id': promotion.id,
                'promotion_name': promotion.name,
                'promotion_type_id': int(promotion.promotion_type_id or 0),
                'coupon_code': promotion.coupon_code,
                'usage_count': len(usages),
                'total_original_amount': total_original,
                'total_paid_amount': total_paid,
                'total_discount_amount': total_discount,
                'effective_discount_percent': effective_percent,
                'configured_discount_percent': int(round(float(promotion.discount_percent or 0))),
            },
        }
