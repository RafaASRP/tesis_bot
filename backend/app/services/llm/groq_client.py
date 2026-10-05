import os
import logging
from typing import Dict
from pydantic import BaseModel, Field

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
    current_step: str = "init"
    slots: CurpSlots = Field(default_factory=CurpSlots)

# Almacén efímero (Zero-Persistence en RAM controlada por sesión)
SESSION_STATES: Dict[str, SessionState] = {}

def clean_input(text: str, prefixes: list) -> str:
    cleaned = text.strip()
    lower = cleaned.lower()
    for p in prefixes:
        if lower.startswith(p):
            cleaned = cleaned[len(p):].strip()
            lower = cleaned.lower()
    return cleaned.title()

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
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
            state.current_step = "nombres"
            state.slots = CurpSlots()
            return "Entendido. He borrado los datos para corregirlos. Empecemos de nuevo: por favor, dime tu nombre o nombres de pila (sin apellidos)."
        else:
            return "Necesito tu confirmación explícita. ¿Son correctos los datos mostrados en pantalla? (Responde Sí o No)"

    # 4. FASE DE RECOLECCIÓN SECUENCIAL PASO A PASO
    if state.status == "collecting":
        # Turno 0: Detección inicial de trámite
        if state.current_step == "init":
            state.greeted = True
            state.current_step = "nombres"
            return "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu trámite. Por favor, dime tu nombre o nombres de pila (sin apellidos)."

        # Turno 1: Captura de Nombre(s)
        if state.current_step == "nombres":
            state.slots.nombres = clean_input(last_msg, ["me llamo", "mi nombre es", "soy", "nombre:"])
            state.current_step = "primer_apellido"
            return "Perfecto. Ahora, por favor dime tu primer apellido (apellido paterno)."

        # Turno 2: Captura de Primer Apellido (Paterno)
        if state.current_step == "primer_apellido":
            state.slots.primer_apellido = clean_input(last_msg, ["mi primer apellido es", "mi apellido paterno es", "apellido paterno:", "apellido:", "es"])
            state.current_step = "segundo_apellido"
            return "Gracias. Por favor, dime tu segundo apellido (apellido materno, o dime 'no tengo' si no cuentas con él)."

        # Turno 3: Captura de Segundo Apellido (Materno)
        if state.current_step == "segundo_apellido":
            if any(w in msg_lower for w in ['no tengo', 'no cuento', 'sin apellido', 'ninguno']) or msg_lower in ['no', 'n/a', 'na']:
                state.slots.segundo_apellido = "No tiene"
            else:
                state.slots.segundo_apellido = clean_input(last_msg, ["mi segundo apellido es", "mi apellido materno es", "apellido materno:", "apellido:", "es"])
            state.current_step = "fecha"
            return "Muy bien. Por favor, indícame tu fecha de nacimiento exacta (ej. 16 de abril de 2001)."

        # Turno 4: Captura de Fecha de Nacimiento
        if state.current_step == "fecha":
            state.slots.fecha = clean_input(last_msg, ["naci el", "nací el", "fecha:"])
            state.current_step = "estado"
            return "Anotado. Por favor, dime en qué estado de la República naciste."

        # Turno 5: Captura de Estado de Nacimiento
        if state.current_step == "estado":
            estados_mx = [
                'aguascalientes', 'baja california sur', 'baja california', 'campeche', 'chiapas',
                'chihuahua', 'ciudad de méxico', 'cdmx', 'coahuila', 'colima', 'durango',
                'estado de méxico', 'edomex', 'guanajuato', 'guerrero', 'hidalgo', 'jalisco',
                'michoacán', 'michoacan', 'morelos', 'nayarit', 'nuevo león', 'nuevo leon',
                'oaxaca', 'puebla', 'querétaro', 'queretaro', 'quintana roo', 'san luis potosí',
                'san luis potosi', 'sinaloa', 'sonora', 'tabasco', 'tamaulipas', 'tlaxcala',
                'veracruz', 'yucatán', 'yucatan', 'zacatecas'
            ]
            matched = None
            for est in estados_mx:
                if est in msg_lower:
                    matched = est.title()
                    break
            state.slots.estado = matched if matched else clean_input(last_msg, ["naci en", "nací en", "estado de", "en el estado de", "en"])
            state.current_step = "genero"
            return "Perfecto. Por favor, confírmame tu género (hombre o mujer)."

        # Turno 6: Captura de Género
        if state.current_step == "genero":
            if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']):
                state.slots.genero = "Hombre"
            elif any(w in msg_lower for w in ['mujer', 'femenino']):
                state.slots.genero = "Mujer"
            else:
                state.slots.genero = clean_input(last_msg, ["soy", "genero:"])

            # Transición automática a confirmación HITL
            state.status = "confirming"
            state.current_step = "confirming"
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

    return "Por favor, indícame cómo puedo ayudarte con tu trámite."
