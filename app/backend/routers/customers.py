from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreCustomer, UpdateCustomer, CustomerList
from app.backend.classes.customer_class import CustomerClass
from app.backend.auth.auth_user import get_current_active_user

customers = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

@customers.post("/")
def index(customer_inputs: CustomerList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).get_all(customer_inputs.page)

    return {"message": data}

@customers.post("/store")
def store(customer_inputs: StoreCustomer, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).store(customer_inputs)

    return {"message": data}

@customers.post("/update/{id}")
def store(id: int, customer_inputs: UpdateCustomer, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).update(id, customer_inputs)

    return {"message": data}

@customers.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).delete(id)

    return {"message": data}

@customers.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).get(id)

    return {"message": data}