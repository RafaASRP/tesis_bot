from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.llm.groq_client import get_groq_response
import logging

router = APIRouter()
logger = logging.getLogger("govassist-chat")

@router.post("/query", response_model=ChatResponse)
async def chat_query(payload: ChatRequest):
    try:
        messages = payload.messages or []
        last_msg = messages[-1].content if messages else ""
        
        logger.info(f"Procesando historial de chat ({len(messages)} mensajes). Último: {last_msg[:40]}...")
        
        # Enviar todo el historial para mantener memoria contextual
        reply = get_groq_response(messages)

        return ChatResponse(
            reply=reply,
            sources=["gob.mx", "GovAssist Core Engine"]
        )
    except Exception as e:
        logger.error(f"Error crítico en chat_query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
