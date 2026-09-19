"""
Servicio de negocio para la gestión de Tarjetas de Crédito y Débito.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict
import calendar
from sqlalchemy.orm import Session

from app.models.card import Card, CardType
from app.schemas.card import CardCreate, CardUpdate, CardResponse


def calculate_days_until(target_day: Optional[int]) -> Optional[int]:
    """
    Calcula los días restantes desde hoy hasta un día específico del mes (1 a 31).
    Si el día ya pasó este mes, calcula la distancia al día del mes siguiente.
    """
    if not target_day or target_day < 1 or target_day > 31:
        return None

    today = date.today()
    current_year = today.year
    current_month = today.month

    # Ajustar si el mes actual tiene menos días que el día objetivo
    max_days_current_month = calendar.monthrange(current_year, current_month)[1]
    effective_day = min(target_day, max_days_current_month)
    target_date_this_month = date(current_year, current_month, effective_day)

    if target_date_this_month >= today:
        return (target_date_this_month - today).days
    else:
        # Próximo mes
        if current_month == 12:
            next_year = current_year + 1
            next_month = 1
        else:
            next_year = current_year
            next_month = current_month + 1

        max_days_next_month = calendar.monthrange(next_year, next_month)[1]
        next_effective_day = min(target_day, max_days_next_month)
        target_date_next_month = date(next_year, next_month, next_effective_day)
        return (target_date_next_month - today).days


def enrich_card_response(card: Card) -> CardResponse:
    """
    Convierte un modelo ORM Card en CardResponse con todos los cálculos financieros y de fechas.
    """
    days_cutoff = calculate_days_until(card.cutoff_day) if card.card_type == CardType.CREDIT else None
    days_due = calculate_days_until(card.due_day) if card.card_type == CardType.CREDIT else None
    is_near = bool(days_due is not None and days_due <= 5 and float(card.current_balance or 0) > 0)

    return CardResponse(
        id=card.id,
        user_id=card.user_id,
        name=card.name,
        bank_name=card.bank_name,
        card_type=card.card_type,
        card_brand=card.card_brand,
        last_four_digits=card.last_four_digits,
        credit_limit=Decimal(str(card.credit_limit or 0)),
        current_balance=Decimal(str(card.current_balance or 0)),
        available_credit=card.available_credit,
        utilization_percentage=card.utilization_percentage,
        cutoff_day=card.cutoff_day,
        due_day=card.due_day,
        interest_rate=card.interest_rate,
        currency=card.currency,
        color=card.color,
        bank_account_id=card.bank_account_id,
        is_active=card.is_active,
        days_until_cutoff=days_cutoff,
        days_until_due=days_due,
        is_near_due=is_near,
        created_at=card.created_at,
        updated_at=card.updated_at
    )


def get_cards_by_user(
    db: Session,
    user_id: int,
    only_active: bool = False,
    card_type: Optional[CardType] = None
) -> List[Card]:
    """
    Retorna las tarjetas registradas por el usuario.
    """
    query = db.query(Card).filter(Card.user_id == user_id)
    if only_active:
        query = query.filter(Card.is_active.is_(True))
    if card_type:
        query = query.filter(Card.card_type == card_type)
    return query.order_by(Card.id.asc()).all()


def get_card_by_id(db: Session, card_id: int, user_id: int) -> Optional[Card]:
    """
    Busca una tarjeta asegurando que pertenezca al usuario autenticado.
    """
    return db.query(Card).filter(Card.id == card_id, Card.user_id == user_id).first()


def create_card(db: Session, user_id: int, card_in: CardCreate) -> Card:
    """
    Crea una nueva tarjeta para el usuario.
    """
    db_card = Card(
        user_id=user_id,
        bank_account_id=card_in.bank_account_id,
        name=card_in.name.strip(),
        bank_name=card_in.bank_name.strip(),
        card_type=card_in.card_type,
        card_brand=card_in.card_brand.strip(),
        last_four_digits=card_in.last_four_digits.strip(),
        credit_limit=Decimal(str(card_in.credit_limit or 0)),
        current_balance=Decimal(str(card_in.current_balance or 0)),
        cutoff_day=card_in.cutoff_day,
        due_day=card_in.due_day,
        interest_rate=card_in.interest_rate,
        currency=card_in.currency.upper(),
        color=card_in.color,
        is_active=card_in.is_active
    )
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card


def update_card(db: Session, card: Card, card_in: CardUpdate) -> Card:
    """
    Actualiza los datos de una tarjeta.
    """
    if card_in.name is not None:
        card.name = card_in.name.strip()
    if card_in.bank_name is not None:
        card.bank_name = card_in.bank_name.strip()
    if card_in.card_type is not None:
        card.card_type = card_in.card_type
    if card_in.card_brand is not None:
        card.card_brand = card_in.card_brand.strip()
    if card_in.last_four_digits is not None:
        card.last_four_digits = card_in.last_four_digits.strip()
    if card_in.credit_limit is not None:
        card.credit_limit = Decimal(str(card_in.credit_limit))
    if card_in.current_balance is not None:
        card.current_balance = Decimal(str(card_in.current_balance))
    if card_in.cutoff_day is not None:
        card.cutoff_day = card_in.cutoff_day
    if card_in.due_day is not None:
        card.due_day = card_in.due_day
    if card_in.interest_rate is not None:
        card.interest_rate = Decimal(str(card_in.interest_rate))
    if card_in.currency is not None:
        card.currency = card_in.currency.upper()
    if card_in.color is not None:
        card.color = card_in.color
    if card_in.bank_account_id is not None:
        card.bank_account_id = card_in.bank_account_id
    if card_in.is_active is not None:
        card.is_active = card_in.is_active

    db.commit()
    db.refresh(card)
    return card


def adjust_card_balance(
    db: Session,
    card: Card,
    delta_amount: Optional[Decimal] = None,
    new_balance: Optional[Decimal] = None
) -> Card:
    """
    Ajusta el saldo o deuda de la tarjeta sumando/restando un delta o fijando un nuevo saldo.
    """
    if new_balance is not None:
        card.current_balance = max(Decimal("0.00"), Decimal(str(new_balance)))
    elif delta_amount is not None:
        updated = Decimal(str(card.current_balance or 0)) + Decimal(str(delta_amount))
        card.current_balance = max(Decimal("0.00"), updated)

    db.commit()
    db.refresh(card)
    return card


def delete_card(db: Session, card: Card, soft_delete: bool = False) -> None:
    """
    Elimina o desactiva la tarjeta.
    """
    if soft_delete:
        card.is_active = False
        db.commit()
    else:
        db.delete(card)
        db.commit()


def get_cards_summary(db: Session, user_id: int) -> dict:
    """
    Genera el resumen de límites, deudas y disponibilidad de tarjetas del usuario.
    """
    cards = get_cards_by_user(db, user_id=user_id)
    credit_cards = [c for c in cards if c.card_type == CardType.CREDIT and c.is_active]
    debit_cards = [c for c in cards if c.card_type == CardType.DEBIT and c.is_active]

    total_limit = sum((Decimal(str(c.credit_limit or 0)) for c in credit_cards), Decimal("0.00"))
    total_debt = sum((Decimal(str(c.current_balance or 0)) for c in credit_cards), Decimal("0.00"))
    total_available = max(Decimal("0.00"), total_limit - total_debt)

    overall_utilization = 0.0
    if total_limit > 0:
        overall_utilization = min(100.0, round(float(total_debt / total_limit) * 100.0, 2))

    enriched_cards = [enrich_card_response(c) for c in cards]

    return {
        "total_cards": len(cards),
        "total_credit_cards": len(credit_cards),
        "total_debit_cards": len(debit_cards),
        "total_credit_limit": total_limit,
        "total_credit_debt": total_debt,
        "total_credit_available": total_available,
        "overall_utilization_rate": overall_utilization,
        "cards": enriched_cards
    }
