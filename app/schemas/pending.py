"""
Esquemas Pydantic de la Bandeja de Pendientes y las reglas aprendidas por comercio.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


class PendingResponse(BaseModel):
    id: int
    status: str
    source: str
    raw_text: Optional[str] = None
    amount: Optional[Decimal] = None
    merchant: str
    transaction_type: str
    card_hint: Optional[str] = None

    suggested_category_id: Optional[int] = None
    suggested_category_name: Optional[str] = None
    suggested_account_id: Optional[int] = None
    suggested_account_name: Optional[str] = None
    suggested_card_id: Optional[int] = None
    suggested_card_name: Optional[str] = None
    suggestion_reason: Optional[str] = None
    suggested_rule_key: str = ""

    transaction_id: Optional[int] = None
    occurred_at: datetime
    occurred_date: date

    model_config = ConfigDict(from_attributes=True)


class PendingCount(BaseModel):
    pending: int


class PendingConfirm(BaseModel):
    """Datos finales con los que el usuario confirma un pendiente."""
    transaction_type: Literal["expense", "income"] = "expense"
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    category_id: int
    source_account_id: Optional[int] = Field(None, description="Cuenta (débito, transferencia o efectivo)")
    card_id: Optional[int] = Field(None, description="Tarjeta usada (crédito o débito)")
    description: str = Field(..., min_length=1, max_length=255)
    notes: Optional[str] = None
    transaction_date: Optional[date] = None

    remember: bool = Field(True, description="Recordar categoría y medio de pago para este comercio")
    remember_key: Optional[str] = Field(None, max_length=120, description="Texto del comercio a recordar (ej. 'Supermaxi')")


class PendingSettings(BaseModel):
    auto_confirm_known: bool = Field(..., description="Registrar solos los pagos de comercios ya aprendidos")


class MerchantRuleResponse(BaseModel):
    id: int
    merchant_key: str
    display_name: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    source_account_id: Optional[int] = None
    account_name: Optional[str] = None
    card_id: Optional[int] = None
    card_name: Optional[str] = None
    times_confirmed: int
