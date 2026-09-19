"""
Servicio de negocio para el Dashboard Principal:
Cálculo de patrimonio neto, métricas del mes actual, distribución de activos/pasivos y series para Chart.js.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import calendar
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.account import BankAccount, AccountType
from app.models.card import Card, CardType
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.services import card_service, transaction_service
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardCharts,
    CategoryChartData,
    MonthlyComparisonData,
    AccountDistributionData,
    CardDebtChartData
)

# Nombres de meses en español
SPANISH_MONTHS = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def get_dashboard_metrics(db: Session, user_id: int) -> DashboardResponse:
    """
    Genera todas las métricas consolidadas, alertas financieras y datos para gráficos del dashboard.
    """
    today = date.today()
    current_year = today.year
    current_month = today.month

    # 1. CUENTAS BANCARIAS Y EFECTIVO (ACTIVOS)
    accounts = db.query(BankAccount).filter(
        BankAccount.user_id == user_id,
        BankAccount.is_active.is_(True)
    ).all()

    total_bank = Decimal("0.00")
    total_cash = Decimal("0.00")
    acc_labels: List[str] = []
    acc_values: List[float] = []
    acc_colors: List[str] = []

    for acc in accounts:
        bal = Decimal(str(acc.current_balance or 0))
        if acc.account_type == AccountType.CASH:
            total_cash += bal
        else:
            total_bank += bal

        if bal > 0:
            acc_labels.append(f"{acc.name} ({acc.bank_name})")
            acc_values.append(float(bal))
            acc_colors.append(acc.color or "#2563eb")

    available_money = total_bank + total_cash

    # 2. TARJETAS DE CRÉDITO (PASIVOS / DEUDA)
    cards = db.query(Card).filter(
        Card.user_id == user_id,
        Card.is_active.is_(True)
    ).all()

    credit_cards = [c for c in cards if c.card_type == CardType.CREDIT]
    total_credit_debt = sum((Decimal(str(c.current_balance or 0)) for c in credit_cards), Decimal("0.00"))
    total_credit_limit = sum((Decimal(str(c.credit_limit or 0)) for c in credit_cards), Decimal("0.00"))
    total_credit_available = max(Decimal("0.00"), total_credit_limit - total_credit_debt)

    overall_utilization = 0.0
    if total_credit_limit > 0:
        overall_utilization = min(100.0, round(float(total_credit_debt / total_credit_limit) * 100.0, 2))

    # Tarjetas para gráfico de deudas
    card_labels: List[str] = []
    card_debts: List[float] = []
    card_limits: List[float] = []
    card_colors: List[str] = []

    for c in credit_cards:
        card_labels.append(f"{c.name} ({c.bank_name})")
        card_debts.append(float(c.current_balance or 0))
        card_limits.append(float(c.credit_limit or 0))
        card_colors.append(c.color or "#003b6f")

    # Tarjetas próximas a vencer ordenadas por días restantes
    enriched_cards = [card_service.enrich_card_response(c) for c in credit_cards]
    upcoming_payments = sorted(
        [c for c in enriched_cards if c.days_until_due is not None],
        key=lambda x: x.days_until_due if x.days_until_due is not None else 999
    )

    # 3. PATRIMONIO NETO (Activos - Pasivos)
    net_worth = available_money - total_credit_debt

    # 4. TRANSACCIONES DEL MES ACTUAL
    start_of_month = date(current_year, current_month, 1)
    max_day_month = calendar.monthrange(current_year, current_month)[1]
    end_of_month = date(current_year, current_month, max_day_month)

    monthly_txs = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_of_month,
        Transaction.transaction_date <= end_of_month
    ).all()

    monthly_income = Decimal("0.00")
    monthly_expense = Decimal("0.00")
    cat_expense_dict: Dict[str, Dict[str, Any]] = {}

    for t in monthly_txs:
        amt = Decimal(str(t.amount or 0))
        if t.transaction_type == TransactionType.INCOME:
            monthly_income += amt
        elif t.transaction_type == TransactionType.EXPENSE:
            monthly_expense += amt
            cat_name = t.category.name if t.category else "Otros Gastos"
            cat_color = t.category.color if t.category else "#64748b"

            if cat_name not in cat_expense_dict:
                cat_expense_dict[cat_name] = {"total": Decimal("0.00"), "color": cat_color}
            cat_expense_dict[cat_name]["total"] += amt

    monthly_balance = monthly_income - monthly_expense
    savings_rate = 0.0
    if monthly_income > 0:
        savings_rate = min(100.0, max(-100.0, round(float(monthly_balance / monthly_income) * 100.0, 2)))

    # Datos para gráfico de categorías (Doughnut)
    cat_labels: List[str] = []
    cat_values: List[float] = []
    cat_colors: List[str] = []

    # Si no hay gastos este mes, buscar en general para no dejar el gráfico vacío
    if not cat_expense_dict:
        all_expenses = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE
        ).limit(100).all()
        for t in all_expenses:
            amt = Decimal(str(t.amount or 0))
            cat_name = t.category.name if t.category else "Otros Gastos"
            cat_color = t.category.color if t.category else "#64748b"
            if cat_name not in cat_expense_dict:
                cat_expense_dict[cat_name] = {"total": Decimal("0.00"), "color": cat_color}
            cat_expense_dict[cat_name]["total"] += amt

    for c_name, data in cat_expense_dict.items():
        cat_labels.append(c_name)
        cat_values.append(float(data["total"]))
        cat_colors.append(data["color"])

    # 5. EVOLUCIÓN HISTÓRICA INGRESOS VS GASTOS (Últimos 6 Meses)
    history_months: List[str] = []
    history_incomes: List[float] = []
    history_expenses: List[float] = []

    for i in range(5, -1, -1):
        # Calcular año y mes de hace i meses
        m_offset = current_month - i
        y_offset = current_year
        while m_offset <= 0:
            m_offset += 12
            y_offset -= 1

        m_start = date(y_offset, m_offset, 1)
        m_max_day = calendar.monthrange(y_offset, m_offset)[1]
        m_end = date(y_offset, m_offset, m_max_day)

        m_name = f"{SPANISH_MONTHS[m_offset]} {y_offset}"
        history_months.append(m_name)

        # Totales del mes
        m_inc = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.INCOME,
            Transaction.transaction_date >= m_start,
            Transaction.transaction_date <= m_end
        ).scalar() or 0

        m_exp = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.transaction_date >= m_start,
            Transaction.transaction_date <= m_end
        ).scalar() or 0

        history_incomes.append(float(m_inc))
        history_expenses.append(float(m_exp))

    # 6. ÚLTIMOS MOVIMIENTOS REGISTRADOS
    recent_tx_models = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(8).all()

    recent_txs = [transaction_service.enrich_transaction_response(t) for t in recent_tx_models]

    return DashboardResponse(
        net_worth=net_worth,
        available_money=available_money,
        total_bank_accounts=total_bank,
        total_cash=total_cash,
        total_credit_debt=total_credit_debt,
        total_credit_limit=total_credit_limit,
        total_credit_available=total_credit_available,
        overall_card_utilization_rate=overall_utilization,
        current_month_name=f"{SPANISH_MONTHS[current_month]} {current_year}",
        monthly_income=monthly_income,
        monthly_expense=monthly_expense,
        monthly_balance=monthly_balance,
        monthly_savings_rate=savings_rate,
        upcoming_card_payments=upcoming_payments,
        recent_transactions=recent_txs,
        charts=DashboardCharts(
            expenses_by_category=CategoryChartData(
                labels=cat_labels,
                values=cat_values,
                colors=cat_colors
            ),
            monthly_incomes_vs_expenses=MonthlyComparisonData(
                months=history_months,
                incomes=history_incomes,
                expenses=history_expenses
            ),
            accounts_distribution=AccountDistributionData(
                labels=acc_labels,
                values=acc_values,
                colors=acc_colors
            ),
            cards_debt_distribution=CardDebtChartData(
                labels=card_labels,
                debts=card_debts,
                limits=card_limits,
                colors=card_colors
            )
        )
    )
