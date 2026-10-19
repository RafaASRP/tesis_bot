import os
import re
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

# Almacén efímero (Zero-Persistence en RAM controlada por sesión)
SESSION_STATES: Dict[str, SessionState] = {}

def clean_birth_date(text: str) -> str | None:
    """
    Normaliza de forma determinista la fecha de nacimiento al formato 'DD de [mes] de AAAA'.
    Elimina expresiones coloquiales como 'yo nací el', 'nací en', etc.
    """
    if not text:
        return None

    meses = {
        'enero': 'enero', 'febrero': 'febrero', 'marzo': 'marzo', 'abril': 'abril',
        'mayo': 'mayo', 'junio': 'junio', 'julio': 'julio', 'agosto': 'agosto',
        'septiembre': 'septiembre', 'setiembre': 'septiembre', 'octubre': 'octubre',
        'noviembre': 'noviembre', 'diciembre': 'diciembre'
    }
    meses_patron = '|'.join(meses.keys())

    # 1. Búsqueda de patrón natural: día + mes + año
    match_txt = re.search(r'(\b[0-3]?\d)\s*(?:de\s+)?(' + meses_patron + r')\s*(?:del?\s+|de\s+|\s+)?(\d{4}\b)', text, re.IGNORECASE)
    if match_txt:
        dia = int(match_txt.group(1))
        mes = meses[match_txt.group(2).lower()]
        anio = match_txt.group(3)
        return f"{dia} de {mes} de {anio}"

    # 2. Búsqueda de patrón numérico: DD/MM/AAAA o DD-MM-AAAA
    match_num = re.search(r'(\b[0-3]?\d)[/-]([0-1]?\d)[/-](\d{4}\b)', text)
    if match_num:
        dia = int(match_num.group(1))
        m_num = int(match_num.group(2))
        anio = match_num.group(3)
        meses_nombres = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        if 1 <= m_num <= 12:
            return f"{dia} de {meses_nombres[m_num - 1]} de {anio}"
        return f"{dia:02d}/{m_num:02d}/{anio}"

    # 3. Poda de muletillas conversacionales
    cleaned = text.strip()
    muletillas = [
        'yo naci el dia', 'yo nací el día', 'yo naci en', 'yo nací en', 'yo naci el', 'yo nací el', 'yo naci', 'yo nací',
        'naci el dia', 'nací el día', 'naci en', 'nací en', 'naci el', 'nací el', 'naci', 'nací',
        'el dia', 'el día', 'el', 'en', 'fecha de nacimiento:', 'fecha:'
    ]
    for mul in muletillas:
        if cleaned.lower().startswith(mul):
            cleaned = cleaned[len(mul):].strip()
    return cleaned.strip() if cleaned else None

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    last_msg_obj = messages_history[-1] if messages_history else None
    last_msg = getattr(last_msg_obj, "content", str(last_msg_obj)).strip() if last_msg_obj else ""
    msg_lower = last_msg.lower()

    # 1. PURGA EXPLÍCITA (Zero-Persistence LGPDPPSO)
    if any(w in msg_lower for w in ['cancelar', 'reiniciar', 'salir', 'borrar', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        return "He reiniciado la consulta por seguridad. ¿En qué trámite federal te puedo ayudar hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?"

    # 2. INICIALIZACIÓN DE ESTADO EFÍMERO
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = SessionState()
    
    state = SESSION_STATES[session_id]

    # 3. FASE DE CONFIRMACIÓN (Human-in-the-Loop) CON ANÁLISIS LÉXICO ESTRICTO
    if state.status == "confirming":
        negativas_palabras = [
            'no', 'mal', 'incorrecto', 'incorrecta', 'incorrectos', 'incorrectas',
            'corregir', 'cambiar', 'error', 'falso', 'equivocado', 'equivocada', 'espera'
        ]
        negativas_frases = [
            'no es correcto', 'no son correctos', 'no es correcta', 'no son correctas',
            'no esta bien', 'no está bien', 'esta mal', 'está mal', 'no confirmo',
            'estan mal', 'están mal', 'no coinciden', 'hay un error'
        ]

        es_negativo = (
            any(re.search(rf"\b{re.escape(w)}\b", msg_lower) for w in negativas_palabras) or
            any(f in msg_lower for f in negativas_frases)
        )

        afirmativas_palabras = [
            'sí', 'si', 'claro', 'correcto', 'correcta', 'correctos', 'correctas',
            'adelante', 'confirmo', 'ok', 'proceder', 'exacto', 'exacta'
        ]
        afirmativas_frases = [
            'está bien', 'esta bien', 'es correcta', 'es correcto', 'son correctos',
            'son correctas', 'si es correcta', 'si es correcto', 'así es', 'asi es',
            'todo es correcto', 'todo bien', 'de acuerdo'
        ]

        # La confirmación afirmativa queda bloqueada si existe cualquier negación léxica
        es_afirmativo = not es_negativo and (
            any(re.search(rf"\b{re.escape(w)}\b", msg_lower) for w in afirmativas_palabras) or
            any(f in msg_lower for f in afirmativas_frases)
        )

        if es_negativo:
            state.status = "collecting"
            state.slots = CurpSlots()
            return "Entendido. He cancelado el envío para corregir los datos. Empecemos de nuevo: por favor, dime tu nombre o nombres de pila (sin apellidos)."
        elif es_afirmativo:
            state.status = "confirmed"
            summary = (
                "¡Datos confirmados exitosamente!\n\n"
                f"• Nombres: {state.slots.nombres}\n"
                f"• Primer Apellido: {state.slots.primer_apellido}\n"
                f"• Segundo Apellido: {state.slots.segundo_apellido or 'N/A'}\n"
                f"• Fecha de Nacimiento: {state.slots.fecha}\n"
                f"• Estado: {state.slots.estado}\n"
                f"• Género: {state.slots.genero}\n\n"
                "Estamos conectando con el portal oficial de gob.mx para realizar tu consulta. Por favor, permanece atento a la pantalla."
            )
            return summary
        else:
            return "Necesito tu confirmación explícita para continuar. ¿Son correctos los datos que ves en pantalla? (Responde únicamente Sí o No)"

    # 4. EXTRACCIÓN NER JSON Y HEURÍSTICA CANÓNICA
    if state.status == "collecting":
        if api_key and "invalid" not in api_key.lower():
            try:
                client = Groq(api_key=api_key)
                extractor_prompt = (
                    "Eres un extractor NER. Analiza el texto del usuario e ignora la paja conversacional. "
                    "Devuelve ÚNICAMENTE un JSON con las claves: 'nombres', 'primer_apellido', 'segundo_apellido', 'fecha', 'estado', 'genero'. "
                    "Para 'fecha', extrae ÚNICAMENTE la fecha en formato natural sin verbos ni prefijos. "
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
                
                if not state.slots.nombres and extracted.get("nombres"): state.slots.nombres = str(extracted["nombres"]).title()
                if not state.slots.primer_apellido and extracted.get("primer_apellido"): state.slots.primer_apellido = str(extracted["primer_apellido"]).title()
                if not state.slots.segundo_apellido and extracted.get("segundo_apellido"): state.slots.segundo_apellido = str(extracted["segundo_apellido"]).title()
                
                if not state.slots.fecha and extracted.get("fecha"):
                    cleaned_date = clean_birth_date(str(extracted["fecha"]))
                    if cleaned_date:
                        state.slots.fecha = cleaned_date

                if not state.slots.estado and extracted.get("estado"): state.slots.estado = str(extracted["estado"]).title()
                if not state.slots.genero and extracted.get("genero"): state.slots.genero = str(extracted["genero"]).title()
            except Exception as e:
                logger.error(f"Error NER JSON: {str(e)}")

        # Respaldo Heurístico Local Segmentado para Nombres
        if not state.slots.nombres:
            palabras = [p.title() for p in last_msg.split() if p.lower() not in ['hola', 'me', 'llamo', 'soy', 'quiero', 'curp', 'tramite', 'por', 'favor', 'necesito', 'un', 'sacar', 'mi']]
            if palabras and not any(w in msg_lower for w in ['curp', 'tramite']):
                if len(palabras) >= 3 and not state.slots.primer_apellido:
                    state.slots.nombres = palabras[0] if len(palabras) == 3 else f"{palabras[0]} {palabras[1]}"
                    state.slots.primer_apellido = palabras[1] if len(palabras) == 3 else palabras[2]
                    state.slots.segundo_apellido = " ".join(palabras[2:]) if len(palabras) == 3 else " ".join(palabras[3:])
                else:
                    state.slots.nombres = " ".join(palabras)
        elif not state.slots.primer_apellido:
            palabras = [p.title() for p in last_msg.split() if p.lower() not in ['mi', 'apellido', 'paterno', 'primer', 'es']]
            if palabras:
                state.slots.primer_apellido = " ".join(palabras)
        elif not state.slots.segundo_apellido:
            if any(w in msg_lower for w in ['no tengo', 'no cuento', 'sin apellido', 'ninguno']) or msg_lower in ['no', 'n/a', 'na']:
                state.slots.segundo_apellido = "No tiene"
            else:
                palabras = [p.title() for p in last_msg.split() if p.lower() not in ['mi', 'apellido', 'materno', 'segundo', 'es']]
                if palabras:
                    state.slots.segundo_apellido = " ".join(palabras)

        # Extracción determinista de fecha sobre el input directo
        if not state.slots.fecha:
            parsed_date = clean_birth_date(last_msg)
            if parsed_date and (any(m in parsed_date.lower() for m in ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']) or any(c.isdigit() for c in parsed_date)):
                state.slots.fecha = parsed_date

        if not state.slots.genero and any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon', 'mujer', 'femenino']):
            state.slots.genero = "Hombre" if any(w in msg_lower for w in ['hombre', 'masculino', 'varón', 'varon']) else "Mujer"
        
        if not state.slots.estado:
            estados_mx = [
                'aguascalientes', 'baja california', 'baja california sur', 'campeche', 'chiapas', 
                'chihuahua', 'coahuila', 'colima', 'durango', 'guanajuato', 'guerrero', 'hidalgo', 
                'jalisco', 'mexico', 'méxico', 'cdmx', 'michoacan', 'michoacán', 'morelos', 
                'nayarit', 'nuevo leon', 'nuevo león', 'oaxaca', 'puebla', 'queretaro', 'querétaro', 
                'quintana roo', 'san luis potosi', 'san luis potosí', 'sinaloa', 'sonora', 'tabasco', 
                'tamaulipas', 'tlaxcala', 'veracruz', 'yucatan', 'yucatán', 'zacatecas'
            ]
            for est in estados_mx:
                if est in msg_lower:
                    state.slots.estado = est.title()
                    break

    # 5. ORDEN ESTRICTO SECUENCIAL
    missing_prompt = ""
    if not state.slots.nombres:
        missing_prompt = "tu nombre o nombres de pila (sin apellidos)"
    elif not state.slots.primer_apellido:
        missing_prompt = "tu primer apellido (apellido paterno)"
    elif not state.slots.segundo_apellido:
        missing_prompt = "tu segundo apellido (apellido materno, o dime 'no tengo' si no cuentas con él)"
    elif not state.slots.fecha:
        missing_prompt = "tu fecha de nacimiento exacta"
    elif not state.slots.estado:
        missing_prompt = "en qué estado de la República naciste"
    elif not state.slots.genero:
        missing_prompt = "tu género (hombre o mujer)"

    # Transición al completar ranuras
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

    # 6. GENERACIÓN DETERMINISTA (Cero Saludos Repetidos)
    prefix = ""
    if not state.greeted:
        prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu trámite. "
        state.greeted = True
    else:
        acks = ["Perfecto. ", "Muy bien. ", "Anotado. ", "Gracias. "]
        prefix = acks[len(last_msg) % len(acks)]

    return f"{prefix}Por favor, dime {missing_prompt}."
