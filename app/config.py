"""
Configuración global de la aplicación utilizando Pydantic Settings.
Lee las variables de entorno desde el archivo .env o variables del sistema.
"""

import logging
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Metadatos de la aplicación
    APP_NAME: str = "FinancialApp"
    APP_ENV: str = "development"
    DEBUG: bool = False
    ENABLE_DOCS: bool = False      # Swagger/ReDoc: activar solo en desarrollo
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    VERSION: str = "1.0.0"
    TIMEZONE: str = "America/Guayaquil"

    # Base de datos (PostgreSQL con SQLAlchemy)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/financial_db"

    # Seguridad y autenticación JWT
    SECRET_KEY: str = "cambiar_esta_clave_secreta_por_una_segura_en_produccion_123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Detrás de un proxy (Render, Docker con Nginx): confiar en la última IP de X-Forwarded-For
    TRUST_PROXY: bool = False

    # Correo (recuperar contraseña). Vacío = envío desactivado.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    PUBLIC_BASE_URL: str = ""   # p. ej. https://financialapp.onrender.com (para los enlaces de los correos)

    # CORS: la app y la API comparten dominio, así que por defecto no se permite ningún otro origen.
    # Solo hace falta si otro sitio web va a llamar a esta API.
    ALLOWED_ORIGINS: str = ""

    @property
    def cors_origins(self) -> List[str]:
        """Lista de orígenes permitidos (vacía = solo el mismo dominio). '*' se ignora en producción."""
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]
        if self.is_production and "*" in origins:
            return [o for o in origins if o != "*"]
        return origins

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in ("production", "prod")

    def validate_for_runtime(self) -> None:
        """Detiene el arranque en producción si la configuración es insegura."""
        if not self.is_production:
            return
        weak = (not self.SECRET_KEY or len(self.SECRET_KEY) < 32
                or self.SECRET_KEY.startswith("cambiar_esta_clave")
                or "change_me" in self.SECRET_KEY)
        if weak:
            raise RuntimeError("SECRET_KEY insegura en producción: define una clave aleatoria de 32+ caracteres.")
        if "*" in self.ALLOWED_ORIGINS:
            logging.getLogger(__name__).warning(
                "ALLOWED_ORIGINS='*' se ignora en producción: la app solo acepta su propio dominio."
            )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Retorna una instancia singleton de Settings con caché en memoria."""
    return Settings()
