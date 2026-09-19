"""
Esquemas Pydantic para Categorías de Ingresos y Gastos.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nombre de la categoría", examples=["Alimentación"])
    icon: str = Field(default="bi-tag", max_length=50, description="Icono de Bootstrap Icons", examples=["bi-cart3"])
    color: str = Field(default="#2563eb", max_length=20, description="Color hexadecimal", examples=["#10b981"])
    category_type: str = Field(default="expense", description="Tipo ('expense', 'income', o 'both')", examples=["expense"])


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = None
    category_type: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: int
    user_id: Optional[int] = None
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
