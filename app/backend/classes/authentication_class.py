from app.backend.db.models import UserModel
from fastapi import HTTPException
from app.backend.auth.auth_user import pwd_context
from app.backend.classes.user_class import UserClass
from app.backend.classes.customer_class import CustomerClass
from datetime import datetime, timedelta
from typing import Union
import os
from jose import jwt
import json
import bcrypt

class AuthenticationClass:
    def __init__(self, db):
        self.db = db

    def authenticate_shopping_login(self, rut):
        customer = CustomerClass(self.db).get('rut', rut)
        print(customer)
        response_data = json.loads(customer)

        if not customer:
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
        return pwd_context.verify(plain_password, hashed_password)
    
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