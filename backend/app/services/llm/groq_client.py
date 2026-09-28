import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

def get_groq_response(messages_history: list) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    # Formatear el historial de mensajes para Groq
    formatted_messages = []
    system_prompt = (
        "Eres GovAssist Core, un asistente virtual empático, cálido y extremadamente paciente diseñado para ayudar "
        "a adultos mayores de 50 años en México a realizar trámites federales en gob.mx (CURP, Acta de Nacimiento, "
        "Semanas Cotizadas IMSS, Pasaporte y Cédula Profesional). "
        "REGLAS CRÍTICAS DE CONVERSACIÓN:\n"
        "1. Analiza TODO el historial de la conversación antes de responder.\n"
        "2. Si el usuario ya te proporcionó algún dato (nombre, fecha de nacimiento, estado, etc.), NUNCA se lo vuelvas a pedir. Regístralo mentalmente.\n"
        "3. Los adultos mayores hablan de forma narrativa y desestructurada. Extrae la información de sus mensajes sin importar cómo la redacten.\n"
        "4. Pide los datos faltantes UNO POR UNO de forma muy amable y natural, nunca en forma de cuestionario rígido o robótico.\n"
        "5. Mantén respuestas breves, claras y con un tono humano y respetuoso."
    )
    
    formatted_messages.append({"role": "system", "content": system_prompt})
    
    for msg in messages_history:
        # Asegurar compatibilidad con el esquema de entrada
        role = getattr(msg, "role", "user")
        content = getattr(msg, "content", str(msg))
        formatted_messages.append({"role": role, "content": content})

    if not api_key or "invalid" in api_key.lower():
        logger.warning("Groq API Key no configurada o inválida. Activando modo heurístico.")
        last_msg = messages_history[-1].content if messages_history else ""
        return fallback_heuristic_response(last_msg)
    
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
        logger.error(f"Error al invocar Groq Cloud LPU: {str(e)}")
        last_msg = messages_history[-1].content if messages_history else ""
        return fallback_heuristic_response(last_msg)

def fallback_heuristic_response(message: str) -> str:
    msg_lower = message.lower()
    if any(w in msg_lower for w in ['curp', 'nacimiento', 'nombre', 'me llamo', 'nací', 'hidalgo']):
        return "¡Muchas gracias por la información! Ya tengo anotados tus datos principales. Para completar la consulta de tu CURP en gob.mx, ¿me confirmas tu género (hombre o mujer) por favor?"
    elif 'acta' in msg_lower:
        return "Claro que sí, te ayudo con tu Acta de Nacimiento. ¿Tienes a la mano tu CURP para buscarla rápido?"
    else:
        return "Te entiendo perfectamente. ¿En qué otro detalle o trámite te gustaría que avancemos?"
