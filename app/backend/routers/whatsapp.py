from fastapi import APIRouter, Depends, Request, HTTPException, Response
from app.backend.db.database import get_db
from sqlalchemy.orm import Session
from app.backend.classes.whatsapp_class import WhatsappClass

whatsapp = APIRouter(
    prefix="/whatsapp",
    tags=["WhatsApp"]
)

@whatsapp.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook endpoint para recibir notificaciones de WhatsApp
    """
    try:
        # Obtener el cuerpo de la petición
        body = await request.json()
        
        # Procesar el webhook con WhatsappClass
        whatsapp_class = WhatsappClass(db)
        result = whatsapp_class.process_webhook(body)
        
        return {"status": "success", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

@whatsapp.get("/webhook")
async def webhook_verify(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint para verificación del webhook (usado por WhatsApp para validar la URL)
    WhatsApp requiere que se retorne el challenge como texto plano
    """
    try:
        # Obtener parámetros de query (usualmente 'hub.mode', 'hub.verify_token', 'hub.challenge')
        query_params = request.query_params
        
        # Procesar la verificación con WhatsappClass
        whatsapp_class = WhatsappClass(db)
        result = whatsapp_class.verify_webhook(query_params)
        
        # Si result es un número (challenge), retornarlo como texto plano
        if isinstance(result, (int, str)) and str(result).isdigit():
            return Response(content=str(result), media_type="text/plain")
        
        # Si es un error, retornar JSON
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying webhook: {str(e)}")

