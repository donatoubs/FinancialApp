"""
Modelo ORM de Cuentas Bancarias y Efectivo (bank_accounts).
"""

from datetime import datetime, timezone
import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


class AccountType(str, enum.Enum):
    CHECKING = "checking"        # Cuenta corriente
    SAVINGS = "savings"          # Cuenta de ahorros
    CASH = "cash"                # Efectivo
    INVESTMENT = "investment"    # Inversión
    OTHER = "other"              # Otra


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String(100), nullable=False)                         # Ej: "Nómina Principal", "Ahorros Emergencia"
    bank_name = Column(String(100), nullable=False)                    # Ej: "BBVA", "Chase", "Efectivo"
    account_type = Column(Enum(AccountType), default=AccountType.CHECKING, nullable=False)
    account_number_mask = Column(String(30), nullable=True)            # Ej: "****1234" (Nunca credenciales completas)
    
    initial_balance = Column(Numeric(14, 2), default=0.00, nullable=False)
    current_balance = Column(Numeric(14, 2), default=0.00, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)        # ISO Code: USD, EUR, etc.
    color = Column(String(20), default="#2563eb", nullable=False)      # Color identificador hexadecimal
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relación con el usuario propietario
    user = relationship("User", back_populates="accounts")

    def __repr__(self):
        return f"<BankAccount(id={self.id}, name='{self.name}', bank='{self.bank_name}', balance={self.current_balance} {self.currency})>"
