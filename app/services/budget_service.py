"""
Servicio de negocio para Presupuestos Mensuales, Alertas Financieras y Exportación de Reportes CSV.
"""

import io
import csv
import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.budget import Budget
from app.models.category import Category
from app.models.card import Card, CardType
from app.models.transaction import Transaction, TransactionType
from app.services import card_service, transaction_service
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSummary,
    FinancialAlert,
    AlertsResponse
)

SPANISH_MONTHS = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def enrich_budget_response(db: Session, budget: Budget, user_id: int) -> BudgetResponse:
    """Calcula en tiempo real el gasto acumulado, saldo disponible y estado del presupuesto."""
    max_day = calendar.monthrange(budget.year, budget.month)[1]
    start_date = date(budget.year, budget.month, 1)
    end_date = date(budget.year, budget.month, max_day)

    # Calcular gasto real en la categoría durante el mes
    spent_total = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.category_id == budget.category_id,
        Transaction.transaction_type == TransactionType.EXPENSE,
        Transaction.transaction_date >= start_date,
        Transaction.transaction_date <= end_date
    ).scalar()

    spent = Decimal(str(spent_total or 0))
    limit = Decimal(str(budget.limit_amount or 0))
    remaining = limit - spent

    spent_percentage = 0.0
    if limit > 0:
        spent_percentage = round(float(spent / limit) * 100.0, 2)

    status = "healthy"
    if spent_percentage >= 100.0:
        status = "exceeded"
    elif spent_percentage >= budget.alert_threshold:
        status = "warning"

    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        month=budget.month,
        year=budget.year,
        limit_amount=limit,
        currency=budget.currency,
        alert_threshold=budget.alert_threshold,
        category_name=budget.category.name if budget.category else "Categoría",
        category_icon=budget.category.icon if budget.category else "bi-tag",
        category_color=budget.category.color if budget.category else "#2563eb",
        spent_amount=spent,
        remaining_amount=remaining,
        spent_percentage=spent_percentage,
        status=status,
        created_at=budget.created_at,
        updated_at=budget.updated_at
    )


def get_budgets_by_user(
    db: Session,
    user_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> List[BudgetResponse]:
    """Retorna los presupuestos del usuario para un mes/año específico."""
    today = date.today()
    m = month or today.month
    y = year or today.year

    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == m,
        Budget.year == y
    ).all()

    return [enrich_budget_response(db, b, user_id) for b in budgets]


def get_budget_summary(
    db: Session,
    user_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None
) -> BudgetSummary:
    """Genera un resumen consolidado de presupuestos del mes con contadores de salud."""
    today = date.today()
    m = month or today.month
    y = year or today.year

    enriched_budgets = get_budgets_by_user(db, user_id, month=m, year=y)

    total_budgeted = sum((b.limit_amount for b in enriched_budgets), Decimal("0.00"))
    total_spent = sum((b.spent_amount for b in enriched_budgets), Decimal("0.00"))
    total_remaining = total_budgeted - total_spent

    overall_percentage = 0.0
    if total_budgeted > 0:
        overall_percentage = round(float(total_spent / total_budgeted) * 100.0, 2)

    count_healthy = sum(1 for b in enriched_budgets if b.status == "healthy")
    count_warning = sum(1 for b in enriched_budgets if b.status == "warning")
    count_exceeded = sum(1 for b in enriched_budgets if b.status == "exceeded")

    return BudgetSummary(
        month=m,
        year=y,
        month_name=f"{SPANISH_MONTHS[m]} {y}",
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        total_remaining=total_remaining,
        overall_percentage=overall_percentage,
        count_healthy=count_healthy,
        count_warning=count_warning,
        count_exceeded=count_exceeded,
        budgets=enriched_budgets
    )


def create_or_update_budget(
    db: Session,
    user_id: int,
    budget_in: BudgetCreate
) -> BudgetResponse:
    """Crea o actualiza un presupuesto asignado a una categoría para un mes determinado."""
    existing = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category_id == budget_in.category_id,
        Budget.month == budget_in.month,
        Budget.year == budget_in.year
    ).first()

    if existing:
        existing.limit_amount = Decimal(str(budget_in.limit_amount))
        existing.alert_threshold = budget_in.alert_threshold
        existing.currency = budget_in.currency.upper()
        db.commit()
        db.refresh(existing)
        return enrich_budget_response(db, existing, user_id)
    else:
        new_budget = Budget(
            user_id=user_id,
            category_id=budget_in.category_id,
            month=budget_in.month,
            year=budget_in.year,
            limit_amount=Decimal(str(budget_in.limit_amount)),
            currency=budget_in.currency.upper(),
            alert_threshold=budget_in.alert_threshold
        )
        db.add(new_budget)
        db.commit()
        db.refresh(new_budget)
        return enrich_budget_response(db, new_budget, user_id)


def delete_budget(db: Session, budget_id: int, user_id: int) -> bool:
    """Elimina un presupuesto configurado."""
    budget = db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
    if not budget:
        return False
    db.delete(budget)
    db.commit()
    return True


def generate_financial_alerts(db: Session, user_id: int) -> AlertsResponse:
    """
    Analiza en tiempo real las finanzas del usuario y genera alertas inteligentes.
    """
    alerts: List[FinancialAlert] = []
    today = date.today()

    # 1. Alertas de Presupuesto del Mes Actual
    budgets = get_budgets_by_user(db, user_id, month=today.month, year=today.year)
    for b in budgets:
        if b.status == "exceeded":
            alerts.append(FinancialAlert(
                id=f"budget_exc_{b.id}",
                alert_type="budget_exceeded",
                title=f"Presupuesto superado en {b.category_name}",
                message=f"Has gastado ${float(b.spent_amount):.2f} de tu límite de ${float(b.limit_amount):.2f} ({b.spent_percentage}% consumido).",
                severity="danger",
                target_url="/budgets"
            ))
        elif b.status == "warning":
            alerts.append(FinancialAlert(
                id=f"budget_warn_{b.id}",
                alert_type="budget_warning",
                title=f"Atención: Presupuesto en {b.category_name}",
                message=f"Has consumido el {b.spent_percentage}% de tu presupuesto (${float(b.spent_amount):.2f} / ${float(b.limit_amount):.2f}).",
                severity="warning",
                target_url="/budgets"
            ))

    # 2. Alertas de Tarjetas de Crédito (Vencimientos y Utilización)
    cards = db.query(Card).filter(
        Card.user_id == user_id,
        Card.card_type == CardType.CREDIT,
        Card.is_active.is_(True)
    ).all()

    for c in cards:
        enriched_c = card_service.enrich_card_response(c)
        bal = Decimal(str(c.current_balance or 0))

        # Alerta de fecha de pago próxima (<= 3 días con deuda)
        if enriched_c.days_until_due is not None and bal > 0:
            if enriched_c.days_until_due == 0:
                alerts.append(FinancialAlert(
                    id=f"card_due_today_{c.id}",
                    alert_type="card_near_due",
                    title=f"¡Pago vence HOY en {c.name}!",
                    message=f"Tienes un saldo pendiente de ${float(bal):.2f} en {c.bank_name} que vence hoy.",
                    severity="danger",
                    target_url="/cards"
                ))
            elif enriched_c.days_until_due <= 3:
                alerts.append(FinancialAlert(
                    id=f"card_due_soon_{c.id}",
                    alert_type="card_near_due",
                    title=f"Pago próximo en {c.name}",
                    message=f"Faltan {enriched_c.days_until_due} días para el vencimiento de tu tarjeta ({c.bank_name}) con deuda de ${float(bal):.2f}.",
                    severity="warning",
                    target_url="/cards"
                ))

        # Alerta de alta utilización de crédito (>= 60%)
        if enriched_c.utilization_percentage >= 60.0:
            alerts.append(FinancialAlert(
                id=f"card_util_{c.id}",
                alert_type="card_high_utilization",
                title=f"Alta utilización de cupo en {c.name}",
                message=f"Estás utilizando el {enriched_c.utilization_percentage}% de tu cupo disponible (${float(bal):.2f} / ${float(c.credit_limit):.2f}).",
                severity="warning",
                target_url="/cards"
            ))

    return AlertsResponse(
        total_alerts=len(alerts),
        alerts=alerts
    )


def generate_transactions_csv_report(
    db: Session,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transaction_type: Optional[TransactionType] = None
) -> str:
    """
    Genera un archivo CSV profesional con el historial de transacciones para exportación.
    """
    txs = transaction_service.get_transactions_by_user(
        db=db,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        limit=5000
    )

    output = io.StringIO()
    # Agregar BOM UTF-8 para compatibilidad perfecta con Microsoft Excel
    output.write('\ufeff')
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)

    # Cabeceras
    writer.writerow([
        "ID",
        "Fecha",
        "Tipo de Movimiento",
        "Monto",
        "Moneda",
        "Descripción",
        "Categoría",
        "Cuenta de Origen / Pago",
        "Cuenta de Destino",
        "Tarjeta",
        "Método de Pago",
        "Notas"
    ])

    type_labels = {
        "income": "Ingreso (+)",
        "expense": "Gasto (-)",
        "transfer": "Transferencia (↔)",
        "card_payment": "Pago Tarjeta (💳)"
    }

    for t in txs:
        cat_name = t.category.name if t.category else "Sin categoría"
        src_name = t.source_account.name if t.source_account else ""
        dest_name = t.destination_account.name if t.destination_account else ""
        card_name = t.card.name if t.card else ""

        writer.writerow([
            t.id,
            t.transaction_date.isoformat(),
            type_labels.get(t.transaction_type.value, t.transaction_type.value),
            f"{float(t.amount):.2f}",
            t.currency,
            t.description,
            cat_name,
            src_name,
            dest_name,
            card_name,
            t.payment_method.value,
            t.notes or ""
        ])

    return output.getvalue()
