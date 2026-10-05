import os
import json
import logging
from typing import Dict
from pydantic import BaseModel, Field
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Tipado estricto con Pydantic v2
class CurpSlots(BaseModel):
    nombres: str | None = None
    primer_apellido: str | None = None
    segundo_apellido: str | None = None
    fecha: str | None = None
    estado: str | None = None
    genero: str | None = None

class SessionState(BaseModel):
    status: str = "collecting"
    greeted: bool = False
    slots: CurpSlots = Field(default_factory=CurpSlots)

# Almacén efímero (Zero-Persistence en RAM controlada por session_id)
SESSION_STATES: Dict[str, SessionState] = {}

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    last_msg_obj = messages_history[-1] if messages_history else None
    last_msg = getattr(last_msg_obj, "content", str(last_msg_obj)).strip() if last_msg_obj else ""
    msg_lower = last_msg.lower()

    # 1. PURGA EXPLÍCITA (Zero-Persistence LGPDPPSO)
    if any(w in msg_lower for w in ['cancelar', 'reiniciar', 'salir', 'borrar', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        return "He purgado tu sesión desde cero por seguridad. ¿En qué trámite federal te ayudo hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?"

    # 2. INICIALIZACIÓN DE ESTADO EFÍMERO
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = SessionState()
    
    state = SESSION_STATES[session_id]

    # 3. FASE DE CONFIRMACIÓN (Human-in-the-Loop)
    if state.status == "confirming":
        afirmativas = ['sí', 'si', 'claro', 'correcto', 'está bien', 'adelante', 'confirmo', 'ok']
        negativas = ['no', 'mal', 'incorrecto', 'corregir', 'cambiar', 'error']
        
        if any(w in msg_lower for w in afirmativas):
            summary = (
                "¡Datos confirmados exitosamente!\n\n"
                f"• Nombres: {state.slots.nombres}\n"
                f"• Primer Apellido: {state.slots.primer_apellido}\n"
                f"• Segundo Apellido: {state.slots.segundo_apellido or 'N/A'}\n"
                f"• Fecha de Nacimiento: {state.slots.fecha}\n"
                f"• Estado: {state.slots.estado}\n"
                f"• Género: {state.slots.genero}\n\n"
                "Conectando de forma segura con gob.mx mediante automatización RPA... Tus datos han sido eliminados de mi memoria temporal."
            )
            # Purga inmediata al confirmar por privacidad
            del SESSION_STATES[session_id]
            return summary
        elif any(w in msg_lower for w in negativas):
            state.status = "collecting"
            state.slots = CurpSlots()
            return "Entendido. He borrado todo para corregirlo. Empecemos de nuevo: por favor, dime tu nombre completo."
        else:
            return "Necesito tu confirmación explícita. ¿Son correctos los datos mostrados en pantalla? (Responde Sí o No)"

    # 4. EXTRACCIÓN NER JSON (Filtro de Paja y Separación de Nombres)
    if state.status == "collecting":
        if api_key and "invalid" not in api_key.lower():
            try:
                client = Groq(api_key=api_key)
                extractor_prompt = (
                    "Eres un extractor NER. Analiza el texto del usuario e ignora la paja conversacional. "
                    "Devuelve ÚNICAMENTE un JSON con las claves: 'nombres', 'primer_apellido', 'segundo_apellido', 'fecha', 'estado', 'genero'. "
                    "Separa el nombre completo OBLIGATORIAMENTE. Si un dato no se menciona, usa null. Capitaliza las palabras."
                )
                extract_res = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": extractor_prompt},
                        {"role": "user", "content": last_msg}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                extracted = json.loads(extract_res.choices[0].message.content)
                
                # Asignar solo a las ranuras vacías
                if not state.slots.nombres and extracted.get("nombres"): state.slots.nombres = str(extracted["nombres"]).title()
                if not state.slots.primer_apellido and extracted.get("primer_apellido"): state.slots.primer_apellido = str(extracted["primer_apellido"]).title()
                if not state.slots.segundo_apellido and extracted.get("segundo_apellido"): state.slots.segundo_apellido = str(extracted["segundo_apellido"]).title()
                if not state.slots.fecha and extracted.get("fecha"): state.slots.fecha = str(extracted["fecha"])
                if not state.slots.estado and extracted.get("estado"): state.slots.estado = str(extracted["estado"]).title()
                if not state.slots.genero and extracted.get("genero"): state.slots.genero = str(extracted["genero"]).title()
            except Exception as e:
                logger.error(f"Error NER JSON: {str(e)}")

        # Respaldo Heurístico Local por si Groq falla o hay timeout
        if not state.slots.nombres and not state.slots.primer_apellido:
            palabras = [p.title() for p in last_msg.split() if p.lower() not in ['hola', 'me', 'llamo', 'soy', 'quiero', 'curp', 'tramite', 'por', 'favor']]
            if len(palabras) >= 2:
                if len(palabras) == 2:
                    state.slots.nombres, state.slots.primer_apellido = palabras[0], palabras[1]
                elif len(palabras) >= 3:
                    state.slots.nombres = palabras[0]
                    state.slots.primer_apellido = palabras[1]
                    state.slots.segundo_apellido = " ".join(palabras[2:])

        if not state.slots.genero and any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon', 'mujer', 'femenino']):
            state.slots.genero = "Hombre" if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']) else "Mujer"
        
        if not state.slots.estado:
            estados_mx = ['hidalgo', 'tlaxcala', 'puebla', 'cdmx', 'mexico', 'méxico', 'veracruz', 'oaxaca', 'jalisco', 'nuevo leon', 'guanajuato', 'aguascalientes', 'baja california']
            for est in estados_mx:
                if est in msg_lower:
                    state.slots.estado = est.title()
                    break
        
        if not state.slots.fecha and (any(m in msg_lower for m in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or any(yr in msg_lower for yr in ['200', '199', '198', '197', '196'])):
            state.slots.fecha = last_msg

    # 5. ORDEN ESTRICTO SECUENCIAL (Control Python Determinista)
    missing_prompt = ""
    if not state.slots.nombres or not state.slots.primer_apellido:
        missing_prompt = "tu nombre completo (incluyendo apellidos)"
    elif not state.slots.fecha:
        missing_prompt = "tu fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not state.slots.estado:
        missing_prompt = "en qué estado de la República naciste"
    elif not state.slots.genero:
        missing_prompt = "tu género (hombre o mujer)"

    # Transición al completarse los datos
    if not missing_prompt:
        state.status = "confirming"
        return (
            "¡Excelente! He extraído y separado todos tus datos de forma segura.\n\n"
            "Por favor, verifica detenidamente que sean correctos:\n"
            f"• Nombres: {state.slots.nombres}\n"
            f"• Primer Apellido: {state.slots.primer_apellido}\n"
            f"• Segundo Apellido: {state.slots.segundo_apellido or 'N/A'}\n"
            f"• Fecha: {state.slots.fecha}\n"
            f"• Estado: {state.slots.estado}\n"
            f"• Género: {state.slots.genero}\n\n"
            "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
        )

    # 6. RESPUESTA CREADA POR CÓDIGO (Cero saludos repetidos garantizado)
    prefix = ""
    if not state.greeted:
        prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu trámite. "
        state.greeted = True
    else:
        acks = ["Perfecto. ", "Muy bien. ", "Anotado. ", "Gracias. "]
        prefix = acks[len(last_msg) % len(acks)]

    return f"{prefix}Por favor, dime {missing_prompt}."
