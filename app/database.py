"""
Configuración de la conexión a la base de datos con SQLAlchemy.
Incluye el motor (engine), generador de sesiones (SessionLocal), clase Base ORM y helper de verificación.
"""

from typing import Generator
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Normalización de la URL de conexión para compatibilidad con Supabase y Render
db_url = settings.DATABASE_URL
# Siempre psycopg2 (el driver instalado): SQLAlchemy 2.1+ usa psycopg 3 por defecto con "postgresql://"
for prefix in ("postgres://", "postgresql://"):
    if db_url.startswith(prefix):
        db_url = "postgresql+psycopg2://" + db_url[len(prefix):]
        break

# En producción la conexión con PostgreSQL va cifrada (TLS) aunque la URL no lo pida
connect_args = {}
if db_url.startswith("postgresql") and settings.is_production and "sslmode=" not in db_url:
    connect_args["sslmode"] = "require"

# Pool pequeño: el pooler gratuito de Supabase admite pocas conexiones simultáneas
engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    connect_args=connect_args,
    echo=False,
)

# Generador de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Clase base para todos los modelos ORM
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Generador de dependencias de FastAPI para inyectar la sesión de base de datos.
    Garantiza el cierre adecuado de la conexión al finalizar la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> dict:
    """
    Verifica la conectividad con la base de datos ejecutando una consulta simple.
    Retorna un diccionario con el estado y detalles informativos.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "message": "Conexión a PostgreSQL establecida correctamente.",
            "error": None
        }
    except Exception as exc:
        logger.warning(f"Error verificando conexión a base de datos: {exc}")
        return {
            "status": "disconnected",
            "message": "No se pudo conectar a la base de datos.",
            "error": str(exc)
        }
