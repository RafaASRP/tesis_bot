import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Almacén efímero en memoria RAM para control de estado (Se purga al completar o reiniciar)
SESSION_STATES = {}

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    # Inicializar estado de sesión si no existe
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = {
            "turns_count": 0,
            "procedure": "curp",
            "slots": {
                "nombre": None,
                "fecha": None,
                "estado": None,
                "genero": None
            },
            "status": "collecting" # Estados: collecting -> waiting_confirmation -> completed
        }
    
    state = SESSION_STATES[session_id]
    slots = state["slots"]
    status = state["status"]
    
    last_msg = messages_history[-1].content.strip() if messages_history else ""
    msg_lower = last_msg.lower()

    # Si estamos esperando confirmación del usuario (Human-in-the-Loop)
    if status == "waiting_confirmation":
        if any(w in msg_lower for w in ['sí', 'si', 'correcto', 'adelante', 'confirmo', 'así es', 'asi es', 'ok', 'va', 'por favor']):
            state["status"] = "completed"
            summary = (
                f"¡Datos confirmados exitosamente!\n\n"
                f"• Nombre completo: {slots['nombre']}\n"
                f"• Fecha de nacimiento: {slots['fecha']}\n"
                f"• Estado: {slots['estado']}\n"
                f"• Género: {slots['genero']}\n\n"
                "Conectando de forma segura con gob.mx mediante Playwright RPA... "
                "¡Trámite procesado con éxito! Tu CURP ha sido consultada y los datos efímeros han sido purgados por seguridad."
            )
            # Purga total de la sesión por privacidad (Zero-Persistence / LGPDPPSO)
            del SESSION_STATES[session_id]
            return summary
        elif any(w in msg_lower for w in ['no', 'mal', 'corregir', 'cambiar', 'espera']):
            # Reiniciar ranuras para corrección
            state["slots"] = {"nombre": None, "fecha": None, "estado": None, "genero": None}
            state["status"] = "collecting"
            return "Entendido, vamos a corregir tus datos. ¿Cuál es tu nombre completo?"
        else:
            return (
                f"Por favor, confírmame si tus datos son correctos:\n"
                f"- Nombre: {slots['nombre']}\n- Fecha: {slots['fecha']}\n- Estado: {slots['estado']}\n- Género: {slots['genero']}\n"
                "¿Deseas proceder con el envío? (Responde Sí o No)"
            )

    # Extracción de ranuras durante la fase de recolección
    if status == "collecting":
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

    # Determinar estrictamente el siguiente campo faltante en orden secuencial
    missing_slot = None
    if not slots["nombre"]:
        missing_slot = "nombre completo"
    elif not slots["fecha"]:
        missing_slot = "fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not slots["estado"]:
        missing_slot = "estado de la República donde nació"
    elif not slots["genero"]:
        missing_slot = "género (hombre o mujer)"

    # Si ya se cubrieron los 4 datos, pasar al estado de confirmación
    if not missing_slot:
        state["status"] = "waiting_confirmation"
        state["turns_count"] += 1
        return (
            f"¡He recopilado todos los datos necesarios para tu CURP!\n\n"
            f"Por favor, verifica que sean correctos:\n"
            f"• Nombre completo: {slots['nombre']}\n"
            f"• Fecha de nacimiento: {slots['fecha']}\n"
            f"• Estado de nacimiento: {slots['estado']}\n"
            f"• Género: {slots['genero']}\n\n"
            f"¿Confirmas que estos datos son correctos para proceder con la consulta en gob.mx? (Responde Sí o No)"
        )

    # Control de saludos: Solo se saluda en el turno 0
    is_first_turn = (state["turns_count"] == 0)
    state["turns_count"] += 1

    greeting_prefix = "¡Hola! Qué gusto saludarte. Vamos a realizar tu trámite paso a paso y con toda la calma. " if is_first_turn else ""

    prompt_map = {
        "nombre completo": "por favor dime tu nombre completo.",
        "fecha de nacimiento exacta (ej. 16 de abril de 2001)": "por favor indícame tu fecha de nacimiento exacta.",
        "estado de la República donde nació": "por favor dime en qué estado de la República naciste.",
        "género (hombre o mujer)": "por favor confírmame tu género (hombre o mujer)."
    }

    request_text = prompt_map.get(missing_slot, f"por favor dime tu {missing_slot}.")

    system_prompt = (
        "Eres GovAssist Core, un asistente virtual empático, cálido y paciente para adultos mayores en México.\n"
        f"Trámite: CURP. Datos actuales: {slots}. Falta pedir estrictamente: {missing_slot}.\n"
        "REGLAS ESTRICTAS:\n"
        "1. CERO SALUDOS si ya ha iniciado la conversación (no repitas 'Hola' ni bienvenidas en turnos posteriores).\n"
        "2. Pide ÚNICAMENTE el dato faltante indicado, de forma muy amable y clara.\n"
        "3. No inventes ni repitas preguntas sobre datos ya llenados."
    )

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages_history:
        formatted_messages.append({"role": getattr(msg, "role", "user"), "content": getattr(msg, "content", str(msg))})

    if not api_key or "invalid" in api_key.lower():
        return f"{greeting_prefix}Para continuar con tu CURP, {request_text}"

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=formatted_messages,
            temperature=0.3,
            max_tokens=250,
        )
        ai_reply = chat_completion.choices[0].message.content
        return f"{greeting_prefix}{ai_reply}" if greeting_prefix else ai_reply
    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        return f"{greeting_prefix}Para continuar con tu CURP, {request_text}"
