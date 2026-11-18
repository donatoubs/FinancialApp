"""
Formato de cifras para textos generados en el servidor (alertas, mensajes),
igual al que usa la interfaz: $1.234,56 · 84% · 10,5% · signo menos tipográfico.
"""

from decimal import Decimal
from typing import Union

Number = Union[int, float, Decimal]


def fmt_money(value: Number) -> str:
    n = float(value or 0)
    text = f"{abs(n):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{'−' if n < 0 else ''}${text}"


def fmt_percent(value: Number) -> str:
    n = float(value or 0)
    if abs(n - round(n)) < 0.05:
        return f"{round(n):d}%"
    return f"{n:.1f}".replace(".", ",") + "%"
