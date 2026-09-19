"""
Esquemas Pydantic para Usuarios: creación, autenticación, actualización y serialización.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.schemas.token import Token


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico del usuario", examples=["usuario@ejemplo.com"])
    full_name: str = Field(..., min_length=2, max_length=100, description="Nombre completo", examples=["Juan Pérez"])
    currency_preference: str = Field(default="USD", min_length=3, max_length=3, description="Código de moneda ISO (USD, EUR, etc.)", examples=["USD"])


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña segura (mínimo 8 caracteres)", examples=["ClaveSegura123!"])


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico registrado", examples=["usuario@ejemplo.com"])
    password: str = Field(..., description="Contraseña del usuario", examples=["ClaveSegura123!"])


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Nuevo nombre completo")
    currency_preference: Optional[str] = Field(None, min_length=3, max_length=3, description="Nueva moneda preferida")
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="Nueva contraseña (opcional)")


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAuthResponse(BaseModel):
    user: UserResponse
    token: Token
    message: str = "Autenticación exitosa"
