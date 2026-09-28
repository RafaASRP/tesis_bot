import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

def get_groq_response(messages_history: list) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    # Prompt de sistema especializado en IHC para adultos mayores y extracción de estado
    system_prompt = (
        "Eres GovAssist Core, un asistente virtual altamente empático, paciente y cálido diseñado para ayudar "
        "a adultos mayores de 50 años en México con trámites de gob.mx (CURP, Acta de Nacimiento, Semanas IMSS, Pasaporte, Cédula).\n\n"
        "DIRECTRICES CRÍTICITAS DE COMPORTAMIENTO:\n"
        "1. ANÁLISIS DE HISTORIAL: Revisa todo el historial de la conversación. Identifica qué datos ya te dio el usuario "
        "(Nombre completo, Fecha de nacimiento, Estado de nacimiento, Género).\n"
        "2. CERO REPETICIÓN: Si el usuario ya te proporcionó algún dato previamente, NUNCA se lo vuelvas a pedir ni digas que te falta si ya lo mencionó en mensajes anteriores.\n"
        "3. LENGUAJE NATURAL Y LIBRE: Los usuarios mayores hablan de forma narrativa (ej. 'Me llamo Juan y nací en Puebla'). "
        "Debes extraer los datos de esa narrativa sin forzarlos a usar formatos rígidos.\n"
        "4. GUÍA PASO A PASO: Si falta algún dato indispensable para el trámite (para CURP se requiere: Nombre, Fecha de Nacimiento, Estado y Género), "
        "pide ÚNICAMENTE el siguiente dato faltante de forma muy amable, conversacional y humana.\n"
        "5. TONO: Usa un español de México respetuoso, claro, cálido, sin tecnicismos robóticos."
    )
    
    formatted_messages = [{"role": "system", "content": system_prompt}]
    
    for msg in messages_history:
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
            temperature=0.5,
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
        return "¡Muchas gracias! He anotado tus datos correctamente. Para finalizar la consulta de tu CURP, ¿me podrías confirmar únicamente tu género (hombre o mujer) por favor?"
    elif 'acta' in msg_lower:
        return "Claro que sí, con gusto te ayudo con tu Acta de Nacimiento. ¿Tienes a la mano tu CURP para buscarla de forma rápida?"
    else:
        return "Te entiendo perfectamente. ¿En qué otro trámite federal te gustaría que avancemos hoy?"
