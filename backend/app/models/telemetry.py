from pydantic import BaseModel, Field

class TelemetryTaskCreate(BaseModel):
    session_id: str = Field(..., description="ID único de la sesión del usuario")
    procedure_name: str = Field(..., description="Nombre del trámite: curp, acta_nacimiento, nss, pasaporte, cedula")
    evaluation_stage: str = Field(..., pattern="^(pre_test|post_test)$", description="Fase de evaluación cuasi-experimental")
    task_time_seconds: float = Field(..., ge=0, description="Tiempo de ejecución en segundos (T)")
    error_count: int = Field(..., ge=0, description="Número de errores cometidos (E)")
    llm_latency_seconds: float = Field(..., ge=0, description="Latencia del motor NLP/LLM (L)")
    success_status: int = Field(..., ge=0, le=1, description="Éxito dicotómico (S): 1 = Éxito, 0 = Abandono")

class TelemetrySUSCreate(BaseModel):
    session_id: str = Field(..., description="ID único de la sesión del usuario")
    evaluation_stage: str = Field(..., pattern="^(pre_test|post_test)$", description="Fase de evaluación")
    q1: int = Field(..., ge=0, le=4)
    q2: int = Field(..., ge=0, le=4)
    q3: int = Field(..., ge=0, le=4)
    q4: int = Field(..., ge=0, le=4)
    q5: int = Field(..., ge=0, le=4)
    q6: int = Field(..., ge=0, le=4)
    q7: int = Field(..., ge=0, le=4)
    q8: int = Field(..., ge=0, le=4)
    q9: int = Field(..., ge=0, le=4)
    q10: int = Field(..., ge=0, le=4)
    total_sus_score: float = Field(..., ge=0, le=100, description="Puntaje global SUS escalado de 0 a 100")
