"""
Esquemas Pydantic para Cuentas Bancarias (bank_accounts): creación, actualización, respuestas y resúmenes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict
from app.models.account import AccountType


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre descriptivo de la cuenta", examples=["Cuenta de Ahorros Principal"])
    bank_name: str = Field(..., min_length=1, max_length=100, description="Nombre de la entidad bancaria o 'Efectivo'", examples=["BBVA"])
    account_type: AccountType = Field(default=AccountType.CHECKING, description="Tipo de cuenta")
    account_number_mask: Optional[str] = Field(None, max_length=30, description="Número de cuenta parcialmente oculto", examples=["****1234"])
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Código de moneda ISO", examples=["USD"])
    color: str = Field(default="#2563eb", max_length=20, description="Color hexadecimal para identificación visual", examples=["#2563eb"])
    is_active: bool = Field(default=True, description="Estado activo o inactivo de la cuenta")


class AccountCreate(AccountBase):
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Saldo inicial con el que abre la cuenta", examples=[Decimal("1000.00")])
    current_balance: Optional[Decimal] = Field(None, description="Saldo actual (si se omite, se iguala al saldo inicial)", examples=[Decimal("1000.00")])


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[AccountType] = None
    account_number_mask: Optional[str] = None
    current_balance: Optional[Decimal] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    color: Optional[str] = None
    is_active: Optional[bool] = None


class AccountBalanceAdjustment(BaseModel):
    delta_amount: Decimal = Field(..., description="Monto a sumar (positivo) o restar (negativo) al saldo")
    reason: Optional[str] = Field(None, description="Motivo del ajuste de saldo")


class AccountResponse(AccountBase):
    id: int
    user_id: int
    initial_balance: Decimal
    current_balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountSummary(BaseModel):
    total_accounts: int
    total_active_accounts: int
    balances_by_currency: Dict[str, Decimal]
    accounts: List[AccountResponse]
