"""
Esquemas Pydantic para Movimientos Financieros (transactions): Ingresos, Gastos, Transferencias y Pagos de Tarjetas.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.transaction import TransactionType, PaymentMethod


class TransactionBase(BaseModel):
    transaction_type: TransactionType = Field(..., description="Tipo de movimiento ('income', 'expense', 'transfer', 'card_payment')", examples=[TransactionType.EXPENSE])
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Monto del movimiento (debe ser mayor a 0)", examples=[Decimal("45.50")])
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Moneda del movimiento", examples=["USD"])
    
    category_id: Optional[int] = Field(None, description="ID de la categoría (Alimentación, Transporte, etc.)")
    source_account_id: Optional[int] = Field(None, description="Cuenta bancaria o de efectivo de origen")
    destination_account_id: Optional[int] = Field(None, description="Cuenta de destino (obligatoria en transferencias)")
    card_id: Optional[int] = Field(None, description="Tarjeta asociada (para compras con crédito o pagos de tarjeta)")
    
    payment_method: PaymentMethod = Field(default=PaymentMethod.CASH, description="Método de pago")
    description: str = Field(..., min_length=1, max_length=255, description="Descripción del movimiento", examples=["Supermercado Supermaxi"])
    notes: Optional[str] = Field(None, description="Notas o detalles adicionales")
    transaction_date: date = Field(default_factory=date.today, description="Fecha de realización del movimiento")


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    transaction_type: Optional[TransactionType] = None
    amount: Optional[Decimal] = Field(None, gt=Decimal("0.00"))
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    category_id: Optional[int] = None
    source_account_id: Optional[int] = None
    destination_account_id: Optional[int] = None
    card_id: Optional[int] = None
    payment_method: Optional[PaymentMethod] = None
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    notes: Optional[str] = None
    transaction_date: Optional[date] = None


class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    source_account_name: Optional[str] = None
    destination_account_name: Optional[str] = None
    card_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionsSummary(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    total_transactions: int
    expenses_by_category: Dict[str, Decimal]
    incomes_by_category: Dict[str, Decimal]
    transactions: List[TransactionResponse]
