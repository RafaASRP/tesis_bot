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

    # Extracción determinista de slots basada en palabras clave del mensaje del usuario
    if not slots["genero"] and any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon', 'mujer', 'femenino']):
        slots["genero"] = "Hombre" if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']) else "Mujer"

    if not slots["estado"]:
        estados_mx = [
            'hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'mexico', 'méxico', 'veracruz', 'oaxaca', 
            'jalisco', 'nuevo leon', 'guanajuato', 'aguascalientes', 'baja california', 
            'baja california sur', 'campeche', 'chiapas', 'chihuahua', 'coahuila', 'colima', 
            'durango', 'guerrero', 'michoacan', 'morelos', 'nayarit', 'queretaro', 
            'quintana roo', 'san luis potosi', 'sinaloa', 'sonora', 'tabasco', 'tamaulipas', 
            'yucatan', 'zacatecas'
        ]
        for est in estados_mx:
            if est in msg_lower:
                slots["estado"] = est.capitalize()
                break

    if not slots["fecha"] and (any(m in msg_lower for m in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or any(yr in msg_lower for yr in ['200', '199', '198', '197', '196', '201'])):
        slots["fecha"] = last_msg

    if not slots["nombre"] and len(last_msg.split()) >= 2 and msg_lower not in ['curp', 'hombre', 'mujer', 'claro', 'sí', 'si', 'un curp']:
        if not any(w in msg_lower for w in ['hidalgo', 'puebla', 'tlaxcala', 'cdmx', 'mexico', 'méxico']):
            slots["nombre"] = last_msg

    # Determinar estrictamente cuál es el siguiente campo faltante
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
        return f"{greeting} ¡Excelente! Tengo todos tus datos listos:\n- Nombre: {slots['nombre']}\n- Fecha: {slots['fecha']}\n- Estado: {slots['estado']}\n- Género: {slots['genero']}\nProcederé a consultar tu CURP de forma automática en gob.mx."

    # Construir prompt directivo estricto para Llama 3 en Groq Cloud
    system_prompt = (
        "Eres GovAssist Core, un asistente virtual extremadamente paciente, cálido y empático para adultos mayores de 50 años en México.\n"
        "Estás guiando al usuario en el trámite de consulta de su CURP en gob.mx.\n\n"
        f"ESTADO ACTUAL DE DATOS RECOLECTADOS:\n- Nombre: {slots['nombre'] or 'FALTA'}\n- Fecha de nacimiento: {slots['fecha'] or 'FALTA'}\n- Estado: {slots['estado'] or 'FALTA'}\n- Género: {slots['genero'] or 'FALTA'}\n\n"
        f"EL ÚNICO DATO QUE DEBES PEDIR O CONFIRMAR EN ESTE TURNO ES: '{missing_slot}'.\n\n"
        "INSTRUCCIONES CLAVE:\n"
        "1. Inicia siempre con un saludo cálido, humano y COMPLETAMENTE DIFERENTE al de mensajes anteriores (cero repeticiones robóticas).\n"
        "2. Reconoce brevemente si el usuario aportó información nueva.\n"
        f"3. Pide ÚNICAMENTE el siguiente dato faltante: '{missing_slot}'. NUNCA repites preguntas sobre datos que ya tienen un valor registrado en el sistema.\n"
        "4. Mantén las respuestas breves, claras y accesibles."
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
        return f"{greeting} Para continuar con tu trámite de CURP, por favor dime tu {missing_slot}."
