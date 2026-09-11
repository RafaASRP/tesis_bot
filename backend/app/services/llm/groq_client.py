import logging
import time
from typing import Dict, Any, Optional
from groq import Groq
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_CITIZEN = """Eres GovAssist, un asistente virtual empático, paciente y claro del Gobierno de México, especializado en orientar a personas adultas mayores sobre trámites oficiales.

Directrices obligatorias de comunicación:
1. Lenguaje: Habla en un tono respetuoso, cálido y sencillo. Evita tecnicismos burocráticos o informáticos.
2. Estructura: Da respuestas directas y breves. Usa listas con viñetas cortas. No escribas párrafos largos.
3. Costos: Indica siempre si el trámite es gratuito o si requiere pago. Si aplica beneficio de descuento con credencial INAPAM (50% en pasaporte), menciónalo explícitamente.
4. Veracidad: Basa tus respuestas únicamente en el contexto oficial provisto. Si no tienes la información exacta en el contexto, indícale amablemente al ciudadano dónde acudir o qué documento tener a la mano.
5. Claridad de acción: Termina con un solo paso concreto que el ciudadano deba realizar a continuación.
"""


class GroqInferenceEngine:
    """
    Motor de inferencia LLM optimizado en Groq LPU con modo de contingencia local.
    Mide la latencia de respuesta (L) para la telemetría experimental.
    """

    def __init__(self):
        self._client: Optional[Groq] = None
        self._is_mock: bool = True
        self.model = settings.GROQ_MODEL
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Inicializa el cliente oficial de Groq o activa contingencia local."""
        is_mock_key = "mock" in settings.GROQ_API_KEY or "tu_groq" in settings.GROQ_API_KEY
        if is_mock_key or not settings.GROQ_API_KEY:
            logger.warning("Groq API Key no válida. Activando motor de contingencia heurístico local.")
            self._is_mock = True
            return

        try:
            self._client = Groq(api_key=settings.GROQ_API_KEY)
            self._is_mock = False
            logger.info("Cliente Groq LPU inicializado exitosamente.")
        except Exception as e:
            logger.error(f"Fallo al inicializar Groq ({e}). Activando contingencia local.")
            self._is_mock = True

    def _generate_fallback_response(self, user_query: str, context_str: str) -> str:
        """
        Motor heurístico local: sintetiza una respuesta empática a partir
        del contexto normativo recuperado por RAG sin depender de conexión externa.
        """
        query_lower = user_query.lower()

        if "curp" in query_lower:
            return (
                "Hola. Con gusto le oriento sobre su CURP:\n\n"
                "• **Costo:** Es un trámite totalmente **gratuito**.\n"
                "• **Opciones:** Puede consultarla si ya conoce su clave de 18 caracteres o con su nombre completo, fecha y estado de nacimiento.\n"
                "• **Paso siguiente:** Tenga a la mano su acta de nacimiento para verificar los datos con exactitud."
            )
        elif "pasaporte" in query_lower:
            return (
                "Hola. Con gusto le oriento sobre el pasaporte mexicano:\n\n"
                "• **Descuento especial:** Si tiene 60 años o más y cuenta con credencial del **INAPAM**, recibe un **50% de descuento** en los derechos federales.\n"
                "• **Costos de referencia con INAPAM:** 3 años en $827.50 MXN, 6 años en $1,125.00 MXN o 10 años en $1,970.00 MXN.\n"
                "• **Cita:** El agendamiento de la cita es gratuito; el pago se hace únicamente en ventanilla bancaria.\n"
                "• **Paso siguiente:** Tenga a la mano su credencial de elector (INE), acta de nacimiento y credencial INAPAM vigente."
            )
        elif "semanas" in query_lower or "imss" in query_lower:
            return (
                "Hola. Con gusto le oriento sobre sus semanas cotizadas en el IMSS:\n\n"
                "• **Costo:** La consulta y la constancia oficial son **gratuitas**.\n"
                "• **Requisitos:** Necesita su CURP, su Número de Seguridad Social (NSS de 11 dígitos) y un correo electrónico personal.\n"
                "• **Paso siguiente:** Le llegará un documento en PDF a su correo con el detalle completo de sus patrones y semanas acumuladas."
            )
        elif "acta" in query_lower:
            return (
                "Hola. Con gusto le oriento sobre su copia certificada del acta de nacimiento:\n\n"
                "• **Costo:** La búsqueda es gratuita; la descarga requiere un pago estatal que varía según su estado de registro (por ejemplo, Tlaxcala $164.00 MXN).\n"
                "• **Requisitos:** Su CURP y el nombre completo de su padre o madre para confirmar su filiación.\n"
                "• **Paso siguiente:** Puede pagarla en línea con tarjeta bancaria o imprimir un formato para pagar en ventanilla del banco."
            )
        elif "cédula" in query_lower or "cedula" in query_lower:
            return (
                "Hola. Con gusto le oriento sobre la cédula profesional electrónica:\n\n"
                "• **Consulta pública:** Verificar si una persona tiene cédula registrada ante la SEP es **100% gratuito**.\n"
                "• **Requisitos para tramitarla:** e.firma vigente (SAT), CURP y que su escuela o universidad ya haya registrado su título.\n"
                "• **Paso siguiente:** Ingrese con su CURP al portal oficial para corroborar que su institución ya haya cargado su título."
            )

        # Síntesis general cuando hay contexto normativo recuperado
        if context_str and "No se encontró" not in context_str:
            primeras_lineas = [l for l in context_str.split("\n") if l.strip() and not l.startswith("---")][:4]
            resumen = " ".join(primeras_lineas)
            return (
                f"Hola. Con base en la información oficial de gob.mx:\n\n"
                f"{resumen}\n\n"
                f"• **Paso siguiente:** Indíqueme si desea que le guíe paso a paso en este trámite."
            )

        return (
            "Hola. Estoy aquí para asistirle con sus trámites oficiales (CURP, Acta de Nacimiento, Semanas del IMSS, Pasaporte y Cédula Profesional).\n\n"
            "• **Paso siguiente:** Por favor dígame cuál de estos documentos desea consultar o tramitar."
        )

    async def generate_response(self, user_query: str, context_str: str) -> Dict[str, Any]:
        """
        Genera la respuesta empática midiendo la latencia exacta (L en segundos).
        """
        start_time = time.perf_counter()

        if self._is_mock or not self._client:
            reply_text = self._generate_fallback_response(user_query, context_str)
            latency = time.perf_counter() - start_time
            return {
                "reply": reply_text,
                "latency_seconds": round(latency, 4),
                "model_used": "local-fallback-heuristic",
                "is_fallback": True
            }

        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_CITIZEN},
                {
                    "role": "user",
                    "content": f"Contexto normativo oficial:\n{context_str}\n\nPregunta del ciudadano:\n{user_query}"
                }
            ]

            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=500
            )

            latency = time.perf_counter() - start_time
            reply_text = response.choices[0].message.content

            return {
                "reply": reply_text,
                "latency_seconds": round(latency, 4),
                "model_used": self.model,
                "is_fallback": False
            }
        except Exception as err:
            logger.error(f"Error en inferencia Groq ({err}). Conmutando a fallback local.")
            reply_text = self._generate_fallback_response(user_query, context_str)
            latency = time.perf_counter() - start_time
            return {
                "reply": reply_text,
                "latency_seconds": round(latency, 4),
                "model_used": "local-fallback-heuristic",
                "is_fallback": True
            }


# Singleton del motor de inferencia Groq
groq_engine = GroqInferenceEngine()
