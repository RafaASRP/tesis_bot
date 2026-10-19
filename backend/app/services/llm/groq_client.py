import os
import re
import json
import logging
from typing import Dict, Tuple, Optional
from pydantic import BaseModel, Field
from groq import Groq

logger = logging.getLogger("govassist-groq")

# Tipado estricto con Pydantic v2
class CurpSlots(BaseModel):
    nombres: Optional[str] = None
    primer_apellido: Optional[str] = None
    segundo_apellido: Optional[str] = None
    fecha: Optional[str] = None
    estado: Optional[str] = None
    genero: Optional[str] = None

class SessionState(BaseModel):
    status: str = "collecting"  # collecting | confirming | asking_correction_slot | correcting_slot | confirmed
    greeted: bool = False
    correcting_field: Optional[str] = None
    slots: CurpSlots = Field(default_factory=CurpSlots)

# Almacén efímero en RAM (LGPDPPSO - Zero Persistence)
SESSION_STATES: Dict[str, SessionState] = {}

# ==============================================================================
# MOTORES HEURÍSTICOS DE LIMPIEZA Y NORMALIZACIÓN LÉXICA
# ==============================================================================

def clean_given_names(text: str) -> Optional[str]:
    """Extrae únicamente los nombres de pila descartando muletillas conversacionales."""
    if not text:
        return None
    cleaned = text.strip()
    muletillas = [
        "yo me llamo", "me llamo", "mi nombre es", "yo soy", "soy", 
        "mi nombre de pila es", "nombre de pila:", "nombre completo:", "nombre:",
        "pues me llamo", "hola me llamo", "hola soy", "hola, me llamo", "hola, soy",
        "mis nombres son", "mi nombre sería", "me pusieron", "es"
    ]
    for mul in muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    
    cleaned = re.sub(r"[.,;:!¡?¿]", "", cleaned).strip()
    return cleaned.title() if len(cleaned) >= 2 else None

def clean_paterno(text: str) -> Optional[str]:
    """Extrae únicamente el apellido paterno eliminando prefijos."""
    if not text:
        return None
    cleaned = text.strip()
    muletillas = [
        "mi primer apellido es", "mi apellido paterno es", "el apellido paterno es",
        "el paterno es", "primer apellido es", "apellido paterno:", "primer apellido:",
        "paterno:", "apellido:", "es", "tengo el apellido", "de primer apellido",
        "sería", "pues es", "mi paterno es"
    ]
    for mul in muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    
    cleaned = re.sub(r"[.,;:!¡?¿]", "", cleaned).strip()
    return cleaned.title() if len(cleaned) >= 2 else None

def clean_materno(text: str) -> Tuple[Optional[str], bool]:
    """
    Extrae el apellido materno. Si detecta ausencia legítima, retorna ('No tiene', True).
    """
    if not text:
        return None, False
    cleaned = text.strip().lower()
    
    patrones_ausencia = [
        r"\bno tengo\b", r"\bno cuento\b", r"\bsin apellido\b", r"\bninguno\b",
        r"\bno hay\b", r"\bno poseo\b", r"^no\b", r"^n/a$", r"^na$", r"^ninguna$"
    ]
    if any(re.search(p, cleaned) for p in patrones_ausencia):
        return "No tiene", True

    muletillas = [
        "mi segundo apellido es", "mi apellido materno es", "el apellido materno es",
        "el materno es", "segundo apellido es", "apellido materno:", "segundo apellido:",
        "materno:", "apellido:", "es", "de segundo apellido", "de parte de mi mama es",
        "de parte de mi mamá es", "sería", "pues es", "mi materno es"
    ]
    raw = text.strip()
    for mul in muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        raw = re.sub(pattern, "", raw, flags=re.IGNORECASE).strip()
    
    raw = re.sub(r"[.,;:!¡?¿]", "", raw).strip()
    return (raw.title(), False) if len(raw) >= 2 else (None, False)

def clean_birth_date(text: str) -> Optional[str]:
    """Normaliza de forma determinista la fecha al formato canónico 'DD de [mes] de AAAA'."""
    if not text:
        return None

    meses = {
        'enero': 'enero', 'febrero': 'febrero', 'marzo': 'marzo', 'abril': 'abril',
        'mayo': 'mayo', 'junio': 'junio', 'julio': 'julio', 'agosto': 'agosto',
        'septiembre': 'septiembre', 'setiembre': 'septiembre', 'octubre': 'octubre',
        'noviembre': 'noviembre', 'diciembre': 'diciembre'
    }
    meses_patron = '|'.join(meses.keys())

    match_txt = re.search(
        rf"\b([0-3]?\d)\s*(?:de\s+)?({meses_patron})\s*(?:del?\s+|de\s+|\s+)?(\d{{4}})\b",
        text,
        re.IGNORECASE
    )
    if match_txt:
        dia = int(match_txt.group(1))
        mes = meses[match_txt.group(2).lower()]
        anio = match_txt.group(3)
        return f"{dia} de {mes} de {anio}"

    match_num = re.search(r"\b([0-3]?\d)[/-]([0-1]?\d)[/-](\d{4}\b)", text)
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

    return None

def clean_mexico_state(text: str) -> Optional[str]:
    """Normaliza el estado al catálogo formal de 32 entidades federativas."""
    if not text:
        return None
    raw = text.lower()

    catalog = {
        "aguascalientes": "Aguascalientes",
        "baja california sur": "Baja California Sur",
        "baja california": "Baja California",
        "campeche": "Campeche",
        "coahuila": "Coahuila",
        "colima": "Colima",
        "chiapas": "Chiapas",
        "chihuahua": "Chihuahua",
        "ciudad de méxico": "Ciudad de México",
        "ciudad de mexico": "Ciudad de México",
        "cdmx": "Ciudad de México",
        "distrito federal": "Ciudad de México",
        "d.f.": "Ciudad de México",
        "df": "Ciudad de México",
        "durango": "Durango",
        "guanajuato": "Guanajuato",
        "guerrero": "Guerrero",
        "hidalgo": "Hidalgo",
        "jalisco": "Jalisco",
        "estado de méxico": "Estado de México",
        "estado de mexico": "Estado de México",
        "edomex": "Estado de México",
        "méxico": "Estado de México",
        "mexico": "Estado de México",
        "michoacán": "Michoacán",
        "michoacan": "Michoacán",
        "morelos": "Morelos",
        "nayarit": "Nayarit",
        "nuevo león": "Nuevo León",
        "nuevo leon": "Nuevo León",
        "oaxaca": "Oaxaca",
        "puebla": "Puebla",
        "querétaro": "Querétaro",
        "queretaro": "Querétaro",
        "quintana roo": "Quintana Roo",
        "san luis potosí": "San Luis Potosí",
        "san luis potosi": "San Luis Potosí",
        "sinaloa": "Sinaloa",
        "sonora": "Sonora",
        "tabasco": "Tabasco",
        "tamaulipas": "Tamaulipas",
        "tlaxcala": "Tlaxcala",
        "veracruz": "Veracruz",
        "yucatán": "Yucatán",
        "yucatan": "Yucatán",
        "zacatecas": "Zacatecas"
    }

    for key, formal in catalog.items():
        if re.search(rf"\b{re.escape(key)}\b", raw):
            return formal

    return None

def clean_gender(text: str) -> Optional[str]:
    """Identifica y normaliza el género ciudadano."""
    if not text:
        return None
    raw = text.lower()
    
    masculinos = [r"\bhombre\b", r"\bmasculino\b", r"\bvarón\b", r"\bvaron\b", r"\bm\b"]
    femeninos = [r"\bmujer\b", r"\bfemenino\b", r"\bfemenina\b", r"\bf\b"]

    if any(re.search(p, raw) for p in masculinos):
        return "Hombre"
    if any(re.search(p, raw) for p in femeninos):
        return "Mujer"
    
    return None

def evaluate_confirmation(text: str) -> Optional[bool]:
    """
    Evalúa la respuesta en la fase HITL.
    Precedencia negativa estricta para evitar falsos positivos con 'correcto'.
    """
    if not text:
        return None
    raw = text.lower().strip()

    negativas = [
        r"\bno\b", r"\bmal\b", r"\bincorrecto\b", r"\bincorrecta\b", r"\bincorrectos\b",
        r"\bcorregir\b", r"\bcambiar\b", r"\berror\b", r"\bfalso\b", r"\bequivocado\b",
        r"\bequivocada\b", r"\bespera\b", r"\bno es correcto\b", r"\bno son correctos\b",
        r"\bno es correcta\b", r"\bno está bien\b", r"\bno esta bien\b", r"\bestá mal\b",
        r"\besta mal\b", r"\bno confirmo\b", r"\bestan mal\b", r"\bestán mal\b",
        r"\bhay un error\b", r"\bme equivoqué\b", r"\bme equivoque\b", r"\bparar\b",
        r"\bson incorrectos\b", r"\bestá incorrecto\b", r"\besta incorrecto\b"
    ]

    if any(re.search(p, raw) for p in negativas):
        return False

    afirmativas = [
        r"\bsí\b", r"\bsi\b", r"\bclaro\b", r"\bcorrecto\b", r"\bcorrecta\b",
        r"\bcorrectos\b", r"\badelante\b", r"\bconfirmo\b", r"\bok\b", r"\bproceder\b",
        r"\bexacto\b", r"\bestá bien\b", r"\besta bien\b", r"\bes correcta\b",
        r"\bes correcto\b", r"\bson correctos\b", r"\bson correctas\b", r"\basi es\b",
        r"\basí es\b", r"\btodo es correcto\b", r"\btodo bien\b", r"\bde acuerdo\b",
        r"\bprocede\b", r"\bcontinua\b", r"\bcontinuar\b"
    ]

    if any(re.search(p, raw) for p in afirmativas):
        return True

    return None

def detect_field_to_correct(text: str) -> Optional[str]:
    """Identifica qué campo específico desea rectificar el ciudadano."""
    raw = text.lower().strip()

    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["todo", "todos", "completo", "empezar de nuevo", "desde el principio", "reiniciar"]):
        return "todo"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["segundo apellido", "materno", "apellido materno", "segundo"]):
        return "segundo_apellido"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["primer apellido", "paterno", "apellido paterno", "primer"]):
        return "primer_apellido"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["apellido", "apellidos"]):
        return "ambiguous_apellido"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["nombre", "nombres", "pila"]):
        return "nombres"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["fecha", "nacimiento", "cumpleaños", "año", "mes", "dia", "día"]):
        return "fecha"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["estado", "entidad", "lugar", "donde naci", "donde nací", "republica", "república"]):
        return "estado"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["genero", "género", "sexo"]):
        return "genero"

    return None

def extract_inline_correction(field: str, text: str) -> Optional[str]:
    """Si el usuario aportó el valor nuevo en la misma frase, lo extrae directamente."""
    raw = text.strip()
    stopwords = ["en", "el", "la", "mi", "de", "los", "las", "dato", "parte", "campo", "es", "esta", "está", "segundo", "primer", "apellido", "materno", "paterno", "nombre", "nombres", "fecha", "nacimiento", "estado", "genero", "género"]
    words = [w for w in re.split(r"\s+", raw) if w.lower() not in stopwords]
    if not words:
        return None

    if field == "segundo_apellido":
        c_val, has_no = clean_materno(raw)
        if has_no: return "No tiene"
        if c_val and c_val.lower() not in ["segundo apellido", "apellido materno", "materno", "segundo"]:
            return c_val
    elif field == "primer_apellido":
        c_val = clean_paterno(raw)
        if c_val and c_val.lower() not in ["primer apellido", "apellido paterno", "paterno", "primer", "apellido"]:
            return c_val
    elif field == "nombres":
        c_val = clean_given_names(raw)
        if c_val and c_val.lower() not in ["nombre", "nombres", "pila"]:
            return c_val
    elif field == "fecha":
        c_val = clean_birth_date(raw)
        if c_val: return c_val
    elif field == "estado":
        c_val = clean_mexico_state(raw)
        if c_val: return c_val
    elif field == "genero":
        c_val = clean_gender(raw)
        if c_val: return c_val

    return None

def format_summary(slots: CurpSlots) -> str:
    """Genera la visualización canónica de los datos para confirmación."""
    return (
        f"• Nombres: {slots.nombres}\n"
        f"• Primer Apellido: {slots.primer_apellido}\n"
        f"• Segundo Apellido: {slots.segundo_apellido or 'N/A'}\n"
        f"• Fecha: {slots.fecha}\n"
        f"• Estado: {slots.estado}\n"
        f"• Género: {slots.genero}"
    )

# ==============================================================================
# CONTROLADOR PRINCIPAL DEL MOTOR CONVERSACIONAL (FastAPI Service)
# ==============================================================================

def get_groq_response(messages_history: list, session_id: str = "default_session") -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    
    last_msg_obj = messages_history[-1] if messages_history else None
    last_msg = getattr(last_msg_obj, "content", str(last_msg_obj)).strip() if last_msg_obj else ""
    msg_lower = last_msg.lower()

    # 1. PURGA EXPLÍCITA (Cero Persistencia LGPDPPSO)
    if any(w in msg_lower for w in ['cancelar', 'reiniciar', 'salir', 'borrar', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        return "He reiniciado la consulta por seguridad. ¿En qué trámite federal te puedo ayudar hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?"

    # 2. INICIALIZACIÓN DE LA MÁQUINA DE ESTADOS (FSM)
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = SessionState()
    
    state = SESSION_STATES[session_id]

    # 3. FASE DE CORRECCIÓN SELECTIVA: RECEPCIÓN DEL VALOR CORREGIDO
    if state.status == "correcting_slot":
        field = state.correcting_field
        if field == "nombres":
            c_val = clean_given_names(last_msg)
            state.slots.nombres = c_val if c_val else last_msg.strip().title()
        elif field == "primer_apellido":
            c_val = clean_paterno(last_msg)
            state.slots.primer_apellido = c_val if c_val else last_msg.strip().title()
        elif field == "segundo_apellido":
            c_val, has_no = clean_materno(last_msg)
            if has_no:
                state.slots.segundo_apellido = "No tiene"
            else:
                state.slots.segundo_apellido = c_val if c_val else last_msg.strip().title()
        elif field == "fecha":
            c_val = clean_birth_date(last_msg)
            state.slots.fecha = c_val if c_val else last_msg.strip()
        elif field == "estado":
            c_val = clean_mexico_state(last_msg)
            state.slots.estado = c_val if c_val else last_msg.strip().title()
        elif field == "genero":
            c_val = clean_gender(last_msg)
            state.slots.genero = c_val if c_val else last_msg.strip().title()

        state.status = "confirming"
        state.correcting_field = None
        return (
            "¡Dato actualizado con éxito!\n\n"
            "Por favor, verifica detenidamente si ahora todos tus datos son correctos:\n"
            f"{format_summary(state.slots)}\n\n"
            "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
        )

    # 4. FASE DE CORRECCIÓN SELECTIVA: PREGUNTAR QUÉ DATO CAMBIAR
    if state.status == "asking_correction_slot":
        target_field = detect_field_to_correct(last_msg)

        if target_field == "todo":
            state.status = "collecting"
            state.slots = CurpSlots()
            return "Entendido. Vamos a reiniciar todos tus datos desde el principio. Por favor, dime tu nombre o nombres de pila (sin apellidos)."

        if target_field == "ambiguous_apellido":
            return "¿Deseas corregir tu primer apellido (paterno) o tu segundo apellido (materno)?"

        if target_field:
            inline_val = extract_inline_correction(target_field, last_msg)
            if inline_val:
                setattr(state.slots, target_field, inline_val)
                state.status = "confirming"
                state.correcting_field = None
                return (
                    "¡Dato actualizado con éxito!\n\n"
                    "Por favor, verifica detenidamente si ahora todos tus datos son correctos:\n"
                    f"{format_summary(state.slots)}\n\n"
                    "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
                )
            else:
                state.status = "correcting_slot"
                state.correcting_field = target_field
                prompts = {
                    "nombres": "tu nombre o nombres de pila (sin apellidos) correcto",
                    "primer_apellido": "tu primer apellido (apellido paterno) correcto",
                    "segundo_apellido": "tu segundo apellido (apellido materno) correcto (o dime 'no tengo' si no cuentas con él)",
                    "fecha": "tu fecha de nacimiento exacta",
                    "estado": "en qué estado de la República naciste",
                    "genero": "tu género (hombre o mujer)"
                }
                return f"De acuerdo. Por favor, indícame {prompts[target_field]}."
        else:
            # Fallback heurístico por si el usuario dio el valor directamente
            date_cand = clean_birth_date(last_msg)
            if date_cand:
                state.slots.fecha = date_cand
                state.status = "confirming"
                return f"¡Dato actualizado con éxito!\n\nPor favor, verifica detenidamente si ahora todos tus datos son correctos:\n{format_summary(state.slots)}\n\n¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"

            state_cand = clean_mexico_state(last_msg)
            if state_cand:
                state.slots.estado = state_cand
                state.status = "confirming"
                return f"¡Dato actualizado con éxito!\n\nPor favor, verifica detenidamente si ahora todos tus datos son correctos:\n{format_summary(state.slots)}\n\n¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"

            gender_cand = clean_gender(last_msg)
            if gender_cand:
                state.slots.genero = gender_cand
                state.status = "confirming"
                return f"¡Dato actualizado con éxito!\n\nPor favor, verifica detenidamente si ahora todos tus datos son correctos:\n{format_summary(state.slots)}\n\n¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"

            return "No logré identificar qué dato deseas corregir. Por favor, indícame el nombre del campo que quieres cambiar: nombre, apellido paterno, apellido materno, fecha, estado o género."

    # 5. FASE DE CONFIRMACIÓN (Human-in-the-Loop)
    if state.status == "confirming":
        decision = evaluate_confirmation(last_msg)
        
        if decision is False:
            target_field = detect_field_to_correct(last_msg)
            if target_field == "todo":
                state.status = "collecting"
                state.slots = CurpSlots()
                return "Entendido. Vamos a reiniciar todos tus datos desde el principio. Por favor, dime tu nombre o nombres de pila (sin apellidos)."
            elif target_field == "ambiguous_apellido":
                state.status = "asking_correction_slot"
                return "¿Deseas corregir tu primer apellido (paterno) o tu segundo apellido (materno)?"
            elif target_field:
                inline_val = extract_inline_correction(target_field, last_msg)
                if inline_val:
                    setattr(state.slots, target_field, inline_val)
                    return (
                        "¡Dato actualizado con éxito!\n\n"
                        "Por favor, verifica detenidamente si ahora todos tus datos son correctos:\n"
                        f"{format_summary(state.slots)}\n\n"
                        "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
                    )
                else:
                    state.status = "correcting_slot"
                    state.correcting_field = target_field
                    prompts = {
                        "nombres": "tu nombre o nombres de pila (sin apellidos) correcto",
                        "primer_apellido": "tu primer apellido (apellido paterno) correcto",
                        "segundo_apellido": "tu segundo apellido (apellido materno) correcto (o dime 'no tengo' si no cuentas con él)",
                        "fecha": "tu fecha de nacimiento exacta",
                        "estado": "en qué estado de la República naciste",
                        "genero": "tu género (hombre o mujer)"
                    }
                    return f"De acuerdo. Por favor, indícame {prompts[target_field]}."
            else:
                state.status = "asking_correction_slot"
                return "Entendido. No te preocupes, vamos a corregirlo. ¿En qué dato está el error? (Puedes decirme: nombre, apellido paterno, apellido materno, fecha, estado o género)."

        elif decision is True:
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

    # 6. EXTRACCIÓN NER JSON Y HEURÍSTICA CANÓNICA EN RECOLECCIÓN
    if state.status == "collecting":
        if api_key and "invalid" not in api_key.lower():
            try:
                client = Groq(api_key=api_key)
                extractor_prompt = (
                    "Eres un extractor NER para trámites oficiales de México. Analiza el texto e ignora la paja conversacional. "
                    "Devuelve ÚNICAMENTE un JSON con las claves: 'nombres', 'primer_apellido', 'segundo_apellido', 'fecha', 'estado', 'genero'. "
                    "Si un dato no existe, asigna null. No agregues texto adicional ni explicaciones."
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
                
                if not state.slots.nombres and extracted.get("nombres"):
                    clean_n = clean_given_names(str(extracted["nombres"]))
                    if clean_n: state.slots.nombres = clean_n

                if not state.slots.primer_apellido and extracted.get("primer_apellido"):
                    clean_p = clean_paterno(str(extracted["primer_apellido"]))
                    if clean_p: state.slots.primer_apellido = clean_p

                if not state.slots.segundo_apellido and extracted.get("segundo_apellido"):
                    clean_m, _ = clean_materno(str(extracted["segundo_apellido"]))
                    if clean_m: state.slots.segundo_apellido = clean_m

                if not state.slots.fecha and extracted.get("fecha"):
                    clean_f = clean_birth_date(str(extracted["fecha"]))
                    if clean_f: state.slots.fecha = clean_f

                if not state.slots.estado and extracted.get("estado"):
                    clean_e = clean_mexico_state(str(extracted["estado"]))
                    if clean_e: state.slots.estado = clean_e

                if not state.slots.genero and extracted.get("genero"):
                    clean_g = clean_gender(str(extracted["genero"]))
                    if clean_g: state.slots.genero = clean_g
            except Exception as e:
                logger.error(f"Error NER JSON Groq: {str(e)}")

        # Respaldo Heurístico Local en Python
        if not state.slots.nombres:
            if not any(w in msg_lower for w in ['curp', 'tramite', 'trámite', 'sacar', 'quiero', 'necesito']):
                c_nom = clean_given_names(last_msg)
                if c_nom: state.slots.nombres = c_nom
        elif not state.slots.primer_apellido:
            c_pat = clean_paterno(last_msg)
            if c_pat: state.slots.primer_apellido = c_pat
        elif not state.slots.segundo_apellido:
            c_mat, _ = clean_materno(last_msg)
            if c_mat: state.slots.segundo_apellido = c_mat

        if not state.slots.fecha:
            c_fec = clean_birth_date(last_msg)
            if c_fec: state.slots.fecha = c_fec

        if not state.slots.estado:
            c_est = clean_mexico_state(last_msg)
            if c_est: state.slots.estado = c_est

        if not state.slots.genero:
            c_gen = clean_gender(last_msg)
            if c_gen: state.slots.genero = c_gen

    # 7. ORDEN SECUENCIAL DETERMINISTA (IHC para Adultos 50+)
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

    # Transición al completar la captura inicial
    if not missing_prompt:
        state.status = "confirming"
        return (
            "¡Excelente! He extraído y separado todos tus datos de forma segura.\n\n"
            "Por favor, verifica detenidamente que sean correctos:\n"
            f"{format_summary(state.slots)}\n\n"
            "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
        )

    # 8. RESPUESTA DETERMINISTA SIN SALUDOS REPETITIVOS
    prefix = ""
    if not state.greeted:
        prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu trámite. "
        state.greeted = True
    else:
        acks = ["Perfecto. ", "Muy bien. ", "Anotado. ", "Gracias. "]
        prefix = acks[len(last_msg) % len(acks)]

    return f"{prefix}Por favor, dime {missing_prompt}."
