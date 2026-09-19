"""
Modelo ORM de Tarjetas de Crédito y Débito (cards).
"""

from datetime import datetime, timezone
from decimal import Decimal
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class CardType(str, enum.Enum):
    CREDIT = "credit"   # Tarjeta de crédito
    DEBIT = "debit"     # Tarjeta de débito


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(100), nullable=False)                        # Ej: "Visa Signature", "Diners Club Miles"
    bank_name = Column(String(100), nullable=False)                   # Ej: "Banco Pichincha", "Diners Club Ecuador"
    card_type = Column(Enum(CardType), default=CardType.CREDIT, nullable=False)
    card_brand = Column(String(50), default="Visa", nullable=False)   # Visa, Mastercard, Diners Club, etc.
    last_four_digits = Column(String(4), nullable=False)              # Últimos 4 dígitos (ej: 4567)

    # Parámetros financieros
    credit_limit = Column(Numeric(14, 2), default=0.00, nullable=False)       # Cupo máximo
    current_balance = Column(Numeric(14, 2), default=0.00, nullable=False)    # Deuda o saldo utilizado
    cutoff_day = Column(Integer, nullable=True)                               # Día de corte (1 a 31)
    due_day = Column(Integer, nullable=True)                                  # Día límite de pago (1 a 31)
    interest_rate = Column(Numeric(5, 2), default=0.00, nullable=True)       # Tasa de interés anual (%)
    
    currency = Column(String(3), default="USD", nullable=False)
    color = Column(String(20), default="#003b6f", nullable=False)             # Color representativo de la tarjeta
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relaciones ORM
    user = relationship("User", back_populates="cards")
    bank_account = relationship("BankAccount")

    @property
    def available_credit(self) -> Decimal:
        """Calcula el crédito disponible: Límite - Saldo Utilizado."""
        if self.card_type != CardType.CREDIT:
            return Decimal("0.00")
        limit = Decimal(str(self.credit_limit or 0))
        balance = Decimal(str(self.current_balance or 0))
        return max(Decimal("0.00"), limit - balance)

    @property
    def utilization_percentage(self) -> float:
        """Calcula el porcentaje de utilización del crédito."""
        if self.card_type != CardType.CREDIT or not self.credit_limit or self.credit_limit <= 0:
            return 0.0
        limit = float(self.credit_limit)
        balance = float(self.current_balance)
        return min(100.0, round((balance / limit) * 100.0, 2))

    def __repr__(self):
        return f"<Card(id={self.id}, name='{self.name}', type={self.card_type.value}, bank='{self.bank_name}', last4='{self.last_four_digits}')>"
