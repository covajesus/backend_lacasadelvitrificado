from app.backend.db.models import UserModel
from fastapi import HTTPException
from app.backend.classes.user_class import UserClass
from app.backend.classes.customer_class import CustomerClass
from datetime import datetime, timedelta
from typing import Union
import os
from jose import jwt
import json
import bcrypt
import hashlib

class AuthenticationClass:
    def __init__(self, db):
        self.db = db

    def authenticate_shopping_login(self, identification_number):
        user = UserClass(self.db).get('rut', identification_number)
        response_data = json.loads(user)

        print(response_data)

        if not user:
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        return response_data
    
    def authenticate_user(self, email, password):
        user = UserClass(self.db).get('email', email)
        print(user)
        response_data = json.loads(user)

        if not user:
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

        if not self.verify_password(password, response_data["user_data"]["hashed_password"]):
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
        
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