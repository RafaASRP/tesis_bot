from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskTelemetryRequest(BaseModel):
    """
    Registro de telemetría cuantitativa de desempeño en tareas (IHC).
    Mide el rendimiento del usuario durante la resolución del trámite.
    """
    model_config = ConfigDict(protected_namespaces=())

    session_id: str = Field(..., description="Identificador anónimo único del participante.")
    procedure_name: str = Field(..., description="Trámite evaluado (curp, acta, semanas, pasaporte, cedula).")
    is_pre_test: bool = Field(..., description="True si corresponde a la interacción directa en gob.mx, False si usó GovAssist.")
    task_time_seconds: float = Field(..., ge=0.0, description="Tiempo total de ejecución de la tarea (Métrica T).")
    user_errors_count: int = Field(..., ge=0, description="Cantidad de errores de navegación cometidos (Métrica E).")
    llm_latency_seconds: float = Field(default=0.0, ge=0.0, description="Latencia acumulada del motor de inferencia (Métrica L).")
    success: int = Field(..., ge=0, le=1, description="Éxito dicotómico en la tarea (Métrica S: 1=Éxito, 0=Abandono/Fallo).")
    voice_used: bool = Field(default=False, description="Indica si el participante utilizó el canal de voz accesible.")


class SUSSubmissionRequest(BaseModel):
    """
    Cuestionario estandarizado de la Escala de Usabilidad del Sistema (Brooke, 1996).
    10 reactivos en escala Likert del 1 (Totalmente en desacuerdo) al 5 (Totalmente de acuerdo).
    """
    model_config = ConfigDict(protected_namespaces=())

    session_id: str = Field(..., description="Identificador anónimo del participante.")
    is_pre_test: bool = Field(..., description="Fase de aplicación: Pre-test (portal estatal) o Post-test (GovAssist).")
    q1: int = Field(..., ge=1, le=5, description="1. Me gustaría utilizar este sistema con frecuencia.")
    q2: int = Field(..., ge=1, le=5, description="2. Encontré el sistema innecesariamente complejo.")
    q3: int = Field(..., ge=1, le=5, description="3. Pensé que el sistema era fácil de usar.")
    q4: int = Field(..., ge=1, le=5, description="4. Creo que necesitaría el apoyo de una persona técnica.")
    q5: int = Field(..., ge=1, le=5, description="5. Encontré que las funciones estaban bien integradas.")
    q6: int = Field(..., ge=1, le=5, description="6. Pensé que había demasiada inconsistencia en este sistema.")
    q7: int = Field(..., ge=1, le=5, description="7. Imagino que la mayoría de la gente aprendería a usarlo muy rápido.")
    q8: int = Field(..., ge=1, le=5, description="8. Encontré el sistema muy engorroso de usar.")
    q9: int = Field(..., ge=1, le=5, description="9. Me sentí muy confiado al usar el sistema.")
    q10: int = Field(..., ge=1, le=5, description="10. Necesité aprender muchas cosas antes de poder usarlo.")

    def compute_sus_score(self) -> float:
        """
        Cálculo estándar del puntaje SUS según la metodología de Brooke:
        - Reactivos impares (positivos: 1, 3, 5, 7, 9): Valor - 1
        - Reactivos pares (negativos: 2, 4, 6, 8, 10): 5 - Valor
        - Suma acumulada multiplicada por 2.5 para escalar a [0, 100].
        """
        odd_sum = (self.q1 - 1) + (self.q3 - 1) + (self.q5 - 1) + (self.q7 - 1) + (self.q9 - 1)
        even_sum = (5 - self.q2) + (5 - self.q4) + (5 - self.q6) + (5 - self.q8) + (5 - self.q10)
        return float((odd_sum + even_sum) * 2.5)


class TelemetryResponse(BaseModel):
    """Respuesta unificada de registro para la instrumentación experimental."""
    model_config = ConfigDict(protected_namespaces=())

    status: str = Field(..., description="Estado de la persistencia (success o fallback_saved).")
    record_type: str = Field(..., description="Tipo de métrica persistida.")
    sus_score: Optional[float] = Field(default=None, description="Puntaje SUS calculado [0-100] si aplica.")
