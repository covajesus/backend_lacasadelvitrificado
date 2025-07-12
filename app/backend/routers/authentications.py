from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.authentication_class import AuthenticationClass
from app.backend.classes.rol_class import RolClass
from datetime import timedelta
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
import json

authentications = APIRouter(
    prefix="/authentications",
    tags=["Authentications"]
)

@authentications.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
    print(user)
    rol = RolClass(db).get('id', user["user_data"]["rol_id"])
    token_expires = timedelta(minutes=120)
    token = AuthenticationClass(db).create_token({'sub': str(user["user_data"]["rut"])}, token_expires)
    expires_in_seconds = token_expires.total_seconds()

    return {
        "access_token": token,
        "user_id": user["user_data"]["id"],
        "rut": user["user_data"]["rut"],
        "rol_id": user["user_data"]["rol_id"],
        "rol": rol.rol,
        "full_name": user["user_data"]["full_name"],
        "email": user["user_data"]["email"],
        "token_type": "bearer",
        "expires_in": expires_in_seconds
    }

@authentications.post("/logout")
def logout(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
    access_token_expires = timedelta(minutes=30)
    access_token_jwt = AuthenticationClass(db).create_token({'sub': str(user.rut)}, access_token_expires)

    return {
        "access_token": access_token_jwt, 
        "rut": user.rut,
        "visual_rut": user.visual_rut,
        "rol_id": user.rol_id,
        "nickname": user.nickname,
        "token_type": "bearer"
    }

@authentications.post("/shopping_login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = AuthenticationClass(db).authenticate_user(form_data.username, form_data.password)
    print(user)
    rol = RolClass(db).get('id', user["user_data"]["rol_id"])
    token_expires = timedelta(minutes=120)
    token = AuthenticationClass(db).create_token({'sub': str(user["user_data"]["rut"])}, token_expires)
    expires_in_seconds = token_expires.total_seconds()

    return {
        "access_token": token,
        "rut": user["user_data"]["rut"],
        "rol_id": user["user_data"]["rol_id"],
        "rol": rol.rol,
        "full_name": user["user_data"]["full_name"],
        "email": user["user_data"]["email"],
        "token_type": "bearer",
        "expires_in": expires_in_seconds
    }

@authentications.post("/refresh")
def refresh_token(
    db: Session = Depends(get_db),
    session_user: UserLogin = Depends(get_current_active_user)
):
    # Generar nuevo token con misma data de usuario
    token_expires = timedelta(minutes=30)
    token = AuthenticationClass(db).create_token({'sub': str(session_user.rut)}, token_expires)
    expires_in_seconds = token_expires.total_seconds()

    # También puedes retornar información adicional si la necesitas
    rol = RolClass(db).get('id', session_user.rol_id)

    return {
        "access_token": token,
        "rut": session_user.rut,
        "rol_id": session_user.rol_id,
        "rol": rol.rol,
        "full_name": session_user.full_name,
        "email": session_user.email,
        "token_type": "bearer",
        "expires_in": expires_in_seconds
    }