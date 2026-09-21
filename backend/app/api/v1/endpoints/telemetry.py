import logging
from fastapi import APIRouter, HTTPException
from backend.app.models.telemetry import TelemetryTaskCreate, TelemetrySUSCreate
from backend.app.core.supabase import supabase

logger = logging.getLogger(__name__)
router = APIRouter()

# Almacén temporal en memoria para respaldo offline (fallback)
OFFLINE_TELEMETRY_TASKS = []
OFFLINE_TELEMETRY_SUS = []

@router.post("/task", status_code=201)
async def record_task_telemetry(data: TelemetryTaskCreate):
    """
    Registra las métricas cuantitativas de rendimiento (T, E, L, S)
    para la comparativa Pre-test vs Post-test.
    """
    try:
        if supabase:
            response = supabase.table("telemetry_tasks").insert(data.model_dump()).execute()
            return {"status": "success", "persisted_in": "supabase", "data": response.data}
        else:
            OFFLINE_TELEMETRY_TASKS.append(data.model_dump())
            logger.warning("Supabase no disponible. Métrica de tarea guardada en memoria local (offline).")
            return {"status": "success", "persisted_in": "local_memory", "data": data.model_dump()}
    except Exception as e:
        logger.error(f"Error al persistir telemetría de tarea: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al registrar telemetría.")

@router.post("/sus", status_code=201)
async def record_sus_telemetry(data: TelemetrySUSCreate):
    """
    Registra las respuestas del cuestionario SUS (Escala de Usabilidad del Sistema)
    y su puntaje global calculado.
    """
    try:
        if supabase:
            response = supabase.table("telemetry_sus").insert(data.model_dump()).execute()
            return {"status": "success", "persisted_in": "supabase", "data": response.data}
        else:
            OFFLINE_TELEMETRY_SUS.append(data.model_dump())
            logger.warning("Supabase no disponible. Cuestionario SUS guardado en memoria local (offline).")
            return {"status": "success", "persisted_in": "local_memory", "data": data.model_dump()}
    except Exception as e:
        logger.error(f"Error al persistir cuestionario SUS: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno al registrar evaluación SUS.")
