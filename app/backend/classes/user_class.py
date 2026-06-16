import json
from datetime import datetime

from app.backend.auth.auth_user import generate_bcrypt_hash
from app.backend.db.models import UserModel
from app.backend.services.crud.base_domain_service import BaseDomainService


class UserClass(BaseDomainService):
    
    @staticmethod
    def _serialize_row(user):
        return {
            "id": user.id,
            "rut": user.rut,
            "full_name": user.full_name,
            "rol_id": user.rol_id,
            "email": user.email,
            "phone": user.phone,
            "added_date": user.added_date,
        }

    def get_all(self, rut=None, page=0, items_per_page=10):
        filters = []
        if rut is not None:
            filters.append(UserModel.rut == rut)
        query = (
            self.db.query(
                UserModel.id,
                UserModel.rut,
                UserModel.full_name,
                UserModel.rol_id,
                UserModel.email,
                UserModel.phone,
                UserModel.added_date,
            )
            .filter(*filters)
            .order_by(UserModel.rut)
        )
        return self.list_query(
            query, page=page, items_per_page=items_per_page, serialize_row=self._serialize_row
        )

    def get(self, field, value):
        try:
            data_query = self.db.query(UserModel).filter(getattr(UserModel, field) == value).first()

            if data_query:
                user_data = {
                    "id": data_query.id,
                    "rut": data_query.rut,
                    "full_name": data_query.full_name,
                    "rol_id": data_query.rol_id,
                    "email": data_query.email,
                    "phone": data_query.phone,
                    "hashed_password": data_query.hashed_password
                }

                result = {
                    "user_data": user_data
                }

                serialized_result = json.dumps(result)

                return serialized_result

            else:
                return "No se encontraron datos para el campo especificado."

        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"
        
    def get_supervisors(self):
        try:
            data = self.db.query(UserModel).order_by(UserModel.nickname).filter(UserModel.rol_id == 3).all()
            return data
        except Exception as e:
            error_message = str(e)
            return f"Error: {error_message}"  
    
    def store(self, user_inputs):
        user = UserModel()
        user.rut = user_inputs['rut']
        user.rol_id = user_inputs['rol_id']
        user.branch_office_id = user_inputs['branch_office_id']
        user.full_name = user_inputs['full_name']
        user.hashed_password = generate_bcrypt_hash(user_inputs['password'])
        user.email = user_inputs['email']
        user.phone = user_inputs['phone']
        user.added_date = datetime.now()
        user.updated_date = datetime.now()

        self.db.add(user)
        try:
            self.db.commit()

            return 1
        except Exception as e:
            return 0
    
    def store_login(self, user_inputs):
        user = UserModel()
        user.rut = user_inputs.identification_number
        user.rol_id = 5
        user.full_name = user_inputs.social_reason
        user.hashed_password = generate_bcrypt_hash('123456')
        user.email = user_inputs.email
        user.phone = user_inputs.phone
        user.added_date = datetime.now()
        user.updated_date = datetime.now()

        self.db.add(user)
        try:
            self.db.commit()

            return 1
        except Exception as e:
            return 0
        
    def delete(self, id):
        return self.delete_entity(UserModel, id)

    def refresh_password(self, rut):
        user = self.db.query(UserModel).filter(UserModel.rut == rut).first()
        user.password = 'pbkdf2:sha256:260000$9199IIO4oyzykgL2$721b8c61330f838acd950f8104f364efc05d513efec2c829fcd773ef4402f10e'
        user.hashed_password = 'pbkdf2:sha256:260000$9199IIO4oyzykgL2$721b8c61330f838acd950f8104f364efc05d513efec2c829fcd773ef4402f10e'
        user.status_id = 1
        user.updated_date = datetime.now()
        self.db.add(user)
        
        try:
            self.db.commit()

            return 1
        except Exception as e:
            return 0

    def update(self, id, form_data):
        user = self.db.query(UserModel).filter(UserModel.id == id).first()

        user.rol_id = form_data['rol_id']
        user.rut = form_data['rut']
        user.full_name = form_data['full_name']
        user.email = form_data['email']
        user.phone = form_data['phone']

        user.updated_date = datetime.now()

        self.db.add(user)

        try:
            self.db.commit()

            return 1
        except Exception as e:
            return 0