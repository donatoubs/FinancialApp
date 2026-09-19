"""
Modelo ORM de Categorías de Ingresos y Gastos (categories).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    name = Column(String(100), nullable=False)                        # Ej: "Alimentación", "Transporte", "Sueldo"
    icon = Column(String(50), default="bi-tag", nullable=False)       # Icono de Bootstrap Icons
    color = Column(String(20), default="#2563eb", nullable=False)     # Color hexadecimal
    category_type = Column(String(20), default="expense", nullable=False)  # "expense", "income", "both"
    is_default = Column(Boolean, default=False, nullable=False)       # True para predeterminadas del sistema

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relación con usuario (None si es global/predeterminada)
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', type='{self.category_type}', is_default={self.is_default})>"
