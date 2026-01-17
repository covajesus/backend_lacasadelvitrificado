from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, BudgetList, StoreBudget
from app.backend.classes.budget_class import BudgetClass
from app.backend.db.models import UserModel

budgets = APIRouter(
    prefix="/budgets",
    tags=["Budgets"]
)

@budgets.post("/")
def index(
    budget_inputs: BudgetList,
    session_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    print(budget_inputs)
    data = BudgetClass(db).get_all(
        rol_id=session_user.rol_id,
        rut=session_user.rut,
        page=budget_inputs.page,
        identification_number=budget_inputs.identification_number,
        social_reason=budget_inputs.social_reason
    )
    return {"message": data}

@budgets.get("/edit/{id}")
def show(
    id: int,
    db: Session = Depends(get_db)
):
    data = BudgetClass(db).get(id)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=404, detail=data["message"])

    return {"message": data}

@budgets.post("/store")
def store(
    budget_inputs: StoreBudget,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    print(budget_inputs)
    data = BudgetClass(db).store(budget_inputs)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])

    return {"message": data}

@budgets.post("/accept/{budget_id}")
def accept_budget(
    budget_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    data = BudgetClass(db).accept(budget_id)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])

    return {"message": data}

@budgets.get("/reject/{budget_id}")
def reject_budget(
    budget_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    data = BudgetClass(db).reject(budget_id)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])

    return {"message": data}

@budgets.delete("/delete/{budget_id}")
def delete_budget(
    budget_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    data = BudgetClass(db).delete(budget_id)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=404, detail=data["message"])

    return {"message": data}

@budgets.get("/product/detail/{customer_id}/{product_id}")
def product_detail(
    customer_id: int,
    product_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint para obtener detalle del producto para presupuesto.
    Devuelve nombre, precio público y descuento del cliente.
    """
    data = BudgetClass(db).product_detail(product_id, customer_id=customer_id)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=404, detail=data["message"])

    return {"message": data}
