import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Almacén efímero en RAM. 
# Dict: session_id -> { "greeted": bool, "status": str, "slots": dict }
SESSION_STATES = {}

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")

    # 1. MECANISMO ESTRICTO DE CERO PERSISTENCIA (LGPDPPSO)
    # Si el historial frontend llega limpio (<= 1 mensaje), purgar memoria e iniciar de 0.
    if len(messages_history) <= 1 and session_id in SESSION_STATES:
        del SESSION_STATES[session_id]

    last_msg_obj = messages_history[-1] if messages_history else None
    last_msg = getattr(last_msg_obj, "content", str(last_msg_obj)).strip() if last_msg_obj else ""
    msg_lower = last_msg.lower()

    if any(w in msg_lower for w in ['reiniciar', 'cancelar', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        return "He limpiado la memoria por completo. ¿En qué trámite te puedo ayudar hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?"

    # Inicialización del estado efímero en RAM
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = {
            "greeted": False,
            "status": "collecting",
            "slots": {"nombre": None, "fecha": None, "estado": None, "genero": None}
        }

    state = SESSION_STATES[session_id]
    slots = state["slots"]
    status = state["status"]

    # 2. CONFIRMACIÓN HITL (Human-in-the-Loop)
    if status == "waiting_confirmation":
        if any(w in msg_lower for w in ['sí', 'si', 'correcto', 'adelante', 'confirmo', 'ok']):
            state["status"] = "completed"
            summary = (
                "¡Datos confirmados exitosamente!\n\n"
                f"• Nombre: {slots['nombre']}\n"
                f"• Fecha: {slots['fecha']}\n"
                f"• Estado: {slots['estado']}\n"
                f"• Género: {slots['genero']}\n\n"
                "Conectando de forma segura con gob.mx mediante RPA... Tus datos han sido eliminados de mi memoria temporal por seguridad."
            )
            # Purga inmediata por privacidad
            del SESSION_STATES[session_id]
            return summary
        elif any(w in msg_lower for w in ['no', 'mal', 'incorrecto', 'corregir']):
            state["status"] = "collecting"
            state["slots"] = {"nombre": None, "fecha": None, "estado": None, "genero": None}
            return "Entendido. He borrado los datos para corregirlos. Empecemos de nuevo: por favor, dime tu nombre completo."
        else:
            return "¿Confirmas que estos datos son correctos para proceder? (Responde Sí o No)"

    # 3. EXTRACCIÓN Y LLENADO DE RANURAS (collecting)
    if status == "collecting":
        if not slots["genero"] and any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon', 'mujer', 'femenino']):
            slots["genero"] = "Hombre" if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']) else "Mujer"

        if not slots["estado"]:
            estados_mx = ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'mexico', 'méxico', 'veracruz', 'oaxaca', 'jalisco', 'nuevo leon', 'guanajuato', 'aguascalientes', 'baja california', 'campeche', 'chiapas', 'chihuahua', 'coahuila', 'colima', 'durango', 'guerrero', 'michoacan', 'morelos', 'nayarit', 'queretaro', 'quintana roo', 'san luis potosi', 'sinaloa', 'sonora', 'tabasco', 'tamaulipas', 'yucatan', 'zacatecas']
            for est in estados_mx:
                if est in msg_lower:
                    slots["estado"] = est.capitalize()
                    break

        if not slots["fecha"] and (any(m in msg_lower for m in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or any(yr in msg_lower for yr in ['200', '199', '198', '197', '196', '201'])):
            slots["fecha"] = last_msg

        if not slots["nombre"] and len(last_msg.split()) >= 2:
            if not any(w in msg_lower for w in ['curp', 'hombre', 'mujer', 'hidalgo', 'puebla', 'tlaxcala', 'cdmx', 'mexico', 'méxico', 'sí', 'no']):
                slots["nombre"] = last_msg

    # 4. ORDEN ESTRICTO DE SOLICITUD
    missing_slot = None
    if not slots["nombre"]:
        missing_slot = "nombre completo"
    elif not slots["fecha"]:
        missing_slot = "fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not slots["estado"]:
        missing_slot = "estado de la República donde naciste"
    elif not slots["genero"]:
        missing_slot = "género (hombre o mujer)"

    if not missing_slot:
        state["status"] = "waiting_confirmation"
        return (
            "¡He recopilado todos los datos necesarios para tu CURP!\n\n"
            "Por favor, verifica que sean correctos:\n"
            f"• Nombre: {slots['nombre']}\n"
            f"• Fecha: {slots['fecha']}\n"
            f"• Estado: {slots['estado']}\n"
            f"• Género: {slots['genero']}\n\n"
            "¿Confirmas que estos datos son correctos para proceder con la búsqueda? (Responde Sí o No)"
        )

    # 5. CONTROL DE SALUDO ÚNICO Y FALLBACK LOCAL
    greeting_prefix = ""
    if not state["greeted"]:
        greeting_prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso. "
        state["greeted"] = True

    prompt_map = {
        "nombre completo": "Por favor, dime tu nombre completo.",
        "fecha de nacimiento exacta (ej. 16 de abril de 2001)": "Gracias. Ahora, por favor indícame tu fecha de nacimiento exacta.",
        "estado de la República donde naciste": "Muy bien. Ahora dime en qué estado de la República naciste.",
        "género (hombre o mujer)": "Casi terminamos. Por favor confírmame tu género (hombre o mujer)."
    }
    request_text = prompt_map.get(missing_slot, f"Por favor dime tu {missing_slot}.")

    if not api_key or "invalid" in api_key.lower():
        return f"{greeting_prefix}{request_text}"

    # 6. INVOCACIÓN DEL LLM (Llama 3) CON TEMPERATURA DETERMINISTA
    system_prompt = (
        "Eres GovAssist Core, asistente empático para adultos mayores en México.\n"
        f"Tu ÚNICA tarea en este turno es solicitar este dato faltante: {missing_slot}.\n"
        "REGLAS CRÍTICAS:\n"
        "1. NO saludes, no digas 'Hola', 'Bienvenido' ni 'Qué gusto'. Ve directamente a pedir el dato.\n"
        "2. Sé amable pero directo.\n"
        "3. NO pidas ni menciones otros datos además del indicado."
    )

    formatted_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": last_msg}]

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=formatted_messages,
            temperature=0.1,
            max_tokens=150,
        )
        ai_reply = chat_completion.choices[0].message.content.strip()

        # Bloqueo heurístico contra alucinaciones de saludos del LLM
        lower_reply = ai_reply.lower()
        if any(lower_reply.startswith(b) for b in ["hola", "saludos", "bienvenido", "buenos", "buenas", "¡hola"]):
            ai_reply = request_text

        return f"{greeting_prefix}{ai_reply}"
    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        return f"{greeting_prefix}{request_text}"
