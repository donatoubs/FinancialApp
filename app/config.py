"""
Configuración global de la aplicación utilizando Pydantic Settings.
Lee las variables de entorno desde el archivo .env o variables del sistema.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Metadatos de la aplicación
    APP_NAME: str = "FinancialApp"
    APP_ENV: str = "development"
    DEBUG: bool = True
    ENABLE_DOCS: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    VERSION: str = "1.0.0"

    # Base de datos (PostgreSQL con SQLAlchemy)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/financial_db"

    # Seguridad y autenticación JWT
    SECRET_KEY: str = "cambiar_esta_clave_secreta_por_una_segura_en_produccion_123456789"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def cors_origins(self) -> List[str]:
        """Convierte la cadena de orígenes CORS en una lista limpia."""
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

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
