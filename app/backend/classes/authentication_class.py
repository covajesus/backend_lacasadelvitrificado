from app.backend.db.models import UserModel, CustomerModel, ProductModel, CampaignAccessTokenModel
from fastapi import HTTPException
from app.backend.classes.user_class import UserClass
from app.backend.classes.customer_class import _normalize_phone_digits
from app.backend.auth.auth_user import generate_bcrypt_hash
from datetime import datetime, timedelta
from typing import Union
import os
from jose import jwt
import json
import bcrypt
import hashlib
import secrets
import string

# RUT de la empresa: no permitir login de shopping (solo RUT sin contraseña).
_BLOCKED_SHOPPING_LOGIN_RUT = "77176777-K"


def _normalize_rut_for_compare(rut: str) -> str:
    if not rut:
        return ""
    return str(rut).strip().upper().replace(".", "").replace(" ", "")


class AuthenticationClass:
    def __init__(self, db):
        self.db = db

    def authenticate_shopping_login(self, identification_number):
        if _normalize_rut_for_compare(identification_number) == _normalize_rut_for_compare(
            _BLOCKED_SHOPPING_LOGIN_RUT
        ):
            raise HTTPException(
                status_code=401,
                detail="El usuario con el rut 77176777-K no tiene permitido el acceso por este medio",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = UserClass(self.db).get('rut', identification_number)
        
        # Verificar si user es un string de error en lugar de JSON
        if not user or not isinstance(user, str) or not user.strip().startswith('{'):
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
        
        try:
            response_data = json.loads(user)
        except (json.JSONDecodeError, ValueError) as e:
            # Si no es JSON válido, significa que no se encontró el usuario
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        print(response_data)

        if not response_data or "user_data" not in response_data:
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        return response_data
    
    def authenticate_user(self, email, password):
        user = UserClass(self.db).get("email", email)
        print(user)

        if not user or not isinstance(user, str) or not user.strip().startswith("{"):
            raise HTTPException(
                status_code=401,
                detail="Contraseña incorrecta",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            response_data = json.loads(user)
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(
                status_code=401,
                detail="Contraseña incorrecta",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not response_data or "user_data" not in response_data:
            raise HTTPException(
                status_code=401,
                detail="Contraseña incorrecta",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not self.verify_password(password, response_data["user_data"]["hashed_password"]):
            raise HTTPException(
                status_code=401,
                detail="Contraseña incorrecta",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return response_data
        
    def verify_password(self, plain_password, hashed_password):
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_token(self, data: dict, time_expire: Union[datetime, None] = None):
        data_copy = data.copy()
        if time_expire is None:
            expires = datetime.utcnow() + timedelta(minutes=1000000)
        else:
            expires = datetime.utcnow() + time_expire

        data_copy.update({"exp": expires})
        token = jwt.encode(data_copy, os.environ['SECRET_KEY'], algorithm=os.environ['ALGORITHM'])

        return token

    def update_password(self, user_inputs):
        existing_user = self.db.query(UserModel).filter(UserModel.visual_rut == user_inputs.visual_rut).one_or_none()

        if not existing_user:
            return "No data found"

        existing_user_data = user_inputs.dict(exclude_unset=True)
        for key, value in existing_user_data.items():
            print(key, value)
            if key == 'hashed_password':
                value = self.generate_bcrypt_hash(value)
            if hasattr(existing_user, key):
                setattr(existing_user, key, value)

        self.db.commit()

        return 1
        
    def generate_bcrypt_hash(self, input_string):
        encoded_string = input_string.encode('utf-8')

        salt = bcrypt.gensalt()

        hashed_string = bcrypt.hashpw(encoded_string, salt)

        return hashed_string

    def validate_budget_token(self, token_md5, budget_id):
        """
        Valida el token MD5 para login automático desde WhatsApp
        Retorna el usuario admin si el token es válido
        """
        # Buscar usuario admin (rol_id 1 o 2)
        admin_user = (
            self.db.query(UserModel)
            .filter((UserModel.rol_id == 1) | (UserModel.rol_id == 2))
            .first()
        )

        if not admin_user:
            raise HTTPException(status_code=401, detail="Usuario admin no encontrado")

        # Generar el token esperado
        token_string = f"{budget_id}_{admin_user.rut}_{admin_user.id}"
        expected_token = hashlib.md5(token_string.encode()).hexdigest()

        # Validar el token
        if token_md5 != expected_token:
            raise HTTPException(status_code=401, detail="Token inválido")

        # Generar token JWT para el usuario
        token_expires = timedelta(minutes=9999999)
        jwt_token = self.create_token({'sub': str(admin_user.rut)}, token_expires)

        return {
            "access_token": jwt_token,
            "user_id": admin_user.id,
            "rut": admin_user.rut,
            "rol_id": admin_user.rol_id,
            "full_name": admin_user.full_name,
            "email": admin_user.email,
            "token_type": "bearer",
            "budget_id": budget_id
        }

    def generate_campaign_login_token(self, customer_id: int, phone: str) -> str:
        phone_norm = _normalize_phone_digits(phone)
        token_string = f"campaign_{int(customer_id)}_{phone_norm}_{os.environ.get('SECRET_KEY', '')}"
        return hashlib.md5(token_string.encode()).hexdigest()

    def authenticate_campaign_phone_login(self, customer_id: int, phone: str, token: str):
        expected = self.generate_campaign_login_token(customer_id, phone)
        if token != expected:
            raise HTTPException(status_code=401, detail="Token inválido")

        customer = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == int(customer_id))
            .first()
        )
        if not customer:
            raise HTTPException(status_code=401, detail="Cliente no encontrado")

        if _normalize_phone_digits(customer.phone) != _normalize_phone_digits(phone):
            raise HTTPException(status_code=401, detail="Teléfono no coincide con el cliente")

        if not customer.identification_number:
            raise HTTPException(status_code=401, detail="El cliente no tiene RUT registrado")

        return self.authenticate_shopping_login(customer.identification_number)

    def _generate_short_access_code(self, length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            exists = (
                self.db.query(CampaignAccessTokenModel.id)
                .filter(CampaignAccessTokenModel.token == code)
                .first()
            )
            if not exists:
                return code
        return secrets.token_urlsafe(12)[:16]

    def _ensure_shopping_user_for_customer(self, customer: CustomerModel) -> None:
        rut = (customer.identification_number or "").strip()
        if not rut:
            raise HTTPException(status_code=401, detail="El cliente no tiene RUT registrado")

        existing = self.db.query(UserModel).filter(UserModel.rut == rut).first()
        if existing:
            return

        self.db.add(
            UserModel(
                rut=rut,
                rol_id=5,
                full_name=customer.social_reason or rut,
                hashed_password=generate_bcrypt_hash("123456"),
                email=customer.email,
                phone=customer.phone,
                added_date=datetime.now(),
                updated_date=datetime.now(),
            )
        )
        self.db.flush()

    def create_campaign_access_token(
        self,
        customer_id: int,
        *,
        product_id: int | None = None,
        campaign_id: int | None = None,
        ttl_hours: int = 48,
    ) -> str:
        customer = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == int(customer_id))
            .first()
        )
        if not customer:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        if not customer.identification_number:
            raise HTTPException(status_code=400, detail="El cliente no tiene RUT registrado")

        self._ensure_shopping_user_for_customer(customer)

        code = self._generate_short_access_code()
        now = datetime.now()
        row = CampaignAccessTokenModel(
            token=code,
            customer_id=int(customer_id),
            product_id=int(product_id) if product_id else None,
            campaign_id=int(campaign_id) if campaign_id else None,
            expires_at=now + timedelta(hours=int(ttl_hours)),
            used_at=None,
            added_date=now,
            updated_date=now,
        )
        self.db.add(row)
        self.db.commit()
        return code

    def authenticate_campaign_access_token(self, token: str) -> dict:
        code = (token or "").strip()
        if not code:
            raise HTTPException(status_code=401, detail="Token inválido")

        row = (
            self.db.query(CampaignAccessTokenModel)
            .filter(CampaignAccessTokenModel.token == code)
            .first()
        )
        if not row:
            raise HTTPException(status_code=401, detail="Token inválido")

        now = datetime.now()
        if row.expires_at and row.expires_at < now:
            raise HTTPException(status_code=401, detail="El enlace expiró")

        customer = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.id == int(row.customer_id))
            .first()
        )
        if not customer:
            raise HTTPException(status_code=401, detail="Cliente no encontrado")

        self._ensure_shopping_user_for_customer(customer)
        user = self.authenticate_shopping_login(customer.identification_number)

        if not row.used_at:
            row.used_at = now
            row.updated_date = now
            self.db.commit()

        product_payload = None
        if row.product_id:
            product = (
                self.db.query(ProductModel)
                .filter(ProductModel.id == int(row.product_id))
                .first()
            )
            if product:
                product_payload = {
                    "id": int(product.id),
                    "name": product.product,
                    "photo": product.photo,
                    "short_description": product.short_description,
                }

        return {
            "user": user,
            "customer_id": int(customer.id),
            "customer_name": customer.social_reason,
            "product_id": int(row.product_id) if row.product_id else None,
            "product": product_payload,
            "campaign_id": int(row.campaign_id) if row.campaign_id else None,
        }