from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreSupplier, SupplierList, UpdateSupplier
from app.backend.classes.supplier_class import SupplierClass
from app.backend.auth.auth_user import get_current_active_user

suppliers = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"]
)

@suppliers.post("/")
def index(supplier_input: SupplierList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierClass(db).get_all(supplier_input.page)

    return {"message": data}

@suppliers.get("/list")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierClass(db).get_list()

    return {"message": data}

@suppliers.post("/store")
def store(supplier_inputs: StoreSupplier, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierClass(db).store(supplier_inputs)

    return {"message": data}

@suppliers.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierClass(db).delete(id)

    return {"message": data}

@suppliers.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierClass(db).get(id)

    return {"message": data}

@suppliers.post("/update/{id}")
def store(id: int, supplier_inputs: UpdateSupplier, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierClass(db).update(id, supplier_inputs)

    return {"message": data}