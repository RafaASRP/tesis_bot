from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ChatQueryRequest(BaseModel):
    """Esquema de entrada para el endpoint conversacional accesible."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Consulta en lenguaje natural del ciudadano."
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Identificador anónimo de la sesión de interacción."
    )
    is_pre_test: bool = Field(
        default=False,
        description="Indica si la interacción pertenece a la fase Pre-test o Post-test."
    )


class ContextSourceItem(BaseModel):
    """Metadato de la fuente normativa recuperada por el pipeline RAG."""
    procedure: str
    source: str
    score: float


class ChatQueryResponse(BaseModel):
    """Esquema de salida estructurado y accesible para personas de 50+ años."""
    model_config = ConfigDict(protected_namespaces=())

    reply: str = Field(
        ...,
        description="Respuesta empática en lenguaje ciudadano sintetizada por el sistema."
    )
    suggested_action: Optional[str] = Field(
        default=None,
        description="Paso concreto siguiente para guiar al adulto mayor sin sobrecarga cognitiva."
    )
    latency_seconds: float = Field(
        ...,
        description="Latencia exacta de inferencia (métrica L) en segundos."
    )
    model_used: str = Field(
        ...,
        description="Identificador del motor o fallback que procesó la solicitud."
    )
    sources: List[ContextSourceItem] = Field(
        default_factory=list,
        description="Fragmentos normativos de respaldo jurídico utilizados."
    )
