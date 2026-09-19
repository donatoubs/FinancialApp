"""
Esquemas Pydantic para el estado y verificación de salud de la aplicación (Healthcheck).
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class DatabaseStatus(BaseModel):
    status: str = Field(..., description="Estado de conexión ('connected' o 'disconnected')")
    message: str = Field(..., description="Mensaje descriptivo del estado de la base de datos")
    error: Optional[str] = Field(None, description="Detalle del error si existe")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Estado global de la API ('ok' o 'degraded')", examples=["ok"])
    app_name: str = Field(..., examples=["FinancialApp"])
    environment: str = Field(..., examples=["development"])
    version: str = Field(..., examples=["1.0.0"])
    database: DatabaseStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
