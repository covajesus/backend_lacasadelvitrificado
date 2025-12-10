from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, SupplierCategoryCreate, SupplierCategoryUpdate, SupplierCategoryList
from app.backend.classes.supplier_category_class import SupplierCategoryClass
from app.backend.auth.auth_user import get_current_active_user

supplier_categories = APIRouter(
    prefix="/supplier_categories",
    tags=["SupplierCategories"]
)

@supplier_categories.post("/")
def index(supplier_category_inputs: SupplierCategoryList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).get_all(supplier_category_inputs.page)
    return {"message": data}

@supplier_categories.get("/list")
def list_all(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).get_list()
    return {"message": data}

@supplier_categories.get("/supplier/{supplier_id}")
def get_by_supplier(supplier_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).get_by_supplier(supplier_id)
    return {"message": data}

@supplier_categories.get("/category/{category_id}")
def get_by_category(category_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).get_by_category(category_id)
    return {"message": data}

@supplier_categories.post("/store")
def store(supplier_category_inputs: SupplierCategoryCreate, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).store(supplier_category_inputs)
    return {"message": data}

@supplier_categories.post("/update/{id}")
def update(id: int, supplier_category_inputs: SupplierCategoryUpdate, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).update(id, supplier_category_inputs)
    return {"message": data}

@supplier_categories.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).delete(id)
    return {"message": data}

@supplier_categories.delete("/delete/supplier/{supplier_id}")
def delete_by_supplier(supplier_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).delete_by_supplier(supplier_id)
    return {"message": data}

@supplier_categories.delete("/delete/category/{category_id}")
def delete_by_category(category_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).delete_by_category(category_id)
    return {"message": data}

@supplier_categories.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SupplierCategoryClass(db).get(id)
    return {"message": data}
