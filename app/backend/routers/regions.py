from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin
from app.backend.classes.region_class import RegionClass
from app.backend.auth.auth_user import get_current_active_user

regions = APIRouter(
    prefix="/regions",
    tags=["Regions"]
)

@regions.get("/no_paginations")
def no_paginations(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = RegionClass(db).get_all_no_paginations()

    return {"message": data}