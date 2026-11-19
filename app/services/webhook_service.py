"""
Servicio de Procesamiento para el Webhook de iOS (Apple Wallet, DeUna y banca móvil).

Flujo:
1. Se interpreta el pago (datos estructurados de Apple Pay o texto de la notificación).
2. Se descartan duplicados (el atajo puede ejecutarse dos veces).
3. Se calculan sugerencias (regla aprendida del comercio > datos del atajo > heurísticas).
4. Si el comercio ya es conocido (y la opción está activa) o el atajo pidió registrar directo,
   se crea el movimiento. Si no, queda en la Bandeja de Pendientes para confirmarlo con un toque.
"""

import re
import secrets
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.pending import PendingStatus, PendingTransaction
from app.models.user import User
from app.schemas.webhook import IOSWebhookPayload, WebhookResponse
from app.services import pending_service
from app.services.notification_parser import clean_place, parse_amount, parse_notification_text
from app.utils.formatting import fmt_money


# ------------------------------------------------------------------------------
# Token del webhook
# ------------------------------------------------------------------------------

def get_or_create_webhook_token(db: Session, user: User) -> str:
    """Retorna el token del webhook del usuario o genera uno si no existe."""
    if not user.webhook_token:
        user.webhook_token = f"fin_{secrets.token_urlsafe(28)}"
        db.commit()
        db.refresh(user)
    return user.webhook_token


def regenerate_webhook_token(db: Session, user: User) -> str:
    """Regenera un nuevo token privado de webhook."""
    user.webhook_token = f"fin_{secrets.token_urlsafe(28)}"
    db.commit()
    db.refresh(user)
    return user.webhook_token


def get_user_by_webhook_token(db: Session, token: str) -> Optional[User]:
    """Busca el usuario activo por su token de webhook (comparación en tiempo constante)."""
    if not token:
        return None
    user = db.query(User).filter(User.webhook_token == token, User.is_active == True).first()  # noqa: E712
    if user and secrets.compare_digest(user.webhook_token, token):
        return user
    return None


# ------------------------------------------------------------------------------
# Interpretación del payload
# ------------------------------------------------------------------------------

def _detect_source(payload: IOSWebhookPayload) -> str:
    source = (payload.source or "").lower().strip()
    if source:
        return source[:30]
    text = " ".join(filter(None, [payload.raw_text, payload.notes, payload.merchant])).lower()
    if "deuna" in text:
        return "deuna"
    return "bank" if payload.raw_text else "apple_pay"


def _interpret(payload: IOSWebhookPayload, source: str):
    """Devuelve (amount, merchant, tx_type, card_hint) sin inventar valores."""
    explicit_type = (payload.transaction_type or "").strip().lower()

    if payload.raw_text and not payload.merchant:
        parsed = parse_notification_text(payload.raw_text)
        amount = parse_amount(payload.amount) if payload.amount is not None else parsed.amount
        tx_type = explicit_type if explicit_type in ("income", "expense", "transfer") else parsed.transaction_type
        return amount, parsed.merchant, tx_type, payload.card or parsed.card_hint

    amount = parse_amount(payload.amount)
    raw_merchant = (payload.merchant or "").strip()
    # Error común en Atajos: se envía el monto en lugar del comercio
    if not raw_merchant or re.fullmatch(r"[\d.,$\s]+", raw_merchant):
        raw_merchant = "Consumo DeUna" if source == "deuna" else "Consumo Apple Pay"
    tx_type = "income" if explicit_type == "income" else "expense"
    return amount, (clean_place(raw_merchant) or raw_merchant)[:255], tx_type, payload.card


def _pending_reason(payload: IOSWebhookPayload, tx_type: str, amount, chosen, has_medium: bool, source: str) -> Optional[str]:
    """Explica en una frase por qué no se registró solo, para que se vea en la notificación del iPhone."""
    if tx_type == "transfer":
        return "Es un movimiento entre tus cuentas: elige de dónde salió."
    if amount is None:
        return "No pude leer el monto."
    if not payload.category:
        return None
    if not chosen:
        return f"No encontré la categoría '{payload.category}' en tu app."
    if not has_medium:
        return ("No sé de qué cuenta salió: crea una cuenta llamada DeUna."
                if source == "deuna" else "No sé con qué cuenta o tarjeta pagaste.")
    return None


def _medium_label(account, card) -> Optional[str]:
    if card:
        return f"Tarjeta {card.name}"
    if account:
        return f"Cuenta {account.name}"
    return None


# ------------------------------------------------------------------------------
# Proceso principal
# ------------------------------------------------------------------------------

def process_ios_webhook(db: Session, user: User, payload: IOSWebhookPayload) -> WebhookResponse:
    if not payload.raw_text and payload.amount is None and not payload.merchant:
        raise HTTPException(status_code=400, detail="Envía 'amount' y 'merchant' (Apple Pay) o 'raw_text' (texto de la notificación).")

    source = _detect_source(payload)
    amount, merchant, tx_type, card_hint = _interpret(payload, source)

    # 1. Duplicados
    dedup_key, is_external = pending_service.build_dedup_key(
        user.id, source, amount, merchant, payload.raw_text, payload.external_id
    )
    duplicate = pending_service.find_duplicate(db, user.id, dedup_key, is_external)
    if duplicate:
        return WebhookResponse(
            success=True,
            status="duplicate",
            message=f"↩️ Ya recibido · {fmt_money(duplicate.amount or 0)} · {duplicate.merchant}. No se registró de nuevo.",
            pending_id=duplicate.id,
            transaction_id=duplicate.transaction_id,
            amount=float(duplicate.amount) if duplicate.amount is not None else None,
            merchant=duplicate.merchant,
            transaction_type=duplicate.transaction_type,
        )

    # 2. Sugerencias
    category, account, card, reason, rule = pending_service.compute_suggestions(
        db, user, merchant, tx_type, source, card_hint, payload.category
    )

    pending = PendingTransaction(
        user_id=user.id,
        status=PendingStatus.PENDING.value,
        source=source,
        raw_text=payload.raw_text,
        amount=amount,
        merchant=merchant,
        transaction_type=tx_type,
        card_hint=card_hint,
        suggested_category_id=category.id if category else None,
        suggested_account_id=account.id if account else None,
        suggested_card_id=card.id if card else None,
        suggestion_reason=reason,
        dedup_key=dedup_key,
    )
    db.add(pending)
    db.flush()

    # 3. ¿Registrar directamente?
    has_medium = bool(account or card)
    # El atajo solo puede pedir registro directo si la categoría elegida existe de verdad
    # ("Revisar después" o una categoría vacía no deben caer en "Otros" sin preguntar).
    chosen = pending_service.find_category_by_name(db, user.id, tx_type, payload.category) if payload.category else None
    if chosen:
        category = chosen
    wants_auto = (rule is not None and user.webhook_auto_confirm) or (payload.auto_register and chosen is not None)
    # Las transferencias entre cuentas propias siempre se confirman a mano (hay que elegir origen y destino)
    can_auto = wants_auto and tx_type != "transfer" and amount is not None and category is not None and has_medium
    if can_auto:
        # Validar el medio sugerido antes de tocar nada (p. ej. débito sin cuenta vinculada)
        try:
            pending_service.resolve_payment(
                db, user.id, tx_type, source, account.id if account else None, card.id if card else None
            )
        except HTTPException:
            can_auto = False

    if can_auto:
        if rule:
            rule.times_confirmed = (rule.times_confirmed or 0) + 1
        tx = pending_service.register_from_pending(
            db, user, pending,
            tx_type=tx_type,
            amount=amount,
            category_id=category.id,
            account_id=account.id if account else None,
            card_id=card.id if card else None,
            description=merchant,
            notes=payload.notes or f"Registrado automáticamente desde el iPhone ({source})",
            tx_date=pending_service.to_response(pending).occurred_date,
        )
        medium = card.name if card else (account.name if account else None)
        parts = [("+" if tx_type == "income" else "") + fmt_money(amount), category.name, merchant, medium]
        return WebhookResponse(
            success=True,
            status="registered",
            message=("💰 " if tx_type == "income" else "✅ ") + " · ".join(p for p in parts if p),
            pending_id=pending.id,
            transaction_id=tx.id,
            amount=float(amount),
            merchant=merchant,
            category=category.name,
            account_or_card=_medium_label(account, card),
            transaction_type=tx_type,
        )

    db.commit()
    amount_txt = fmt_money(amount) if amount is not None else "monto sin leer"
    why = _pending_reason(payload, tx_type, amount, chosen, has_medium, source) if payload.auto_register else None
    return WebhookResponse(
        success=True,
        status="pending",
        message=f"🕓 Pendiente · {amount_txt} · {merchant}" + (f"\n{why}" if why else "\nConfírmalo en la app."),
        pending_id=pending.id,
        amount=float(amount) if amount is not None else None,
        merchant=merchant,
        category=category.name if category else None,
        account_or_card=_medium_label(account, card),
        transaction_type=tx_type,
    )
