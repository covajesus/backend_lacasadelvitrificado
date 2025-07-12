from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreInventory, InventoryList, AddAdjustmentInput, RemoveAdjustmentInput
from app.backend.classes.inventory_class import InventoryClass
from app.backend.auth.auth_user import get_current_active_user

inventories = APIRouter(
    prefix="/inventories",
    tags=["Inventories"]
)

@inventories.post("/")
def index(inventory_inputs: InventoryList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).get_all(inventory_inputs.page)

    return {"message": data}

@inventories.post("/store")
def store(inventory_inputs: StoreInventory, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).store(inventory_inputs)

    return {"message": data}

@inventories.delete("/delete/{id}")
def delete(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).delete(id)

    return {"message": data}

@inventories.get("/edit/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).get(id)

    return {"message": data}

@inventories.post("/add_adjustment")
def add_adjustment(inventory_inputs: AddAdjustmentInput, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).add_adjustment(inventory_inputs)

    return {"message": data}

@inventories.post("/remove_adjustment")
def remove_adjustment(inventory_inputs: RemoveAdjustmentInput, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = InventoryClass(db).remove_adjustment(inventory_inputs)

    return {"message": data}