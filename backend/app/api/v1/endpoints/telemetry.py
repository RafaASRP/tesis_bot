import logging
from fastapi import APIRouter, HTTPException, status
from backend.app.models.telemetry import (
    TaskTelemetryRequest,
    SUSSubmissionRequest,
    TelemetryResponse
)
from backend.app.core.supabase import supabase_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/task",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar métricas de desempeño cuantitativo de tarea (T, E, L, S)"
)
async def record_task_telemetry(payload: TaskTelemetryRequest) -> TelemetryResponse:
    """
    Persiste el rendimiento de interacción del usuario en un trámite específico.
    Captura:
    - T: Tiempo total de resolución en segundos.
    - E: Cantidad de errores o correcciones cometidas por el participante.
    - L: Latencia total del modelo de inferencia.
    - S: Éxito dicotómico (1 = Trámite completado / 0 = Abandono).
    """
    try:
        record = {
            "session_id": payload.session_id,
            "procedure_name": payload.procedure_name,
            "is_pre_test": payload.is_pre_test,
            "task_time_seconds": payload.task_time_seconds,
            "user_errors_count": payload.user_errors_count,
            "llm_latency_seconds": payload.llm_latency_seconds,
            "success": payload.success,
            "voice_used": payload.voice_used
        }

        result = supabase_manager.insert_record("telemetry_metrics", record)
        
        return TelemetryResponse(
            status=result["status"],
            record_type="task_performance",
            sus_score=None
        )
    except Exception as e:
        logger.error(f"Error registrando métricas de tarea: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fallo al persistir la telemetría de rendimiento."
        )


@router.post(
    "/sus",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar respuestas del cuestionario estandarizado SUS y calcular puntaje"
)
async def record_sus_evaluation(payload: SUSSubmissionRequest) -> TelemetryResponse:
    """
    Calcula el puntaje global de la Escala de Usabilidad del Sistema (Brooke, 1996)
    a partir de los 10 reactivos Likert y lo guarda para contraste pre-test vs. post-test.
    """
    try:
        score = payload.compute_sus_score()

        record = {
            "session_id": payload.session_id,
            "is_pre_test": payload.is_pre_test,
            "q1": payload.q1,
            "q2": payload.q2,
            "q3": payload.q3,
            "q4": payload.q4,
            "q5": payload.q5,
            "q6": payload.q6,
            "q7": payload.q7,
            "q8": payload.q8,
            "q9": payload.q9,
            "q10": payload.q10,
            "sus_score": score
        }

        result = supabase_manager.insert_record("sus_responses", record)

        return TelemetryResponse(
            status=result["status"],
            record_type="sus_evaluation",
            sus_score=score
        )
    except Exception as e:
        logger.error(f"Error registrando escala SUS: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fallo al procesar el cuestionario de usabilidad."
        )
