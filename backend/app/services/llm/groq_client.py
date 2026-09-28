import os
import logging
import random
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Almacén de sesiones en memoria RAM para control estricto de ranuras (Slot-Filling)
SESSION_STATES = {}

# Lista de saludos cálidos y variados para evitar repeticiones robóticas
GREETINGS = [
    "¡Qué gusto saludarte de nuevo! Vamos a avanzar con calma.",
    "Hola, qué bueno verte por aquí otra vez. Estoy listo para ayudarte.",
    "¡Hola! Qué gusto saludarte. No te preocupes, lo hacemos paso a paso.",
    "Hola, bienvenido de nuevo. Vamos a resolver tu trámite con calma y seguridad."
]

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    # Inicializar estado de sesión si no existe
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = {
            "procedure": "curp",
            "slots": {
                "nombre": None,
                "fecha": None,
                "estado": None,
                "genero": None
            }
        }
    
    state = SESSION_STATES[session_id]
    slots = state["slots"]
    last_msg = messages_history[-1].content if messages_history else ""
    msg_lower = last_msg.lower()

    # 1. Extracción determinista de slots basada en palabras clave del mensaje del usuario
    if not slots["genero"]:
        if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']):
            slots["genero"] = "Hombre"
        elif any(w in msg_lower for w in ['mujer', 'femenino']):
            slots["genero"] = "Mujer"

    if not slots["estado"]:
        estados_mx = ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'mexico', 'méxico', 'veracruz', 'oaxaca', 'jalisco', 'nuevo leon', 'guanajuato']
        for est in estados_mx:
            if est in msg_lower:
                slots["estado"] = est.capitalize()
                break

    if not slots["fecha"]:
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        if any(m in msg_lower for m in meses) or any(yr in msg_lower for yr in ['200', '199', '198', '197', '196']):
            slots["fecha"] = last_msg

    if not slots["nombre"]:
        if any(w in msg_lower for w in ['me llamo', 'soy', 'nombre es']) or (len(last_msg.split()) >= 2 and not any(w in msg_lower for w in ['curp', 'hombre', 'mujer', 'hidalgo', 'puebla', 'tlaxcala'])):
            slots["nombre"] = last_msg

    # 2. Determinar estrictamente cuál es el siguiente campo faltante
    missing_slot = None
    if not slots["nombre"]:
        missing_slot = "nombre completo"
    elif not slots["fecha"]:
        missing_slot = "fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not slots["estado"]:
        missing_slot = "estado de la República donde nació"
    elif not slots["genero"]:
        missing_slot = "género (hombre o mujer)"

    greeting = random.choice(GREETINGS)

    # Si ya se tienen todos los datos cubiertos
    if not missing_slot:
        return f"{greeting} He registrado toda tu información con éxito (Nombre: {slots['nombre']}, Fecha: {slots['fecha']}, Estado: {slots['estado']}, Género: {slots['genero']}). Estoy procediendo a consultar tu CURP en gob.mx de forma automática."

    # 3. Construir prompt directivo con estado absoluto para Groq
    system_prompt = (
        "Eres GovAssist Core, un asistente virtual empático, cálido y paciente para adultos mayores de 50 años en México. "
        f"Trámite actual: CURP. Datos recolectados hasta el momento: {slots}. "
        f"El ÚNICO dato que falta obligatoriamente pedir en este turno es: {missing_slot}. "
        "INSTRUCCIONES ESTRICTAS:\n"
        f"1. Inicia la respuesta con un tono humano y accesible.\n"
        "2. Reconoce brevemente lo que el usuario acaba de escribir.\n"
        f"3. Pide ÚNICAMENTE el siguiente dato faltante: '{missing_slot}'. NUNCA vuelvas a pedir información que ya esté recolectada.\n"
        "4. Mantén las respuestas breves y claras."
    )

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        formatted_messages.append({"role": getattr(msg, "role", "user"), "content": getattr(msg, "content", str(msg))})

    if not api_key or "invalid" in api_key.lower():
        return f"{greeting} Para continuar con tu trámite de CURP, por favor dime tu {missing_slot}."

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=formatted_messages,
            temperature=0.4,
            max_tokens=300,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error al invocar Groq Cloud LPU: {str(e)}")
        return f"{greeting} Para continuar con tu CURP, por favor dime tu {missing_slot}."
