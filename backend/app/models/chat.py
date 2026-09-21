from typing import List, Optional
from pydantic import BaseModel, Field

class MessageItem(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$", description="Rol del emisor del mensaje")
    content: str = Field(..., min_length=1, description="Contenido en texto plano del mensaje")

class ChatRequest(BaseModel):
    messages: List[MessageItem] = Field(..., description="Historial de la conversación")
    session_id: str = Field(default="default_session", description="ID efímero de la sesión de voz/texto")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Respuesta empática generada por el LLM o el fallback")
    detected_intent: Optional[str] = Field(
        default=None,
        description="Trámite detectado: curp, acta_nacimiento, nss, pasaporte, cedula"
    )
    required_data: Optional[List[str]] = Field(
        default_factory=list,
        description="Lista de entidades faltantes para ejecutar el RPA (ej. ['clave_curp'] o ['nombre', 'fecha_nacimiento'])"
    )
    is_fallback: bool = Field(default=False, description="Bandera que indica si la respuesta provino del sistema heurístico local")
