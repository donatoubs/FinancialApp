"""
Registro y detección de actividad sospechosa.

Cada evento guarda quién, qué, desde qué IP y navegador. Algunas reglas marcan eventos como
sospechosos (severity "warning" o "critical") para que aparezcan en el panel de administración:

- Contraseña incorrecta repetida o cuenta bloqueada por intentos.
- Inicio de sesión desde una IP que la cuenta no había usado antes.
- Token del atajo del iPhone inválido (alguien probando tokens).
- Acceso al panel de administración sin permiso.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.security_event import SecurityEvent
from app.security.rate_limiter import client_ip

logger = logging.getLogger("security")

# Etiquetas legibles (se muestran en el panel y en el historial del usuario)
EVENT_LABELS = {
    "login_success": "Inicio de sesión",
    "login_new_ip": "Inicio de sesión desde una IP nueva",
    "login_failed": "Contraseña incorrecta",
    "login_locked": "Cuenta bloqueada por intentos fallidos",
    "login_inactive": "Intento de entrar a una cuenta desactivada",
    "register": "Cuenta creada",
    "logout": "Cierre de sesión",
    "logout_all": "Cierre de sesión en todos los dispositivos",
    "password_changed": "Contraseña cambiada",
    "password_reset_requested": "Pidió recuperar la contraseña",
    "password_reset_done": "Contraseña restablecida con enlace",
    "password_reset_invalid": "Enlace de recuperación inválido o vencido",
    "account_deleted": "Cuenta eliminada",
    "data_exported": "Descargó sus datos",
    "webhook_bad_token": "Token del atajo inválido",
    "webhook_token_regenerated": "Token del atajo regenerado",
    "admin_forbidden": "Intento de entrar al panel de administración sin permiso",
    "admin_user_deactivated": "Administrador desactivó una cuenta",
    "admin_user_activated": "Administrador reactivó una cuenta",
    "admin_user_logout": "Administrador cerró las sesiones de una cuenta",
    "rate_limited": "Demasiadas peticiones",
}

SEVERITY = {
    "login_failed": "warning",
    "login_new_ip": "warning",
    "login_inactive": "warning",
    "password_reset_invalid": "warning",
    "webhook_bad_token": "warning",
    "rate_limited": "warning",
    "login_locked": "critical",
    "admin_forbidden": "critical",
}

# Eventos que el propio usuario ve en "Perfil ➝ Seguridad ➝ Historial de accesos"
USER_VISIBLE = {
    "login_success", "login_new_ip", "login_failed", "login_locked", "logout_all",
    "password_changed", "password_reset_done", "data_exported", "webhook_token_regenerated",
    "admin_user_deactivated", "admin_user_activated", "admin_user_logout",
}


def record(
    db: Session,
    request: Optional[Request],
    event_type: str,
    user=None,
    email: Optional[str] = None,
    detail: Optional[str] = None,
    commit: bool = True,
) -> SecurityEvent:
    """Guarda un evento. Nunca debe romper la petición que lo origina."""
    severity = SEVERITY.get(event_type, "info")
    event = SecurityEvent(
        user_id=getattr(user, "id", None),
        email=(email or getattr(user, "email", None) or None),
        event_type=event_type,
        severity=severity,
        ip=client_ip(request)[:64] if request else None,
        user_agent=(request.headers.get("user-agent", "")[:255] or None) if request else None,
        detail=(detail or "")[:255] or None,
    )
    try:
        db.add(event)
        if commit:
            db.commit()
    except Exception as exc:   # el registro es secundario: si falla, la acción principal sigue
        db.rollback()
        logger.error("No se pudo guardar el evento de seguridad %s: %s", event_type, exc)
    if severity != "info":
        logger.warning("[seguridad] %s email=%s ip=%s %s", event_type, event.email, event.ip, detail or "")
    return event


def is_new_ip(db: Session, user_id: int, ip: str) -> bool:
    """True si la cuenta ya tenía inicios de sesión y ninguno desde esta IP."""
    base = db.query(SecurityEvent.id).filter(
        SecurityEvent.user_id == user_id,
        SecurityEvent.event_type.in_(("login_success", "login_new_ip")),
    )
    if base.first() is None:
        return False   # primer inicio de sesión: no hay con qué comparar
    return base.filter(SecurityEvent.ip == ip).first() is None


def for_user(db: Session, user_id: int, limit: int = 30) -> List[SecurityEvent]:
    return (
        db.query(SecurityEvent)
        .filter(SecurityEvent.user_id == user_id, SecurityEvent.event_type.in_(USER_VISIBLE))
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def purge_old(db: Session) -> int:
    """Borra eventos más antiguos que la retención configurada."""
    days = get_settings().SECURITY_EVENTS_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = db.query(SecurityEvent).filter(SecurityEvent.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return deleted


def serialize(event: SecurityEvent) -> dict:
    return {
        "id": event.id,
        "user_id": event.user_id,
        "email": event.email,
        "event_type": event.event_type,
        "label": EVENT_LABELS.get(event.event_type, event.event_type),
        "severity": event.severity,
        "ip": event.ip,
        "user_agent": event.user_agent,
        "detail": event.detail,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
