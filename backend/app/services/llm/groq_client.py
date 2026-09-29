import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Almacén efímero en memoria RAM para control estricto de FSM (Zero-Persistence)
SESSION_STATES = {}

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")

    # 1. CERO PERSISTENCIA: Si es el primer mensaje o el frontend se recargó, purgar sesión.
    if len(messages_history) <= 1:
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
    
    last_msg_obj = messages_history[-1] if messages_history else None
    last_msg = getattr(last_msg_obj, "content", str(last_msg_obj)).strip() if last_msg_obj else ""
    msg_lower = last_msg.lower()

    # Opción de borrado de memoria explícito por el usuario
    if any(w in msg_lower for w in ['cancelar', 'reiniciar', 'salir', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        return "He cancelado el trámite y borrado tus datos por seguridad. ¿En qué te puedo ayudar hoy?"

    # Inicialización del estado de la sesión
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = {
            "status": "collecting",
            "turns": 0,
            "slots": {
                "nombre": None,
                "fecha_nacimiento": None,
                "estado_nacimiento": None,
                "genero": None
            }
        }
    
    state = SESSION_STATES[session_id]
    slots = state["slots"]
    status = state["status"]

    # 2. FASE DE CONFIRMACIÓN (Human-in-the-Loop)
    if status == "confirming":
        afirmativas = ['sí', 'si', 'claro', 'correcto', 'está bien', 'esta bien', 'adelante', 'confirmo', 'ok', 'envíalo', 'mandalo']
        negativas = ['no', 'mal', 'incorrecto', 'corregir', 'cambiar', 'error', 'espera']
        
        if any(w in msg_lower for w in afirmativas):
            summary = (
                "¡Datos confirmados exitosamente!\n\n"
                f"• Nombre: {slots['nombre']}\n"
                f"• Fecha: {slots['fecha_nacimiento']}\n"
                f"• Estado: {slots['estado_nacimiento']}\n"
                f"• Género: {slots['genero']}\n\n"
                "Iniciando conexión segura con gob.mx mediante automatización RPA... Tus datos han sido eliminados de mi memoria por seguridad."
            )
            # Purga inmediata y total por privacidad (LGPDPPSO)
            del SESSION_STATES[session_id]
            return summary
        elif any(w in msg_lower for w in negativas):
            # Reiniciar slots y devolver a recolección
            state["status"] = "collecting"
            state["slots"] = {"nombre": None, "fecha_nacimiento": None, "estado_nacimiento": None, "genero": None}
            return "Entendido, no te preocupes. He borrado todo para corregirlo. Empecemos de nuevo: por favor, dime tu nombre completo."
        else:
            return "Necesito tu confirmación explícita para proceder. ¿Son correctos los datos en pantalla? (Responde Sí o No)"

    # 3. FASE DE RECOLECCIÓN (Extracción Heurística Segura y Secuencial)
    if status == "collecting" and state["turns"] > 0:
        # Extraer Género
        if not slots["genero"]:
            if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']):
                slots["genero"] = "Hombre"
            elif any(w in msg_lower for w in ['mujer', 'femenino']):
                slots["genero"] = "Mujer"

        # Extraer Estado
        if not slots["estado_nacimiento"]:
            estados_mx = ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'mexico', 'méxico', 'veracruz', 'oaxaca', 'jalisco', 'nuevo leon', 'guanajuato', 'aguascalientes', 'baja california', 'campeche', 'chiapas', 'chihuahua', 'coahuila', 'colima', 'durango', 'guerrero', 'michoacan', 'morelos', 'nayarit', 'queretaro', 'quintana roo', 'san luis potosi', 'sinaloa', 'sonora', 'tabasco', 'tamaulipas', 'yucatan', 'zacatecas']
            for est in estados_mx:
                if est in msg_lower:
                    slots["estado_nacimiento"] = est.title()
                    break

        # Extraer Fecha
        if not slots["fecha_nacimiento"]:
            meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            if any(m in msg_lower for m in meses) or any(yr in msg_lower for yr in ['200', '199', '198', '197', '196', '201']):
                slots["fecha_nacimiento"] = last_msg

        # Extraer Nombre (filtro estricto para evitar que comandos capturen el slot de nombre)
        if not slots["nombre"]:
            ignore_words = ['curp', 'acta', 'imss', 'pasaporte', 'cédula', 'hola', 'quiero', 'necesito', 'ayuda', 'por favor']
            if not any(msg_lower == w for w in ignore_words) and "curp" not in msg_lower:
                if len(last_msg.split()) >= 2:
                    slots["nombre"] = last_msg

    # 4. ORDEN ESTRICTO DE SOLICITUD
    missing_slot = None
    if not slots["nombre"]:
        missing_slot = "nombre completo"
    elif not slots["fecha_nacimiento"]:
        missing_slot = "fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not slots["estado_nacimiento"]:
        missing_slot = "estado de la República donde naciste"
    elif not slots["genero"]:
        missing_slot = "género (hombre o mujer)"

    # Si ya se llenaron los 4 datos, pasar a confirmación
    if not missing_slot:
        state["status"] = "confirming"
        return (
            "¡Excelente! He recopilado todos los datos necesarios para tu CURP.\n\n"
            "Por favor, verifica detenidamente que sean correctos:\n"
            f"• Nombre: {slots['nombre']}\n"
            f"• Fecha: {slots['fecha_nacimiento']}\n"
            f"• Estado: {slots['estado_nacimiento']}\n"
            f"• Género: {slots['genero']}\n\n"
            "¿Confirmas que esta información es correcta para enviarla y procesar tu trámite? (Responde Sí o No)"
        )

    # 5. CONTROL DE SALUDO ÚNICO
    greeting = ""
    if state["turns"] == 0:
        greeting = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu CURP. "
    
    state["turns"] += 1

    prompt_map = {
        "nombre completo": "Por favor, dime tu nombre completo.",
        "fecha de nacimiento exacta (ej. 16 de abril de 2001)": "Por favor indícame tu fecha de nacimiento exacta.",
        "estado de la República donde naciste": "Por favor dime en qué estado de la República naciste.",
        "género (hombre o mujer)": "Por favor confírmame tu género (hombre o mujer)."
    }
    fallback_request = prompt_map.get(missing_slot, f"Por favor dime tu {missing_slot}.")

    if not api_key or "invalid" in api_key.lower():
        return f"{greeting}{fallback_request}"

    # 6. LLM SOLO PARA EMPATÍA (SIN SALUDOS, SIN ALUCINACIONES)
    system_prompt = (
        "Eres GovAssist Core, un asistente empático para adultos mayores en México.\n"
        f"El ÚNICO dato que debes pedir en este momento es: {missing_slot}.\n\n"
        "REGLAS CRÍTICAS DE OBLIGATORIO CUMPLIMIENTO:\n"
        "1. PROHIBIDO SALUDAR. NO digas 'Hola', 'Bienvenido', 'Qué gusto', 'Buen día' bajo ninguna circunstancia. Empieza directamente tu frase.\n"
        "2. Reconoce amablemente la información anterior (si la hubo).\n"
        f"3. Pide ÚNICAMENTE '{missing_slot}'. NO pidas nada más.\n"
        "4. Sé breve, claro y muy respetuoso."
    )

    formatted_messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": last_msg}]

    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=formatted_messages,
            temperature=0.1,  # Temperatura bajísima para comportamiento determinista
            max_tokens=150,
        )
        ai_reply = chat_completion.choices[0].message.content.strip()

        # Filtro de seguridad (hardcoded) para eliminar saludos tercos del LLM
        lower_reply = ai_reply.lower()
        saludos_bloqueados = ["hola", "¡hola", "bienvenido", "saludos", "buen día", "buen dia", "buenas", "qué tal", "que tal"]
        for s in saludos_bloqueados:
            if lower_reply.startswith(s):
                # Si el LLM desobedece e intenta saludar de nuevo, forzamos el texto fallback local
                ai_reply = fallback_request
                break

        return f"{greeting}{ai_reply}"
    except Exception as e:
        logger.error(f"Error Groq: {str(e)}")
        return f"{greeting}{fallback_request}"
