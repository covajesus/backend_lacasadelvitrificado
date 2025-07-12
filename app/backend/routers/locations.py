from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreLocation, LocationList
from app.backend.classes.location_class import LocationClass
from app.backend.auth.auth_user import get_current_active_user

locations = APIRouter(
    prefix="/locations",
    tags=["Locations"]
)

@locations.post("/")
def index(location_input: LocationList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = LocationClass(db).get_all(location_input.page)

    return {"message": data}

@locations.get("/list")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = LocationClass(db).get_list()

    return {"message": data}

@locations.post("/store")
def store(location_inputs: StoreLocation, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = LocationClass(db).store(location_inputs)

    return {"message": data}

@locations.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = LocationClass(db).delete(id)

    return {"message": data}

@locations.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = LocationClass(db).get(id)

    return {"message": data}