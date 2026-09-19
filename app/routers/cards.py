"""
Router para la gestión de Tarjetas de Crédito y Débito (CRUD, límites, cortes, pagos y resúmenes).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.card import CardType
from app.schemas.card import (
    CardCreate,
    CardUpdate,
    CardBalanceAdjustment,
    CardResponse,
    CardsSummary
)
from app.auth.dependencies import get_current_active_user
from app.services import card_service

router = APIRouter(prefix="/cards", tags=["Tarjetas de Crédito y Débito"])


@router.get(
    "",
    response_model=List[CardResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar tarjetas del usuario",
    description="Retorna todas las tarjetas del usuario autenticado calculando disponibilidad y días restantes para corte/pago."
)
def list_cards(
    only_active: bool = Query(False, description="Filtrar solo tarjetas activas"),
    card_type: Optional[CardType] = Query(None, description="Filtrar por tipo ('credit' o 'debit')"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    cards = card_service.get_cards_by_user(
        db=db,
        user_id=current_user.id,
        only_active=only_active,
        card_type=card_type
    )
    return [card_service.enrich_card_response(c) for c in cards]


@router.get(
    "/summary",
    response_model=CardsSummary,
    status_code=status.HTTP_200_OK,
    summary="Resumen de límites, deuda y utilización de tarjetas",
    description="Calcula el cupo total, deuda total, disponible y porcentaje general de utilización."
)
def get_cards_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return card_service.get_cards_summary(db=db, user_id=current_user.id)


@router.post(
    "",
    response_model=CardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva tarjeta",
    description="Crea una tarjeta de crédito o débito asociada al usuario autenticado."
)
def create_card(
    card_in: CardCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    card = card_service.create_card(
        db=db,
        user_id=current_user.id,
        card_in=card_in
    )
    return card_service.enrich_card_response(card)


@router.get(
    "/{card_id}",
    response_model=CardResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de una tarjeta",
    description="Retorna el detalle completo y métricas de una tarjeta específica."
)
def get_card_detail(
    card_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    card = card_service.get_card_by_id(db=db, card_id=card_id, user_id=current_user.id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tarjeta solicitada no existe o no tienes permisos para verla."
        )
    return card_service.enrich_card_response(card)


@router.put(
    "/{card_id}",
    response_model=CardResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar datos de una tarjeta",
    description="Modifica nombre, banco, límites, fechas de corte/pago o color de la tarjeta."
)
def update_card(
    card_id: int,
    card_in: CardUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    card = card_service.get_card_by_id(db=db, card_id=card_id, user_id=current_user.id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tarjeta no existe."
        )
    updated = card_service.update_card(db=db, card=card, card_in=card_in)
    return card_service.enrich_card_response(updated)


@router.post(
    "/{card_id}/adjust-balance",
    response_model=CardResponse,
    status_code=status.HTTP_200_OK,
    summary="Ajustar saldo o deuda de la tarjeta",
    description="Permite registrar compras o pagos sumando/restando un delta o fijando el nuevo saldo."
)
def adjust_card_balance(
    card_id: int,
    adjustment: CardBalanceAdjustment,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    card = card_service.get_card_by_id(db=db, card_id=card_id, user_id=current_user.id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tarjeta no existe."
        )
    updated = card_service.adjust_card_balance(
        db=db,
        card=card,
        delta_amount=adjustment.delta_amount,
        new_balance=adjustment.new_balance
    )
    return card_service.enrich_card_response(updated)


@router.delete(
    "/{card_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar o archivar tarjeta",
    description="Elimina la tarjeta permanentemente o la desactiva si se indica el parámetro."
)
def delete_card(
    card_id: int,
    soft_delete: bool = Query(False, description="Desactivar en lugar de eliminar permanentemente"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    card = card_service.get_card_by_id(db=db, card_id=card_id, user_id=current_user.id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La tarjeta no existe."
        )
    card_service.delete_card(db=db, card=card, soft_delete=soft_delete)
    action = "desactivada" if soft_delete else "eliminada"
    return {"message": f"Tarjeta {action} exitosamente.", "card_id": card_id}
