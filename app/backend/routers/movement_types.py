from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreLocation, LocationList
from app.backend.classes.movement_type_class import MovementTypeClass
from app.backend.auth.auth_user import get_current_active_user

movement_types = APIRouter(
    prefix="/movement_types",
    tags=["Movement_types"]
)

@movement_types.get("/list")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = MovementTypeClass(db).get_list()

    return {"message": data}