from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreUnitMeasure, UnitMeasureList
from app.backend.classes.unit_measure_class import UnitMeasureClass
from app.backend.auth.auth_user import get_current_active_user

unit_measures = APIRouter(
    prefix="/unit_measures",
    tags=["Unit_measures"]
)

@unit_measures.post("/")
def index(unit_measure_inputs: UnitMeasureList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UnitMeasureClass(db).get_all(unit_measure_inputs.page)

    return {"message": data}

@unit_measures.get("/list")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UnitMeasureClass(db).get_list()

    return {"message": data}

@unit_measures.post("/store")
def store(unit_measure_inputs: StoreUnitMeasure, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UnitMeasureClass(db).store(unit_measure_inputs)

    return {"message": data}

@unit_measures.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UnitMeasureClass(db).delete(id)

    return {"message": data}

@unit_measures.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UnitMeasureClass(db).get(id)

    return {"message": data}

@unit_measures.put("/update/{id}")
def update(id: int, unit_measure_inputs: StoreUnitMeasure, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = UnitMeasureClass(db).update(id, unit_measure_inputs)

    return {"message": data}