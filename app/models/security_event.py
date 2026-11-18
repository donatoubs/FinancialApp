"""
Registro de actividad de seguridad: inicios de sesión, intentos fallidos, cambios de contraseña,
bloqueos, tokens del atajo inválidos y acciones del administrador.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String

from app.database import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Si se borra la cuenta el evento se conserva (con el correo) para poder investigar
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    event_type = Column(String(40), nullable=False, index=True)
    severity = Column(String(10), nullable=False, default="info")   # info | warning | critical
    ip = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    detail = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    __table_args__ = (Index("ix_security_events_severity_created", "severity", "created_at"),)
