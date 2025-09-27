from fastapi import APIRouter, Depends
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.schemas import UserLogin, StoreSale, SaleList, SalesReportFilter
from app.backend.classes.sale_class import SaleClass
from app.backend.auth.auth_user import get_current_active_user
from app.backend.classes.file_class import FileClass
from fastapi import File, UploadFile, HTTPException
from app.backend.classes.dte_class import DteClass
from app.backend.classes.inventory_class import InventoryClass
from app.backend.db.models import SaleModel
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

        if dte_response and dte_response > 0:  # Si se generó el DTE y retornó un folio
            # Actualizar el folio en la venta
            sale = db.query(SaleModel).filter(SaleModel.id == id).first()
            if sale:
                sale.folio = dte_response
                sale.updated_date = datetime.now()
                db.commit()
                return {"message": f"Dte created successfully with folio: {dte_response}"}
            else:
                return {"message": "Sale not found"}
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
    payment_support: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    if form_data.rol_id != 2 and payment_support is not None:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]
        extension = payment_support.filename.split('.')[-1]
        filename = f"payment_{timestamp}_{unique_id}.{extension}"
        FileClass(db).upload(payment_support, filename)
        response = SaleClass(db).store(form_data, filename)
    else:
        filename = None
        response = SaleClass(db).store(form_data)

    return {"message": response}


@sales.get("/check_inventory/{product_id}/{quantity}")
def check_inventory(product_id: int, quantity: int, db: Session = Depends(get_db)):
    response = SaleClass(db).check_product_inventory(product_id, quantity)

    return response
    
@sales.post("/report")
def sales_report(
    filter_data: SalesReportFilter,
    db: Session = Depends(get_db)
):
    """
    Endpoint para generar reporte de ventas por producto.
    
    Muestra por cada producto:
    - Cantidad vendida
    - Ingresos (actual, potencial público/privado)
    - Costos (basado en unit_cost de inventory_movements)
    - Ganancias (actual vs potencial)
    - Márgenes de ganancia
    
    Filtros opcionales:
    - date_from: Fecha inicio (YYYY-MM-DD)
    - date_to: Fecha fin (YYYY-MM-DD).
    """
    data = SaleClass(db).get_sales_report(
        start_date=filter_data.date_from,
        end_date=filter_data.date_to
    )

    return {"message": data}