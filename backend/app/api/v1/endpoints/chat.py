import time
import logging
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse
from app.services.llm.groq_client import nlp_engine

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query", response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """
    Endpoint conversacional principal. 
    Recibe el historial de la PWA, detecta intenciones de trámites federales
    y devuelve una respuesta empática en lenguaje ciudadano.
    """
    start_time = time.time()
    try:
        # Procesamiento de Lenguaje Natural (Groq Cloud + Fallback local)
        response_data = await nlp_engine.generate_response(request.messages)
        
        # Cálculo de latencia (L) para telemetría cuantitativa
        latency = round(time.time() - start_time, 3)
        logger.info(f"NLP Query Procesada. Latencia (L): {latency}s | Intención: {response_data['detected_intent']}")
        
        return ChatResponse(
            reply=response_data["reply"],
            detected_intent=response_data["detected_intent"],
            required_data=response_data["required_data"],
            is_fallback=response_data["is_fallback"]
        )
    except Exception as e:
        logger.error(f"Error en el endpoint de chat: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno procesando la conversación.")
