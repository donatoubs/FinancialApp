"""Router de Analíticas: comparación de meses, categorías, comercios y hábitos de gasto."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.services import analytics_service
from app.utils.dates import today_local

router = APIRouter(prefix="/analytics", tags=["Analíticas"])


@router.get("", summary="Analíticas del mes elegido")
def get_analytics(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    months: int = Query(12, ge=3, le=24, description="Meses de historial"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    today = today_local()
    return analytics_service.get_analytics(db, current_user.id, year or today.year, month or today.month, months)
