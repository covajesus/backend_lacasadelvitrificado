from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreSale, SaleList
from app.backend.classes.sale_class import SaleClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.file_class import FileClass
from fastapi import File, UploadFile, HTTPException
from app.backend.classes.dte_class import DteClass
from app.backend.classes.inventory_class import InventoryClass
from datetime import datetime
import uuid

sales = APIRouter(
    prefix="/sales",
    tags=["Sales"]
)

@sales.post("/")
def index(sale_inputs: SaleList, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SaleClass(db).get_all(sale_inputs.rol_id, sale_inputs.rut, sale_inputs.page)

    return {"message": data}

@sales.get("/show/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SaleClass(db).get(id)

    return {"message": data}

@sales.get("/details/{id}")
def edit(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    data = SaleClass(db).details(id)

    return {"message": data}

@sales.get("/accept_sale_payment/{id}/{dte_type_id}/{status_id}")
def accept_sale_payment(id: int, dte_type_id: int, status_id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if status_id == 2:
        SaleClass(db).change_status(id, status_id)

        dte_response = DteClass(db).generate_dte(id)

        if dte_response == 1:
            return {"message": "Dte created successfully"}
        else:
            return {"message": "Dte creation failed"}

@sales.get("/reject_sale_payment/{id}/{status_id}")
def reject_sale_payment(id: int, status_id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    SaleClass(db).change_status(id, status_id)

    reverse_response = SaleClass(db).reverse(id)

    return {"message": reverse_response}
        
@sales.get("/delivered_sale/{id}")
def accept_sale_payment(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    SaleClass(db).change_status(id, 4)

    return {"message": "Sale marked as delivered"}

@sales.post("/store")
def store(
    form_data: StoreSale = Depends(StoreSale.as_form),
    payment_support: UploadFile = File(...),  # Obligatorio
    db: Session = Depends(get_db)
):
    try:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]
        extension = payment_support.filename.split('.')[-1]
        filename = f"payment_{timestamp}_{unique_id}.{extension}"
        FileClass(db).upload(payment_support, filename)
        response = SaleClass(db).store(form_data, filename)

        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")