"""
Módulo de enrutadores de la API REST.
"""

from app.routers import health, auth, accounts, cards, categories, transactions, dashboard, budgets

__all__ = [
    "health",
    "auth",
    "accounts",
    "cards",
    "categories",
    "transactions",
    "dashboard",
    "budgets"
]
