import os
import logging
from groq import Groq

logger = logging.getLogger("govassist-groq")

def get_groq_response(user_message: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or "invalid" in api_key.lower():
        logger.warning("Groq API Key no configurada o inválida. Activando modo heurístico inteligente.")
        return fallback_heuristic_response(user_message)
    
    try:
        client = Groq(api_key=api_key)
        system_prompt = (
            "Eres GovAssist Core, un asistente virtual empático, cálido y extremadamente paciente diseñado para ayudar "
            "a adultos mayores de 50 años en México a realizar trámites federales en gob.mx (CURP, Acta de Nacimiento, "
            "Semanas Cotizadas IMSS, Pasaporte y Cédula Profesional). "
            "Los usuarios te hablarán de forma natural, desestructurada y conversacional (por ejemplo, contándote su nombre, "
            "dándote datos sueltos o expresando dudas). "
            "Tu tarea es comprender su intención global, reconocer la información que ya te proporcionaron de manera natural, "
            "y guiarlos paso a paso con un lenguaje ciudadano, claro, respetuoso y humano, sin sonar como un formulario robótico."
        )
        
        chat_completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error al invocar Groq Cloud LPU: {str(e)}")
        return fallback_heuristic_response(user_message)

def fallback_heuristic_response(message: str) -> str:
    msg_lower = message.lower()
    if any(w in msg_lower for w in ['curp', 'nacimiento', 'nombre', 'me llamo', 'nací']):
        return "¡Mucho gusto! He tomado nota de tus datos. Para consultar o tramitar tu CURP de forma correcta, ¿me podrías confirmar tu fecha de nacimiento exacta y el estado donde naciste, por favor?"
    elif 'acta' in msg_lower:
        return "Claro que sí, con gusto te ayudo con tu Acta de Nacimiento. ¿Tienes a la mano tu CURP o prefieres buscarla con tus datos personales?"
    elif 'imss' in msg_lower or 'semanas' in msg_lower:
        return "Para revisar tus Semanas Cotizadas del IMSS de manera sencilla, por favor compárteme tu CURP y tu Número de Seguridad Social (NSS)."
    elif 'pasaporte' in msg_lower:
        return "Te guiaré paso a paso con tu Pasaporte SRE. ¿Eres adulto mayor para aplicar al descuento del 50% con INAPAM?"
    elif 'cédula' in msg_lower or 'cedula' in msg_lower:
        return "Para buscar tu Cédula Profesional en el Registro Nacional de la SEP, dime tu nombre completo o el número de tu cédula."
    else:
        return "Hola, con mucho gusto te atiendo. He comprendido tu mensaje. ¿En cuál de nuestros trámites federales (CURP, Acta de Nacimiento, Semanas Cotizadas del IMSS, Pasaporte o Cédula Profesional) te gustaría que te apoye hoy?"
