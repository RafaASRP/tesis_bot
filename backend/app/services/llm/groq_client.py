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
    last_prompted_slot: Optional[str] = None
    correcting_field: Optional[str] = None
    slots: CurpSlots = Field(default_factory=CurpSlots)

# Almacén efímero en RAM (LGPDPPSO - Zero Persistence)
SESSION_STATES: Dict[str, SessionState] = {}

# Vocabulario de control utilizado para no confundir la indicación de un error con un valor real
META_CORRECTION_WORDS = {
    "el", "la", "los", "las", "un", "una", "en", "de", "del", "mi", "mis",
    "error", "errores", "esta", "está", "estan", "están", "es", "son",
    "dato", "datos", "campo", "campos", "parte", "partes",
    "nombre", "nombres", "pila", "apellido", "apellidos", "primer", "segundo",
    "paterno", "materno", "fecha", "nacimiento", "estado", "entidad",
    "genero", "género", "sexo", "mal", "incorrecto", "incorrecta",
    "incorrectos", "incorrectas", "corregir", "cambiar", "por", "favor",
    "tengo", "tiene", "hubo", "hay", "seria", "sería", "fue"
}

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
        "mis nombres son", "mi nombre sería", "me pusieron", "es", "me dicen",
        "de nombre es", "de nombre", "pila:"
    ]
    sorted_muletillas = sorted(muletillas, key=len, reverse=True)
    for mul in sorted_muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    
    cleaned = re.sub(r"[.,;:!¡?¿]", "", cleaned).strip()
    return cleaned.title() if len(cleaned) >= 2 else None

def clean_paterno(text: str) -> Optional[str]:
    """Extrae únicamente el apellido paterno eliminando prefijos y verbos reflexivos."""
    if not text:
        return None
    cleaned = text.strip()
    muletillas = [
        "mi primer apellido es", "mi apellido paterno es", "el apellido paterno es",
        "el primer apellido es", "el paterno es", "primer apellido es", "apellido paterno:",
        "primer apellido:", "paterno:", "mi paterno es", "apellido:", "tengo el apellido",
        "de primer apellido", "mi apellido es", "me apellido es", "me apellido",
        "mi apellido", "de apellido", "apellidado", "tengo por apellido",
        "sería", "pues es", "es"
    ]
    sorted_muletillas = sorted(muletillas, key=len, reverse=True)
    for mul in sorted_muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    
    cleaned = re.sub(r"[.,;:!¡?¿]", "", cleaned).strip()
    return cleaned.title() if len(cleaned) >= 2 else None

def clean_materno(text: str) -> Tuple[Optional[str], bool]:
    """Extrae el apellido materno o detecta ausencia legítima."""
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
        "el segundo apellido es", "el materno es", "segundo apellido es", "apellido materno:",
        "segundo apellido:", "materno:", "mi materno es", "apellido:", "de segundo apellido",
        "de parte de mi mama es", "de parte de mi mamá es", "sería", "pues es", "mi materno es",
        "mi segundo apellido", "segundo apellido", "materno es", "me apellido", "de apellido", "es"
    ]
    raw = text.strip()
    sorted_muletillas = sorted(muletillas, key=len, reverse=True)
    for mul in sorted_muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        raw = re.sub(pattern, "", raw, flags=re.IGNORECASE).strip()
    
    raw = re.sub(r"[.,;:!¡?¿]", "", raw).strip()
    return (raw.title(), False) if len(raw) >= 2 else (None, False)

def clean_birth_date(text: str) -> Optional[str]:
    """Normaliza de forma determinista la fecha al formato canónico 'DD de [mes] de AAAA'."""
    if not text:
        return None

    raw = text.strip()
    muletillas = [
        'yo naci el dia', 'yo nací el día', 'yo naci en', 'yo nací en',
        'yo naci el', 'yo nací el', 'yo naci', 'yo nací',
        'naci el dia', 'nací el día', 'naci en', 'nací en',
        'naci el', 'nací el', 'naci', 'nací',
        'el dia', 'el día', 'mi fecha es', 'fecha de nacimiento:', 'fecha:'
    ]
    for mul in muletillas:
        if raw.lower().startswith(mul):
            raw = raw[len(mul):].strip()

    meses_dict = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'setiembre': 9, 'octubre': 10,
        'noviembre': 11, 'diciembre': 12
    }
    meses_nombres = [
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
    ]
    meses_patron = '|'.join(meses_dict.keys())

    def normalize_year(y: int) -> int:
        if y < 100:
            return 2000 + y if y <= 26 else 1900 + y
        return y

    # 1. Patrón con mes en texto
    m_txt = re.search(
        rf"\b([0-3]?\d)\s*(?:de\s+)?({meses_patron})\s*(?:del?\s+|de\s+|\s+)?(\d{{2,4}})\b",
        raw,
        re.IGNORECASE
    )
    if m_txt:
        dia = int(m_txt.group(1))
        mes_num = meses_dict[m_txt.group(2).lower()]
        anio = normalize_year(int(m_txt.group(3)))
        if 1 <= dia <= 31 and 1900 <= anio <= 2026:
            return f"{dia} de {meses_nombres[mes_num - 1]} de {anio}"

    # 2. Patrón numérico con conectores (del, de, /, -, ., espacios)
    m_num = re.search(
        r"\b([0-3]?\d)\s*(?:del?|de|[\/\-\.\s])\s*([0-1]?\d)\s*(?:del?|de|[\/\-\.\s])\s*(\d{2,4})\b",
        raw,
        re.IGNORECASE
    )
    if m_num:
        dia = int(m_num.group(1))
        mes_num = int(m_num.group(2))
        anio = normalize_year(int(m_num.group(3)))
        if 1 <= dia <= 31 and 1 <= mes_num <= 12 and 1900 <= anio <= 2026:
            return f"{dia} de {meses_nombres[mes_num - 1]} de {anio}"

    # 3. Patrón numérico compacto
    m_comp = re.search(r"\b([0-3]\d)([0-1]\d)(\d{2,4})\b", raw)
    if m_comp:
        dia = int(m_comp.group(1))
        mes_num = int(m_comp.group(2))
        anio = normalize_year(int(m_comp.group(3)))
        if 1 <= dia <= 31 and 1 <= mes_num <= 12 and 1900 <= anio <= 2026:
            return f"{dia} de {meses_nombres[mes_num - 1]} de {anio}"

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
    """Evalúa la respuesta en la fase HITL priorizando negaciones."""
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
    """Identifica el campo específico a rectificar."""
    raw = text.lower().strip()

    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["todo", "todos", "completo", "empezar de nuevo", "reiniciar"]):
        return "todo"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["segundo apellido", "materno", "apellido materno"]):
        return "segundo_apellido"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["primer apellido", "paterno", "apellido paterno"]):
        return "primer_apellido"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["apellido", "apellidos"]):
        return "ambiguous_apellido"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["nombre", "nombres", "pila"]):
        return "nombres"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["fecha", "nacimiento", "cumpleaños", "año", "mes", "dia", "día"]):
        return "fecha"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["estado", "entidad", "lugar", "donde naci", "donde nací"]):
        return "estado"
    if any(re.search(rf"\b{re.escape(w)}\b", raw) for w in ["genero", "género", "sexo"]):
        return "genero"

    return None

def has_substantive_inline_value(text: str) -> bool:
    """Verifica si el mensaje contiene un valor sustantivo nuevo o solo nombra el campo."""
    clean = re.sub(r"[.,;:!¡?¿\-\(\)]", " ", text.lower())
    tokens = [t.strip() for t in clean.split() if t.strip()]
    substantive = [t for t in tokens if t not in META_CORRECTION_WORDS]
    return len(substantive) > 0

def extract_inline_correction(field: str, text: str) -> Optional[str]:
    """Extrae el nuevo valor únicamente si el usuario lo incluyó de forma sustantiva."""
    if not has_substantive_inline_value(text):
        return None

    raw = text.strip()
    m_val = re.search(r"(?:es|sería|seria|debe ser|poner|pon)\s+(.+)$", raw, re.IGNORECASE)
    candidate = m_val.group(1).strip() if m_val else raw

    if field == "segundo_apellido":
        c_val, has_no = clean_materno(candidate)
        if has_no: return "No tiene"
        if c_val and c_val.lower() not in ["segundo apellido", "apellido materno", "materno", "segundo"]:
            return c_val
    elif field == "primer_apellido":
        c_val = clean_paterno(candidate)
        if c_val and c_val.lower() not in ["primer apellido", "apellido paterno", "paterno", "primer", "apellido"]:
            return c_val
    elif field == "nombres":
        c_val = clean_given_names(candidate)
        if c_val and c_val.lower() not in ["nombre", "nombres", "pila"]:
            return c_val
    elif field == "fecha":
        c_val = clean_birth_date(candidate)
        if c_val: return c_val
    elif field == "estado":
        c_val = clean_mexico_state(candidate)
        if c_val: return c_val
    elif field == "genero":
        c_val = clean_gender(candidate)
        if c_val: return c_val

    return None

def format_summary(slots: CurpSlots) -> str:
    """Genera el resumen de validación."""
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

    # 1. PURGA EXPLÍCITA (LGPDPPSO)
    if any(w in msg_lower for w in ['cancelar', 'reiniciar', 'salir', 'borrar', 'empezar de nuevo']):
        if session_id in SESSION_STATES:
            del SESSION_STATES[session_id]
        return "He reiniciado la consulta por seguridad. ¿En qué trámite federal te puedo ayudar hoy (CURP, Acta, IMSS, Pasaporte, Cédula)?"

    # 2. INICIALIZACIÓN DE ESTADO EFÍMERO
    if session_id not in SESSION_STATES:
        SESSION_STATES[session_id] = SessionState()
    
    state = SESSION_STATES[session_id]

    # REINICIO AL DETECTAR INICIO DE TRÁMITE DE CURP
    if any(w in msg_lower for w in ['quiero mi curp', 'necesito mi curp', 'sacar mi curp', 'tramitar curp', 'quiero un curp', 'necesito un curp', 'sacar curp']):
        state.slots = CurpSlots()
        state.status = "collecting"
        state.greeted = True
        state.last_prompted_slot = "nombres"
        return "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu CURP. Por favor, dime tu nombre o nombres de pila (sin apellidos)."

    # 3. FASE DE CORRECCIÓN SELECTIVA: RECEPCIÓN DEL VALOR CORREGIDO
    if state.status == "correcting_slot":
        field = state.correcting_field
        success = False
        if field == "nombres":
            c_val = clean_given_names(last_msg)
            if c_val:
                state.slots.nombres = c_val
                success = True
        elif field == "primer_apellido":
            c_val = clean_paterno(last_msg)
            if c_val:
                state.slots.primer_apellido = c_val
                success = True
        elif field == "segundo_apellido":
            c_val, has_no = clean_materno(last_msg)
            state.slots.segundo_apellido = "No tiene" if has_no else (c_val if c_val else last_msg.strip().title())
            success = True
        elif field == "fecha":
            c_val = clean_birth_date(last_msg)
            if c_val:
                state.slots.fecha = c_val
                success = True
            else:
                return "No logré reconocer la fecha. Por favor indícala indicando día, mes y año (por ejemplo: 17 de abril de 2001 o 17/04/2001)."
        elif field == "estado":
            c_val = clean_mexico_state(last_msg)
            if c_val:
                state.slots.estado = c_val
                success = True
            else:
                return "No reconocí la entidad. Por favor indícame tu estado de nacimiento (por ejemplo: Hidalgo, Tlaxcala, Puebla o CDMX)."
        elif field == "genero":
            c_val = clean_gender(last_msg)
            if c_val:
                state.slots.genero = c_val
                success = True
            else:
                return "Por favor, indícame tu género (hombre o mujer)."

        if success:
            state.status = "confirming"
            state.correcting_field = None
            return (
                "¡Dato actualizado con éxito!\n\n"
                "Por favor, verifica detenidamente si ahora todos tus datos son correctos:\n"
                f"{format_summary(state.slots)}\n\n"
                "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
            )

    # 4. FASE DE CORRECCIÓN SELECTIVA: IDENTIFICACIÓN DEL CAMPO ERRÓNEO
    if state.status == "asking_correction_slot":
        target_field = detect_field_to_correct(last_msg)

        if target_field == "todo":
            state.status = "collecting"
            state.slots = CurpSlots()
            state.last_prompted_slot = "nombres"
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
                    "fecha": "tu fecha de nacimiento exacta (ej. 17 de abril de 2001 o 17/04/2001)",
                    "estado": "en qué estado de la República naciste",
                    "genero": "tu género (hombre o mujer)"
                }
                return f"De acuerdo. Por favor, indícame {prompts[target_field]}."
        else:
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

    # 5. FASE DE CONFIRMACIÓN (HITL)
    if state.status == "confirming":
        decision = evaluate_confirmation(last_msg)
        
        if decision is False:
            target_field = detect_field_to_correct(last_msg)
            if target_field == "todo":
                state.status = "collecting"
                state.slots = CurpSlots()
                state.last_prompted_slot = "nombres"
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
                        "fecha": "tu fecha de nacimiento exacta (ej. 17 de abril de 2001)",
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

    # 6. EXTRACCIÓN HEURÍSTICA Y NER EN FASE DE RECOLECCIÓN
    if state.status == "collecting":
        last_slot = state.last_prompted_slot
        slot_updated = False

        if last_slot == "nombres" and not state.slots.nombres:
            c_nom = clean_given_names(last_msg)
            if c_nom:
                state.slots.nombres = c_nom
                slot_updated = True
        elif last_slot == "primer_apellido" and not state.slots.primer_apellido:
            c_pat = clean_paterno(last_msg)
            if c_pat:
                state.slots.primer_apellido = c_pat
                slot_updated = True
        elif last_slot == "segundo_apellido" and not state.slots.segundo_apellido:
            c_mat, has_no = clean_materno(last_msg)
            state.slots.segundo_apellido = "No tiene" if has_no else c_mat
            if state.slots.segundo_apellido:
                slot_updated = True
        elif last_slot == "fecha" and not state.slots.fecha:
            c_fec = clean_birth_date(last_msg)
            if c_fec:
                state.slots.fecha = c_fec
                slot_updated = True
            else:
                return "No logré reconocer la fecha. Por favor indícala indicando día, mes y año (por ejemplo: 17 de abril de 2001 o 17/04/2001)."
        elif last_slot == "estado" and not state.slots.estado:
            c_est = clean_mexico_state(last_msg)
            if c_est:
                state.slots.estado = c_est
                slot_updated = True
            else:
                return "No reconocí la entidad. Por favor indícame tu estado de nacimiento (por ejemplo: Hidalgo, Tlaxcala, Puebla o CDMX)."
        elif last_slot == "genero" and not state.slots.genero:
            c_gen = clean_gender(last_msg)
            if c_gen:
                state.slots.genero = c_gen
                slot_updated = True
            else:
                return "Por favor, indícame tu género (hombre o mujer)."

        if not slot_updated and api_key and "invalid" not in api_key.lower():
            try:
                client = Groq(api_key=api_key)
                extractor_prompt = (
                    "Eres un extractor NER para trámites oficiales de México. Analiza el texto e ignora la paja conversacional. "
                    "Devuelve ÚNICAMENTE un JSON con las claves: 'nombres', 'primer_apellido', 'segundo_apellido', 'fecha', 'estado', 'genero'. "
                    "Si un dato no existe, asigna null. No agregues texto adicional."
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

    # 7. DETERMINACIÓN DEL SIGUIENTE SLOT SECUENCIAL
    missing_slot = None
    missing_prompt = ""
    if not state.slots.nombres:
        missing_slot = "nombres"
        missing_prompt = "tu nombre o nombres de pila (sin apellidos)"
    elif not state.slots.primer_apellido:
        missing_slot = "primer_apellido"
        missing_prompt = "tu primer apellido (apellido paterno)"
    elif not state.slots.segundo_apellido:
        missing_slot = "segundo_apellido"
        missing_prompt = "tu segundo apellido (apellido materno, o dime 'no tengo' si no cuentas con él)"
    elif not state.slots.fecha:
        missing_slot = "fecha"
        missing_prompt = "tu fecha de nacimiento exacta (ej. 17 de abril de 2001 o 17/04/2001)"
    elif not state.slots.estado:
        missing_slot = "estado"
        missing_prompt = "en qué estado de la República naciste"
    elif not state.slots.genero:
        missing_slot = "genero"
        missing_prompt = "tu género (hombre o mujer)"

    # Transición al completar recolección
    if not missing_slot:
        state.status = "confirming"
        state.last_prompted_slot = None
        return (
            "¡Excelente! He extraído y separado todos tus datos de forma segura.\n\n"
            "Por favor, verifica detenidamente que sean correctos:\n"
            f"{format_summary(state.slots)}\n\n"
            "¿Confirmas que esta información es correcta para proceder? (Responde Sí o No)"
        )

    state.last_prompted_slot = missing_slot

    prefix = ""
    if not state.greeted:
        prefix = "¡Hola! Qué gusto saludarte. Te guiaré paso a paso con tu CURP. "
        state.greeted = True
    else:
        acks = ["Perfecto. ", "Muy bien. ", "Anotado. ", "Gracias. "]
        prefix = acks[len(last_msg) % len(acks)]

    return f"{prefix}Por favor, dime {missing_prompt}."
