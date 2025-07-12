from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreCategory, CategoryList, UpdateCategory
from app.backend.classes.category_class import CategoryClass
from app.backend.auth.auth_user import get_current_active_user

categories = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)

@categories.post("/")
def index(category_inputs: CategoryList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CategoryClass(db).get_all(category_inputs.page)

    return {"message": data}

@categories.get("/list")
def index(session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CategoryClass(db).get_list()

    return {"message": data}

@categories.post("/store")
def store(category_inputs: StoreCategory, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CategoryClass(db).store(category_inputs)

    return {"message": data}

@categories.post("/update/{id}")
def store(id: int, category_inputs: UpdateCategory, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CategoryClass(db).update(id, category_inputs)

    return {"message": data}

@categories.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CategoryClass(db).delete(id)

    return {"message": data}

@categories.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = CategoryClass(db).get(id)

    return {"message": data}