"""
Modelo ORM de Movimientos Financieros (transactions): Ingresos, Gastos, Transferencias y Pagos de Tarjetas.
"""

from datetime import datetime, date, timezone
import enum
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class TransactionType(str, enum.Enum):
    INCOME = "income"               # Ingreso de dinero (ej. Sueldo, Ventas, Dividendos)
    EXPENSE = "expense"             # Gasto (ej. Supermercado, Servicios, Compras)
    TRANSFER = "transfer"           # Transferencia entre dos cuentas bancarias/efectivo
    CARD_PAYMENT = "card_payment"   # Pago realizado a la deuda de una tarjeta de crédito


class PaymentMethod(str, enum.Enum):
    CASH = "cash"                   # Efectivo
    BANK_TRANSFER = "bank_transfer" # Transferencia bancaria directa
    DEBIT_CARD = "debit_card"       # Tarjeta de débito
    CREDIT_CARD = "credit_card"     # Tarjeta de crédito
    OTHER = "other"                 # Otro método


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    source_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    destination_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id", ondelete="SET NULL"), nullable=True, index=True)
    
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH, nullable=False)
    description = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    transaction_date = Column(Date, default=date.today, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones ORM
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    source_account = relationship("BankAccount", foreign_keys=[source_account_id])
    destination_account = relationship("BankAccount", foreign_keys=[destination_account_id])
    card = relationship("Card")

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.transaction_type.value}, amount={self.amount} {self.currency}, date={self.transaction_date})>"
