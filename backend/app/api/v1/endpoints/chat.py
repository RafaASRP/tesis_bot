from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
import logging

router = APIRouter()
logger = logging.getLogger("govassist-chat")

@router.post("/query", response_model=ChatResponse)
async def chat_query(payload: ChatRequest):
    try:
        user_message = ""
        if payload.messages and len(payload.messages) > 0:
            user_message = payload.messages[-1].content
        
        logger.info(f"Procesando consulta conversacional: {user_message[:50]}...")
        
        reply = (
            f"Hola. He recibido tu solicitud sobre '{user_message}'. "
            "Para continuar con el trámite federal en gob.mx, por favor indícame los datos requeridos."
        )
        
        lower_msg = user_message.lower()
        if "curp" in lower_msg:
            reply = "Para consultar tu CURP, por favor proporciona tu nombre completo, fecha de nacimiento, estado y género."
        elif "acta" in lower_msg:
            reply = "Para el Acta de Nacimiento, necesito tu CURP o tus datos de filiación registral."
        elif "imss" in lower_msg or "semanas" in lower_msg:
            reply = "Para consultar tus Semanas Cotizadas del IMSS, necesito tu CURP y tu Número de Seguridad Social (NSS)."

        return ChatResponse(
            reply=reply,
            sources=["gob.mx", "Registro Nacional de Población"]
        )
    except Exception as e:
        logger.error(f"Error crítico en chat_query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
