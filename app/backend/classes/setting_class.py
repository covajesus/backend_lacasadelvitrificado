from app.backend.db.models import SettingModel
from datetime import datetime

class SettingClass:
    def __init__(self, db):
        self.db = db
    
    def update(self, id, form_data):
        existing_setting = self.db.query(SettingModel).filter(SettingModel.id == id).one_or_none()

        if not existing_setting:
            return "No data found"

        try:
            existing_setting.tax_value = form_data.tax_value
            existing_setting.identificacion_number = form_data.identificacion_number
            existing_setting.account_type = form_data.account_type
            existing_setting.account_number = form_data.account_number
            existing_setting.account_name = form_data.account_name
            existing_setting.bank = form_data.bank
            existing_setting.delivery_cost = form_data.delivery_cost

            self.db.commit()
            self.db.refresh(existing_setting)
            return "Settings updated successfully"
        except Exception as e:
            self.db.rollback()
            error_message = str(e)
            return {"status": "error", "message": error_message}

    def get(self, id):
        try:
            data_query = self.db.query(
                SettingModel
            ).filter(SettingModel.id == id).first()

            if data_query:
                setting_data = {
                    "id": data_query.id,
                    "tax_value": data_query.tax_value,
                    "identificacion_number": data_query.identificacion_number,
                    "account_type": data_query.account_type,
                    "account_number": data_query.account_number,
                    "account_name": data_query.account_name,
                    "bank": data_query.bank,
                    "delivery_cost": data_query.delivery_cost
                }

                return {"setting_data": setting_data}

            else:
                return {"error": "No se encontraron datos para el campo especificado."}
            
        except Exception as e:
            return {"error": str(e)}