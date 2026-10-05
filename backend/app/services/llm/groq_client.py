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

# Almacén efímero (Zero-Persistence en RAM)
SESSION_STATES: Dict[str, SessionState] = {}

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    last_msg_obj = messages_history[-1] if messages_history else None
    last_msg = getattr(last_msg_obj, "content", str(last_msg_obj)).strip() if last_msg_obj else ""
    msg_lower = last_msg.lower()

    # 1. CERO PERSISTENCIA: Limpieza si se recarga la PWA o se pide reiniciar
    if len(messages_history) <= 1 or any(w in msg_lower for w in ['cancelar', 'reiniciar', 'salir', 'borrar', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        if len(messages_history) > 1:
            return "He purgado tu sesión desde cero por seguridad. ¿En qué trámite te ayudo hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?"

    # Inicializar estado efímero
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = SessionState()
    
    state = SESSION_STATES[session_id]

    # 2. FASE DE CONFIRMACIÓN (HITL)
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
            del SESSION_STATES[session_id]
            return summary
        elif any(w in msg_lower for w in negativas):
            state.status = "collecting"
            state.slots = CurpSlots()
            return "Entendido. He borrado todo para corregirlo. Empecemos de nuevo: por favor, dime tu nombre y apellidos."
        else:
            return "Necesito tu confirmación explícita. ¿Son correctos los datos mostrados? (Responde Sí o No)"

    # 3. EXTRACCIÓN NER JSON (Filtro contra paja conversacional)
    if state.status == "collecting" and api_key and "invalid" not in api_key.lower():
        try:
            client = Groq(api_key=api_key)
            extractor_prompt = (
                "Eres un extractor NER. Analiza el texto del usuario e ignora la paja conversacional. "
                "Devuelve ÚNICAMENTE un JSON con las claves: 'nombres', 'primer_apellido', 'segundo_apellido', 'fecha', 'estado', 'genero'. "
                "Separa el nombre completo obligatoriamente. Si un dato no se menciona, usa null. Corrige ortografía a Capitalizada."
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
            
            # Asignación selectiva
            if not state.slots.nombres and extracted.get("nombres"): state.slots.nombres = str(extracted["nombres"]).title()
            if not state.slots.primer_apellido and extracted.get("primer_apellido"): state.slots.primer_apellido = str(extracted["primer_apellido"]).title()
            if not state.slots.segundo_apellido and extracted.get("segundo_apellido"): state.slots.segundo_apellido = str(extracted["segundo_apellido"]).title()
            if not state.slots.fecha and extracted.get("fecha"): state.slots.fecha = str(extracted["fecha"])
            if not state.slots.estado and extracted.get("estado"): state.slots.estado = str(extracted["estado"]).title()
            if not state.slots.genero and extracted.get("genero"): state.slots.genero = str(extracted["genero"]).title()
        except Exception as e:
            logger.error(f"Error NER JSON: {str(e)}")

    # 4. ORDEN ESTRICTO SECUENCIAL (Lógica Dura Python)
    missing_prompt = ""
    if not state.slots.nombres or not state.slots.primer_apellido:
        missing_prompt = "tu nombre completo (incluyendo apellidos)"
    elif not state.slots.fecha:
        missing_prompt = "tu fecha de nacimiento exacta (ej. 16 de abril de 2001)"
    elif not state.slots.estado:
        missing_prompt = "en qué estado de la República naciste"
    elif not state.slots.genero:
        missing_prompt = "tu género (hombre o mujer)"

    # Si todo está lleno, cambiar a confirmación
    if not missing_prompt:
        state.status = "confirming"
        return (
            "¡Excelente! He recopilado y separado todos tus datos.\n\n"
            "Por favor, verifica detenidamente que sean correctos:\n"
            f"• Nombres: {state.slots.nombres}\n"
            f"• Primer Apellido: {state.slots.primer_apellido}\n"
            f"• Segundo Apellido: {state.slots.segundo_apellido or 'N/A'}\n"
            f"• Fecha: {state.slots.fecha}\n"
            f"• Estado: {state.slots.estado}\n"
            f"• Género: {state.slots.genero}\n\n"
            "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
        )

    # 5. RESPUESTA DETERMINISTA (Cero IA, Cero Saludos Repetitivos)
    prefix = ""
    if not state.greeted:
        prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso. "
        state.greeted = True
    else:
        acks = ["Perfecto. ", "Muy bien. ", "Anotado. ", "Gracias. "]
        prefix = acks[hash(last_msg) % len(acks)]

    return f"{prefix}Por favor, dime {missing_prompt}."
