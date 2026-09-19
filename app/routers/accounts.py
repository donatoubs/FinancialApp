"""
Router para la gestión de Cuentas Bancarias y Efectivo (CRUD completo y resumen de saldos).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.account import AccountType
from app.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountBalanceAdjustment,
    AccountResponse,
    AccountSummary
)
from app.auth.dependencies import get_current_active_user
from app.services import account_service

router = APIRouter(prefix="/accounts", tags=["Cuentas Bancarias"])


@router.get(
    "",
    response_model=List[AccountResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar cuentas bancarias del usuario",
    description="Retorna todas las cuentas registradas del usuario autenticado con filtros opcionales."
)
def list_accounts(
    only_active: bool = Query(False, description="Filtrar solo cuentas en estado activo"),
    account_type: Optional[AccountType] = Query(None, description="Filtrar por tipo de cuenta"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return account_service.get_accounts_by_user(
        db=db,
        user_id=current_user.id,
        only_active=only_active,
        account_type=account_type
    )


@router.get(
    "/summary",
    response_model=AccountSummary,
    status_code=status.HTTP_200_OK,
    summary="Obtener resumen financiero de cuentas",
    description="Retorna el conteo total de cuentas y los saldos acumulados por cada tipo de moneda."
)
def get_accounts_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return account_service.get_accounts_summary(db=db, user_id=current_user.id)


@router.post(
    "",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva cuenta bancaria o de efectivo",
    description="Crea una cuenta asociada al usuario autenticado. El saldo actual se inicializa con el saldo inicial si no se especifica."
)
def create_account(
    account_in: AccountCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return account_service.create_account(
        db=db,
        user_id=current_user.id,
        account_in=account_in
    )


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener detalle de una cuenta bancaria",
    description="Retorna la información completa de una cuenta bancaria específica por su ID."
)
def get_account_detail(
    account_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = account_service.get_account_by_id(db=db, account_id=account_id, user_id=current_user.id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cuenta bancaria solicitada no existe o no tienes permisos para acceder a ella."
        )
    return account


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar cuenta bancaria",
    description="Permite modificar los datos, nombre, banco, número oculto, color o estado de la cuenta."
)
def update_account(
    account_id: int,
    account_in: AccountUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = account_service.get_account_by_id(db=db, account_id=account_id, user_id=current_user.id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cuenta bancaria solicitada no existe o no tienes permisos para modificarla."
        )
    return account_service.update_account(db=db, account=account, account_in=account_in)


@router.post(
    "/{account_id}/adjust-balance",
    response_model=AccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Ajustar saldo de la cuenta manualmente",
    description="Ajusta el saldo sumando o restando el monto indicado (útil para conciliaciones manuales)."
)
def adjust_account_balance(
    account_id: int,
    adjustment: AccountBalanceAdjustment,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = account_service.get_account_by_id(db=db, account_id=account_id, user_id=current_user.id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cuenta bancaria no existe."
        )
    return account_service.update_account_balance(db=db, account=account, delta_amount=adjustment.delta_amount)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_200_OK,
    summary="Eliminar o archivar cuenta bancaria",
    description="Elimina la cuenta de forma permanente o la marca como inactiva (soft delete) si se indica el parámetro."
)
def delete_account(
    account_id: int,
    soft_delete: bool = Query(False, description="Si es True, sólo se desactiva en vez de borrarla permanentemente"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = account_service.get_account_by_id(db=db, account_id=account_id, user_id=current_user.id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La cuenta bancaria solicitada no existe."
        )
    account_service.delete_account(db=db, account=account, soft_delete=soft_delete)
    
    action = "desactivada" if soft_delete else "eliminada"
    return {"message": f"Cuenta bancaria {action} exitosamente.", "account_id": account_id}
