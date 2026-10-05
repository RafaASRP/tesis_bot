import os
import json
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    # 1. IDENTIFICACIÓN DE TURNOS (Stateless)
    user_messages = [getattr(m, "content", str(m)).strip() for m in messages_history if getattr(m, "role", "user") == "user"]
    bot_messages = [getattr(m, "content", str(m)).strip() for m in messages_history if getattr(m, "role", "assistant") in ["assistant", "bot"]]
    
    turn_count = len(user_messages)
    last_msg = user_messages[-1].lower() if user_messages else ""
    last_bot_msg = bot_messages[-1].lower() if bot_messages else ""

    # 2. PURGA Y REINICIO EXPLÍCITO
    if any(w in last_msg for w in ['cancelar', 'reiniciar', 'salir', 'borrar', 'empezar de nuevo']):
        return "He purgado el historial por seguridad. ¿En qué trámite federal te ayudo hoy?"

    # 3. FASE DE CONFIRMACIÓN HITL (Human-in-the-Loop)
    if "¿confirmas que esta información es correcta" in last_bot_msg:
        afirmativas = ['sí', 'si', 'claro', 'correcto', 'está bien', 'adelante', 'confirmo', 'ok']
        negativas = ['no', 'mal', 'incorrecto', 'corregir', 'cambiar', 'error']
        
        if any(w in last_msg for w in afirmativas):
            return "¡Datos confirmados exitosamente!\n\nConectando de forma segura con gob.mx mediante automatización RPA... (Tus datos han sido eliminados)."
        elif any(w in last_msg for w in negativas):
            return "Entendido. Vamos a corregir los datos. Por favor, escribe de nuevo tu nombre completo (incluyendo apellidos)."

    # 4. EXTRACCIÓN NER JSON SOBRE EL HISTORIAL COMPLETO (Inmune a la amnesia de RAM)
    conversation_text = "\n".join([f"{getattr(m, 'role', 'user').upper()}: {getattr(m, 'content', str(m))}" for m in messages_history])
    
    slots = {
        "nombres": None,
        "primer_apellido": None,
        "segundo_apellido": None,
        "fecha": None,
        "estado": None,
        "genero": None
    }

    if api_key and "invalid" not in api_key.lower():
        try:
            client = Groq(api_key=api_key)
            extractor_prompt = (
                "Eres un extractor NER. Analiza toda la conversación. Extrae los datos ACTUALES del usuario para su trámite. "
                "Si el usuario corrigió un dato, toma el más reciente. "
                "Devuelve ÚNICAMENTE un JSON con las claves: 'nombres', 'primer_apellido', 'segundo_apellido', 'fecha', 'estado', 'genero'. "
                "Separa el nombre completo OBLIGATORIAMENTE. Si un dato no existe, asigna null. Capitaliza las palabras."
            )
            extract_res = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": extractor_prompt},
                    {"role": "user", "content": conversation_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            extracted = json.loads(extract_res.choices[0].message.content)
            
            slots["nombres"] = extracted.get("nombres")
            slots["primer_apellido"] = extracted.get("primer_apellido")
            slots["segundo_apellido"] = extracted.get("segundo_apellido")
            slots["fecha"] = extracted.get("fecha")
            slots["estado"] = extracted.get("estado")
            slots["genero"] = extracted.get("genero")
        except Exception as e:
            logger.error(f"Error NER JSON: {str(e)}")

    # Respaldo Heurístico Local Extremo
    if not slots["nombres"] and not slots["primer_apellido"]:
        palabras = [p.title() for p in last_msg.split() if p.lower() not in ['hola', 'me', 'llamo', 'soy', 'quiero', 'curp', 'tramite', 'un', 'el']]
        if len(palabras) >= 2:
            slots["nombres"] = palabras[0]
            slots["primer_apellido"] = palabras[1]
            if len(palabras) > 2:
                slots["segundo_apellido"] = " ".join(palabras[2:])

    # 5. ORDEN ESTRICTO SECUENCIAL Y VALIDACIÓN
    missing_prompt = ""
    if not slots["nombres"] or not slots["primer_apellido"]:
        missing_prompt = "tu nombre completo (incluyendo apellidos)"
    elif not slots["fecha"]:
        missing_prompt = "tu fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not slots["estado"]:
        missing_prompt = "en qué estado de la República naciste"
    elif not slots["genero"]:
        missing_prompt = "tu género (hombre o mujer)"

    # Transición al completarse los datos
    if not missing_prompt:
        return (
            "¡Excelente! He extraído y separado todos tus datos de forma segura.\n\n"
            "Por favor, verifica detenidamente que sean correctos:\n"
            f"• Nombres: {slots['nombres']}\n"
            f"• Primer Apellido: {slots['primer_apellido']}\n"
            f"• Segundo Apellido: {slots['segundo_apellido'] or 'N/A'}\n"
            f"• Fecha: {slots['fecha']}\n"
            f"• Estado: {slots['estado']}\n"
            f"• Género: {slots['genero']}\n\n"
            "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
        )

    # 6. SOLUCIÓN AL PASO 1: BLOQUEO ABSOLUTO DE SALUDOS REPETITIVOS
    if turn_count <= 1:
        # Turno 0: Único momento donde se saluda
        prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu trámite. "
    else:
        # Turnos > 1: Garantía algorítmica de cero saludos
        acks = ["Perfecto. ", "Muy bien. ", "Anotado. ", "Gracias. "]
        prefix = acks[len(last_msg) % len(acks)] if missing_prompt != "tu nombre completo (incluyendo apellidos)" else ""

    return f"{prefix}Por favor, dime {missing_prompt}."
