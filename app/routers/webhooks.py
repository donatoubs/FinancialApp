"""
Router de Webhooks para Atajos de iOS (Apple Pay, DeUna y banca móvil).

El token personal viaja SOLO en la cabecera `X-Webhook-Token`: nunca en la URL,
porque las URLs quedan guardadas en los registros (logs) del servidor y de proxies.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.auth.dependencies import get_current_active_user
from app.schemas.webhook import IOSWebhookPayload, WebhookResponse, WebhookTokenResponse
from app.security.rate_limiter import client_ip, webhook_bad_token_limiter, webhook_rate_limiter
from app.services import security_events, webhook_service

router = APIRouter(prefix="/webhooks", tags=["Webhooks & Atajos iOS"])

TOKEN_HEADER = "X-Webhook-Token"


def _webhook_url(request: Request) -> str:
    return f"{str(request.base_url).rstrip('/')}/api/v1/webhooks/ios"


@router.post(
    "/ios",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recibir un pago desde Atajos de iOS",
    description="Requiere la cabecera X-Webhook-Token con el token personal del usuario."
)
def handle_ios_webhook(
    payload: IOSWebhookPayload,
    request: Request,
    x_webhook_token: Optional[str] = Header(None, alias=TOKEN_HEADER),
    db: Session = Depends(get_db)
):
    webhook_rate_limiter.check(request)

    if not x_webhook_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Falta la cabecera {TOKEN_HEADER}. Agrégala en la acción 'Obtener contenido de URL' del atajo."
        )

    # Una IP que prueba tokens inválidos queda bloqueada un rato (impide adivinarlos)
    webhook_bad_token_limiter.ensure_allowed(client_ip(request))
    user = webhook_service.get_user_by_webhook_token(db=db, token=x_webhook_token.strip())
    if not user:
        security_events.record(db, request, "webhook_bad_token")
        webhook_bad_token_limiter.hit(client_ip(request))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido. Copia el token actual desde Pendientes ➝ Conecta tu iPhone."
        )

    return webhook_service.process_ios_webhook(db=db, user=user, payload=payload)


@router.get(
    "/my-token",
    response_model=WebhookTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener la dirección y el token del webhook",
)
def get_my_webhook_token(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    token = webhook_service.get_or_create_webhook_token(db=db, user=current_user)
    return WebhookTokenResponse(webhook_token=token, webhook_url=_webhook_url(request))


@router.post(
    "/regenerate-token",
    response_model=WebhookTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerar el token del webhook",
    description="Invalida el token anterior; los atajos deben actualizarse con el nuevo."
)
def regenerate_my_webhook_token(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    new_token = webhook_service.regenerate_webhook_token(db=db, user=current_user)
    security_events.record(db, request, "webhook_token_regenerated", user=current_user)
    return WebhookTokenResponse(webhook_token=new_token, webhook_url=_webhook_url(request))
