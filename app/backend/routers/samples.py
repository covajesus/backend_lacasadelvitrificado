from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.sample_class import SampleClass
from app.backend.db.database import get_db
from app.backend.schemas import (
    SampleRequestList,
    StoreSampleRequest,
    UpdateSampleRequest,
    UserLogin,
)

samples = APIRouter(
    prefix="/samples",
    tags=["Samples"],
)


@samples.post("/")
def index(
    sample_input: SampleRequestList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).get_all(
        page=sample_input.page,
        rut=sample_input.rut,
        customer_name=sample_input.customer_name,
        rol_id=sample_input.rol_id,
        user_rut=sample_input.user_rut,
    )
    return {"message": data}


@samples.get("/products")
def products(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).get_products_with_samples()
    return {"message": data}


@samples.get("/product/{id}")
def sample_product(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).get_sample_product(id)
    return {"message": data}


@samples.post("/store")
def store(
    sample_inputs: StoreSampleRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).store(sample_inputs)
    return {"message": data}


@samples.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).get(id)
    return {"message": data}


@samples.post("/update/{id}")
def update(
    id: int,
    sample_inputs: UpdateSampleRequest,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).update(id, sample_inputs)
    return {"message": data}


@samples.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = SampleClass(db).delete(id)
    return {"message": data}
