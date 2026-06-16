from datetime import datetime

from app.backend.db.models import SettingModel
from app.backend.services.crud.base_domain_service import BaseDomainService
from app.backend.services.integrations.simplefactura_client import SimpleFacturaClient


class SettingClass(BaseDomainService):
    def __init__(self, db):
        super().__init__(db)
        self._simplefactura = SimpleFacturaClient()

    def get_simplefactura_token(self):
        return self.safe(lambda: self._refresh_simplefactura_token())

    def _refresh_simplefactura_token(self):
        data = self._simplefactura.fetch_token(
            email="info@vitrificadoschile.com",
            password="23414255Jo",
        )
        if "accessToken" not in data:
            return {"error": "Token not found in response"}
        existing_setting = self.db.query(SettingModel).filter(SettingModel.id == 1).one_or_none()
        if existing_setting:
            existing_setting.simplefactura_token = data["accessToken"]
            self.db.commit()
        return data["accessToken"]

    def validate_token(self):
        setting_data = self.db.query(SettingModel).filter(SettingModel.id == 1).first()
        if not setting_data or not setting_data.simplefactura_token:
            return 0
        return 1 if self._simplefactura.is_token_valid(setting_data.simplefactura_token) else 0

    def update(self, id, form_data):
        existing_setting = self.db.query(SettingModel).filter(SettingModel.id == id).one_or_none()
        if not existing_setting:
            return "No data found"
        return self.safe(lambda: self._update_setting(existing_setting, form_data), rollback=True)

    def _update_setting(self, existing_setting, form_data):
        existing_setting.tax_value = form_data.tax_value
        existing_setting.identification_number = form_data.identification_number
        existing_setting.account_type = form_data.account_type
        existing_setting.account_number = form_data.account_number
        existing_setting.account_name = form_data.account_name
        existing_setting.account_email = form_data.account_email
        existing_setting.bank = form_data.bank
        existing_setting.delivery_cost = form_data.delivery_cost
        existing_setting.shop_address = form_data.shop_address
        existing_setting.payment_card_url = form_data.payment_card_url
        existing_setting.prepaid_discount = form_data.prepaid_discount
        existing_setting.phone = form_data.phone
        existing_setting.updated_date = datetime.now()
        self.db.commit()
        self.db.refresh(existing_setting)
        return "Settings updated successfully"

    def get(self, id):
        return self.safe(
            lambda: self.get_or_error(
                self.db.query(SettingModel).filter(SettingModel.id == id).first(),
                data_key="setting_data",
                serialize=lambda row: {
                    "id": row.id,
                    "tax_value": row.tax_value,
                    "identification_number": row.identification_number,
                    "account_type": row.account_type,
                    "account_number": row.account_number,
                    "account_name": row.account_name,
                    "account_email": row.account_email,
                    "bank": row.bank,
                    "delivery_cost": row.delivery_cost,
                    "simplefactura_token": row.simplefactura_token,
                    "shop_address": row.shop_address,
                    "payment_card_url": row.payment_card_url,
                    "prepaid_discount": row.prepaid_discount,
                    "phone": row.phone,
                },
            )
        )
