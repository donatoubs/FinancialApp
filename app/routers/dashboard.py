"""
Router para el Dashboard Principal y Estadísticas Financieras Consolidadas.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.auth.dependencies import get_current_active_user
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard Financiero"])


@router.get(
    "",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener métricas y gráficos del Dashboard principal",
    description="Retorna patrimonio neto, dinero disponible, deudas, ingresos y gastos del mes actual, próximos pagos y series para Chart.js."
)
def get_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return dashboard_service.get_dashboard_metrics(db=db, user_id=current_user.id)
