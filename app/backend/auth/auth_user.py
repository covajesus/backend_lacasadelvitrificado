from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import HTTPException, Depends
from app.backend.db.models import UserModel
import os
from jose import jwt, JWTError
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
import bcrypt

oauth2_scheme = OAuth2PasswordBearer("/login_users/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra un hash bcrypt"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def hash_password(password: str) -> str:
    """Genera un hash bcrypt de una contraseña"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        decoded_token = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['ALGORITHM']])
        username = decoded_token.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    user = get_user(username)

    if user is None or user == "":
        raise HTTPException(status_code=401, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    return user
    
def get_current_active_user(current_user: UserModel = Depends(get_current_user)):
    return current_user

def get_user(rut):
    db: Session = next(get_db())

    user = db.query(UserModel). \
                    filter(UserModel.rut == rut). \
                    first()
    
    if not user:
        return None
    return user

def generate_bcrypt_hash(input_string):
    encoded_string = input_string.encode('utf-8')

    salt = bcrypt.gensalt()

    hashed_string = bcrypt.hashpw(encoded_string, salt)

    return hashed_string