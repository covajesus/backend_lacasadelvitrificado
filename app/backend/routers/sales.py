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
from app.backend.classes.whatsapp_class import WhatsappClass
from app.backend.db.models import SaleModel, CustomerModel
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

@sales.get("/ws")
def edit(db: Session = Depends(get_db)):
    data = WhatsappClass(db).send()

    return {"message": data}

@sales.get("/accept_sale_payment/{id}/{dte_type_id}/{status_id}")
def accept_sale_payment(id: int, dte_type_id: int, status_id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if status_id == 2:
        try:
            change_status_result = SaleClass(db).change_status(id, status_id)
            
            # Si ya está en ese estado, retornar mensaje
            if change_status_result == "Sale already in this status":
                return {"message": {"status": "info", "message": "La venta ya está en este estado"}}
            
            if change_status_result == "No data found":
                raise HTTPException(status_code=404, detail="Venta no encontrada")
        except Exception as e:
            # Manejar error de bloqueo de fila
            if "could not obtain lock" in str(e).lower() or "lock" in str(e).lower():
                raise HTTPException(status_code=409, detail="La venta está siendo procesada. Por favor, intente nuevamente en unos segundos.")
            raise HTTPException(status_code=500, detail=f"Error al cambiar estado de la venta: {str(e)}")

        dte_response = DteClass(db).generate_dte(id)

        if dte_response and dte_response > 0:  # Si se generó el DTE y retornó un folio
            # Actualizar el folio en la venta
            sale = db.query(SaleModel).filter(SaleModel.id == id).first()
            if sale:
                sale.folio = dte_response
                sale.updated_date = datetime.now()
                db.commit()
                
                # Enviar WhatsApp con los datos del DTE
                try:
                    # Obtener datos del cliente
                    customer = db.query(CustomerModel).filter(CustomerModel.id == sale.customer_id).first()
                    if customer and customer.phone:
                        # Determinar tipo de DTE
                        dte_type = "Boleta Electrónica" if sale.dte_type_id == 1 else "Factura Electrónica"
                        
                        # Formatear fecha
                        date_formatted = sale.added_date.strftime("%d-%m-%Y")
                        
                        # Enviar WhatsApp del DTE
                        whatsapp = WhatsappClass(db)
                        whatsapp.send_dte(
                            customer_phone=customer.phone,
                            dte_type=dte_type,
                            folio=dte_response,
                            date=date_formatted,
                            amount=int(sale.total),
                            dynamic_value=dte_response  # Usar el folio como valor dinámico
                        )
                        print(f"[WHATSAPP] Mensaje DTE enviado al cliente {customer.phone}")
                    else:
                        print("[WHATSAPP] Cliente no encontrado o sin teléfono")
                except Exception as e:
                    print(f"[WHATSAPP] Error enviando mensaje: {str(e)}")
                
                return {"message": f"Dte created successfully with folio: {dte_response}"}
            else:
                return {"message": "Sale not found"}
        else:
            return {"message": "Dte creation failed"}

@sales.get("/reject_sale_payment/{id}/{status_id}")
def reject_sale_payment(id: int, status_id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    SaleClass(db).change_status(id, status_id)

    reverse_response = SaleClass(db).reverse(id)

    # Enviar alerta de pago rechazado por WhatsApp
    try:
        # Obtener datos de la venta y cliente
        sale = db.query(SaleModel).filter(SaleModel.id == id).first()
        if sale:
            customer = db.query(CustomerModel).filter(CustomerModel.id == sale.customer_id).first()
            if customer and customer.phone:
                whatsapp = WhatsappClass(db)
                whatsapp.send_rejected_payment_alert(
                    customer_phone=customer.phone,
                    id=sale.id
                )
                print(f"[WHATSAPP] Alerta de pago rechazado enviada al cliente {customer.phone}")
            else:
                print("[WHATSAPP] Cliente no encontrado o sin teléfono")
    except Exception as e:
        print(f"[WHATSAPP] Error enviando alerta de pago rechazado: {str(e)}")

    return {"message": reverse_response}
        
@sales.get("/delivered_sale/{id}")
def delivered_sale(id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    SaleClass(db).change_status(id, 4)
    
    # Enviar alerta de pedido entregado
    try:
        # Obtener datos de la venta y cliente
        sale = db.query(SaleModel).filter(SaleModel.id == id).first()
        if sale:
            customer = db.query(CustomerModel).filter(CustomerModel.id == sale.customer_id).first()
            if customer and customer.phone:
                whatsapp = WhatsappClass(db)
                whatsapp.send_order_delivered_alert(
                    customer_phone=customer.phone,
                    id=sale.id
                )
                print(f"[WHATSAPP] Alerta de pedido entregado enviada al cliente {customer.phone}")
            else:
                print("[WHATSAPP] Cliente no encontrado o sin teléfono")
    except Exception as e:
        print(f"[WHATSAPP] Error enviando alerta de pedido entregado: {str(e)}")

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
        # Manejar archivos con múltiples puntos (ej: imagen.android.jpg)
        extension = payment_support.filename.rsplit('.', 1)[-1].lower() if '.' in payment_support.filename else ''
        filename = f"payment_{timestamp}_{unique_id}.{extension}"
        FileClass(db).upload(payment_support, filename)
        response = SaleClass(db).store(form_data, filename)
    else:
        filename = None
        response = SaleClass(db).store(form_data)

    return {"message": response}


@sales.post("/upload_payment/{sale_id}")
def upload_payment(
    sale_id: int,
    payment_support: UploadFile = File(...),
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Sube el comprobante de pago para una venta existente.
    """
    try:
        # Verificar que la venta existe
        sale = db.query(SaleModel).filter(SaleModel.id == sale_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        unique_id = uuid.uuid4().hex[:8]
        # Manejar archivos con múltiples puntos (ej: imagen.android.jpg)
        extension = payment_support.filename.rsplit('.', 1)[-1].lower() if '.' in payment_support.filename else ''
        filename = f"payment_{timestamp}_{unique_id}.{extension}"
        
        # Subir archivo
        FileClass(db).upload(payment_support, filename)
        
        # Actualizar la venta con el nombre del archivo
        sale.payment_support = filename
        sale.updated_date = datetime.now()
        db.commit()
        
        return {"message": {"status": "success", "filename": filename, "message": "Comprobante de pago subido exitosamente"}}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir comprobante: {str(e)}")


@sales.delete("/delete_payment/{sale_id}")
def delete_payment(
    sale_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Elimina el comprobante de pago de una venta existente.
    """
    try:
        # Verificar que la venta existe
        sale = db.query(SaleModel).filter(SaleModel.id == sale_id).first()
        if not sale:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        
        # Verificar si tiene comprobante de pago
        if not sale.payment_support:
            raise HTTPException(status_code=404, detail="La venta no tiene comprobante de pago")
        
        # Eliminar el archivo físico
        FileClass(db).delete(sale.payment_support)
        
        # Actualizar la venta eliminando la referencia al archivo
        sale.payment_support = None
        sale.updated_date = datetime.now()
        db.commit()
        
        return {"message": {"status": "success", "message": "Comprobante de pago eliminado exitosamente"}}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar comprobante: {str(e)}")


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

@sales.delete("/delete/{sale_id}")
def delete_sale(
    sale_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Elimina una venta y sus productos asociados.
    Solo se pueden eliminar ventas que no tengan DTE generado (sin folio).
    """
    data = SaleClass(db).delete(sale_id)
    
    if data.get("status") == "error":
        raise HTTPException(status_code=400, detail=data["message"])
    
    return {"message": data}