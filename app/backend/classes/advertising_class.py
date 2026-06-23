import re
import threading
import time
from datetime import datetime

from sqlalchemy import or_

from app.backend.classes.file_class import FileClass
from app.backend.classes.promotion_class import PromotionClass
from app.backend.classes.whatsapp_class import WhatsappClass
from app.backend.db.models import (
    AdvertisingCampaignCustomerModel,
    AdvertisingCampaignModel,
    CustomerModel,
    PromotionModel,
    PromotionProductModel,
    WhatsAppMessageModel,
)
from app.backend.services.crud.base_domain_service import BaseDomainService
from app.backend.services.promotions.promotion_pricing_service import (
    PROMOTION_AUDIENCE_SELECTED,
    PROMOTION_TYPE_COUPON,
    PROMOTION_TYPE_PRODUCT_DISCOUNT,
)

AUDIENCE_ALL = 1
AUDIENCE_SELECTED = 2
STATUS_DRAFT = 0
STATUS_SENT = 1

CAMPAIGN_DELIVERY_WAIT_SECONDS = 15.0
CAMPAIGN_DELIVERY_POLL_SECONDS = 0.5
CAMPAIGN_DELIVERY_SUCCESS_STATUSES = frozenset({'delivered', 'read'})


def _has_valid_phone(phone: str | None) -> bool:
    if not phone or not str(phone).strip():
        return False
    digits = re.sub(r'\D', '', str(phone))
    return len(digits) >= 8


def _format_clp(value: float) -> str:
    return f"${int(round(float(value or 0))):,}".replace(',', '.')


def _format_whatsapp_date(value) -> str | None:
    """Fecha para mensajes WhatsApp: dd-mm-YYYY."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime('%d-%m-%Y')
    text = str(value).strip()
    if not text:
        return None
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text[:10], fmt).strftime('%d-%m-%Y')
        except ValueError:
            continue
    return text

class AdvertisingClass(BaseDomainService):
    AUDIENCE_LABELS = {
        AUDIENCE_ALL: 'Todos los clientes',
        AUDIENCE_SELECTED: 'Clientes seleccionados',
    }

    STATUS_LABELS = {
        STATUS_DRAFT: 'Borrador',
        STATUS_SENT: 'Enviada',
    }

    _send_jobs: dict[int, dict] = {}
    _send_jobs_lock = threading.Lock()

    @classmethod
    def _set_job(cls, campaign_id: int, data: dict) -> None:
        with cls._send_jobs_lock:
            cls._send_jobs[int(campaign_id)] = data

    @classmethod
    def _get_job(cls, campaign_id: int) -> dict | None:
        with cls._send_jobs_lock:
            job = cls._send_jobs.get(int(campaign_id))
            return dict(job) if job else None

    @classmethod
    def _update_job(cls, campaign_id: int, **kwargs) -> None:
        with cls._send_jobs_lock:
            job = cls._send_jobs.get(int(campaign_id))
            if job is not None:
                job.update(kwargs)

    @classmethod
    def _clear_job(cls, campaign_id: int) -> None:
        with cls._send_jobs_lock:
            cls._send_jobs.pop(int(campaign_id), None)

    def _wait_for_whatsapp_delivery_status(
        self,
        message_ids: list[str],
        timeout_seconds: float = CAMPAIGN_DELIVERY_WAIT_SECONDS,
    ) -> dict[str, dict]:
        """Espera webhooks de Meta (sent/delivered/failed) antes de contar éxitos."""
        unique_ids = [str(mid).strip() for mid in message_ids if str(mid or '').strip()]
        if not unique_ids:
            return {}

        deadline = time.time() + timeout_seconds
        pending = set(unique_ids)
        resolved: dict[str, dict] = {}

        while pending and time.time() < deadline:
            rows = (
                self.db.query(WhatsAppMessageModel)
                .filter(WhatsAppMessageModel.message_id.in_(list(pending)))
                .all()
            )
            for row in rows:
                status = str(row.status or 'sent').strip().lower()
                if status in CAMPAIGN_DELIVERY_SUCCESS_STATUSES or status == 'failed':
                    resolved[row.message_id] = {
                        'status': status,
                        'error_code': row.error_code,
                        'error_message': row.error_message,
                    }
                    pending.discard(row.message_id)
            if pending:
                time.sleep(CAMPAIGN_DELIVERY_POLL_SECONDS)

        if pending:
            rows = (
                self.db.query(WhatsAppMessageModel)
                .filter(WhatsAppMessageModel.message_id.in_(list(pending)))
                .all()
            )
            found = {row.message_id: row for row in rows}
            for message_id in pending:
                row = found.get(message_id)
                resolved[message_id] = {
                    'status': str(row.status or 'sent').strip().lower() if row else 'unknown',
                    'error_code': row.error_code if row else None,
                    'error_message': row.error_message if row else None,
                }

        return resolved

    @staticmethod
    def _delivery_failure_detail(customer_label: str, delivery_info: dict) -> str:
        error_code = delivery_info.get('error_code')
        error_message = (delivery_info.get('error_message') or '').strip()
        status = str(delivery_info.get('status') or '').strip().lower()

        if error_message:
            if error_code:
                return f'{customer_label}: [{error_code}] {error_message}'
            return f'{customer_label}: {error_message}'
        if status == 'sent':
            return (
                f'{customer_label}: Meta aceptó el mensaje pero no confirmó la entrega '
                f'(puede haber sido bloqueado por WhatsApp).'
            )
        return f'{customer_label}: WhatsApp/Meta no entregó el mensaje.'

    def _build_campaign_send_summary(
        self,
        sent_count: int,
        failed_count: int,
        failure_details: list[str],
    ) -> tuple[str, str | None]:
        if failed_count > 0 and sent_count == 0:
            message = f'No se entregó ningún mensaje. Fallidos: {failed_count}.'
            error = '\n'.join(failure_details[:5]) if failure_details else message
            return message, error

        if failed_count > 0:
            message = (
                f'Campaña finalizada con errores. '
                f'Entregados: {sent_count}, fallidos: {failed_count}.'
            )
            error = '\n'.join(failure_details[:5])
            if len(failure_details) > 5:
                error += f'\n… y {len(failure_details) - 5} error(es) más.'
            return message, error

        return f'Campaña enviada correctamente. Entregados: {sent_count}.', None

    def _get_active_promotion(self, promotion_id: int):
        promotion = (
            self.db.query(PromotionModel)
            .filter(PromotionModel.id == int(promotion_id))
            .first()
        )
        if not promotion:
            return None, 'Promoción no encontrada.'
        if int(promotion.status_id or 0) != 1:
            return None, 'La promoción seleccionada no está activa.'
        return promotion, None

    def _resolve_campaign_product_id(self, promotion_id: int | None) -> int | None:
        if not promotion_id:
            return None
        promotion, error = self._get_active_promotion(int(promotion_id))
        if error or not promotion:
            return None
        if int(promotion.promotion_type_id or 0) != PROMOTION_TYPE_PRODUCT_DISCOUNT:
            return None
        if promotion.product_id:
            return int(promotion.product_id)

        linked_product = (
            self.db.query(PromotionProductModel.product_id)
            .filter(PromotionProductModel.promotion_id == int(promotion_id))
            .order_by(PromotionProductModel.id.asc())
            .first()
        )
        if linked_product and linked_product.product_id:
            return int(linked_product.product_id)
        return None

    def build_promotion_whatsapp_message(self, promotion_id: int, extra_message: str | None = None) -> str:
        promotion, error = self._get_active_promotion(promotion_id)
        if error or not promotion:
            return ''

        promo_data = PromotionClass(self.db)._serialize_row(promotion)
        promotion_type_id = int(promo_data.get('promotion_type_id') or 0)
        discount_percent = int(round(float(promo_data.get('discount_percent') or 0)))
        lines = [f"🎉 *{promo_data.get('name', 'Promoción')}*"]

        description = (promo_data.get('description') or '').strip()
        if description:
            lines.append(description)

        if promotion_type_id == PROMOTION_TYPE_COUPON:
            coupon_code = (promo_data.get('coupon_code') or '').strip()
            if coupon_code:
                lines.append(f"🏷️ Cupón: *{coupon_code}*")
            lines.append(f"💰 Descuento: *{discount_percent}%*")
            minimum = float(promo_data.get('minimum_purchase') or 0)
            if minimum > 0:
                lines.append(f"🛒 Compra mínima: {_format_clp(minimum)}")
        else:
            products = promo_data.get('products') or []
            product_name = 'Producto'
            if products:
                product_name = products[0].get('product_name') or f"Producto #{products[0].get('product_id')}"
            lines = [
                '🥳 ¡Nueva promoción! 🎉',
                f'📦 *Producto:* {product_name}',
                f'💰 *Descuento:* {discount_percent}%',
            ]
            start_date = _format_whatsapp_date(promo_data.get('start_date'))
            end_date = _format_whatsapp_date(promo_data.get('end_date'))
            if start_date or end_date:
                lines.append(f'🗓️ *Vigencia:* {start_date or "—"} al {end_date or "—"}')
            else:
                lines.append('🗓️ *Vigencia:* —')
            lines.append('')
            lines.append('Toca el botón *Ir a la promoción*.')
            extra = (extra_message or '').strip()
            if extra:
                lines.append('')
                lines.append(extra)
            return '\n'.join(lines)

        start_date = _format_whatsapp_date(promo_data.get('start_date'))
        end_date = _format_whatsapp_date(promo_data.get('end_date'))
        if start_date or end_date:
            lines.append(f"📅 Vigencia: {start_date or '—'} al {end_date or '—'}")

        lines.append('')
        lines.append('Toca el botón *Ir a la promoción* para ver la tienda.')

        extra = (extra_message or '').strip()
        if extra:
            lines.append('')
            lines.append(extra)

        return '\n'.join(lines)

    def get_product_discount_template_body_params(self, promotion_id: int) -> list[str] | None:
        promotion, error = self._get_active_promotion(int(promotion_id))
        if error or not promotion:
            return None
        if int(promotion.promotion_type_id or 0) != PROMOTION_TYPE_PRODUCT_DISCOUNT:
            return None

        promo_data = PromotionClass(self.db)._serialize_row(promotion)
        products = promo_data.get('products') or []
        product_name = 'Producto'
        if products:
            product_name = products[0].get('product_name') or f"Producto #{products[0].get('product_id')}"

        discount_percent = int(round(float(promo_data.get('discount_percent') or 0)))
        start_date = _format_whatsapp_date(promo_data.get('start_date'))
        end_date = _format_whatsapp_date(promo_data.get('end_date'))
        if start_date or end_date:
            validity = f'{start_date or "—"} al {end_date or "—"}'
        else:
            validity = '—'

        whatsapp = WhatsappClass(self.db)
        return [
            whatsapp._clean_text_for_whatsapp(str(product_name))[:1024],
            whatsapp._clean_text_for_whatsapp(f'{discount_percent}%')[:1024],
            whatsapp._clean_text_for_whatsapp(validity)[:1024],
        ]

    def build_campaign_whatsapp_message(
        self,
        promotion_id: int | None,
        message: str | None = None,
    ) -> str:
        if promotion_id:
            return self.build_promotion_whatsapp_message(int(promotion_id), message)

        body = (message or '').strip()
        if not body:
            return ''

        lines = [body, '', 'Toca el botón *Ir a la promoción* para ver la tienda.']
        return '\n'.join(lines)

    def get_message_preview(self, message: str | None = None):
        whatsapp_message = self.build_campaign_whatsapp_message(None, message)
        if not whatsapp_message.strip():
            return 'Debe escribir el mensaje de WhatsApp.'
        return {
            'status': 'success',
            'data': {
                'whatsapp_message': whatsapp_message,
                'site_button_label': WhatsappClass.CAMPAIGN_SITE_BUTTON_LABEL,
                'site_url': WhatsappClass.get_campaign_site_url(),
            },
        }

    def get_promotion_preview(self, promotion_id: int, extra_message: str | None = None):
        promotion, error = self._get_active_promotion(promotion_id)
        if error:
            return error

        promo_data = PromotionClass(self.db)._serialize_row(promotion)
        audience_type = int(promo_data.get('audience_type') or AUDIENCE_ALL)
        customers = promo_data.get('customers') or []
        product_id = self._resolve_campaign_product_id(int(promotion_id))
        site_url = WhatsappClass.get_campaign_site_url()

        return {
            'status': 'success',
            'data': {
                'promotion_id': int(promotion_id),
                'promotion_name': promo_data.get('name'),
                'promotion_type_label': promo_data.get('promotion_type_label'),
                'product_id': product_id,
                'whatsapp_message': self.build_promotion_whatsapp_message(promotion_id, extra_message),
                'site_button_label': WhatsappClass.CAMPAIGN_SITE_BUTTON_LABEL,
                'site_url': site_url,
                'suggested_audience_type': (
                    AUDIENCE_SELECTED
                    if audience_type == PROMOTION_AUDIENCE_SELECTED and customers
                    else AUDIENCE_ALL
                ),
                'suggested_customers': customers,
            },
        }

    def _load_customers(self, campaign_id: int) -> list[dict]:
        rows = (
            self.db.query(
                AdvertisingCampaignCustomerModel.customer_id,
                CustomerModel.social_reason,
                CustomerModel.identification_number,
                CustomerModel.phone,
            )
            .join(CustomerModel, CustomerModel.id == AdvertisingCampaignCustomerModel.customer_id)
            .filter(AdvertisingCampaignCustomerModel.campaign_id == campaign_id)
            .all()
        )
        return [
            {
                'customer_id': int(row.customer_id),
                'social_reason': row.social_reason,
                'identification_number': row.identification_number,
                'phone': row.phone,
            }
            for row in rows
        ]

    def _serialize_row(self, row) -> dict:
        audience_type = int(getattr(row, 'audience_type', AUDIENCE_ALL) or AUDIENCE_ALL)
        customers = self._load_customers(row.id) if audience_type == AUDIENCE_SELECTED else []
        image_path = getattr(row, 'image_path', None)
        image_url = FileClass(self.db).get(image_path) if image_path else None
        promotion_id = getattr(row, 'promotion_id', None)
        promotion_name = None
        promotion_type_label = None
        if promotion_id:
            promotion = (
                self.db.query(PromotionModel)
                .filter(PromotionModel.id == int(promotion_id))
                .first()
            )
            if promotion:
                promotion_name = promotion.name
                promotion_type_label = PromotionClass(self.db)._type_label(promotion.promotion_type_id)

        whatsapp_preview = self.build_campaign_whatsapp_message(
            int(promotion_id) if promotion_id else None,
            getattr(row, 'message', None),
        )

        return {
            'id': row.id,
            'name': row.name,
            'promotion_id': int(promotion_id) if promotion_id else None,
            'promotion_name': promotion_name or ('Mensaje personalizado' if not promotion_id else None),
            'promotion_type_label': promotion_type_label,
            'message': row.message,
            'whatsapp_message': whatsapp_preview,
            'site_button_label': WhatsappClass.CAMPAIGN_SITE_BUTTON_LABEL,
            'site_url': WhatsappClass.get_campaign_site_url(),
            'image_path': image_path,
            'image_url': image_url,
            'audience_type': audience_type,
            'audience_label': self.AUDIENCE_LABELS.get(audience_type, 'Desconocido'),
            'status_id': int(row.status_id or STATUS_DRAFT),
            'status_label': self.STATUS_LABELS.get(int(row.status_id or STATUS_DRAFT), 'Desconocido'),
            'sent_count': int(row.sent_count or 0),
            'failed_count': int(row.failed_count or 0),
            'customers': customers,
            'customer_ids': [int(item['customer_id']) for item in customers if item.get('customer_id')],
            'added_date': row.added_date.strftime('%Y-%m-%d %H:%M:%S') if row.added_date else None,
            'sent_date': row.sent_date.strftime('%Y-%m-%d %H:%M:%S') if row.sent_date else None,
        }

    def get_all(self, page=0, items_per_page=10, q=None, status_id=None):
        query = self.db.query(AdvertisingCampaignModel).order_by(AdvertisingCampaignModel.id.desc())
        if q and str(q).strip():
            term = f"%{str(q).strip()}%"
            promotion_ids = (
                self.db.query(PromotionModel.id)
                .filter(PromotionModel.name.ilike(term))
            )
            query = query.filter(
                or_(
                    AdvertisingCampaignModel.name.ilike(term),
                    AdvertisingCampaignModel.message.ilike(term),
                    AdvertisingCampaignModel.promotion_id.in_(promotion_ids),
                )
            )
        if status_id is not None and int(status_id) >= 0:
            query = query.filter(AdvertisingCampaignModel.status_id == int(status_id))
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get(self, campaign_id: int):
        row = (
            self.db.query(AdvertisingCampaignModel)
            .filter(AdvertisingCampaignModel.id == int(campaign_id))
            .first()
        )
        return self.safe(
            lambda: self.get_or_error(
                row,
                data_key='campaign_data',
                serialize=self._serialize_row,
            )
        )

    def _validate_inputs(self, inputs, campaign_id: int | None = None):
        name = (inputs.name or '').strip()
        if not name:
            return 'Debe indicar el nombre de la campaña.'

        promotion_id = getattr(inputs, 'promotion_id', None)
        promotion_id = int(promotion_id) if promotion_id else None
        message = (getattr(inputs, 'message', None) or '').strip()

        if promotion_id:
            _, promotion_error = self._get_active_promotion(promotion_id)
            if promotion_error:
                return promotion_error
        elif not message:
            return 'Debe escribir el mensaje de WhatsApp o seleccionar una promoción.'

        audience_type = int(getattr(inputs, 'audience_type', AUDIENCE_ALL) or AUDIENCE_ALL)
        customer_ids = [int(cid) for cid in (getattr(inputs, 'customer_ids', None) or []) if cid]
        if audience_type == AUDIENCE_SELECTED and not customer_ids:
            return 'Debe seleccionar al menos un cliente.'
        if campaign_id:
            existing = (
                self.db.query(AdvertisingCampaignModel)
                .filter(AdvertisingCampaignModel.id == int(campaign_id))
                .first()
            )
            if existing and int(existing.status_id or STATUS_DRAFT) == STATUS_SENT:
                return 'No se puede editar una campaña ya enviada.'
        return None

    def _replace_customers(self, campaign_id: int, audience_type: int, customer_ids: list[int]):
        self.db.query(AdvertisingCampaignCustomerModel).filter(
            AdvertisingCampaignCustomerModel.campaign_id == campaign_id
        ).delete(synchronize_session=False)
        if int(audience_type or AUDIENCE_ALL) != AUDIENCE_SELECTED:
            return
        for customer_id in customer_ids:
            self.db.add(
                AdvertisingCampaignCustomerModel(
                    campaign_id=campaign_id,
                    customer_id=int(customer_id),
                    added_date=datetime.utcnow(),
                )
            )

    def store(self, inputs, image_path: str | None = None):
        return self.safe(lambda: self._store_campaign(inputs, image_path), rollback=True)

    def _store_campaign(self, inputs, image_path: str | None = None):
        validation_error = self._validate_inputs(inputs)
        if validation_error:
            return validation_error

        audience_type = int(getattr(inputs, 'audience_type', AUDIENCE_ALL) or AUDIENCE_ALL)
        customer_ids = [int(cid) for cid in (getattr(inputs, 'customer_ids', None) or []) if cid]
        promotion_id = getattr(inputs, 'promotion_id', None)
        promotion_id = int(promotion_id) if promotion_id else None
        extra_message = (getattr(inputs, 'message', None) or '').strip()

        row = AdvertisingCampaignModel(
            name=inputs.name.strip(),
            promotion_id=promotion_id,
            message=extra_message,
            image_path=image_path,
            audience_type=audience_type,
            status_id=STATUS_DRAFT,
            sent_count=0,
            failed_count=0,
            added_date=datetime.utcnow(),
            updated_date=datetime.utcnow(),
        )
        self.db.add(row)
        self.db.flush()
        self._replace_customers(row.id, audience_type, customer_ids)
        self.db.commit()
        self.db.refresh(row)
        return {
            'status': 'Campaña registrada exitosamente.',
            'campaign_id': row.id,
        }

    def update(self, campaign_id: int, inputs, image_path: str | None = None, remove_image: bool = False):
        existing = (
            self.db.query(AdvertisingCampaignModel)
            .filter(AdvertisingCampaignModel.id == int(campaign_id))
            .first()
        )
        if not existing:
            return 'No data found'
        return self.safe(
            lambda: self._update_campaign(existing, inputs, image_path, remove_image),
            rollback=True,
        )

    def _update_campaign(self, existing, inputs, image_path: str | None, remove_image: bool):
        validation_error = self._validate_inputs(inputs, campaign_id=existing.id)
        if validation_error:
            return validation_error

        audience_type = int(getattr(inputs, 'audience_type', AUDIENCE_ALL) or AUDIENCE_ALL)
        customer_ids = [int(cid) for cid in (getattr(inputs, 'customer_ids', None) or []) if cid]

        existing.name = inputs.name.strip()
        promotion_id = getattr(inputs, 'promotion_id', None)
        existing.promotion_id = int(promotion_id) if promotion_id else None
        existing.message = (getattr(inputs, 'message', None) or '').strip()
        existing.audience_type = audience_type
        existing.updated_date = datetime.utcnow()

        if image_path:
            if existing.image_path and existing.image_path != image_path:
                try:
                    FileClass(self.db).delete(existing.image_path)
                except Exception:
                    pass
            existing.image_path = image_path
        elif remove_image and existing.image_path:
            try:
                FileClass(self.db).delete(existing.image_path)
            except Exception:
                pass
            existing.image_path = None

        self._replace_customers(existing.id, audience_type, customer_ids)
        self.db.commit()
        self.db.refresh(existing)
        return 'Campaign updated successfully'

    def delete(self, campaign_id: int):
        row = (
            self.db.query(AdvertisingCampaignModel)
            .filter(AdvertisingCampaignModel.id == int(campaign_id))
            .first()
        )
        if not row:
            return 'No data found'
        if row.image_path:
            try:
                FileClass(self.db).delete(row.image_path)
            except Exception:
                pass
        self.db.query(AdvertisingCampaignCustomerModel).filter(
            AdvertisingCampaignCustomerModel.campaign_id == int(campaign_id)
        ).delete(synchronize_session=False)
        return self.delete_entity(AdvertisingCampaignModel, int(campaign_id))

    def _resolve_recipients(self, campaign: AdvertisingCampaignModel) -> list[CustomerModel]:
        audience_type = int(campaign.audience_type or AUDIENCE_ALL)
        if audience_type == AUDIENCE_SELECTED:
            rows = (
                self.db.query(CustomerModel)
                .join(
                    AdvertisingCampaignCustomerModel,
                    AdvertisingCampaignCustomerModel.customer_id == CustomerModel.id,
                )
                .filter(AdvertisingCampaignCustomerModel.campaign_id == campaign.id)
                .all()
            )
        else:
            rows = self.db.query(CustomerModel).all()

        seen_phones: set[str] = set()
        recipients: list[CustomerModel] = []
        whatsapp = WhatsappClass(self.db)
        for customer in rows:
            if not _has_valid_phone(customer.phone):
                continue
            normalized = whatsapp._clean_phone_number(customer.phone)
            if not normalized or normalized in seen_phones:
                continue
            seen_phones.add(normalized)
            recipients.append(customer)
        return recipients

    def send(self, campaign_id: int):
        return self.start_send(campaign_id)

    def start_send(self, campaign_id: int):
        return self.safe(lambda: self._start_send_campaign(int(campaign_id)), rollback=False)

    def _start_send_campaign(self, campaign_id: int):
        campaign = (
            self.db.query(AdvertisingCampaignModel)
            .filter(AdvertisingCampaignModel.id == campaign_id)
            .first()
        )
        if not campaign:
            return 'No data found'
        if int(campaign.status_id or STATUS_DRAFT) == STATUS_SENT:
            return 'La campaña ya fue enviada.'

        promotion_id = int(campaign.promotion_id) if campaign.promotion_id else None
        if promotion_id:
            _, promotion_error = self._get_active_promotion(promotion_id)
            if promotion_error:
                return promotion_error

        recipients = self._resolve_recipients(campaign)
        if not recipients:
            return 'No hay clientes con teléfono válido para enviar la campaña.'

        whatsapp_message = self.build_campaign_whatsapp_message(
            promotion_id,
            campaign.message,
        )
        if not whatsapp_message.strip():
            return 'No se pudo generar el mensaje de la campaña.'

        existing_job = self._get_job(campaign_id)
        if existing_job and not existing_job.get('done'):
            return {
                'status': 'started',
                'message': 'El envío ya está en curso.',
                'campaign_id': campaign_id,
                'total': int(existing_job.get('total') or 0),
            }

        total = len(recipients)
        self._set_job(
            campaign_id,
            {
                'campaign_id': campaign_id,
                'campaign_name': campaign.name,
                'total': total,
                'processed': 0,
                'sent_count': 0,
                'failed_count': 0,
                'done': False,
                'error': None,
                'current_customer': None,
            },
        )

        thread = threading.Thread(
            target=self._send_campaign_worker,
            args=(campaign_id,),
            daemon=True,
        )
        thread.start()
        return {
            'status': 'started',
            'message': 'Envío iniciado.',
            'campaign_id': campaign_id,
            'total': total,
        }

    @staticmethod
    def _send_campaign_worker(campaign_id: int) -> None:
        from app.backend.db.database import SessionLocal

        db = SessionLocal()
        try:
            AdvertisingClass(db)._send_campaign_with_progress(campaign_id)
        except Exception as exc:
            AdvertisingClass._update_job(campaign_id, done=True, error=str(exc))
            print(f"[ADVERTISING SEND] Error en campaña {campaign_id}: {exc}")
        finally:
            db.close()

    def _send_campaign_with_progress(self, campaign_id: int) -> None:
        campaign = (
            self.db.query(AdvertisingCampaignModel)
            .filter(AdvertisingCampaignModel.id == campaign_id)
            .first()
        )
        if not campaign:
            self._update_job(campaign_id, done=True, error='Campaña no encontrada.')
            return

        recipients = self._resolve_recipients(campaign)
        promotion_id = int(campaign.promotion_id) if campaign.promotion_id else None
        whatsapp_message = self.build_campaign_whatsapp_message(
            promotion_id,
            campaign.message,
        )
        image_url = None
        if campaign.image_path:
            image_url = FileClass(self.db).get(campaign.image_path)

        whatsapp = WhatsappClass(self.db)
        sent_count = 0
        failed_count = 0
        failure_details: list[str] = []
        pending_deliveries: list[dict] = []
        campaign_product_id = self._resolve_campaign_product_id(promotion_id)
        promotion_type_id = None
        template_body_params = None
        if promotion_id:
            promotion_row, _ = self._get_active_promotion(int(promotion_id))
            if promotion_row:
                promotion_type_id = int(promotion_row.promotion_type_id or 0)
            if promotion_type_id == PROMOTION_TYPE_PRODUCT_DISCOUNT:
                template_body_params = self.get_product_discount_template_body_params(int(promotion_id))

        for index, customer in enumerate(recipients, start=1):
            customer_label = customer.social_reason or customer.identification_number or f'Cliente #{customer.id}'
            self._update_job(
                campaign_id,
                processed=index - 1,
                current_customer=customer_label,
            )

            result = whatsapp.send_campaign_message(
                customer.phone,
                whatsapp_message,
                image_url=image_url,
                site_url=whatsapp.build_campaign_site_url_for_customer(
                    customer.id,
                    customer.phone,
                    product_id=campaign_product_id,
                ),
                promotion_type_id=promotion_type_id,
                template_body_params=template_body_params,
            )
            message_id = str(result.get('message_id') or '').strip()
            if message_id:
                pending_deliveries.append(
                    {
                        'message_id': message_id,
                        'customer_label': customer_label,
                    }
                )
            else:
                failed_count += 1
                api_error = str(result.get('error') or 'Error al enviar por WhatsApp.').strip()
                failure_details.append(f'{customer_label}: {api_error}')

            self._update_job(
                campaign_id,
                processed=index,
                sent_count=sent_count,
                failed_count=failed_count,
                current_customer=customer_label,
            )
            time.sleep(0.35)

        if pending_deliveries:
            self._update_job(
                campaign_id,
                current_customer='Verificando entrega con Meta…',
            )
            delivery_status = self._wait_for_whatsapp_delivery_status(
                [item['message_id'] for item in pending_deliveries]
            )
            for item in pending_deliveries:
                info = delivery_status.get(item['message_id'], {'status': 'unknown'})
                status = str(info.get('status') or 'unknown').strip().lower()
                if status in CAMPAIGN_DELIVERY_SUCCESS_STATUSES:
                    sent_count += 1
                else:
                    failed_count += 1
                    failure_details.append(
                        self._delivery_failure_detail(item['customer_label'], info)
                    )

        summary_message, summary_error = self._build_campaign_send_summary(
            sent_count,
            failed_count,
            failure_details,
        )

        campaign.status_id = STATUS_SENT
        campaign.sent_count = sent_count
        campaign.failed_count = failed_count
        campaign.sent_date = datetime.utcnow()
        campaign.updated_date = datetime.utcnow()
        self.db.commit()

        self._update_job(
            campaign_id,
            processed=len(recipients),
            sent_count=sent_count,
            failed_count=failed_count,
            done=True,
            current_customer=None,
            message=summary_message,
            error=summary_error,
            failure_details=failure_details[:10],
        )

    def get_send_progress(self, campaign_id: int):
        job = self._get_job(int(campaign_id))
        if not job:
            return {'status': 'error', 'message': 'No hay envío en curso para esta campaña.'}
        return {'status': 'success', 'data': job}
