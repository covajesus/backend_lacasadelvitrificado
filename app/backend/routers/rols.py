from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import Rol, UpdateRol, UserLogin
from app.backend.classes.rol_class import RolClass
from app.backend.auth.auth_user import get_current_active_user

rols = APIRouter(
    prefix="/rols",
    tags=["Rols"]
)

@rols.get("/")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = RolClass(db).get_all()

    return {"message": data}

@rols.post("/store")
def store(rol:Rol, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    bank_inputs = rol.dict()
    data = RolClass(db).store(bank_inputs)

    return {"message": data}

@rols.get("/edit/{id}")
def edit(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = RolClass(db).get("id", id)

    return {"message": data}

@rols.delete("/delete/{id}")
def delete(id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = RolClass(db).delete(id)

    return {"message": data}

@rols.patch("/update/{id}")
def update(id: int, rol: UpdateRol, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = RolClass(db).update(id, rol)

    return {"message": data}