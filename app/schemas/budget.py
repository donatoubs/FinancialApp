"""
Esquemas Pydantic para Presupuestos Mensuales por Categoría y Alertas Financieras.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class BudgetBase(BaseModel):
    category_id: int = Field(..., description="ID de la categoría de gasto a presupuestar")
    month: int = Field(..., ge=1, le=12, description="Mes del presupuesto (1-12)", examples=[8])
    year: int = Field(..., ge=2000, le=2100, description="Año del presupuesto", examples=[2026])
    limit_amount: Decimal = Field(..., gt=Decimal("0.00"), description="Límite máximo de gasto mensual", examples=[Decimal("350.00")])
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Moneda", examples=["USD"])
    alert_threshold: int = Field(default=80, ge=1, le=100, description="Porcentaje de consumo para emitir advertencia", examples=[80])


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    limit_amount: Optional[Decimal] = Field(None, gt=Decimal("0.00"))
    alert_threshold: Optional[int] = Field(None, ge=1, le=100)


class BudgetResponse(BudgetBase):
    id: int
    user_id: int
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    
    # Métricas calculadas en tiempo real
    spent_amount: Decimal = Field(default=Decimal("0.00"), description="Monto gastado en el mes")
    remaining_amount: Decimal = Field(default=Decimal("0.00"), description="Monto disponible restante")
    spent_percentage: float = Field(default=0.0, description="Porcentaje de consumo del presupuesto")
    status: str = Field(default="healthy", description="'healthy' (<80%), 'warning' (>=80%), 'exceeded' (>=100%)")
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetSummary(BaseModel):
    month: int
    year: int
    month_name: str
    total_budgeted: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    overall_percentage: float
    count_healthy: int
    count_warning: int
    count_exceeded: int
    budgets: List[BudgetResponse]


class FinancialAlert(BaseModel):
    id: str
    alert_type: str = Field(..., description="'budget_warning', 'budget_exceeded', 'card_near_due', 'card_high_utilization'")
    title: str
    message: str
    severity: str = Field(..., description="'info', 'warning', 'danger'")
    target_url: str


class AlertsResponse(BaseModel):
    total_alerts: int
    alerts: List[FinancialAlert]
