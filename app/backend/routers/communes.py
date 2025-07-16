from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin
from app.backend.classes.commune_class import CommuneClass
from app.backend.auth.auth_user import get_current_active_user

communes = APIRouter(
    prefix="/communes",
    tags=["Communes"]
)

@communes.get("/no_paginations/{region_id}")
def no_paginations(region_id: int, db: Session = Depends(get_db)):
    data = CommuneClass(db).get_all_no_paginations(region_id)

    return {"message": data}