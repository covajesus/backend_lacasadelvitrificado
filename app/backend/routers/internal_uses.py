from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.internal_use_class import InternalUseClass
from app.backend.db.database import get_db
from app.backend.schemas import (
    InternalUseRequestList,
    StoreInternalUseRequest,
    UserLogin,
)

internal_uses = APIRouter(
    prefix="/internal-uses",
    tags=["Internal Uses"],
)


@internal_uses.post("/")
def index(
    internal_use_input: InternalUseRequestList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = InternalUseClass(db).get_all(
        page=internal_use_input.page,
        description=internal_use_input.description,
        rol_id=internal_use_input.rol_id,
    )
    return {"message": data}


@internal_uses.get("/products")
def products(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = InternalUseClass(db).get_products()
    return {"message": data}


@internal_uses.get("/product/{id}")
def internal_use_product(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = InternalUseClass(db).get_product(id)
    return {"message": data}


@internal_uses.post("/store")
def store(
    internal_use_inputs: StoreInternalUseRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = InternalUseClass(db).store(internal_use_inputs)
    return {"message": data}


@internal_uses.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = InternalUseClass(db).delete(id)
    return {"message": data}
