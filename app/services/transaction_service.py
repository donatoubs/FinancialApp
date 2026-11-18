"""
Servicio de negocio para Movimientos Financieros:
Creación, actualización, reversión atómica y actualización automática de saldos de cuentas y tarjetas.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException, status

from app.models.transaction import Transaction, TransactionType, PaymentMethod
from app.models.account import BankAccount
from app.models.card import Card, CardType
from app.models.category import Category
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.utils.dates import today_local


def _validate_ownership(
    db: Session,
    user_id: int,
    category_id: Optional[int] = None,
    source_account_id: Optional[int] = None,
    destination_account_id: Optional[int] = None,
    card_id: Optional[int] = None,
) -> None:
    """
    Verifica que la categoría, cuentas y tarjeta referenciadas pertenezcan al usuario
    (las categorías globales del sistema, con user_id NULL, también son válidas).
    """
    if category_id is not None:
        exists = db.query(Category.id).filter(
            Category.id == category_id,
            (Category.user_id == user_id) | (Category.user_id.is_(None))
        ).first()
        if not exists:
            raise HTTPException(status_code=400, detail="La categoría indicada no existe o no te pertenece.")

    for acc_id, label in ((source_account_id, "origen"), (destination_account_id, "destino")):
        if acc_id is not None:
            exists = db.query(BankAccount.id).filter(
                BankAccount.id == acc_id, BankAccount.user_id == user_id
            ).first()
            if not exists:
                raise HTTPException(status_code=400, detail=f"La cuenta de {label} no existe o no te pertenece.")

    if card_id is not None:
        exists = db.query(Card.id).filter(Card.id == card_id, Card.user_id == user_id).first()
        if not exists:
            raise HTTPException(status_code=400, detail="La tarjeta indicada no existe o no te pertenece.")


def _validate_structure(tx_type: TransactionType, source_account_id, destination_account_id, card_id) -> None:
    """Reglas de consistencia según el tipo de movimiento."""
    if tx_type == TransactionType.TRANSFER:
        if not source_account_id or not destination_account_id:
            raise HTTPException(status_code=400, detail="Una transferencia requiere cuenta de origen y cuenta de destino.")
        if source_account_id == destination_account_id:
            raise HTTPException(status_code=400, detail="La cuenta de origen y destino deben ser distintas.")

    if tx_type == TransactionType.CARD_PAYMENT:
        if not card_id or not source_account_id:
            raise HTTPException(status_code=400, detail="El pago de tarjeta requiere especificar la cuenta pagadora y la tarjeta.")


def enrich_transaction_response(tx: Transaction) -> TransactionResponse:
    """Convierte una entidad Transaction en TransactionResponse con nombres de relaciones."""
    return TransactionResponse(
        id=tx.id,
        user_id=tx.user_id,
        transaction_type=tx.transaction_type,
        amount=Decimal(str(tx.amount)),
        currency=tx.currency,
        category_id=tx.category_id,
        source_account_id=tx.source_account_id,
        destination_account_id=tx.destination_account_id,
        card_id=tx.card_id,
        payment_method=tx.payment_method,
        description=tx.description,
        notes=tx.notes,
        transaction_date=tx.transaction_date,
        category_name=tx.category.name if tx.category else None,
        category_icon=tx.category.icon if tx.category else None,
        category_color=tx.category.color if tx.category else None,
        source_account_name=tx.source_account.name if tx.source_account else None,
        destination_account_name=tx.destination_account.name if tx.destination_account else None,
        card_name=tx.card.name if tx.card else None,
        created_at=tx.created_at,
        updated_at=tx.updated_at
    )


def _apply_balance_effect(db: Session, tx: Transaction, user_id: int, multiplier: int = 1) -> None:
    """
    Aplica (+1) o revierte (-1) el impacto financiero de una transacción en las cuentas y tarjetas.
    """
    amount = Decimal(str(tx.amount)) * multiplier

    # 1. INGRESO: Suma al saldo de la cuenta de origen
    if tx.transaction_type == TransactionType.INCOME:
        if tx.source_account_id:
            account = db.query(BankAccount).filter(BankAccount.id == tx.source_account_id, BankAccount.user_id == user_id).first()
            if account:
                account.current_balance = Decimal(str(account.current_balance)) + amount

    # 2. GASTO:
    # - Si se pagó con tarjeta de crédito: suma a la deuda de la tarjeta
    # - Si se pagó con cuenta / débito / efectivo: resta del saldo de la cuenta
    elif tx.transaction_type == TransactionType.EXPENSE:
        if tx.card_id and tx.payment_method == PaymentMethod.CREDIT_CARD:
            card = db.query(Card).filter(Card.id == tx.card_id, Card.user_id == user_id).first()
            if card:
                card.current_balance = Decimal(str(card.current_balance)) + amount
        elif tx.source_account_id:
            account = db.query(BankAccount).filter(BankAccount.id == tx.source_account_id, BankAccount.user_id == user_id).first()
            if account:
                account.current_balance = Decimal(str(account.current_balance)) - amount

    # 3. TRANSFERENCIA: Resta de cuenta origen y suma a cuenta destino
    elif tx.transaction_type == TransactionType.TRANSFER:
        if tx.source_account_id:
            src = db.query(BankAccount).filter(BankAccount.id == tx.source_account_id, BankAccount.user_id == user_id).first()
            if src:
                src.current_balance = Decimal(str(src.current_balance)) - amount
        if tx.destination_account_id:
            dest = db.query(BankAccount).filter(BankAccount.id == tx.destination_account_id, BankAccount.user_id == user_id).first()
            if dest:
                dest.current_balance = Decimal(str(dest.current_balance)) + amount

    # 4. PAGO DE TARJETA: Resta de cuenta bancaria y reduce la deuda de la tarjeta
    elif tx.transaction_type == TransactionType.CARD_PAYMENT:
        if tx.source_account_id:
            src = db.query(BankAccount).filter(BankAccount.id == tx.source_account_id, BankAccount.user_id == user_id).first()
            if src:
                src.current_balance = Decimal(str(src.current_balance)) - amount
        if tx.card_id:
            card = db.query(Card).filter(Card.id == tx.card_id, Card.user_id == user_id).first()
            if card:
                card.current_balance = Decimal(str(card.current_balance)) - amount


def create_transaction(db: Session, user_id: int, tx_in: TransactionCreate) -> Transaction:
    """
    Registra un movimiento y actualiza atómicamente los saldos de cuentas y tarjetas correspondientes.
    """
    # Validaciones según tipo y propiedad de las entidades referenciadas
    _validate_structure(tx_in.transaction_type, tx_in.source_account_id, tx_in.destination_account_id, tx_in.card_id)
    _validate_ownership(
        db, user_id,
        category_id=tx_in.category_id,
        source_account_id=tx_in.source_account_id,
        destination_account_id=tx_in.destination_account_id,
        card_id=tx_in.card_id,
    )

    db_tx = Transaction(
        user_id=user_id,
        transaction_type=tx_in.transaction_type,
        amount=Decimal(str(tx_in.amount)),
        currency=tx_in.currency.upper(),
        category_id=tx_in.category_id,
        source_account_id=tx_in.source_account_id,
        destination_account_id=tx_in.destination_account_id,
        card_id=tx_in.card_id,
        payment_method=tx_in.payment_method,
        description=tx_in.description.strip(),
        notes=tx_in.notes.strip() if tx_in.notes else None,
        transaction_date=tx_in.transaction_date or today_local()
    )
    db.add(db_tx)
    
    # Aplicar impacto financiero
    _apply_balance_effect(db, db_tx, user_id, multiplier=1)

    db.commit()
    db.refresh(db_tx)
    return db_tx


def get_transactions_by_user(
    db: Session,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    transaction_type: Optional[TransactionType] = None,
    category_id: Optional[int] = None,
    account_id: Optional[int] = None,
    card_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Transaction]:
    """
    Retorna la lista filtrada de transacciones del usuario ordenada cronológicamente descendente.
    """
    query = db.query(Transaction).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)
    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if account_id:
        query = query.filter(
            (Transaction.source_account_id == account_id) | (Transaction.destination_account_id == account_id)
        )
    if card_id:
        query = query.filter(Transaction.card_id == card_id)

    return query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).offset(offset).limit(limit).all()


def get_transaction_by_id(db: Session, tx_id: int, user_id: int) -> Optional[Transaction]:
    """Busca una transacción asegurando propiedad del usuario."""
    return db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()


def update_transaction(
    db: Session,
    tx: Transaction,
    tx_in: TransactionUpdate,
    user_id: int
) -> Transaction:
    """
    Actualiza una transacción: revierte el impacto anterior y aplica el nuevo impacto en saldos.
    """
    # Solo los campos enviados explícitamente (permite limpiar campos enviando null)
    changes = tx_in.model_dump(exclude_unset=True)

    # Campos obligatorios en BD: no se pueden poner en null
    for required in ("transaction_type", "amount", "currency", "payment_method", "description", "transaction_date"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=400, detail=f"El campo '{required}' no puede quedar vacío.")

    # Estado resultante para validar antes de tocar saldos
    def final(field):
        return changes[field] if field in changes else getattr(tx, field)

    _validate_structure(final("transaction_type"), final("source_account_id"), final("destination_account_id"), final("card_id"))
    _validate_ownership(
        db, user_id,
        category_id=changes.get("category_id"),
        source_account_id=changes.get("source_account_id"),
        destination_account_id=changes.get("destination_account_id"),
        card_id=changes.get("card_id"),
    )

    # 1. Revertir saldo anterior
    _apply_balance_effect(db, tx, user_id, multiplier=-1)

    # 2. Actualizar campos
    for field, value in changes.items():
        if field == "amount":
            value = Decimal(str(value))
        elif field == "currency":
            value = value.upper()
        elif field == "description":
            value = value.strip()
        elif field == "notes":
            value = value.strip() if value else None
        setattr(tx, field, value)

    # 3. Aplicar nuevo saldo
    _apply_balance_effect(db, tx, user_id, multiplier=1)

    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, tx: Transaction, user_id: int) -> None:
    """
    Elimina una transacción y revierte su impacto en cuentas o tarjetas.
    """
    # Revertir saldo
    _apply_balance_effect(db, tx, user_id, multiplier=-1)
    db.delete(tx)
    db.commit()


def get_transactions_summary(
    db: Session,
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> dict:
    """
    Calcula el total de ingresos, gastos, balance neto y desglose por categoría en un rango de fechas.
    """
    txs = get_transactions_by_user(db, user_id, start_date=start_date, end_date=end_date, limit=1000)

    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")
    expenses_by_cat: Dict[str, Decimal] = {}
    incomes_by_cat: Dict[str, Decimal] = {}

    for t in txs:
        amt = Decimal(str(t.amount))
        cat_name = t.category.name if t.category else "Sin Categoría"

        if t.transaction_type == TransactionType.INCOME:
            total_income += amt
            incomes_by_cat[cat_name] = incomes_by_cat.get(cat_name, Decimal("0.00")) + amt
        elif t.transaction_type == TransactionType.EXPENSE:
            total_expense += amt
            expenses_by_cat[cat_name] = expenses_by_cat.get(cat_name, Decimal("0.00")) + amt

    net_balance = total_income - total_expense
    enriched_txs = [enrich_transaction_response(t) for t in txs]

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_balance": net_balance,
        "total_transactions": len(txs),
        "expenses_by_category": expenses_by_cat,
        "incomes_by_category": incomes_by_cat,
        "transactions": enriched_txs
    }
