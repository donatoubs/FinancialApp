"""
Router para la gestión de Presupuestos Mensuales, Alertas Financieras y Exportación de Reportes.
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.transaction import TransactionType
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSummary,
    AlertsResponse
)
from app.auth.dependencies import get_current_active_user
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["Presupuestos y Reportes"])


@router.get(
    "",
    response_model=List[BudgetResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar presupuestos mensuales",
    description="Retorna los presupuestos configurados por categoría para el mes y año solicitados con métricas de consumo en tiempo real."
)
def list_budgets(
    month: Optional[int] = Query(None, ge=1, le=12, description="Mes (1-12)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Año (ej. 2026)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return budget_service.get_budgets_by_user(db=db, user_id=current_user.id, month=month, year=year)


@router.get(
    "/summary",
    response_model=BudgetSummary,
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen financiero de presupuestos",
    description="Calcula el total presupuestado, total consumido, saldo disponible y contadores de categorías saludables, en advertencia y sobregiradas."
)
def get_budget_summary(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return budget_service.get_budget_summary(db=db, user_id=current_user.id, month=month, year=year)


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar o actualizar presupuesto mensual por categoría",
    description="Crea o actualiza el límite de gasto para una categoría en un mes y año determinados."
)
def create_or_update_budget(
    budget_in: BudgetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return budget_service.create_or_update_budget(db=db, user_id=current_user.id, budget_in=budget_in)


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar presupuesto",
    description="Elimina la configuración de presupuesto para una categoría y mes."
)
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    success = budget_service.delete_budget(db=db, budget_id=budget_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El presupuesto no existe o no tienes permisos para eliminarlo."
        )
    return {"message": "Presupuesto eliminado exitosamente.", "budget_id": budget_id}


@router.get(
    "/alerts",
    response_model=AlertsResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener alertas financieras en tiempo real",
    description="Retorna avisos activos de presupuestos excedidos, advertencias de consumo y recordatorios de pago de tarjetas de crédito."
)
def get_financial_alerts(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return budget_service.generate_financial_alerts(db=db, user_id=current_user.id)


@router.get(
    "/export/csv",
    summary="Exportar reporte de movimientos en formato CSV",
    description="Genera y descarga un archivo CSV con el historial de transacciones para Excel o contabilidad."
)
def export_transactions_csv(
    start_date: Optional[date] = Query(None, description="Fecha inicial"),
    end_date: Optional[date] = Query(None, description="Fecha final"),
    transaction_type: Optional[TransactionType] = Query(None, description="Tipo de movimiento"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    csv_content = budget_service.generate_transactions_csv_report(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type
    )

    filename = f"reporte_financiero_{date.today().isoformat()}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
