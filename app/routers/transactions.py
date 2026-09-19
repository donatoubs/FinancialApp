"""
Router para la gestión de Movimientos Financieros (Ingresos, Gastos, Transferencias y Pagos de Tarjetas).
"""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.transaction import TransactionType
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionsSummary
)
from app.auth.dependencies import get_current_active_user
from app.services import transaction_service

router = APIRouter(prefix="/transactions", tags=["Movimientos Financieros"])


@router.get(
    "",
    response_model=List[TransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar movimientos del usuario",
    description="Retorna el historial de movimientos financieros con filtros por fecha, tipo, categoría, cuenta o tarjeta."
)
def list_transactions(
    start_date: Optional[date] = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Fecha final (YYYY-MM-DD)"),
    transaction_type: Optional[TransactionType] = Query(None, description="Tipo de movimiento"),
    category_id: Optional[int] = Query(None, description="ID de la categoría"),
    account_id: Optional[int] = Query(None, description="ID de la cuenta bancaria"),
    card_id: Optional[int] = Query(None, description="ID de la tarjeta"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    txs = transaction_service.get_transactions_by_user(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        transaction_type=transaction_type,
        category_id=category_id,
        account_id=account_id,
        card_id=card_id,
        limit=limit,
        offset=offset
    )
    return [transaction_service.enrich_transaction_response(t) for t in txs]


@router.get(
    "/summary",
    response_model=TransactionsSummary,
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen financiero de movimientos",
    description="Calcula ingresos totales, gastos totales, balance neto y distribución por categorías en un rango de fechas."
)
def get_transactions_summary(
    start_date: Optional[date] = Query(None, description="Fecha inicial"),
    end_date: Optional[date] = Query(None, description="Fecha final"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return transaction_service.get_transactions_summary(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo movimiento financiero",
    description="Crea un ingreso, gasto, transferencia o pago de tarjeta y actualiza automáticamente los saldos de forma atómica."
)
def create_transaction(
    tx_in: TransactionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tx = transaction_service.create_transaction(
        db=db,
        user_id=current_user.id,
        tx_in=tx_in
    )
    return transaction_service.enrich_transaction_response(tx)


@router.get(
    "/{tx_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de un movimiento",
    description="Retorna la información completa de una transacción por ID."
)
def get_transaction_detail(
    tx_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tx = transaction_service.get_transaction_by_id(db=db, tx_id=tx_id, user_id=current_user.id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El movimiento financiero no existe o no tienes permisos para acceder a él."
        )
    return transaction_service.enrich_transaction_response(tx)


@router.put(
    "/{tx_id}",
    response_model=TransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar un movimiento financiero",
    description="Actualiza la transacción, recalculando y sincronizando los saldos de cuentas y tarjetas afectadas."
)
def update_transaction(
    tx_id: int,
    tx_in: TransactionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tx = transaction_service.get_transaction_by_id(db=db, tx_id=tx_id, user_id=current_user.id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El movimiento financiero no existe."
        )
    updated = transaction_service.update_transaction(
        db=db,
        tx=tx,
        tx_in=tx_in,
        user_id=current_user.id
    )
    return transaction_service.enrich_transaction_response(updated)


@router.delete(
    "/{tx_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar un movimiento financiero",
    description="Elimina la transacción y revierte automáticamente su impacto en los saldos de cuentas y tarjetas."
)
def delete_transaction(
    tx_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    tx = transaction_service.get_transaction_by_id(db=db, tx_id=tx_id, user_id=current_user.id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El movimiento financiero no existe."
        )
    transaction_service.delete_transaction(db=db, tx=tx, user_id=current_user.id)
    return {"message": "Movimiento financiero eliminado y saldos revertidos con éxito.", "transaction_id": tx_id}
