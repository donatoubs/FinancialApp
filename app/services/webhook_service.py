"""
Servicio de Procesamiento para el Webhook de iOS (Apple Wallet & DeUna).
Extrae montos, comercios, asocia cuentas/tarjetas y auto-categoriza compras.
"""

import re
import secrets
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.account import BankAccount
from app.models.card import Card, CardType
from app.models.category import Category
from app.models.transaction import TransactionType, PaymentMethod
from app.schemas.transaction import TransactionCreate
from app.schemas.webhook import IOSWebhookPayload, WebhookResponse
from app.services import transaction_service


# Diccionario de palabras clave para auto-categorización en Ecuador
KEYWORD_CATEGORY_MAP = {
    "Alimentación": [
        "supermaxi", "megamaxi", "comisariato", "tia", "santa maria", "coral", "aki", "gran aki",
        "restaurante", "kfc", "mcdonald", "sweet & coffee", "sweet and coffee", "cafe", "coffee",
        "panaderia", "pizza", "hamburguesa", "burger", "subway", "starbucks", "almuerzo", "cena",
        "desayuno", "heladeria", "baskin", "crepes", "mariscos", "chifa", "pollo", "parrillada"
    ],
    "Transporte": [
        "uber", "cabify", "didi", "indrive", "gasolinera", "primax", "terpel", "petroecuador",
        "mobil", "peaje", "parqueadero", "parking", "taller", "mecanica", "lavadora", "llantas"
    ],
    "Salud": [
        "fybeca", "sanasana", "medicity", "farmacia", "cruz azul", "economica", "hospital",
        "clinica", "medico", "laboratorio", "dentista", "odontologo", "optica", "salud"
    ],
    "Servicios": [
        "netflix", "spotify", "apple", "google", "youtube", "disney", "prime video", "hbo",
        "max", "cnt", "claro", "movistar", "tuenti", "luz", "agua", "internet", "netlife", "enel"
    ],
    "Educación": [
        "universidad", "uide", "colegio", "escuela", "udla", "usfq", "puce", "curso",
        "udemy", "platzi", "coursera", "libro", "libreria", "copias"
    ],
    "Entretenimiento": [
        "cine", "cinemark", "supercines", "multicines", "bar", "discoteca", "fiesta",
        "juego", "steam", "playstation", "xbox", "nintendo", "concierto", "teatro"
    ],
    "Compras": [
        "zara", "h&m", "marathon", "etafashion", "de prati", "mall", "quicentro", "cci",
        "san luis", "condado", "scalare", "amazon", "aliexpress", "shein", "temu"
    ]
}


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
    """Busca el usuario activo por su token de webhook."""
    if not token:
        return None
    return db.query(User).filter(User.webhook_token == token, User.is_active == True).first()


def _parse_text_notification(raw_text: str) -> Tuple[Decimal, str, TransactionType]:
    """
    Parsea una notificación de texto de DeUna, Banco Pichincha, Guayaquil, etc.
    Extrae: (monto, comercio/destinatario, tipo_de_transaccion)
    """
    text = raw_text.strip()
    lower_text = text.lower()

    # 1. Determinar si es Ingreso o Gasto
    is_income = any(word in lower_text for word in [
        "recibiste", "acredito", "transferencia recibida", "deposito", "abono", "te envio"
    ])
    tx_type = TransactionType.INCOME if is_income else TransactionType.EXPENSE

    # 2. Formato exacto DeUna: "Pagaste a X, por $Y el Z" o "Recibiste de X, por $Y el Z"
    deuna_pay_match = re.search(r'Pagaste a\s+(.*?)(?:,\s*|\s+)por\s+\$?([0-9]+(?:[.,][0-9]{1,2})?)', text, re.IGNORECASE)
    deuna_rec_match = re.search(r'Recibiste (?:de\s+)?(.*?)(?:,\s*|\s+)por\s+\$?([0-9]+(?:[.,][0-9]{1,2})?)', text, re.IGNORECASE)

    if deuna_pay_match:
        merchant = deuna_pay_match.group(1).strip()
        amount_str = deuna_pay_match.group(2).replace(',', '.')
        return Decimal(amount_str), merchant, TransactionType.EXPENSE

    if deuna_rec_match:
        merchant = deuna_rec_match.group(1).strip()
        amount_str = deuna_rec_match.group(2).replace(',', '.')
        return Decimal(amount_str), f"De: {merchant}", TransactionType.INCOME

    # 3. Fallback genérico para monto usando Regex ($12.50, 12,50, etc.)
    amount_match = re.search(r'(?:\$|\bUSD\b)\s*([0-9]+(?:[.,][0-9]{1,2})?)', text, re.IGNORECASE)
    if not amount_match:
        amount_match = re.search(r'\b([0-9]+(?:[.,][0-9]{2}))\b', text)

    if amount_match:
        amount_str = amount_match.group(1).replace(',', '.')
        amount = Decimal(amount_str)
    else:
        amount = Decimal("1.00")

    # 4. Extraer comercio o destinatario genérico
    merchant = "Transacción DeUna"
    if " a " in text:
        parts = text.split(" a ", 1)
        if len(parts) > 1:
            merchant = parts[1].split(",")[0].strip()
    elif " de " in text and is_income:
        parts = text.split(" de ", 1)
        if len(parts) > 1:
            merchant = f"De: {parts[1].split(',')[0].strip()}"
    elif " en " in text:
        parts = text.split(" en ", 1)
        if len(parts) > 1:
            merchant = parts[1].split(",")[0].strip()
    else:
        merchant = text[:40]

    merchant = re.sub(r'[\.\,\!\?]+$', '', merchant).strip()
    return amount, merchant, tx_type


def _match_category(db: Session, user_id: int, merchant: str, tx_type: TransactionType) -> Category:
    """Busca la mejor categoría según el nombre del comercio."""
    target_type = "income" if tx_type == TransactionType.INCOME else "expense"
    user_categories = db.query(Category).filter(
        (Category.user_id == user_id) | (Category.user_id.is_(None)),
        Category.category_type.in_([target_type, "both"])
    ).all()

    if not user_categories:
        # Fallback a cualquier categoría
        cat = db.query(Category).first()
        if cat:
            return cat
        raise HTTPException(status_code=500, detail="No existen categorías configuradas en el sistema.")

    if tx_type == TransactionType.INCOME:
        # Para ingresos, buscar Transferencias o Sueldo
        for cat in user_categories:
            if "transferencia" in cat.name.lower() or "sueldo" in cat.name.lower():
                return cat
        return user_categories[0]

    merchant_lower = merchant.lower()

    # Comparar contra las palabras clave
    for cat_name, keywords in KEYWORD_CATEGORY_MAP.items():
        if any(kw in merchant_lower for kw in keywords):
            # Buscar categoría en la BD con nombre similar
            for cat in user_categories:
                if cat_name.lower() in cat.name.lower():
                    return cat

    # Si no hubo coincidencia, buscar categoría "Otros Gastos" o "General"
    for cat in user_categories:
        if "otro" in cat.name.lower() or "general" in cat.name.lower() or "vario" in cat.name.lower():
            return cat

    return user_categories[0]


def process_ios_webhook(db: Session, user: User, payload: IOSWebhookPayload) -> WebhookResponse:
    """
    Procesa una transacción enviada desde Atajos de iOS (Apple Wallet o DeUna).
    Crea el movimiento y actualiza los saldos en tiempo real.
    """
    # 1. Determinar monto, comercio y tipo
    if payload.raw_text:
        amount, merchant, tx_type = _parse_text_notification(payload.raw_text)
    else:
        if payload.amount is None or payload.amount <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser un valor positivo.")
        amount = Decimal(str(payload.amount))
        raw_merchant = (payload.merchant or "").strip()
        # Si el comercio recibido es solo un número (error común de variables en iOS Shortcuts), usar descripción por defecto
        if not raw_merchant or raw_merchant.replace('.', '').replace(',', '').isdigit():
            merchant = "Consumo DeUna" if (payload.source or "").lower() == "deuna" else "Consumo Apple Pay"
        else:
            merchant = raw_merchant
        tx_type = TransactionType.INCOME if (payload.transaction_type or "").upper() == "INCOME" else TransactionType.EXPENSE

    # 2. Identificar la tarjeta o cuenta bancaria
    user_cards = db.query(Card).filter(Card.user_id == user.id, Card.is_active == True).all()
    user_accounts = db.query(BankAccount).filter(BankAccount.user_id == user.id, BankAccount.is_active == True).all()

    card_id: Optional[int] = None
    source_account_id: Optional[int] = None
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    matched_label: str = "Billetera"

    # Verificar si el origen es DeUna (por source, texto o notas)
    source_str = (payload.source or "").lower().strip()
    is_deuna = (
        source_str == "deuna" or 
        "deuna" in (payload.raw_text or "").lower() or 
        "deuna" in (payload.notes or "").lower() or
        "deuna" in merchant.lower()
    )

    if is_deuna:
        # Buscar cuenta de Banco Pichincha o DeUna
        pichincha_acc = next((acc for acc in user_accounts if "pichincha" in acc.bank_name.lower() or "pichincha" in acc.name.lower() or "deuna" in acc.name.lower()), None)
        if pichincha_acc:
            source_account_id = pichincha_acc.id
            payment_method = PaymentMethod.DEBIT_CARD
            matched_label = f"DeUna ({pichincha_acc.name})"
        elif user_accounts:
            source_account_id = user_accounts[0].id
            payment_method = PaymentMethod.DEBIT_CARD
            matched_label = f"DeUna ({user_accounts[0].name})"
        elif user_cards:
            # Si el usuario no ha creado ninguna cuenta bancaria aún, usar su tarjeta
            card_id = user_cards[0].id
            payment_method = PaymentMethod.CREDIT_CARD
            matched_label = f"DeUna ({user_cards[0].name})"
    elif payload.card and user_cards:
        # Buscar coincidencia con tarjetas registradas
        card_search = payload.card.lower()
        matched_card = next((
            c for c in user_cards if c.name.lower() in card_search or c.franchise.value.lower() in card_search
        ), None)

        if matched_card:
            if matched_card.card_type == CardType.CREDIT:
                card_id = matched_card.id
                payment_method = PaymentMethod.CREDIT_CARD
                matched_label = f"Tarjeta de Crédito {matched_card.name}"
            else:
                # Débito vinculada a cuenta
                payment_method = PaymentMethod.DEBIT_CARD
                source_account_id = matched_card.linked_account_id or (user_accounts[0].id if user_accounts else None)
                matched_label = f"Tarjeta Débito {matched_card.name}"
        else:
            # Asignar a la primera tarjeta de crédito por defecto
            credit_card = next((c for c in user_cards if c.card_type == CardType.CREDIT), user_cards[0])
            card_id = credit_card.id
            payment_method = PaymentMethod.CREDIT_CARD
            matched_label = f"Tarjeta {credit_card.name}"
    elif user_cards:
        # Sin especificar tarjeta, elegir la primera tarjeta de crédito
        credit_card = next((c for c in user_cards if c.card_type == CardType.CREDIT), user_cards[0])
        card_id = credit_card.id
        payment_method = PaymentMethod.CREDIT_CARD
        matched_label = f"Tarjeta {credit_card.name}"
    elif user_accounts:
        source_account_id = user_accounts[0].id
        payment_method = PaymentMethod.DEBIT_CARD
        matched_label = f"Cuenta {user_accounts[0].name}"
    else:
        raise HTTPException(
            status_code=400,
            detail="Debes tener al menos una cuenta bancaria o tarjeta registrada en la app para vincular el pago."
        )

    # 3. Categorización: si el atajo envió una categoría explícita, priorizarla
    category = None
    if payload.category:
        cat_search = payload.category.lower().strip()
        user_categories = db.query(Category).filter(
            (Category.user_id == user.id) | (Category.user_id.is_(None))
        ).all()
        category = next((c for c in user_categories if c.name.lower() in cat_search or cat_search in c.name.lower()), None)

    if not category:
        category = _match_category(db, user.id, merchant, tx_type)

    # 4. Crear transacción y actualizar saldos atómicamente
    tx_in = TransactionCreate(
        transaction_type=tx_type,
        amount=amount,
        currency=user.currency_preference or "USD",
        category_id=category.id,
        source_account_id=source_account_id,
        card_id=card_id,
        payment_method=payment_method,
        description=merchant,
        notes=payload.notes or f"Registrado automáticamente vía Atajos de iOS ({'DeUna' if is_deuna else 'Apple Wallet'})",
        transaction_date=date.today()
    )

    created_tx = transaction_service.create_transaction(db=db, user_id=user.id, tx_in=tx_in)

    return WebhookResponse(
        success=True,
        message=f"{'Ingreso' if tx_type == TransactionType.INCOME else 'Gasto'} de ${amount:.2f} en '{merchant}' registrado exitosamente.",
        transaction_id=created_tx.id,
        amount=float(amount),
        category=category.name,
        account_or_card=matched_label,
        transaction_type=tx_type.value
    )
