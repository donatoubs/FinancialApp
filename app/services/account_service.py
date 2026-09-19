"""
Servicio de negocio para la gestión de Cuentas Bancarias y Efectivo.
"""

from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.account import BankAccount, AccountType
from app.schemas.account import AccountCreate, AccountUpdate


def get_accounts_by_user(
    db: Session,
    user_id: int,
    only_active: bool = False,
    account_type: Optional[AccountType] = None
) -> List[BankAccount]:
    """
    Retorna la lista de cuentas bancarias pertenecientes a un usuario.
    Permite filtrar por cuentas activas y por tipo de cuenta.
    """
    query = db.query(BankAccount).filter(BankAccount.user_id == user_id)
    if only_active:
        query = query.filter(BankAccount.is_active.is_(True))
    if account_type:
        query = query.filter(BankAccount.account_type == account_type)
    return query.order_by(BankAccount.id.asc()).all()


def get_account_by_id(db: Session, account_id: int, user_id: int) -> Optional[BankAccount]:
    """
    Busca una cuenta bancaria asegurando que pertenezca al usuario indicado.
    """
    return db.query(BankAccount).filter(
        BankAccount.id == account_id,
        BankAccount.user_id == user_id
    ).first()


def create_account(db: Session, user_id: int, account_in: AccountCreate) -> BankAccount:
    """
    Crea una nueva cuenta bancaria para el usuario.
    Si current_balance no se indica, se inicializa con el initial_balance.
    """
    initial_bal = Decimal(str(account_in.initial_balance))
    current_bal = Decimal(str(account_in.current_balance)) if account_in.current_balance is not None else initial_bal

    db_account = BankAccount(
        user_id=user_id,
        name=account_in.name.strip(),
        bank_name=account_in.bank_name.strip(),
        account_type=account_in.account_type,
        account_number_mask=account_in.account_number_mask.strip() if account_in.account_number_mask else None,
        initial_balance=initial_bal,
        current_balance=current_bal,
        currency=account_in.currency.upper(),
        color=account_in.color,
        is_active=account_in.is_active
    )
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account


def update_account(db: Session, account: BankAccount, account_in: AccountUpdate) -> BankAccount:
    """
    Actualiza los campos permitidos de una cuenta bancaria.
    """
    if account_in.name is not None:
        account.name = account_in.name.strip()
    if account_in.bank_name is not None:
        account.bank_name = account_in.bank_name.strip()
    if account_in.account_type is not None:
        account.account_type = account_in.account_type
    if account_in.account_number_mask is not None:
        account.account_number_mask = account_in.account_number_mask.strip() if account_in.account_number_mask else None
    if account_in.current_balance is not None:
        account.current_balance = Decimal(str(account_in.current_balance))
    if account_in.currency is not None:
        account.currency = account_in.currency.upper()
    if account_in.color is not None:
        account.color = account_in.color
    if account_in.is_active is not None:
        account.is_active = account_in.is_active

    db.commit()
    db.refresh(account)
    return account


def update_account_balance(db: Session, account: BankAccount, delta_amount: Decimal) -> BankAccount:
    """
    Incrementa o decrementa el saldo actual de una cuenta (usado en transacciones).
    """
    account.current_balance = Decimal(str(account.current_balance)) + Decimal(str(delta_amount))
    db.commit()
    db.refresh(account)
    return account


def delete_account(db: Session, account: BankAccount, soft_delete: bool = False) -> None:
    """
    Elimina físicamente la cuenta o la marca como inactiva (soft delete).
    """
    if soft_delete:
        account.is_active = False
        db.commit()
    else:
        db.delete(account)
        db.commit()


def get_accounts_summary(db: Session, user_id: int) -> dict:
    """
    Calcula el resumen de cuentas del usuario con totales agrupados por moneda.
    """
    accounts = get_accounts_by_user(db, user_id=user_id)
    total_accounts = len(accounts)
    active_accounts = [acc for acc in accounts if acc.is_active]

    balances_by_currency: Dict[str, Decimal] = {}
    for acc in active_accounts:
        curr = acc.currency.upper()
        bal = Decimal(str(acc.current_balance))
        balances_by_currency[curr] = balances_by_currency.get(curr, Decimal("0.00")) + bal

    return {
        "total_accounts": total_accounts,
        "total_active_accounts": len(active_accounts),
        "balances_by_currency": balances_by_currency,
        "accounts": accounts
    }
