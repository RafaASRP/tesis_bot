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
    status: str = "collecting"
    greeted: bool = False
    slots: CurpSlots = Field(default_factory=CurpSlots)

# Almacén efímero en RAM (Cumplimiento LGPDPPSO - Zero Persistence)
SESSION_STATES: Dict[str, SessionState] = {}

# ==============================================================================
# MOTORES HEURÍSTICOS DE PURGA Y NORMALIZACIÓN DE "PAJA" CONVERSACIONAL
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
        "mis nombres son", "mi nombre sería", "me pusieron"
    ]
    for mul in muletillas:
        pattern = rf"^{re.escape(mul)}\s*"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
    
    # Eliminar signos o palabras de cierre
    cleaned = re.sub(r"[.,;:!¡?¿]", "", cleaned).strip()
    return cleaned.title() if len(cleaned) >= 2 else None

def clean_paterno(text: str) -> Optional[str]:
    """Extrae únicamente el apellido paterno eliminando introducciones conversacionales."""
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
    
    # Detección de no posesión de segundo apellido
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
    """
    Normaliza de forma determinista la fecha al formato canónico 'DD de [mes] de AAAA'.
    Elimina expresiones como 'yo nací el día', 'fue el', 'del año', etc.
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

    # Formato natural: '16 de abril del 2001', 'el 16 de abril de 2001'
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

    # Formato numérico: DD/MM/AAAA o DD-MM-AAAA
    match_num = re.search(r"\b([0-3]?\d)[/-]([0-1]?\d)[/-](\d{4})\b", text)
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
    """
    Normaliza el estado al catálogo formal de 32 entidades de gob.mx
    descartando muletillas como 'nací en el estado de', 'soy de', etc.
    """
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

    # Búsqueda por correspondencia exacta o subcadena en catálogo
    for key, formal in catalog.items():
        if re.search(rf"\b{re.escape(key)}\b", raw):
            return formal

    return None

def clean_gender(text: str) -> Optional[str]:
    """Identifica y normaliza el género ciudadano descartando pronombres."""
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
    Evalúa la respuesta del usuario en la fase Human-in-the-Loop (HITL).
    Retorna True (Afirmativo), False (Negativo) o None (Ambigüedad).
    Aplica precedencia negativa estricta con límites de palabra para evitar falsos positivos.
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
        r"\bhay un error\b", r"\bme equivoqué\b", r"\bme equivoque\b", r"\bparar\b"
    ]

    # Evaluación negativa inmediata
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

    # 3. FASE DE CONFIRMACIÓN (Human-in-the-Loop)
    if state.status == "confirming":
        decision = evaluate_confirmation(last_msg)
        
        if decision is False:
            state.status = "collecting"
            state.slots = CurpSlots()
            return "Entendido. He cancelado el proceso para corregir los datos. Empecemos de nuevo: por favor, dime tu nombre o nombres de pila (sin apellidos)."
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

    # 4. EXTRACCIÓN NER JSON Y HEURÍSTICA CANÓNICA
    if state.status == "collecting":
        # Llamada estructurada a Groq Llama 3 para aislamiento de entidades
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
                
                # Asignación preliminar asistida por IA
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

        # Respaldo Heurístico Local Determinista (Filtrado estricto en Python)
        if not state.slots.nombres:
            # Ignorar si es el saludo inicial del trámite
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

    # 5. ORDEN SECUENCIAL DETERMINISTA (IHC para Adultos 50+)
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

    # Transición al completar todos los slots requeridos
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
