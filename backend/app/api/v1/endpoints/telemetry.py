from fastapi import APIRouter, BackgroundTasks
import logging
from app.models.telemetry import TelemetryPayload, SUSPayload
from app.core.supabase import get_supabase_client

router = APIRouter()
logger = logging.getLogger("govassist-telemetry")

def _save_to_supabase(table: str, data: dict):
    """Función de contingencia para escritura asíncrona segura."""
    try:
        client = get_supabase_client()
        if client:
            client.table(table).insert(data).execute()
            logger.info(f"Telemetría registrada en {table} exitosamente.")
        else:
            logger.warning(f"Modo offline activo. Métrica {table} guardada en bitácora local: {data}")
    except Exception as e:
        logger.error(f"Fallo al registrar telemetría en {table}: {str(e)}. Fallback a log local: {data}")

@router.post("/metrics", summary="Registra métricas cuantitativas T, E, L, S")
async def record_metrics(payload: TelemetryPayload, background_tasks: BackgroundTasks):
    """Captura métricas de rendimiento para la evaluación cuasi-experimental."""
    background_tasks.add_task(_save_to_supabase, "telemetry_metrics", payload.model_dump())
    return {"status": "success", "message": "Métricas T, E, L, S encoladas para registro."}

@router.post("/sus", summary="Registra evaluación de usabilidad SUS")
async def record_sus(payload: SUSPayload, background_tasks: BackgroundTasks):
    """Captura los 10 reactivos del cuestionario SUS y su puntaje global."""
    background_tasks.add_task(_save_to_supabase, "sus_evaluations", payload.model_dump())
    return {"status": "success", "message": "Evaluación SUS encolada para registro."}
