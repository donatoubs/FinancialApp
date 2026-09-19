"""
Esquemas Pydantic para el Dashboard Principal y Estadísticas Financieras Consolidadas.
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.transaction import TransactionResponse
from app.schemas.card import CardResponse


class CategoryChartData(BaseModel):
    labels: List[str]
    values: List[float]
    colors: List[str]


class MonthlyComparisonData(BaseModel):
    months: List[str]
    incomes: List[float]
    expenses: List[float]


class AccountDistributionData(BaseModel):
    labels: List[str]
    values: List[float]
    colors: List[str]


class CardDebtChartData(BaseModel):
    labels: List[str]
    debts: List[float]
    limits: List[float]
    colors: List[str]


class DashboardCharts(BaseModel):
    expenses_by_category: CategoryChartData
    monthly_incomes_vs_expenses: MonthlyComparisonData
    accounts_distribution: AccountDistributionData
    cards_debt_distribution: CardDebtChartData


class DashboardResponse(BaseModel):
    # Patrimonio y Activos
    net_worth: Decimal = Field(..., description="Patrimonio neto: Dinero disponible en cuentas - Deuda de tarjetas")
    available_money: Decimal = Field(..., description="Total de dinero disponible en cuentas bancarias y efectivo")
    total_bank_accounts: Decimal = Field(..., description="Total en cuentas bancarias corrientes/ahorros/inversión")
    total_cash: Decimal = Field(..., description="Total en efectivo / caja")

    # Pasivos / Deuda de Tarjetas
    total_credit_debt: Decimal = Field(..., description="Deuda total acumulada en tarjetas de crédito")
    total_credit_limit: Decimal = Field(..., description="Límite total de crédito aprobado")
    total_credit_available: Decimal = Field(..., description="Crédito disponible total")
    overall_card_utilization_rate: float = Field(..., description="Porcentaje global de utilización de crédito")

    # Métricas del Mes Actual
    current_month_name: str
    monthly_income: Decimal = Field(..., description="Ingresos totales en el mes en curso")
    monthly_expense: Decimal = Field(..., description="Gastos totales en el mes en curso")
    monthly_balance: Decimal = Field(..., description="Balance del mes: Ingresos - Gastos")
    monthly_savings_rate: float = Field(..., description="Tasa de ahorro mensual (%)")

    # Alertas y Listados
    upcoming_card_payments: List[CardResponse]
    recent_transactions: List[TransactionResponse]

    # Datos para gráficos de Chart.js
    charts: DashboardCharts

    model_config = ConfigDict(from_attributes=True)
