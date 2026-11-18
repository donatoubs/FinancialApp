"""
Envío de correos por SMTP (por ejemplo, Gmail con contraseña de aplicación).
Si SMTP no está configurado, `email_enabled()` es False y no se envía nada.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import get_settings

logger = logging.getLogger(__name__)


def email_enabled() -> bool:
    s = get_settings()
    return bool(s.SMTP_HOST and s.SMTP_FROM)


def send_email(to: str, subject: str, text: str) -> bool:
    """Envía un correo de texto. Devuelve False si no está configurado o si falla."""
    s = get_settings()
    if not email_enabled():
        return False
    msg = EmailMessage()
    msg["From"] = s.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    try:
        with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15) as server:
            if s.SMTP_STARTTLS:
                server.starttls(context=ssl.create_default_context())
            if s.SMTP_USER:
                server.login(s.SMTP_USER, s.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001 - no se debe filtrar el motivo al cliente
        logger.error("No se pudo enviar el correo a %s: %s", to, exc)
        return False
