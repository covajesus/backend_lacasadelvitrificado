from fastapi import APIRouter, Depends, Request, HTTPException, Response, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.backend.db.database import get_db
from app.backend.classes.whatsapp_class import WhatsappClass
from app.backend.db.models import WhatsAppMessageModel
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin
from app.backend.auth.auth_user import get_current_active_user
from app.backend.schemas import UserLogin

whatsapp = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"]
)

@whatsapp.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    print("🔥 WEBHOOK POST RECIBIDO 🔥")

    try:
        try:
            body = await request.json()
        except Exception:
            print("⚠️ Body vacío o no JSON")
            return {"status": "ok"}

        print("📦 BODY:", body)

        whatsapp_class = WhatsappClass(db)

        # PROTECCIÓN TOTAL
        if not isinstance(body, dict):
            print("⚠️ Body no es dict")
            return {"status": "ok"}

        if "entry" not in body:
            print("⚠️ Sin entry")
            return {"status": "ok"}

        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                print(f"🔍 Change value: {value.keys()}")

                # MENSAJES (BOTONES / TEXTO)
                messages = value.get("messages", [])
                if messages:
                    print(f"📩 Procesando {len(messages)} mensajes")
                    for message in messages:
                        try:
                            whatsapp_class.handle_message(message)
                        except Exception as e:
                            print(f"❌ Error procesando mensaje: {str(e)}")

                # ESTADOS (DELIVERED / READ)
                statuses = value.get("statuses", [])
                if statuses:
                    print(f"📬 Procesando {len(statuses)} estados")
                    for status_item in statuses:
                        try:
                            print(f"🔄 Llamando handle_status con: {status_item}")
                            whatsapp_class.handle_status(status_item)
                        except Exception as e:
                            print(f"❌ Error procesando estado: {str(e)}")
                            import traceback
                            traceback.print_exc()
                else:
                    print("⚠️ No se encontraron 'statuses' en el webhook")

        return {"status": "ok"}

    except Exception as e:
        # NUNCA DEVOLVER 500 A WHATSAPP
        print("❌ ERROR WEBHOOK:", str(e))
        return {"status": "ok"}

@whatsapp.get("/webhook")
async def webhook_verify(request: Request):
    """
    Verificación inicial del webhook (Meta)
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    VERIFY_TOKEN = "MI_TOKEN_SECRETO"  # el mismo que pusiste en Meta

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Token inválido")

@whatsapp.get("/messages")
def get_messages(
    budget_id: Optional[int] = Query(None, description="Filtrar por ID de presupuesto"),
    sale_id: Optional[int] = Query(None, description="Filtrar por ID de venta"),
    status: Optional[str] = Query(None, description="Filtrar por estado (sent, delivered, read, failed)"),
    limit: int = Query(100, description="Límite de resultados"),
    db: Session = Depends(get_db)
):
    """
    Obtiene los mensajes de WhatsApp con filtros opcionales.
    Permite ver el estado actual de los mensajes (sent, delivered, read, failed).
    """
    whatsapp_class = WhatsappClass(db)
    messages = whatsapp_class.get_all_messages(
        budget_id=budget_id,
        sale_id=sale_id,
        status=status,
        limit=limit
    )
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "message_id": msg.message_id,
            "recipient_phone": msg.recipient_phone,
            "message_type": msg.message_type,
            "template_name": msg.template_name,
            "budget_id": msg.budget_id,
            "sale_id": msg.sale_id,
            "status": msg.status,
            "error_code": msg.error_code,
            "error_message": msg.error_message,
            "sent_date": msg.sent_date.isoformat() if msg.sent_date else None,
            "delivered_date": msg.delivered_date.isoformat() if msg.delivered_date else None,
            "read_date": msg.read_date.isoformat() if msg.read_date else None,
            "added_date": msg.added_date.isoformat() if msg.added_date else None,
            "updated_date": msg.updated_date.isoformat() if msg.updated_date else None
        })
    
    return {
        "status": "success",
        "count": len(result),
        "messages": result
    }

@whatsapp.get("/status/budget/{budget_id}")
def get_status_by_budget(
    budget_id: int,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado del mensaje de WhatsApp relacionado con un presupuesto específico.
    """
    whatsapp_class = WhatsappClass(db)
    messages = whatsapp_class.get_messages_by_budget(budget_id)
    
    if not messages:
        return {
            "message": {
                "budget_id": budget_id,
                "status": "not_found",
                "message": "No se encontraron mensajes de WhatsApp para este presupuesto",
                "data": None
            }
        }
    
    # Obtener el mensaje más reciente
    latest_message = messages[0]  # Ya está ordenado por fecha descendente
    
    return {
        "message": {
            "budget_id": budget_id,
            "status": "success",
            "data": {
                "id": latest_message.id,
                "message_id": latest_message.message_id,
                "recipient_phone": latest_message.recipient_phone,
                "message_type": latest_message.message_type,
                "template_name": latest_message.template_name,
                "status": latest_message.status,
                "error_code": latest_message.error_code,
                "error_message": latest_message.error_message,
                "sent_date": latest_message.sent_date.isoformat() if latest_message.sent_date else None,
                "delivered_date": latest_message.delivered_date.isoformat() if latest_message.delivered_date else None,
                "read_date": latest_message.read_date.isoformat() if latest_message.read_date else None,
                "added_date": latest_message.added_date.isoformat() if latest_message.added_date else None,
                "updated_date": latest_message.updated_date.isoformat() if latest_message.updated_date else None
            },
            "all_messages_count": len(messages)
        }
    }

@whatsapp.get("/messages/budget/{budget_id}")
def get_messages_by_budget(
    budget_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los mensajes de WhatsApp relacionados con un presupuesto específico.
    Útil para ver si el mensaje del presupuesto fue entregado o leído.
    """
    whatsapp_class = WhatsappClass(db)
    messages = whatsapp_class.get_messages_by_budget(budget_id)
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "message_id": msg.message_id,
            "recipient_phone": msg.recipient_phone,
            "message_type": msg.message_type,
            "template_name": msg.template_name,
            "status": msg.status,
            "error_code": msg.error_code,
            "error_message": msg.error_message,
            "sent_date": msg.sent_date.isoformat() if msg.sent_date else None,
            "delivered_date": msg.delivered_date.isoformat() if msg.delivered_date else None,
            "read_date": msg.read_date.isoformat() if msg.read_date else None,
            "added_date": msg.added_date.isoformat() if msg.added_date else None,
            "updated_date": msg.updated_date.isoformat() if msg.updated_date else None
        })
    
    return {
        "status": "success",
        "budget_id": budget_id,
        "count": len(result),
        "messages": result
    }

@whatsapp.get("/messages/sale/{sale_id}")
def get_messages_by_sale(
    sale_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los mensajes de WhatsApp relacionados con una venta específica.
    Útil para ver si el mensaje del DTE fue entregado o leído.
    """
    whatsapp_class = WhatsappClass(db)
    messages = whatsapp_class.get_messages_by_sale(sale_id)
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "message_id": msg.message_id,
            "recipient_phone": msg.recipient_phone,
            "message_type": msg.message_type,
            "template_name": msg.template_name,
            "status": msg.status,
            "error_code": msg.error_code,
            "error_message": msg.error_message,
            "sent_date": msg.sent_date.isoformat() if msg.sent_date else None,
            "delivered_date": msg.delivered_date.isoformat() if msg.delivered_date else None,
            "read_date": msg.read_date.isoformat() if msg.read_date else None,
            "added_date": msg.added_date.isoformat() if msg.added_date else None,
            "updated_date": msg.updated_date.isoformat() if msg.updated_date else None
        })
    
    return {
        "status": "success",
        "sale_id": sale_id,
        "count": len(result),
        "messages": result
    }

@whatsapp.get("/messages/status/{message_id}")
def get_message_status(
    message_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado actual de un mensaje específico por su message_id de WhatsApp.
    """
    whatsapp_class = WhatsappClass(db)
    message = whatsapp_class.get_message_by_id(message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    
    return {
        "status": "success",
        "message": {
            "id": message.id,
            "message_id": message.message_id,
            "recipient_phone": message.recipient_phone,
            "message_type": message.message_type,
            "template_name": message.template_name,
            "budget_id": message.budget_id,
            "sale_id": message.sale_id,
            "status": message.status,
            "error_code": message.error_code,
            "error_message": message.error_message,
            "sent_date": message.sent_date.isoformat() if message.sent_date else None,
            "delivered_date": message.delivered_date.isoformat() if message.delivered_date else None,
            "read_date": message.read_date.isoformat() if message.read_date else None,
            "added_date": message.added_date.isoformat() if message.added_date else None,
            "updated_date": message.updated_date.isoformat() if message.updated_date else None
        }
    }

@whatsapp.post("/statuses")
def list_statuses(
    page: int = 0,
    items_per_page: int = 10,
    budget_id: Optional[int] = None,
    sale_id: Optional[int] = None,
    status: Optional[str] = None,
    session_user: UserLogin = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los estados de los mensajes de WhatsApp con paginación.
    Permite filtrar por budget_id, sale_id y status.
    """
    # Construir query base
    query = db.query(WhatsAppMessageModel)
    
    if budget_id:
        query = query.filter(WhatsAppMessageModel.budget_id == budget_id)
    if sale_id:
        query = query.filter(WhatsAppMessageModel.sale_id == sale_id)
    if status:
        query = query.filter(WhatsAppMessageModel.status == status)
    
    # Contar total
    total = query.count()
    
    # Aplicar paginación
    offset = page * items_per_page
    messages = query.order_by(WhatsAppMessageModel.added_date.desc()).offset(offset).limit(items_per_page).all()
    
    # Formatear resultados
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "message_id": msg.message_id,
            "recipient_phone": msg.recipient_phone,
            "message_type": msg.message_type,
            "template_name": msg.template_name,
            "budget_id": msg.budget_id,
            "sale_id": msg.sale_id,
            "status": msg.status,
            "error_code": msg.error_code,
            "error_message": msg.error_message,
            "sent_date": msg.sent_date.isoformat() if msg.sent_date else None,
            "delivered_date": msg.delivered_date.isoformat() if msg.delivered_date else None,
            "read_date": msg.read_date.isoformat() if msg.read_date else None,
            "added_date": msg.added_date.isoformat() if msg.added_date else None,
            "updated_date": msg.updated_date.isoformat() if msg.updated_date else None
        })
    
    return {
        "message": {
            "data": result,
            "total": total,
            "page": page,
            "items_per_page": items_per_page,
            "total_pages": (total + items_per_page - 1) // items_per_page if items_per_page > 0 else 0
        }
    }
