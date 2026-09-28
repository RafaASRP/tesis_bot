import os
import logging
import random
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Almacén de sesiones en memoria RAM para control estricto de ranuras (Slot-Filling)
SESSION_STATES = {}

# Saludos cálidos, variados y humanos para evitar repeticiones robóticas
GREETINGS = [
    "¡Qué gusto saludarte! Vamos a realizar tu trámite paso a paso y con toda la calma.",
    "Hola, qué bueno que te acercas. Estoy aquí para ayudarte de forma sencilla y segura.",
    "¡Bienvenido! No te preocupes por los trámites digitales, yo te guiaré con paciencia.",
    "Hola, un placer saludarte. Vamos a resolver tu solicitud de manera muy fácil y clara."
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
    last_msg = messages_history[-1].content.strip() if messages_history else ""
    msg_lower = last_msg.lower()

    # Detección heurística complementaria para asegurar extracción de datos simples
    if not slots["genero"] and any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon', 'mujer', 'femenino']):
        slots["genero"] = "Hombre" if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']) else "Mujer"

    if not slots["estado"]:
        estados_mx = ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'mexico', 'méxico', 'veracruz', 'oaxaca', 'jalisco', 'nuevo leon', 'guanajuato']
        for est in estados_mx:
            if est in msg_lower:
                slots["estado"] = est.capitalize()
                break

    if not slots["fecha"] and (any(m in msg_lower for m in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or any(yr in msg_lower for yr in ['200', '199', '198', '197', '196'])):
        slots["fecha"] = last_msg

    if not slots["nombre"] and len(last_msg.split()) >= 2 and msg_lower not in ['curp', 'hombre', 'mujer', 'claro', 'sí', 'si']:
        if not slots["nombre"] and not any(w in msg_lower for w in ['hidalgo', 'puebla', 'tlaxcala']):
            slots["nombre"] = last_msg

    # Determinar qué campo falta por recolectar
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

    # Si la API Key de Groq no está disponible, activar respaldo inteligente offline
    if not api_key or "invalid" in api_key.lower():
        if not missing_slot:
            return f"{greeting} He reunido todos tus datos correctamente: {slots}. Procederé a consultar tu CURP."
        prompt_map = {
            "nombre": "por favor dime tu nombre completo.",
            "fecha": "por favor indícame tu fecha de nacimiento exacta.",
            "estado": "por favor dime en qué estado de la República naciste.",
            "genero": "por favor confírmame tu género (hombre o mujer)."
        }
        return f"{greeting} Entendido. Para continuar con tu trámite de CURP, {prompt_map[missing_slot]}"

    # Prompt directivo estricto para Llama 3 en Groq Cloud
    system_prompt = (
        "Eres GovAssist Core, un asistente virtual extremadamente paciente, cálido y empático para adultos mayores de 50 años en México.\n"
        "Estás guiando al usuario en el trámite de consulta de su CURP en gob.mx.\n"
        f"ESTADO ACTUAL DE DATOS RECOLECTADOS:\n- Nombre: {slots['nombre'] or 'FALTA'}\n- Fecha de nacimiento: {slots['fecha'] or 'FALTA'}\n- Estado: {slots['estado'] or 'FALTA'}\n- Género: {slots['genero'] or 'FALTA'}\n\n"
        f"EL ÚNICO DATO QUE DEBES PEDIR O CONFIRMAR EN ESTE TURNO ES: {missing_slot if missing_slot else 'NINGUNO (Datos completos)'}.\n\n"
        "INSTRUCCIONES CLAVE:\n"
        "1. Inicia siempre con un saludo cálido, humano y COMPLETAMENTE DIFERENTE al de mensajes anteriores (cero repeticiones robóticas).\n"
        "2. Reconoce brevemente la respuesta del usuario (aunque diga 'claro' o 'sí', acéptalo con amabilidad).\n"
        "3. Si falta algún dato, pide ÚNICAMENTE el siguiente dato faltante de forma natural. NUNCA repitas preguntas sobre datos que ya tienen valor registrado.\n"
        "4. Si ya están los 4 datos completos, felicita al usuario e indícale que estás consultando gob.mx."
    )

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        formatted_messages.append({"role": getattr(msg, "role", "user"), "content": getattr(msg, "content", str(msg))})

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=formatted_messages,
            temperature=0.6,
            max_tokens=350,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error al invocar Groq Cloud LPU: {str(e)}")
        if not missing_slot:
            return f"{greeting} ¡Excelente! He recopilado toda tu información para la CURP."
        return f"{greeting} Para continuar con tu trámite de CURP, por favor dime tu {missing_slot}."
