import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Almacén temporal en memoria RAM para el estado de la sesión (Slots por trámite)
# session_id -> {"procedure": "curp", "slots": {"nombre": None, "fecha": None, "estado": None, "genero": None}}
CONVERSATION_STATES = {}

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    # Inicializar o recuperar estado de la sesión
    if session_id not in CONVERSATION_STATES:
        CONVERSATION_STATES[session_id] = {
            "procedure": None,
            "slots": {"nombre": None, "fecha": None, "estado": None, "genero": None}
        }
    
    state = CONVERSATION_STATES[session_id]
    slots = state["slots"]
    
    # Obtener el último mensaje del usuario
    last_user_msg = messages_history[-1].content if messages_history else ""
    msg_lower = last_user_msg.lower()

    # Detección de trámite si no está definido
    if not state["procedure"]:
        if any(w in msg_lower for w in ['curp']):
            state["procedure"] = "curp"
        elif any(w in msg_lower for w in ['acta', 'nacimiento']):
            state["procedure"] = "acta"
        elif any(w in msg_lower for w in ['imss', 'semanas', 'cotizadas']):
            state["procedure"] = "imss"
        elif any(w in msg_lower for w in ['pasaporte', 'sre']):
            state["procedure"] = "pasaporte"
        elif any(w in msg_lower for w in ['cédula', 'cedula', 'profesional']):
            state["procedure"] = "cedula"

    # Si es CURP, aplicar lógica estricta de Slot-Filling conversacional
    if state["procedure"] == "curp":
        # Heurísticas de extracción para complementar al LLM y asegurar robustez
        if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']):
            slots["genero"] = "Hombre"
        elif any(w in msg_lower for w in ['mujer', 'femenino']):
            slots["genero"] = "Mujer"
            
        if any(w in msg_lower for w in ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'méxico', 'mexico', 'veracruz', 'oaxaca']):
            for estado_val in ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'méxico', 'mexico', 'veracruz', 'oaxaca']:
                if estado_val in msg_lower:
                    slots["estado"] = estado_val.capitalize()
                    
        if any(w in msg_lower for w in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or '200' in msg_lower or '199' in msg_lower:
            slots["fecha"] = last_user_msg
            
        if "me llamo" in msg_lower or "soy" in msg_lower or len(last_user_msg.split()) > 3:
            if not slots["nombre"] and not any(w in msg_lower for w in ['curp', 'hombre', 'mujer']):
                slots["nombre"] = last_user_msg

    # Construir prompt dinámico basado en los huecos (slots) faltantes
    missing_slots = [k for k, v in slots.items() if v is None] if state["procedure"] == "curp" else []
    
    system_prompt = (
        "Eres GovAssist Core, un asistente virtual altamente empático, cálido y paciente para adultos mayores de 50 años "
        "en México que realizan trámites en gob.mx.\n"
        f"Trámite actual detectado: {state['procedure'] or 'Ninguno'}\n"
        f"Datos recolectados hasta ahora para CURP: {slots}\n"
        f"Datos que AÚN FALTAN por recolectar: {missing_slots}\n\n"
        "INSTRUCCIONES CLAVE:\n"
        "1. Saluda siempre de forma cálida, humana y diferente (nunca uses respuestas idénticas robóticas).\n"
        "2. NUNCA vuelvas a pedir un dato que ya aparezca en los datos recolectados.\n"
        "3. Si el usuario habla de forma narrativa, extrae lo que te dio, agradéceselo con calidez, y pide ÚNICAMENTE el siguiente dato faltante de la lista.\n"
        "4. Si ya se tienen TODOS los datos de la CURP, indícale amablemente al usuario que estás procediendo a consultar gob.mx con Playwright."
    )

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        formatted_messages.append({"role": getattr(msg, "role", "user"), "content": getattr(msg, "content", str(msg))})

    if not api_key or "invalid" in api_key.lower():
        return f"¡Hola! Entiendo perfectamente. Me falta el siguiente dato para tu CURP: {missing_slots[0] if missing_slots else 'verificación'}."

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=formatted_messages,
            temperature=0.6,
            max_tokens=400,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error en Groq: {str(e)}")
        return "Disculpa, tuve un pequeño titubeo. ¿Podrías confirmarme el siguiente dato para continuar?"
