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

@sales.get("/accept_sale_payment/{id}/{dte_type_id}/{status_id}/{dte_status_id}")
def accept_sale_payment(id: int, dte_type_id: int, status_id: int, dte_status_id: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if status_id == 2:
        try:
            change_status_result = SaleClass(db).change_status(id, status_id)
            
            # Verificar si el resultado es un diccionario con error
            if isinstance(change_status_result, dict) and change_status_result.get("status") == "error":
                raise HTTPException(status_code=500, detail=change_status_result.get("message", "Error al cambiar estado de la venta"))
            
            # Si ya está en ese estado, retornar mensaje
            if change_status_result == "Sale already in this status":
                return {"message": {"status": "info", "message": "La venta ya está en este estado"}}
            
            if change_status_result == "No data found":
                raise HTTPException(status_code=404, detail="Venta no encontrada")
        except HTTPException:
            # Re-lanzar HTTPException sin modificar
            raise
        except Exception as e:
            # Manejar error de bloqueo de fila
            error_msg = str(e).lower()
            error_msg_original = str(e)
            
            if "could not obtain lock" in error_msg or "lock" in error_msg or "deadlock" in error_msg or "being processed" in error_msg or "timeout" in error_msg or "wait" in error_msg:
                print(f"[ERROR] Error de bloqueo al aceptar pago de venta {id}: {error_msg_original}")
                raise HTTPException(status_code=409, detail="La venta está siendo procesada por otro usuario. Por favor, espere unos segundos e intente nuevamente.")
            
            # Verificar si es un error de stock o validación
            if "stock" in error_msg or "insuficiente" in error_msg or "disponible" in error_msg or "lotes" in error_msg or "inventario" in error_msg:
                print(f"[ERROR] Error de stock al aceptar pago de venta {id}: {error_msg_original}")
                raise HTTPException(status_code=400, detail=f"Error de validación: {error_msg_original}")
            
            # Log del error para debugging
            print(f"[ERROR] Error inesperado al aceptar pago de venta {id}: {error_msg_original}")
            print(f"[ERROR] Tipo de error: {type(e).__name__}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Error al aceptar el pago: {error_msg_original}")

        # Actualizar dte_type_id y dte_status_id según si se genera DTE o no
        # Si dte_status_id == 1: usar el dte_type_id del parámetro (1=Boleta, 2=Factura)
        # Si dte_status_id != 1: establecer dte_type_id = 2 (Sin DTE)
        sale = db.query(SaleModel).filter(SaleModel.id == id).first()
        if sale:
            print(f"[DEBUG] Parámetros recibidos - dte_status_id: {dte_status_id}, dte_type_id: {dte_type_id}")
            print(f"[DEBUG] dte_type_id actual en venta: {sale.dte_type_id}")
            
            # Guardar dte_status_id
            sale.dte_status_id = dte_status_id
            
            if dte_status_id == 1:
                sale.dte_type_id = dte_type_id  # Usar el dte_type_id que viene del frontend
                print(f"[DEBUG] Actualizando dte_type_id a: {dte_type_id} (1=Boleta, 2=Factura)")
            else:
                sale.dte_type_id = 2  # Sin DTE
                print(f"[DEBUG] Sin DTE, estableciendo dte_type_id = 2")
            
            sale.updated_date = datetime.now()
            db.commit()
            db.refresh(sale)  # Refrescar para asegurar que tenemos el valor actualizado
            print(f"[DEBUG] dte_status_id guardado en BD: {sale.dte_status_id}")
            print(f"[DEBUG] dte_type_id guardado en BD: {sale.dte_type_id}")
            print(f"[DEBUG] dte_type_id después de refresh: {sale.dte_type_id}")

        # Retornar éxito después de aceptar el pago
        return {
            "status": "success",
            "message": "Payment accepted successfully."
        }

@sales.get("/send_dte")
def send_dte(db: Session = Depends(get_db)):
    """
    Procesa todas las ventas con status_id = 2 (aceptadas):
    - Si NO tiene folio y dte_status_id == 1: Genera DTE, envía WhatsApp y actualiza folio
    - Si NO tiene folio y dte_status_id != 1: No hace nada
    - Si YA tiene folio: No hace nada (ya está procesada)
    """
    try:
        # Buscar todas las ventas con status_id = 2 (aceptadas)
        sales = db.query(SaleModel).filter(SaleModel.status_id == 2).all()
        
        if not sales:
            return {
                "status": "info",
                "message": "No hay ventas con status_id = 2 para procesar",
                "processed": 0,
                "success": 0,
                "errors": 0,
                "skipped": 0,
                "details": []
            }
        
        processed_count = 0
        success_count = 0
        error_count = 0
        skipped_count = 0
        details = []
        
        whatsapp = WhatsappClass(db)
        
        for sale in sales:
            try:
                # Si ya tiene folio, saltar (ya está procesada)
                if sale.folio:
                    skipped_count += 1
                    details.append({
                        "sale_id": sale.id,
                        "status": "skipped",
                        "message": f"Venta {sale.id} ya tiene folio ({sale.folio}), no requiere procesamiento"
                    })
                    continue
                
                # Si no tiene folio, revisar dte_status_id
                if not sale.folio:
                    # Si dte_status_id == 1: quiere boleta o factura
                    if sale.dte_status_id == 1:
                        processed_count += 1
                        
                        # Verificar que la venta tenga dte_type_id configurado (debe ser 1, no 2 que significa "Sin DTE")
                        if sale.dte_type_id == 2:
                            skipped_count += 1
                            details.append({
                                "sale_id": sale.id,
                                "status": "skipped",
                                "message": f"Venta {sale.id} tiene dte_status_id=1 pero dte_type_id=2 (inconsistencia)"
                            })
                            continue
                        
                        # Generar el DTE
                        print(f"[SEND_DTE] La venta {sale.id} no tiene folio, generando DTE...")
                        print(f"[SEND_DTE] dte_type_id en venta: {sale.dte_type_id}")
                        
                        dte_response = DteClass(db).generate_dte(sale.id)
                        
                        if dte_response and dte_response > 0:  # Si se generó el DTE y retornó un folio
                            # Actualizar el folio en la venta
                            sale.folio = dte_response
                            sale.updated_date = datetime.now()
                            db.commit()
                            db.refresh(sale)
                            print(f"[SEND_DTE] DTE generado exitosamente para venta {sale.id} con folio: {dte_response}")
                        else:
                            # Si generate_dte retornó 0, significa que falló
                            print(f"[ERROR] generate_dte retornó 0 o None para venta {sale.id}")
                            error_count += 1
                            details.append({
                                "sale_id": sale.id,
                                "status": "error",
                                "message": f"No se pudo generar el DTE para la venta {sale.id}"
                            })
                            continue
                        
                        # Obtener datos del cliente
                        customer = db.query(CustomerModel).filter(CustomerModel.id == sale.customer_id).first()
                        if not customer:
                            error_count += 1
                            details.append({
                                "sale_id": sale.id,
                                "status": "error",
                                "message": f"Cliente no encontrado para la venta {sale.id}"
                            })
                            continue
                        
                        if not customer.phone:
                            error_count += 1
                            details.append({
                                "sale_id": sale.id,
                                "status": "error",
                                "message": f"El cliente {customer.id} no tiene teléfono registrado para la venta {sale.id}"
                            })
                            continue
                        
                        # Determinar tipo de DTE
                        dte_type = "Boleta Electrónica" if sale.dte_type_id == 1 else "Factura Electrónica"
                        
                        # Formatear fecha
                        date_formatted = sale.added_date.strftime("%d-%m-%Y")
                        
                        # Enviar WhatsApp del DTE
                        whatsapp.send_dte(
                            customer_phone=customer.phone,
                            dte_type=dte_type,
                            folio=sale.folio,
                            date=date_formatted,
                            amount=int(sale.total),
                            dynamic_value=sale.folio  # Usar el folio como valor dinámico
                        )
                        
                        print(f"[WHATSAPP] Mensaje DTE enviado al cliente {customer.phone} para venta {sale.id}")
                        
                        success_count += 1
                        details.append({
                            "sale_id": sale.id,
                            "status": "success",
                            "message": f"DTE generado y enviado por WhatsApp al cliente {customer.phone}",
                            "folio": sale.folio
                        })
                    
                    else:
                        # Si dte_status_id != 1: no quiere DTE, no hacer nada
                        skipped_count += 1
                        details.append({
                            "sale_id": sale.id,
                            "status": "skipped",
                            "message": f"Venta {sale.id} no requiere DTE (dte_status_id = {sale.dte_status_id})"
                        })
                        continue
                
            except Exception as e:
                error_count += 1
                print(f"[ERROR] Error procesando venta {sale.id}: {str(e)}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                details.append({
                    "sale_id": sale.id,
                    "status": "error",
                    "message": f"Error al procesar venta {sale.id}: {str(e)}"
                })
        
        return {
            "status": "success",
            "message": f"Procesadas {processed_count} ventas. Exitosas: {success_count}, Errores: {error_count}, Omitidas: {skipped_count}",
            "processed": processed_count,
            "success": success_count,
            "errors": error_count,
            "skipped": skipped_count,
            "details": details
        }
        
    except Exception as e:
        print(f"[ERROR] Error en send_dte: {str(e)}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Error al procesar DTEs: {str(e)}"
        }

@sales.get("/reject_sale_payment/{id}/{status_id}")
def reject_sale_payment(id: int, status_id:int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    SaleClass(db).change_status(id, status_id)

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

    return {"message": "Payment rejected successfully"}

@sales.get("/reverse/{orderId}")
def reverse_sale(orderId: int, session_user: UserLogin = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Endpoint para revertir una venta.
    Devuelve todos los productos al inventario y rechaza la venta.
    """
    try:
        # Revertir movimientos de inventario
        reverse_response = SaleClass(db).reverse(orderId)
        
        # Cambiar el status de la venta a rechazado (status_id = 3)
        change_status_result = SaleClass(db).change_status(orderId, 3)
        
        # Verificar si hubo error al cambiar status
        if isinstance(change_status_result, dict) and change_status_result.get("status") == "error":
            return {"message": {"status": "error", "message": change_status_result.get("message", "Error al cambiar estado de la venta")}}
        
        return {"message": {"status": "success", "message": "Venta revertida exitosamente. Productos devueltos al inventario."}}
    except Exception as e:
        print(f"[ERROR] Error al revertir venta {orderId}: {str(e)}")
        return {"message": {"status": "error", "message": f"Error al revertir la venta: {str(e)}"}}
        
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