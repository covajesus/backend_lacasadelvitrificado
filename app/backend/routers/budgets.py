from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.backend.db.database import get_db
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin, BudgetList, StoreBudget, StoreBudgetWithoutCustomer
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

@budgets.post("/store/without-customer")
def store_without_customer(
    budget_inputs: StoreBudgetWithoutCustomer,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Crea un presupuesto sin guardar el cliente en la tabla customers.
    Los datos del cliente se proporcionan en el request pero no se guardan permanentemente.
    """
    print(budget_inputs)
    data = BudgetClass(db).store_without_customer(budget_inputs)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])

    return {"message": data}

@budgets.post("/accept/{budget_id}/{dte_type_id}")
@budgets.post("/accept/{budget_id}")
def accept_budget_with_dte_status(
    budget_id: int,
    dte_type_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Acepta un presupuesto y crea una venta con dte_status_id en la URL.
    Parámetros:
    - budget_id: ID del presupuesto
    - dte_status_id: 1 para Boleta (dte_type_id=1), 2 para Factura (dte_type_id=2)
    """
    # Si dte_status_id es 1, dte_type_id es 1 (Boleta). Si dte_status_id es 2, dte_type_id es 2 (Factura).
    dte_status_id = 1

    data = BudgetClass(db).accept(budget_id, dte_type_id=dte_type_id, dte_status_id=dte_status_id)

    if isinstance(data, dict) and data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])

    return {"message": data}

@budgets.post("/accept/{budget_id}")
def accept_budget(
    budget_id: int,
    dte_type_id: Optional[int] = None,
    dte_status_id: Optional[int] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Acepta un presupuesto y crea una venta.
    Parámetros opcionales por query string:
    - dte_type_id: 1 para Boleta, 2 para Factura
    - dte_status_id: 1 para generar DTE, cualquier otro valor para no generar
    """
    data = BudgetClass(db).accept(budget_id, dte_type_id=dte_type_id, dte_status_id=dte_status_id)

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
