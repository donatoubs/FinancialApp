"""
Esquemas Pydantic para el Webhook de Atajos de iOS (Apple Wallet & DeUna).
"""

from typing import Optional
from pydantic import BaseModel, Field


class IOSWebhookPayload(BaseModel):
    """
    Datos recibidos desde el Atajo de iOS (Shortcuts).
    Soporta datos estructurados nativos de Apple Pay o texto sin procesar (DeUna / Push).
    """
    # Campos estructurados (Apple Pay)
    amount: Optional[float] = Field(None, description="Monto numérico de la transacción", example=14.50)
    merchant: Optional[str] = Field(None, description="Establecimiento o comercio", example="Supermaxi")
    card: Optional[str] = Field(None, description="Nombre o franquicia de la tarjeta usada en Apple Wallet", example="Visa Banco Guayaquil")
    category: Optional[str] = Field(None, description="Categoría opcional especificada", example="Alimentación")
    transaction_type: Optional[str] = Field(None, description="EXPENSE o INCOME", example="EXPENSE")
    notes: Optional[str] = Field(None, description="Notas adicionales opcionales")
    
    # Campo para notificaciones de texto (DeUna, SMS, Alertas Bancarias)
    raw_text: Optional[str] = Field(None, description="Texto completo de la notificación de DeUna o Banco", example="DeUna: Pagaste $4.50 a Cafetería Don Juan")
    source: Optional[str] = Field(None, description="Origen de la alerta (apple_pay, deuna, sms, etc.)", example="deuna")


class WebhookResponse(BaseModel):
    """Respuesta enviada de vuelta al iPhone tras procesar el movimiento."""
    success: bool
    message: str
    transaction_id: Optional[int] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    account_or_card: Optional[str] = None
    transaction_type: Optional[str] = None


class WebhookTokenResponse(BaseModel):
    """Token y URL configurada para el atajo de iOS."""
    webhook_token: str
    webhook_url: str
