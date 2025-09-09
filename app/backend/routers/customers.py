from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreCustomer, UpdateCustomer, CustomerList
from app.backend.classes.customer_class import CustomerClass
from app.backend.classes.user_class import UserClass
from app.backend.auth.auth_user import get_current_active_user

customers = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)

@customers.post("/")
def index(customer_inputs: CustomerList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).get_all(
        page=customer_inputs.page,
        name=customer_inputs.name,
        rut=customer_inputs.rut
    )

    return {"message": data}

@customers.get("/discounts/{identification_number}")
def discounts(identification_number:str, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).discounts(identification_number)

    return {"message": data}

@customers.post("/store")
def store(customer_inputs: StoreCustomer, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).store(customer_inputs)

    return {"message": data}

@customers.post("/store_login")
def store_login(customer_inputs: StoreCustomer, db: Session = Depends(get_db)):
    CustomerClass(db).store(customer_inputs)

    UserClass(db).store_login(customer_inputs)

    return {"message": "Customer and User created successfully"}

@customers.post("/update/{id}")
def store(id: int, customer_inputs: UpdateCustomer, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).update(id, customer_inputs)

    return {"message": data}

@customers.post("/discount/apply-settings/{customer_id}/{product_id}")
def apply_settings_discount(
    customer_id: int, 
    product_id: int, 
    session_user: UserLogin = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """
    Aplica el descuento de settings a un producto específico para un cliente
    """
    data = CustomerClass(db).apply_settings_discount(customer_id, product_id)
    return {"message": data}

@customers.delete("/discount/{customer_id}/{product_id}")
def delete_product_discount(
    customer_id: int, 
    product_id: int, 
    session_user: UserLogin = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """
    Elimina un descuento de producto específico para un cliente
    """
    data = CustomerClass(db).delete_product_discount(customer_id, product_id)
    return {"message": data}

@customers.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).delete(id)

    return {"message": data}

@customers.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CustomerClass(db).get(id)

    return {"message": data}