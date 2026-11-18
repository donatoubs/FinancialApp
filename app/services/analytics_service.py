"""
Analíticas: comparación entre meses, gastos por categoría, comercios donde más se gasta
y hábitos de consumo. Todo se calcula a partir de los movimientos reales del usuario.
"""

import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.services.notification_parser import normalize_merchant
from app.utils.dates import today_local

MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
MONTHS_ES_LONG = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                  "Septiembre", "Octubre", "Noviembre", "Diciembre"]
WEEKDAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _shift_month(year: int, month: int, delta: int) -> Tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def _month_range(year: int, month: int) -> Tuple[date, date]:
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def _sum(txs, tx_type) -> Decimal:
    return sum((Decimal(str(t.amount)) for t in txs if t.transaction_type == tx_type), Decimal("0"))


def _delta(current: Decimal, previous: Decimal):
    """Variación porcentual; None si no hay base para comparar."""
    if previous == 0:
        return None
    return round(float((current - previous) / previous * 100), 1)


def get_analytics(db: Session, user_id: int, year: int, month: int, months: int = 12) -> Dict:
    today = today_local()
    start_hist, _ = _month_range(*_shift_month(year, month, -(months - 1)))
    _, end_month = _month_range(year, month)
    habit_start = max(start_hist, end_month - timedelta(days=89))

    txs: List[Transaction] = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= start_hist,
        Transaction.transaction_date <= end_month,
    ).all()

    by_month = defaultdict(list)
    for t in txs:
        by_month[(t.transaction_date.year, t.transaction_date.month)].append(t)

    # 1. Evolución de ingresos y gastos
    history = []
    for i in range(months - 1, -1, -1):
        y, m = _shift_month(year, month, -i)
        items = by_month.get((y, m), [])
        history.append({
            "label": f"{MONTHS_ES[m - 1]}{'' if y == year else f' {str(y)[2:]}'}",
            "year": y, "month": m,
            "income": float(_sum(items, TransactionType.INCOME)),
            "expense": float(_sum(items, TransactionType.EXPENSE)),
        })

    # 2. Mes elegido frente al anterior
    py, pm = _shift_month(year, month, -1)
    cur, prev = by_month.get((year, month), []), by_month.get((py, pm), [])
    cur_in, cur_out = _sum(cur, TransactionType.INCOME), _sum(cur, TransactionType.EXPENSE)
    prev_in, prev_out = _sum(prev, TransactionType.INCOME), _sum(prev, TransactionType.EXPENSE)

    # 3. Categorías (mes elegido vs anterior)
    cats: Dict[str, Dict] = {}
    for items, key in ((cur, "amount"), (prev, "previous")):
        for t in items:
            if t.transaction_type != TransactionType.EXPENSE:
                continue
            name = t.category.name if t.category else "Sin categoría"
            entry = cats.setdefault(name, {"name": name, "color": t.category.color if t.category else "#7C8A86",
                                           "amount": 0.0, "previous": 0.0})
            entry[key] += float(t.amount)
    categories = sorted((c for c in cats.values() if c["amount"] > 0 or c["previous"] > 0),
                        key=lambda c: c["amount"], reverse=True)

    # 4. Dónde más gastas (comercios del mes elegido)
    merchants: Dict[str, Dict] = {}
    for t in cur:
        if t.transaction_type != TransactionType.EXPENSE:
            continue
        key = normalize_merchant(t.description) or t.description.lower()
        entry = merchants.setdefault(key, {"name": t.description, "amount": 0.0, "count": 0})
        entry["amount"] += float(t.amount)
        entry["count"] += 1
    top_merchants = sorted(merchants.values(), key=lambda m: m["amount"], reverse=True)[:6]

    # 5. Hábitos: gasto por día de la semana (últimos 90 días del periodo)
    weekday_totals = [0.0] * 7
    weekday_counts = [0] * 7
    for t in txs:
        if t.transaction_type == TransactionType.EXPENSE and t.transaction_date >= habit_start:
            weekday_totals[t.transaction_date.weekday()] += float(t.amount)
            weekday_counts[t.transaction_date.weekday()] += 1

    is_current = (year, month) == (today.year, today.month)
    days = today.day if is_current else calendar.monthrange(year, month)[1]
    expenses = [t for t in cur if t.transaction_type == TransactionType.EXPENSE]
    largest = max(expenses, key=lambda t: Decimal(str(t.amount)), default=None)

    return {
        "period": {"year": year, "month": month, "label": f"{MONTHS_ES_LONG[month - 1]} {year}",
                   "previous_label": f"{MONTHS_ES_LONG[pm - 1]} {py}", "is_current": is_current},
        "summary": {
            "income": float(cur_in), "expense": float(cur_out), "net": float(cur_in - cur_out),
            "previous_income": float(prev_in), "previous_expense": float(prev_out),
            "previous_net": float(prev_in - prev_out),
            "income_delta": _delta(cur_in, prev_in), "expense_delta": _delta(cur_out, prev_out),
            "transactions": len(cur),
        },
        "history": history,
        "categories": categories,
        "top_merchants": top_merchants,
        "habits": {
            "since": habit_start.isoformat(),
            "weekdays": [{"label": WEEKDAYS_ES[i], "amount": round(weekday_totals[i], 2), "count": weekday_counts[i]}
                         for i in range(7)],
            "daily_average": round(float(cur_out) / days, 2) if days else 0.0,
            "expense_count": len(expenses),
            "average_ticket": round(float(cur_out) / len(expenses), 2) if expenses else 0.0,
            "largest": {"description": largest.description, "amount": float(largest.amount),
                        "date": largest.transaction_date.isoformat()} if largest else None,
        },
    }
