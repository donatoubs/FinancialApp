"""
Router de la Bandeja de Pendientes: pagos recibidos desde el iPhone que esperan confirmación,
reglas aprendidas por comercio y configuración del registro automático.
"""

from typing import List, Literal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.pending import (
    MerchantRuleResponse,
    PendingConfirm,
    PendingCount,
    PendingResponse,
    PendingSettings,
)
from app.schemas.transaction import TransactionResponse
from app.services import pending_service, transaction_service

router = APIRouter(prefix="/pending", tags=["Bandeja de Pendientes"])


@router.get("", response_model=List[PendingResponse], summary="Listar pendientes")
def list_pending(
    status_filter: Literal["pending", "confirmed", "discarded"] = Query("pending", alias="status"),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    items = pending_service.list_pending(db, current_user.id, status_filter, limit)
    return [pending_service.to_response(p) for p in items]


@router.get("/count", response_model=PendingCount, summary="Cantidad de pendientes por confirmar")
def count_pending(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return PendingCount(pending=pending_service.count_pending(db, current_user.id))


@router.post("/{pending_id}/confirm", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED,
             summary="Confirmar un pendiente y crear el movimiento")
def confirm_pending(
    pending_id: int,
    data: PendingConfirm,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tx = pending_service.confirm_pending(db, current_user, pending_id, data)
    return transaction_service.enrich_transaction_response(tx)


@router.post("/{pending_id}/discard", summary="Descartar un pendiente")
def discard_pending(
    pending_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    pending_service.discard_pending(db, current_user.id, pending_id)
    return {"message": "Pendiente descartado.", "pending_id": pending_id}


@router.get("/settings", response_model=PendingSettings, summary="Configuración del registro automático")
def get_settings(current_user: User = Depends(get_current_active_user)):
    return PendingSettings(auto_confirm_known=bool(current_user.webhook_auto_confirm))


@router.put("/settings", response_model=PendingSettings, summary="Actualizar configuración del registro automático")
def update_settings(
    data: PendingSettings,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    current_user.webhook_auto_confirm = data.auto_confirm_known
    db.commit()
    return PendingSettings(auto_confirm_known=current_user.webhook_auto_confirm)


@router.get("/rules", response_model=List[MerchantRuleResponse], summary="Comercios aprendidos")
def list_rules(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return pending_service.list_rules(db, current_user.id)


@router.delete("/rules/{rule_id}", summary="Olvidar un comercio aprendido")
def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    pending_service.delete_rule(db, current_user.id, rule_id)
    return {"message": "Regla eliminada.", "rule_id": rule_id}
