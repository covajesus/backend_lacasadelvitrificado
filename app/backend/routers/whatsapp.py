from fastapi import APIRouter, Depends, Request, HTTPException, Response
from sqlalchemy.orm import Session
from app.backend.db.database import get_db
from app.backend.classes.whatsapp_class import WhatsappClass

whatsapp = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"]
)

@whatsapp.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Recibe eventos de WhatsApp (botones, mensajes, etc.)
    """
    try:
        body = await request.json()
        whatsapp_class = WhatsappClass(db)
        result = whatsapp_class.process_webhook(body)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
