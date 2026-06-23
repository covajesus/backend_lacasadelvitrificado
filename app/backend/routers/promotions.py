from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.promotion_class import PromotionClass
from app.backend.db.database import get_db
from app.backend.schemas import (
    PromotionList,
    StorePromotion,
    UpdatePromotion,
    UserLogin,
    ValidateCoupon,
)

promotions = APIRouter(
    prefix="/promotions",
    tags=["Promotions"],
)


@promotions.post("/")
def index(
    promotion_inputs: PromotionList,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).get_all(
        page=promotion_inputs.page,
        q=promotion_inputs.q,
        promotion_type_id=promotion_inputs.promotion_type_id,
        status_id=promotion_inputs.status_id,
    )
    return {"message": data}


@promotions.get("/list")
def list_promotions(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).get_list()
    return {"message": data}


@promotions.post("/store")
def store(
    promotion_inputs: StorePromotion,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).store(promotion_inputs)
    return {"message": data}


@promotions.post("/update/{id}")
def update(
    id: int,
    promotion_inputs: UpdatePromotion,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).update(id, promotion_inputs)
    return {"message": data}


@promotions.delete("/delete/{id}")
def delete(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).delete(id)
    return {"message": data}


@promotions.post("/deactivate/{id}")
def deactivate(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).deactivate(id)
    return {"message": data}


@promotions.get("/edit/{id}")
def edit(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).get(id)
    return {"message": data}


@promotions.get("/visible_coupons/{customer_rut}")
def visible_coupons(
    customer_rut: str,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).get_visible_coupons(customer_rut)
    return {"message": data}


@promotions.get("/generate_coupon_code")
def generate_coupon_code(
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).generate_coupon_code()
    return {"message": data}


@promotions.post("/validate_coupon")
def validate_coupon(
    coupon_inputs: ValidateCoupon,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).validate_coupon(
        coupon_inputs.coupon_code,
        coupon_inputs.product_ids,
        coupon_inputs.subtotal,
        items=[item.model_dump() for item in coupon_inputs.items] if coupon_inputs.items else None,
        customer_rut=coupon_inputs.customer_rut,
    )
    return {"message": data}


@promotions.get("/usage_summary/{id}")
def usage_summary(
    id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    data = PromotionClass(db).get_usage_summary(promotion_id=id)
    return {"message": data}
