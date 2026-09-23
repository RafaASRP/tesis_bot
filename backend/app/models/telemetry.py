from pydantic import BaseModel, Field
from typing import List

class TelemetryPayload(BaseModel):
    session_id: str = Field(..., description="Identificador único de la sesión")
    procedure_type: str = Field(..., description="Tipo de trámite (ej. CURP, Acta)")
    task_time_seconds: float = Field(..., ge=0.0, description="Tiempo de ejecución (T)")
    error_count: int = Field(default=0, ge=0, description="Tasa de error (E)")
    llm_latency_ms: float = Field(..., ge=0.0, description="Latencia del LLM (L)")
    success: int = Field(..., ge=0, le=1, description="Tasa de éxito dicotómica (S: 1=Éxito / 0=Abandono)")
    is_post_test: bool = Field(default=True, description="Bandera para diseño cuasi-experimental")

class SUSPayload(BaseModel):
    session_id: str = Field(..., description="Identificador único de la sesión")
    scores: List[int] = Field(..., min_length=10, max_length=10, description="10 reactivos Likert")
    global_score: float = Field(..., ge=0.0, le=100.0, description="Puntaje global SUS (0 a 100)")
