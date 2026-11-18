"""
Esquemas Pydantic para el Webhook de Atajos de iOS (Apple Wallet, DeUna, banca móvil).
"""

from typing import Optional, Union
from pydantic import BaseModel, Field


class IOSWebhookPayload(BaseModel):
    """
    Datos recibidos desde el Atajo de iOS (Shortcuts).
    Soporta datos estructurados de Apple Pay o texto sin procesar (DeUna, SMS, correos del banco).
    """
    # Campos estructurados (Apple Pay). El monto puede llegar como número o texto ("$3,75").
    amount: Optional[Union[float, str]] = Field(None, description="Monto de la transacción", examples=[14.50])
    merchant: Optional[str] = Field(None, max_length=255, description="Establecimiento o comercio", examples=["Supermaxi"])
    card: Optional[str] = Field(None, max_length=100, description="Nombre de la tarjeta en Apple Wallet", examples=["Visa Banco Guayaquil"])
    category: Optional[str] = Field(None, max_length=100, description="Categoría elegida en el atajo (opcional)", examples=["Alimentación"])
    transaction_type: Optional[str] = Field(None, description="EXPENSE o INCOME", examples=["EXPENSE"])
    notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales opcionales")

    # Texto completo de notificaciones (DeUna, SMS, correo del banco)
    raw_text: Optional[str] = Field(None, max_length=2000, description="Texto completo de la notificación",
                                    examples=["DeUna: Pagaste a Cafetería Don Juan, por $4.50 el 17/11"])
    source: Optional[str] = Field(None, max_length=30, description="Origen: apple_pay, deuna, bank, sms", examples=["deuna"])

    # Control
    external_id: Optional[str] = Field(None, max_length=100, description="Identificador único del pago para evitar duplicados")
    auto_register: bool = Field(False, description="Registrar directamente si hay datos suficientes (por ejemplo, si elegiste la categoría en el atajo)")


class WebhookResponse(BaseModel):
    """Respuesta enviada de vuelta al iPhone tras procesar el movimiento."""
    success: bool
    status: str = Field(..., description="registered | pending | duplicate")
    message: str
    pending_id: Optional[int] = None
    transaction_id: Optional[int] = None
    amount: Optional[float] = None
    merchant: Optional[str] = None
    category: Optional[str] = None
    account_or_card: Optional[str] = None
    transaction_type: Optional[str] = None


class WebhookTokenResponse(BaseModel):
    """Token y URL configurada para el atajo de iOS."""
    webhook_token: str
    webhook_url: str
