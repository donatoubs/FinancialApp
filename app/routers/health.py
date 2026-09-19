"""
Router para endpoints de verificación de salud y diagnóstico del sistema.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.config import get_settings
from app.database import check_db_connection
from app.schemas.health import HealthResponse, DatabaseStatus

router = APIRouter(prefix="/health", tags=["Salud del Sistema"])
settings = get_settings()


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar salud de la API y conexión a PostgreSQL",
    description="Retorna el estado operativo de la API, versión, entorno y estado de conexión a la base de datos."
)
def get_health_status():
    db_result = check_db_connection()
    overall_status = "ok" if db_result["status"] == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        version=settings.VERSION,
        database=DatabaseStatus(
            status=db_result["status"],
            message=db_result["message"],
            error=db_result["error"]
        ),
        timestamp=datetime.now(timezone.utc)
    )
