"""
Modelo ORM de Presupuestos Mensuales por Categoría (budgets).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    month = Column(Integer, nullable=False)                          # Mes (1-12)
    year = Column(Integer, nullable=False)                           # Año (ej. 2026)
    limit_amount = Column(Numeric(14, 2), nullable=False)           # Monto límite presupuestado
    currency = Column(String(3), default="USD", nullable=False)     # Moneda
    alert_threshold = Column(Integer, default=80, nullable=False)   # Porcentaje para alerta (ej: 80%)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Restricción única: Un presupuesto por categoría, mes y año para cada usuario
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", "year", name="uq_user_category_month_year"),
    )

    # Relaciones ORM
    user = relationship("User", back_populates="budgets")
    category = relationship("Category")

    def __repr__(self):
        return f"<Budget(id={self.id}, user_id={self.user_id}, category_id={self.category_id}, month={self.month}/{self.year}, limit={self.limit_amount})>"
