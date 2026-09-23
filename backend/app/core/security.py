import logging
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataSecurityEngine:
    """
    Motor criptográfico simétrico AES-256 (Fernet) para protección
    de datos personales en tránsito y memoria volátil según LGPDPPSO.
    """

    def __init__(self, key: Optional[str] = None):
        raw_key = key or settings.SECRET_ENCRYPTION_KEY
        if not raw_key:
            # En entornos de desarrollo donde la clave no esté inyectada,
            # se genera una en memoria volátil para asegurar resiliencia.
            self._key = Fernet.generate_key()
            logger.warning("SECRET_ENCRYPTION_KEY no provista. Se generó una clave efímera en memoria.")
        else:
            self._key = raw_key.encode() if isinstance(raw_key, str) else raw_key
        
        self._cipher = Fernet(self._key)

    def encrypt_data(self, plain_text: str) -> str:
        """Cifra un dato sensible a texto seguro codificado en Base64."""
        if not plain_text:
            return ""
        encrypted_bytes = self._cipher.encrypt(plain_text.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")

    def decrypt_data(self, cipher_text: str) -> str:
        """Descifra una cadena de texto cifrada con la clave del sistema."""
        if not cipher_text:
            return ""
        try:
            decrypted_bytes = self._cipher.decrypt(cipher_text.encode("utf-8"))
            return decrypted_bytes.decode("utf-8")
        except InvalidToken:
            logger.error("Token de cifrado inválido o clave inconsistente.")
            raise ValueError("No fue posible descifrar los datos: clave inválida.")

    @staticmethod
    def mask_curp(curp: str) -> str:
        """
        Enmascara una CURP para bitácoras y telemetría cuantitativa:
        Ejemplo: ABCD010203HDFRRN09 -> ABCD******RN09
        """
        clean_curp = curp.strip().upper()
        if len(clean_curp) == 18:
            return f"{clean_curp[:4]}******{clean_curp[-4:]}"
        return "****"

    @staticmethod
    def mask_email(email: str) -> str:
        """
        Enmascara una dirección de correo para auditorías de privacidad:
        Ejemplo: usuario@dominio.com -> u***o@dominio.com
        """
        clean_email = email.strip()
        if "@" not in clean_email:
            return "****"
        name, domain = clean_email.split("@", 1)
        if len(name) <= 2:
            masked_name = name[0] + "*"
        else:
            masked_name = f"{name[0]}***{name[-1]}"
        return f"{masked_name}@{domain}"


# Instancia singleton para inyección de dependencias en endpoints y servicios
security_engine = DataSecurityEngine()
