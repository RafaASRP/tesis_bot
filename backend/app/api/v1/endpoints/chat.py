import logging
from fastapi import APIRouter, HTTPException, status
from backend.app.models.chat import ChatQueryRequest, ChatQueryResponse, ContextSourceItem
from backend.app.services.rag.rag_service import rag_service
from backend.app.services.llm.groq_client import groq_engine
from backend.app.core.supabase import supabase_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/query",
    response_model=ChatQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Consulta conversacional accesible con RAG y LLM"
)
async def query_citizen_assistant(request: ChatQueryRequest) -> ChatQueryResponse:
    """
    Procesa la consulta ciudadana en lenguaje natural:
    1. Recupera fragmentos normativos relevantes mediante similitud por coseno (RAG).
    2. Sintetiza una respuesta empática y accesible (Groq LPU o Fallback local).
    3. Registra de forma asíncrona la métrica de latencia L para la evaluación cuasi-experimental.
    """
    try:
        user_message = request.message.strip()
        if not user_message:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El mensaje del ciudadano no puede estar vacío."
            )

        # 1. Recuperación de contexto normativo
        raw_sources = rag_service.retrieve_context(user_message)
        context_text = rag_service.get_formatted_context(user_message)

        # Mapeo a esquema tipado
        source_items = [
            ContextSourceItem(
                procedure=item["procedure"],
                source=item["source"],
                score=round(item["score"], 4)
            )
            for item in raw_sources
        ]

        # 2. Inferencia LLM con medición de latencia (L)
        inference_result = await groq_engine.generate_response(
            user_query=user_message,
            context_str=context_text
        )

        latency = inference_result["latency_seconds"]
        reply_text = inference_result["reply"]
        model_name = inference_result["model_used"]

        # Determinación de sugerencia de acción clara para adultos mayores
        suggested_action = "Tener sus documentos oficiales a la mano"
        lower_query = user_message.lower()
        if "curp" in lower_query:
            suggested_action = "Consultar o descargar constancia oficial de CURP"
        elif "pasaporte" in lower_query:
            suggested_action = "Revisar requisitos y preparar pago con descuento INAPAM"
        elif "semanas" in lower_query or "imss" in lower_query:
            suggested_action = "Solicitar reporte de semanas cotizadas a su correo"
        elif "acta" in lower_query:
            suggested_action = "Verificar datos de filiación registral (nombre de padres)"
        elif "cédula" in lower_query or "cedula" in lower_query:
            suggested_action = "Consultar número de cédula en el Registro Nacional"

        # 3. Registro telemetría de latencia (L) en contingencia/Supabase
        telemetry_record = {
            "session_id": request.session_id or "anonymous_session",
            "is_pre_test": request.is_pre_test,
            "latency_seconds": latency,
            "model_used": model_name,
            "query_length": len(user_message),
            "sources_count": len(source_items)
        }
        supabase_manager.insert_record("telemetry_metrics", telemetry_record)

        return ChatQueryResponse(
            reply=reply_text,
            suggested_action=suggested_action,
            latency_seconds=latency,
            model_used=model_name,
            sources=source_items
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interno procesando consulta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocurrió un error al procesar la orientación del trámite."
        )
