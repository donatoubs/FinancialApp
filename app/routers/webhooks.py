"""
Router de Webhooks para Integraciones Externas: Apple Wallet y DeUna (Atajos de iOS).
Permite recibir transacciones en segundo plano autenticadas mediante un token de acceso privado.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_active_user
from app.schemas.webhook import IOSWebhookPayload, WebhookResponse, WebhookTokenResponse
from app.services import webhook_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Atajos iOS"])


@router.post(
    "/ios",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recibir transacción desde Atajos de iOS (Apple Wallet o DeUna)",
    description="Endpoint público protegido por token secreto para registrar consumos automáticos en tiempo real."
)
def handle_ios_webhook(
    payload: IOSWebhookPayload,
    request: Request,
    token: Optional[str] = Query(None, description="Token de autenticación personal para el atajo"),
    x_webhook_token: Optional[str] = Header(None, alias="X-Webhook-Token", description="Cabecera alternativa con el token"),
    db: Session = Depends(get_db)
):
    # Aceptar token por Query Param o por Cabecera HTTP
    auth_token = token or x_webhook_token
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el token de autorización. Agrega '?token=tu_token' a la URL."
        )

    user = webhook_service.get_user_by_webhook_token(db=db, token=auth_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de webhook inválido o expirado. Genera uno nuevo en tu perfil de FinancialApp."
        )

    return webhook_service.process_ios_webhook(db=db, user=user, payload=payload)


@router.get(
    "/my-token",
    response_model=WebhookTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener mi Token y URL de Webhook",
    description="Retorna el token y la URL completa configurada para registrar en la app Atajos del iPhone."
)
def get_my_webhook_token(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    token = webhook_service.get_or_create_webhook_token(db=db, user=current_user)
    
    # Construir la URL base dinámica (soporta dominio en producción de Render o local)
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/api/v1/webhooks/ios?token={token}"

    return WebhookTokenResponse(
        webhook_token=token,
        webhook_url=webhook_url
    )


@router.post(
    "/regenerate-token",
    response_model=WebhookTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerar Token de Webhook",
    description="Invalida el token anterior y crea uno nuevo si sospechas que tu token fue comprometido."
)
def regenerate_my_webhook_token(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    new_token = webhook_service.regenerate_webhook_token(db=db, user=current_user)
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/api/v1/webhooks/ios?token={new_token}"

    return WebhookTokenResponse(
        webhook_token=new_token,
        webhook_url=webhook_url
    )
