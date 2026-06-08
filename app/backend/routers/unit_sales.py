from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.unit_sale_class import UnitSaleClass
from app.backend.db.database import get_db
from app.backend.schemas import (
    UnitSaleRequestList,
    StoreUnitSaleRequest,
    UpdateUnitSaleRequest,
    UserLogin,
)

unit_sales = APIRouter(
    prefix="/unit-sales",
    tags=["Unit Sales"],
)


@unit_sales.post("/")
def index(
    unit_sale_input: UnitSaleRequestList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).get_all(
        page=unit_sale_input.page,
        rut=unit_sale_input.rut,
        customer_name=unit_sale_input.customer_name,
        rol_id=unit_sale_input.rol_id,
        user_rut=unit_sale_input.user_rut,
    )
    return {"message": data}


@unit_sales.get("/products")
def products(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).get_products()
    return {"message": data}


@unit_sales.get("/product/{id}")
def unit_sale_product(
    id: int,
    customer_id: Optional[int] = Query(None),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).get_product(id, customer_id)
    return {"message": data}


@unit_sales.post("/store")
def store(
    unit_sale_inputs: StoreUnitSaleRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).store(unit_sale_inputs)
    return {"message": data}


@unit_sales.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).get(id)
    return {"message": data}


@unit_sales.post("/update/{id}")
def update(
    id: int,
    unit_sale_inputs: UpdateUnitSaleRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).update(id, unit_sale_inputs)
    return {"message": data}


@unit_sales.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = UnitSaleClass(db).delete(id)
    return {"message": data}
