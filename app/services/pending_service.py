"""
Servicio de la Bandeja de Pendientes:
- Sugerencias de categoría y medio de pago (reglas aprendidas + heurísticas).
- Detección de duplicados.
- Confirmación (crea el movimiento real y aprende del comercio) y descarte.
"""

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.account import AccountType, BankAccount
from app.models.card import Card, CardType
from app.models.category import Category
from app.models.pending import MerchantRule, PendingStatus, PendingTransaction
from app.models.transaction import PaymentMethod, Transaction, TransactionType
from app.models.user import User
from app.schemas.pending import MerchantRuleResponse, PendingConfirm, PendingResponse
from app.schemas.transaction import TransactionCreate
from app.services import transaction_service
from app.services.notification_parser import (
    keyword_category_hint,
    merchant_matches_key,
    normalize_merchant,
    strip_accents,
    suggest_rule_key,
)
from app.utils.dates import local_tz

DUPLICATE_WINDOW = timedelta(minutes=3)


# ------------------------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------------------------

def _norm_name(text: str) -> str:
    return strip_accents(text or "").lower().strip()


def build_dedup_key(user_id: int, source: str, amount: Optional[Decimal], merchant: str,
                    raw_text: Optional[str], external_id: Optional[str]) -> Tuple[str, bool]:
    """Devuelve (clave, es_id_externo). Con id externo el duplicado se detecta sin ventana de tiempo."""
    if external_id:
        base = f"{user_id}|ext|{external_id.strip()}"
        return hashlib.sha256(base.encode()).hexdigest(), True
    detail = f"{amount}" if amount is not None else (raw_text or "")
    base = f"{user_id}|{source}|{detail}|{normalize_merchant(merchant)}"
    return hashlib.sha256(base.encode()).hexdigest(), False


def find_duplicate(db: Session, user_id: int, dedup_key: str, is_external: bool) -> Optional[PendingTransaction]:
    query = db.query(PendingTransaction).filter(
        PendingTransaction.user_id == user_id,
        PendingTransaction.dedup_key == dedup_key,
    )
    if not is_external:
        query = query.filter(PendingTransaction.created_at >= datetime.now(timezone.utc) - DUPLICATE_WINDOW)
    return query.order_by(PendingTransaction.id.desc()).first()


def _user_categories(db: Session, user_id: int, tx_type: str) -> List[Category]:
    return db.query(Category).filter(
        (Category.user_id == user_id) | (Category.user_id.is_(None)),
        Category.category_type.in_([tx_type, "both"]),
    ).order_by(Category.id).all()


def find_category_by_name(db: Session, user_id: int, tx_type: str, name: str) -> Optional[Category]:
    """Busca una categoría por nombre aproximado (sin tildes, contenida o que contenga)."""
    target = _norm_name(name)
    if not target:
        return None
    cats = _user_categories(db, user_id, tx_type)
    for cat in cats:
        if _norm_name(cat.name) == target:
            return cat
    for cat in cats:
        cat_name = _norm_name(cat.name)
        if cat_name.startswith(target) or target in cat_name or cat_name in target:
            return cat
    return None


def _fallback_category(db: Session, user_id: int, tx_type: str) -> Optional[Category]:
    cats = _user_categories(db, user_id, tx_type)
    for cat in cats:
        if _norm_name(cat.name).startswith("otros"):
            return cat
    return cats[0] if cats else None


def find_rule(db: Session, user_id: int, merchant: str) -> Optional[MerchantRule]:
    """Regla aprendida más específica (clave más larga) que coincide con el comercio."""
    merchant_norm = normalize_merchant(merchant)
    if not merchant_norm:
        return None
    rules = db.query(MerchantRule).filter(MerchantRule.user_id == user_id).all()
    matches = [r for r in rules if merchant_matches_key(merchant_norm, r.merchant_key)]
    return max(matches, key=lambda r: len(r.merchant_key)) if matches else None


def _match_card_hint(cards: List[Card], hint: str) -> Optional[Card]:
    """Identifica la tarjeta a partir del nombre que envía Apple Wallet."""
    hint_n = _norm_name(hint)
    if not hint_n:
        return None
    # 1. Últimos 4 dígitos
    for c in cards:
        if c.last_four_digits and c.last_four_digits in hint_n:
            return c
    # 2. Nombre de la tarjeta contenido en el texto (o viceversa)
    for c in cards:
        name = _norm_name(c.name)
        if name and (name in hint_n or hint_n in name):
            return c
    # 3. Banco + franquicia
    for c in cards:
        bank = _norm_name(c.bank_name).replace("banco ", "")
        if bank and bank in hint_n and _norm_name(c.card_brand) in hint_n:
            return c
    # 4. Franquicia, solo si es única
    by_brand = [c for c in cards if _norm_name(c.card_brand) and _norm_name(c.card_brand) in hint_n]
    return by_brand[0] if len(by_brand) == 1 else None


# ------------------------------------------------------------------------------
# Sugerencias
# ------------------------------------------------------------------------------

def compute_suggestions(db: Session, user: User, merchant: str, tx_type: str, source: str,
                        card_hint: Optional[str], category_hint: Optional[str]):
    """
    Devuelve (category, account, card, reason, rule).
    Prioridad: regla aprendida > datos del atajo > heurísticas.
    """
    cards = db.query(Card).filter(Card.user_id == user.id, Card.is_active == True).all()  # noqa: E712
    accounts = db.query(BankAccount).filter(BankAccount.user_id == user.id, BankAccount.is_active == True).all()  # noqa: E712

    category: Optional[Category] = None
    account: Optional[BankAccount] = None
    card: Optional[Card] = None
    reason: Optional[str] = None

    rule = find_rule(db, user.id, merchant)
    if rule:
        category = rule.category if rule.category and rule.category.category_type in (tx_type, "both") else None
        account, card, reason = rule.source_account, rule.card, "rule"

    if category_hint:
        category = find_category_by_name(db, user.id, tx_type, category_hint) or category

    # Medio de pago (si la regla no lo definió)
    if not account and not card:
        if card_hint and tx_type == "expense":
            card = _match_card_hint(cards, card_hint)
            reason = reason or ("card_hint" if card else None)
        if not card and source == "deuna":
            account = next((a for a in accounts if "pichincha" in _norm_name(a.bank_name)
                            or "deuna" in _norm_name(a.name) or "pichincha" in _norm_name(a.name)), None)
            reason = reason or ("deuna" if account else None)
        if not card and not account:
            if tx_type == "expense" and source == "apple_pay" and len(cards) == 1:
                card, reason = cards[0], reason or "single_option"
            elif len(accounts) == 1 and (not cards or tx_type == "income" or source != "apple_pay"):
                account, reason = accounts[0], reason or "single_option"

    # Categoría (si no hubo regla ni elección en el atajo)
    if not category:
        prefix = keyword_category_hint(merchant) if tx_type == "expense" else None
        if prefix:
            category = next((c for c in _user_categories(db, user.id, tx_type)
                             if _norm_name(c.name).startswith(prefix)), None)
            reason = reason or ("keywords" if category else None)
        if not category:
            category = _fallback_category(db, user.id, tx_type)

    return category, account, card, reason, rule


def resolve_payment(db: Session, user_id: int, tx_type: str, source: str,
                    account_id: Optional[int], card_id: Optional[int]):
    """
    Traduce (cuenta, tarjeta) a los campos del movimiento: (source_account_id, card_id, payment_method).
    Lanza HTTP 400 si la combinación no es válida.
    """
    card = None
    if card_id is not None:
        card = db.query(Card).filter(Card.id == card_id, Card.user_id == user_id).first()
        if not card:
            raise HTTPException(status_code=400, detail="La tarjeta indicada no existe o no te pertenece.")

    account = None
    if account_id is not None:
        account = db.query(BankAccount).filter(BankAccount.id == account_id, BankAccount.user_id == user_id).first()
        if not account:
            raise HTTPException(status_code=400, detail="La cuenta indicada no existe o no te pertenece.")

    if tx_type == "income":
        if not account:
            raise HTTPException(status_code=400, detail="Elige la cuenta donde recibiste el dinero.")
        method = PaymentMethod.CASH if account.account_type == AccountType.CASH else PaymentMethod.BANK_TRANSFER
        return account.id, None, method

    if card and card.card_type == CardType.CREDIT:
        return None, card.id, PaymentMethod.CREDIT_CARD

    if card:  # Débito: descuenta de su cuenta vinculada (o de la elegida)
        linked = account.id if account else card.bank_account_id
        if not linked:
            raise HTTPException(status_code=400, detail="Esta tarjeta de débito no tiene cuenta vinculada. Elige la cuenta.")
        return linked, card.id, PaymentMethod.DEBIT_CARD

    if account:
        if account.account_type == AccountType.CASH:
            return account.id, None, PaymentMethod.CASH
        method = PaymentMethod.DEBIT_CARD if source == "apple_pay" else PaymentMethod.BANK_TRANSFER
        return account.id, None, method

    raise HTTPException(status_code=400, detail="Elige la cuenta o tarjeta con la que pagaste.")


# ------------------------------------------------------------------------------
# Respuestas
# ------------------------------------------------------------------------------

def _display_rule_key(merchant: str) -> str:
    key = suggest_rule_key(merchant)
    words = merchant.split()
    if words and key and " " not in key:
        return words[0].strip(" .,:;-")
    return merchant


def to_response(p: PendingTransaction) -> PendingResponse:
    occurred = p.occurred_at
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)
    return PendingResponse(
        id=p.id,
        status=p.status,
        source=p.source,
        raw_text=p.raw_text,
        amount=Decimal(str(p.amount)) if p.amount is not None else None,
        merchant=p.merchant,
        transaction_type=p.transaction_type,
        card_hint=p.card_hint,
        suggested_category_id=p.suggested_category_id,
        suggested_category_name=p.suggested_category.name if p.suggested_category else None,
        suggested_account_id=p.suggested_account_id,
        suggested_account_name=p.suggested_account.name if p.suggested_account else None,
        suggested_card_id=p.suggested_card_id,
        suggested_card_name=p.suggested_card.name if p.suggested_card else None,
        suggestion_reason=p.suggestion_reason,
        suggested_rule_key=_display_rule_key(p.merchant),
        transaction_id=p.transaction_id,
        occurred_at=occurred,
        occurred_date=occurred.astimezone(local_tz()).date(),
    )


# ------------------------------------------------------------------------------
# Operaciones
# ------------------------------------------------------------------------------

def list_pending(db: Session, user_id: int, status_filter: str = PendingStatus.PENDING.value,
                 limit: int = 100) -> List[PendingTransaction]:
    return db.query(PendingTransaction).filter(
        PendingTransaction.user_id == user_id,
        PendingTransaction.status == status_filter,
    ).order_by(PendingTransaction.occurred_at.desc(), PendingTransaction.id.desc()).limit(limit).all()


def count_pending(db: Session, user_id: int) -> int:
    return db.query(PendingTransaction).filter(
        PendingTransaction.user_id == user_id,
        PendingTransaction.status == PendingStatus.PENDING.value,
    ).count()


def get_pending(db: Session, user_id: int, pending_id: int) -> PendingTransaction:
    p = db.query(PendingTransaction).filter(
        PendingTransaction.id == pending_id, PendingTransaction.user_id == user_id
    ).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El pendiente no existe.")
    return p


def learn_rule(db: Session, user_id: int, key_text: str, category_id: Optional[int],
               account_id: Optional[int], card_id: Optional[int]) -> Optional[MerchantRule]:
    """Crea o actualiza la regla del comercio (no hace commit)."""
    key = normalize_merchant(key_text)[:120]
    if not key:
        return None
    rule = db.query(MerchantRule).filter(MerchantRule.user_id == user_id, MerchantRule.merchant_key == key).first()
    if rule:
        rule.times_confirmed = (rule.times_confirmed or 0) + 1
    else:
        rule = MerchantRule(user_id=user_id, merchant_key=key, times_confirmed=1)
        db.add(rule)
    rule.display_name = key_text.strip()[:120]
    rule.category_id = category_id
    rule.source_account_id = account_id
    rule.card_id = card_id
    return rule


def register_from_pending(db: Session, user: User, p: PendingTransaction, *, tx_type: str, amount: Decimal,
                          category_id: Optional[int], account_id: Optional[int], card_id: Optional[int],
                          description: str, notes: Optional[str], tx_date,
                          destination_account_id: Optional[int] = None) -> Transaction:
    """Crea el movimiento real a partir de un pendiente y lo marca como confirmado."""
    if p.status != PendingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Este pendiente ya fue confirmado o descartado.")

    if tx_type == "transfer":
        # Dinero propio que pasa de una cuenta a otra (p. ej. recarga del banco a DeUna)
        if not account_id or not destination_account_id:
            raise HTTPException(status_code=400, detail="Elige la cuenta de origen y la de destino.")
        owned = db.query(BankAccount.id).filter(
            BankAccount.user_id == user.id, BankAccount.id.in_([account_id, destination_account_id])
        ).count()
        if owned != len({account_id, destination_account_id}):
            raise HTTPException(status_code=400, detail="La cuenta indicada no existe o no te pertenece.")
        tx_in = TransactionCreate(
            transaction_type=TransactionType.TRANSFER,
            amount=amount,
            currency=user.currency_preference or "USD",
            source_account_id=account_id,
            destination_account_id=destination_account_id,
            payment_method=PaymentMethod.BANK_TRANSFER,
            description=description.strip()[:255],
            notes=notes,
            transaction_date=tx_date,
        )
    else:
        if not category_id:
            raise HTTPException(status_code=400, detail="Elige una categoría.")
        src_account_id, final_card_id, method = resolve_payment(db, user.id, tx_type, p.source, account_id, card_id)
        tx_in = TransactionCreate(
            transaction_type=TransactionType.INCOME if tx_type == "income" else TransactionType.EXPENSE,
            amount=amount,
            currency=user.currency_preference or "USD",
            category_id=category_id,
            source_account_id=src_account_id,
            card_id=final_card_id,
            payment_method=method,
            description=description.strip()[:255],
            notes=notes,
            transaction_date=tx_date,
        )

    # Se marca antes para que quede en el mismo commit que el movimiento
    p.status = PendingStatus.CONFIRMED.value
    p.resolved_at = datetime.now(timezone.utc)
    try:
        tx = transaction_service.create_transaction(db=db, user_id=user.id, tx_in=tx_in)
    except Exception:
        db.rollback()
        raise
    p.transaction_id = tx.id
    db.commit()
    return tx


def confirm_pending(db: Session, user: User, pending_id: int, data: PendingConfirm) -> Transaction:
    p = get_pending(db, user.id, pending_id)
    if data.remember and data.transaction_type != "transfer" and data.category_id:
        learn_rule(db, user.id, data.remember_key or _display_rule_key(p.merchant),
                   data.category_id, data.source_account_id, data.card_id)
    tx_date = data.transaction_date or to_response(p).occurred_date
    return register_from_pending(
        db, user, p,
        tx_type=data.transaction_type,
        amount=data.amount,
        category_id=data.category_id,
        account_id=data.source_account_id,
        card_id=data.card_id,
        description=data.description,
        notes=data.notes,
        tx_date=tx_date,
        destination_account_id=data.destination_account_id,
    )


def discard_pending(db: Session, user_id: int, pending_id: int) -> None:
    p = get_pending(db, user_id, pending_id)
    if p.status != PendingStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Este pendiente ya fue confirmado o descartado.")
    p.status = PendingStatus.DISCARDED.value
    p.resolved_at = datetime.now(timezone.utc)
    db.commit()


def list_rules(db: Session, user_id: int) -> List[MerchantRuleResponse]:
    rules = db.query(MerchantRule).filter(MerchantRule.user_id == user_id).order_by(MerchantRule.display_name).all()
    return [
        MerchantRuleResponse(
            id=r.id,
            merchant_key=r.merchant_key,
            display_name=r.display_name,
            category_id=r.category_id,
            category_name=r.category.name if r.category else None,
            source_account_id=r.source_account_id,
            account_name=r.source_account.name if r.source_account else None,
            card_id=r.card_id,
            card_name=r.card.name if r.card else None,
            times_confirmed=r.times_confirmed,
        )
        for r in rules
    ]


def delete_rule(db: Session, user_id: int, rule_id: int) -> None:
    rule = db.query(MerchantRule).filter(MerchantRule.id == rule_id, MerchantRule.user_id == user_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="La regla no existe.")
    db.delete(rule)
    db.commit()
