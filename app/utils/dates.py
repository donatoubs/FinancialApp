"""
Utilidades de fecha con zona horaria local del usuario (por defecto Ecuador continental).
Evita que el servidor (UTC en Render) registre movimientos nocturnos con la fecha del día siguiente.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def local_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().TIMEZONE)


def now_local() -> datetime:
    """Fecha y hora actual en la zona horaria configurada."""
    return datetime.now(local_tz())


def today_local() -> date:
    """Fecha actual en la zona horaria configurada."""
    return now_local().date()
