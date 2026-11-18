"""
Esquemas Pydantic para Usuarios: creación, autenticación, actualización y serialización.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.schemas.token import Token


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico del usuario", examples=["usuario@ejemplo.com"])
    full_name: str = Field(..., min_length=2, max_length=100, description="Nombre completo", examples=["Juan Pérez"])
    currency_preference: str = Field(default="USD", min_length=3, max_length=3, description="Código de moneda ISO (USD, EUR, etc.)", examples=["USD"])


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña segura (mínimo 8 caracteres)", examples=["ClaveSegura123!"])
    phone: str = Field(..., max_length=30, pattern=r"^[0-9+()\s-]+$", description="Celular (obligatorio)", examples=["0991234567"])

    @field_validator("phone")
    @classmethod
    def phone_has_enough_digits(cls, v: str) -> str:
        digits = sum(ch.isdigit() for ch in v)
        if not 9 <= digits <= 15:
            raise ValueError("El celular debe tener entre 9 y 15 dígitos.")
        return " ".join(v.split())


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico registrado", examples=["usuario@ejemplo.com"])
    password: str = Field(..., description="Contraseña del usuario", examples=["ClaveSegura123!"])


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Nuevo nombre completo")
    phone: Optional[str] = Field(None, max_length=30, pattern=r"^[0-9+()\s-]*$", description="Teléfono (opcional)")
    currency_preference: Optional[str] = Field(None, min_length=3, max_length=3, description="Nueva moneda preferida")
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="Nueva contraseña (opcional)")
    current_password: Optional[str] = Field(None, max_length=100, description="Contraseña actual (obligatoria para cambiarla)")


class UserResponse(UserBase):
    id: int
    phone: Optional[str] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAuthResponse(BaseModel):
    user: UserResponse
    token: Token
    message: str = "Autenticación exitosa"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., max_length=100)
    new_password: str = Field(..., min_length=8, max_length=100)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    password: str = Field(..., min_length=8, max_length=100)


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., max_length=100)
