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

                # MENSAJES (BOTONES / TEXTO)
                for message in value.get("messages", []):
                    whatsapp_class.handle_message(message)

                # ESTADOS (DELIVERED / READ)
                for status in value.get("statuses", []):
                    whatsapp_class.handle_status(status)

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
