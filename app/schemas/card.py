"""
Esquemas Pydantic para Tarjetas de Crédito y Débito (cards): creación, actualización, respuestas y resúmenes.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.card import CardType


class CardBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la tarjeta", examples=["Visa Signature Banco Pichincha"])
    bank_name: str = Field(..., min_length=1, max_length=100, description="Banco o emisor de la tarjeta", examples=["Banco Pichincha"])
    card_type: CardType = Field(default=CardType.CREDIT, description="Tipo de tarjeta ('credit' o 'debit')")
    card_brand: str = Field(default="Visa", max_length=50, description="Franquicia (Visa, Mastercard, Diners Club, etc.)", examples=["Visa"])
    last_four_digits: str = Field(..., min_length=4, max_length=4, pattern=r"^\d{4}$", description="Últimos 4 dígitos numéricos", examples=["4567"])
    
    credit_limit: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Límite o cupo total de crédito", examples=[Decimal("2000.00")])
    cutoff_day: Optional[int] = Field(None, ge=1, le=31, description="Día del mes de corte del estado de cuenta (1 a 31)", examples=[15])
    due_day: Optional[int] = Field(None, ge=1, le=31, description="Día del mes límite para el pago (1 a 31)", examples=[5])
    interest_rate: Optional[Decimal] = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"), description="Tasa de interés anual (%)", examples=[Decimal("16.50")])
    
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Moneda de la tarjeta", examples=["USD"])
    color: str = Field(default="#003b6f", max_length=20, description="Color representativo o corporativo", examples=["#ffdd00"])
    bank_account_id: Optional[int] = Field(None, description="ID de la cuenta bancaria vinculada para débito o pago automático")
    is_active: bool = Field(default=True, description="Estado activo o inactivo de la tarjeta")


class CardCreate(CardBase):
    current_balance: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Saldo utilizado o deuda actual", examples=[Decimal("450.00")])


class CardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=100)
    card_type: Optional[CardType] = None
    card_brand: Optional[str] = Field(None, max_length=50)
    last_four_digits: Optional[str] = Field(None, min_length=4, max_length=4, pattern=r"^\d{4}$")
    credit_limit: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    current_balance: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    cutoff_day: Optional[int] = Field(None, ge=1, le=31)
    due_day: Optional[int] = Field(None, ge=1, le=31)
    interest_rate: Optional[Decimal] = Field(None, ge=Decimal("0.00"), le=Decimal("100.00"))
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    color: Optional[str] = None
    bank_account_id: Optional[int] = None
    is_active: Optional[bool] = None


class CardBalanceAdjustment(BaseModel):
    delta_amount: Optional[Decimal] = Field(None, description="Monto a sumar (+) por compras o restar (-) por pagos")
    new_balance: Optional[Decimal] = Field(None, ge=Decimal("0.00"), description="Nuevo saldo utilizado total")
    reason: Optional[str] = Field(None, description="Motivo del ajuste")


class CardResponse(CardBase):
    id: int
    user_id: int
    current_balance: Decimal
    available_credit: Decimal
    utilization_percentage: float
    days_until_cutoff: Optional[int] = None
    days_until_due: Optional[int] = None
    is_near_due: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CardsSummary(BaseModel):
    total_cards: int
    total_credit_cards: int
    total_debit_cards: int
    total_credit_limit: Decimal
    total_credit_debt: Decimal
    total_credit_available: Decimal
    overall_utilization_rate: float
    cards: List[CardResponse]
