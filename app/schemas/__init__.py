"""
Exportación de esquemas Pydantic del sistema.
"""

from app.schemas.health import HealthResponse, DatabaseStatus
from app.schemas.token import Token, TokenData
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    UserAuthResponse
)
from app.schemas.account import (
    AccountBase,
    AccountCreate,
    AccountUpdate,
    AccountBalanceAdjustment,
    AccountResponse,
    AccountSummary
)
from app.schemas.card import (
    CardBase,
    CardCreate,
    CardUpdate,
    CardBalanceAdjustment,
    CardResponse,
    CardsSummary
)
from app.schemas.category import (
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse
)
from app.schemas.transaction import (
    TransactionBase,
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionsSummary
)
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardCharts,
    CategoryChartData,
    MonthlyComparisonData,
    AccountDistributionData,
    CardDebtChartData
)
from app.schemas.budget import (
    BudgetBase,
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSummary,
    FinancialAlert,
    AlertsResponse
)

__all__ = [
    "HealthResponse",
    "DatabaseStatus",
    "Token",
    "TokenData",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserUpdate",
    "UserResponse",
    "UserAuthResponse",
    "AccountBase",
    "AccountCreate",
    "AccountUpdate",
    "AccountBalanceAdjustment",
    "AccountResponse",
    "AccountSummary",
    "CardBase",
    "CardCreate",
    "CardUpdate",
    "CardBalanceAdjustment",
    "CardResponse",
    "CardsSummary",
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryResponse",
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionsSummary",
    "DashboardResponse",
    "DashboardCharts",
    "CategoryChartData",
    "MonthlyComparisonData",
    "AccountDistributionData",
    "CardDebtChartData",
    "BudgetBase",
    "BudgetCreate",
    "BudgetUpdate",
    "BudgetResponse",
    "BudgetSummary",
    "FinancialAlert",
    "AlertsResponse"
]
