import os
import re
import logging
from typing import List, Dict, Tuple, Any, Optional
from groq import AsyncGroq
from app.models.chat import MessageItem
from app.core.config import settings

logger = logging.getLogger(__name__)

class GovAssistNLP:
    """
    Motor de Procesamiento de Lenguaje Natural impulsado por Groq LPU (Llama 3 70b).
    Diseñado con un prompt empático para ciudadanos de 50+ años y un sistema de fallback
    heurístico local para garantizar resiliencia en la extracción de intenciones.
    """
    def __init__(self):
        self.api_key = getattr(settings, "GROQ_API_KEY", os.environ.get("GROQ_API_KEY", ""))
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None
        self.model = "llama3-70b-8192"
        
        self.system_prompt = {
            "role": "system",
            "content": (
                "Eres GovAssist, un asistente gubernamental empático, paciente y claro, diseñado para "
                "ayudar a adultos mayores (50+ años) en México a realizar trámites federales en gob.mx. "
                "Habla de usted, usa un lenguaje ciudadano, evita tecnicismos informáticos y sé breve. "
                "Actualmente puedes ayudar con: 1. Consulta de CURP. "
                "Si el usuario quiere consultar su CURP, pregúntale amablemente si conoce su Clave de 18 caracteres "
                "o si prefiere buscarla usando sus Datos Personales (nombre, fecha de nacimiento, sexo y estado). "
                "Si el usuario menciona otro trámite (Acta, IMSS, Pasaporte, Cédula), indícale que pronto estarán disponibles."
            )
        }

    def _heuristic_fallback(self, user_text: str) -> Tuple[str, Optional[str], List[str]]:
        """
        Contingencia local basada en expresiones regulares para clasificar intenciones
        si el servicio en la nube (Groq) no está disponible o falla por latencia.
        """
        text = user_text.lower()
        intent = None
        required = []
        
        # Detección Heurística de CURP
        if "curp" in text:
            intent = "curp"
            curp_match = re.search(r"[a-z]{4}\d{6}[hm][a-z]{5}[a-z0-9]\d", text)
            if curp_match:
                reply = f"He detectado tu CURP: {curp_match.group(0).upper()}. ¿Deseas que descargue tu documento oficial ahora?"
            else:
                reply = "Para descargar tu CURP, ¿tienes tu clave de 18 letras y números a la mano, o prefieres que la busquemos por tu nombre y fecha de nacimiento?"
                required = ["modalidad_busqueda"]
        elif any(word in text for word in ["acta", "nacimiento"]):
            intent = "acta_nacimiento"
            reply = "El trámite de Acta de Nacimiento estará disponible muy pronto. Por ahora, puedo ayudarte con tu CURP."
        else:
            reply = "Hola. Soy tu asistente de trámites. ¿En qué te puedo ayudar hoy? Si gustas, puedo buscar y descargar tu CURP."
            
        return reply, intent, required

    async def generate_response(self, messages: List[MessageItem]) -> Dict[str, Any]:
        user_message = messages[-1].content if messages else ""
        
        if not self.client:
            logger.warning("GROQ_API_KEY no configurada. Activando fallback heurístico local.")
            reply, intent, required = self._heuristic_fallback(user_message)
            return {"reply": reply, "detected_intent": intent, "required_data": required, "is_fallback": True}

        formatted_messages = [self.system_prompt] + [{"role": m.role, "content": m.content} for m in messages]

        try:
            chat_completion = await self.client.chat.completions.create(
                messages=formatted_messages,
                model=self.model,
                temperature=0.3,
                max_tokens=256,
            )
            
            llm_reply = chat_completion.choices[0].message.content
            
            # Análisis ligero de intención post-respuesta para guiar al frontend
            _, fallback_intent, _ = self._heuristic_fallback(user_message)
            
            return {
                "reply": llm_reply,
                "detected_intent": fallback_intent, 
                "required_data": [], 
                "is_fallback": False
            }
            
        except Exception as e:
            logger.error(f"Fallo en Groq LPU: {str(e)}. Activando fallback heurístico local.")
            reply, intent, required = self._heuristic_fallback(user_message)
            return {"reply": reply, "detected_intent": intent, "required_data": required, "is_fallback": True}

nlp_engine = GovAssistNLP()
