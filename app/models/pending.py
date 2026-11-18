"""
Modelos ORM de la Bandeja de Pendientes:
- PendingTransaction: movimientos recibidos desde el iPhone (Apple Pay, DeUna, banca) que esperan confirmación.
- MerchantRule: preferencias aprendidas por comercio (categoría y medio de pago) al confirmar pendientes.

Los campos de tipo/método/estado se guardan como texto para evitar tipos ENUM nuevos en PostgreSQL.
"""

from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Numeric, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class PendingStatus(str, enum.Enum):
    PENDING = "pending"         # Esperando que el usuario lo confirme o descarte
    CONFIRMED = "confirmed"     # Convertido en movimiento real (manual o automáticamente)
    DISCARDED = "discarded"     # Descartado por el usuario


def _utcnow():
    return datetime.now(timezone.utc)


class PendingTransaction(Base):
    __tablename__ = "pending_transactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), default=PendingStatus.PENDING.value, nullable=False, index=True)

    # Datos recibidos
    source = Column(String(30), default="apple_pay", nullable=False)   # apple_pay, deuna, bank, sms, manual
    raw_text = Column(Text, nullable=True)                              # Texto original de la notificación
    amount = Column(Numeric(14, 2), nullable=True)                      # Puede faltar si no se pudo leer
    merchant = Column(String(255), nullable=False)
    transaction_type = Column(String(20), default="expense", nullable=False)  # expense | income
    card_hint = Column(String(100), nullable=True)                      # Nombre de tarjeta enviado por Wallet

    # Sugerencias calculadas (reglas aprendidas o heurísticas)
    suggested_category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    suggested_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True)
    suggested_card_id = Column(Integer, ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    suggestion_reason = Column(String(30), nullable=True)               # rule | keywords | single_option | deuna

    # Control de duplicados y resultado
    dedup_key = Column(String(64), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)

    occurred_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    suggested_category = relationship("Category")
    suggested_account = relationship("BankAccount")
    suggested_card = relationship("Card")

    __table_args__ = (
        Index("ix_pending_user_status", "user_id", "status"),
    )

    def __repr__(self):
        return f"<PendingTransaction(id={self.id}, status={self.status}, amount={self.amount}, merchant='{self.merchant}')>"


class MerchantRule(Base):
    __tablename__ = "merchant_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Comercio normalizado (minúsculas, sin tildes). Aplica a comercios iguales o que empiecen así.
    merchant_key = Column(String(120), nullable=False)
    display_name = Column(String(120), nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    source_account_id = Column(Integer, ForeignKey("bank_accounts.id", ondelete="CASCADE"), nullable=True)
    card_id = Column(Integer, ForeignKey("cards.id", ondelete="CASCADE"), nullable=True)

    times_confirmed = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    category = relationship("Category")
    source_account = relationship("BankAccount")
    card = relationship("Card")

    __table_args__ = (
        UniqueConstraint("user_id", "merchant_key", name="uq_merchant_rule_user_key"),
    )

    def __repr__(self):
        return f"<MerchantRule(user={self.user_id}, key='{self.merchant_key}', category={self.category_id})>"
