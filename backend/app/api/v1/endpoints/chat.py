from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.llm.groq_client import get_groq_response
import logging

router = APIRouter()
logger = logging.getLogger("govassist-chat")

@router.post("/query", response_model=ChatResponse)
async def chat_query(payload: ChatRequest):
    try:
        user_message = ""
        if payload.messages and len(payload.messages) > 0:
            user_message = payload.messages[-1].content
        
        logger.info(f"Procesando entrada natural de usuario: {user_message[:60]}...")
        
        # Invocación al motor inteligente Groq LPU con prompt empático y fallback heurístico
        reply = get_groq_response(user_message)

        return ChatResponse(
            reply=reply,
            sources=["gob.mx", "GovAssist Core Engine"]
        )
    except Exception as e:
        logger.error(f"Error crítico en chat_query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
