from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, UpdateSettings
from app.backend.classes.setting_class import SettingClass
from app.backend.auth.auth_user import get_current_active_user

settings = APIRouter(
    prefix="/settings",
    tags=["Locations"]
)

@settings.post("/update/{id}")
def update(id: int, setting_inputs: UpdateSettings, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SettingClass(db).store(setting_inputs)

    return {"message": data}

@settings.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SettingClass(db).get(id)

    return {"message": data}