"""
Esquemas Pydantic para Usuarios: creación, autenticación, actualización y serialización.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from app.schemas.token import Token


# Contraseñas demasiado comunes (aunque tengan letras y números)
_COMMON_PASSWORDS = {
    "password1", "password123", "contraseña1", "contrasena1", "contrasena123", "12345678a", "qwerty123",
    "abc12345", "abcd1234", "1q2w3e4r", "admin123", "ecuador123", "welcome1", "iloveyou1", "a1234567",
}


def check_password_strength(value: str) -> str:
    """Mínimo 8 caracteres, con al menos una letra y un número, y que no sea una contraseña común."""
    if len(value) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("La contraseña debe tener letras y números.")
    if value.lower() in _COMMON_PASSWORDS or len(set(value)) < 4:
        raise ValueError("Esa contraseña es muy fácil de adivinar. Elige otra.")
    return value


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico del usuario", examples=["usuario@ejemplo.com"])
    full_name: str = Field(..., min_length=2, max_length=100, description="Nombre completo", examples=["Juan Pérez"])
    currency_preference: str = Field(default="USD", min_length=3, max_length=3, description="Código de moneda ISO (USD, EUR, etc.)", examples=["USD"])


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="Contraseña segura (mínimo 8 caracteres)", examples=["ClaveSegura123!"])
    phone: str = Field(..., max_length=30, pattern=r"^[0-9+()\s-]+$", description="Celular (obligatorio)", examples=["0991234567"])

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)

    @field_validator("phone")
    @classmethod
    def phone_has_enough_digits(cls, v: str) -> str:
        digits = sum(ch.isdigit() for ch in v)
        if not 9 <= digits <= 15:
            raise ValueError("El celular debe tener entre 9 y 15 dígitos.")
        return " ".join(v.split())


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico registrado", examples=["usuario@ejemplo.com"])
    password: str = Field(..., max_length=100, description="Contraseña del usuario", examples=["ClaveSegura123!"])
    remember: bool = Field(True, description="Mantener la sesión iniciada (30 días) o solo hasta cerrar el navegador")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Nuevo nombre completo")
    phone: Optional[str] = Field(None, max_length=30, pattern=r"^[0-9+()\s-]*$", description="Teléfono (opcional)")
    currency_preference: Optional[str] = Field(None, min_length=3, max_length=3, description="Nueva moneda preferida")
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="Nueva contraseña (opcional)")
    current_password: Optional[str] = Field(None, max_length=100, description="Contraseña actual (obligatoria para cambiarla)")

    @field_validator("password")
    @classmethod
    def _strong(cls, v: Optional[str]) -> Optional[str]:
        return check_password_strength(v) if v else v


class UserResponse(UserBase):
    id: int
    phone: Optional[str] = None
    last_login_at: Optional[datetime] = None
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

    @field_validator("new_password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator("password")
    @classmethod
    def _strong(cls, v: str) -> str:
        return check_password_strength(v)


class DeleteAccountRequest(BaseModel):
    password: str = Field(..., max_length=100)
