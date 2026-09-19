"""
Esquemas Pydantic para tokens de autenticación JWT.
"""

from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="Token de acceso JWT")
    token_type: str = Field(default="bearer", description="Tipo de token")


class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None
