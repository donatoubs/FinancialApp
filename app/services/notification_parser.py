"""
Parser de notificaciones financieras (DeUna, bancos de Ecuador, SMS) y utilidades de normalización.

Funciones puras, sin acceso a base de datos, para poder probarlas fácilmente.
"""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional, Union


# ------------------------------------------------------------------------------
# Normalización
# ------------------------------------------------------------------------------

def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def normalize_merchant(name: str) -> str:
    """'Supermaxi La Carolina #123' -> 'supermaxi la carolina'"""
    text = strip_accents(name or "").lower()
    text = re.sub(r"[^a-z0-9& ]+", " ", text)
    text = re.sub(r"\b\d+\b", " ", text)          # quita números sueltos (sucursales, códigos)
    return re.sub(r"\s+", " ", text).strip()


# Palabras demasiado genéricas para usarse solas como clave de un comercio
GENERIC_WORDS = {
    "cafeteria", "restaurante", "farmacia", "tienda", "panaderia", "comercial", "almacen",
    "consumo", "pago", "compra", "transferencia", "el", "la", "los", "las", "de", "del",
}


def suggest_rule_key(merchant: str) -> str:
    """
    Propone la clave con la que recordar un comercio.
    Solo se acorta a la primera palabra si es una marca conocida (para abarcar todas sus sucursales):
    'Supermaxi La Carolina' -> 'supermaxi'; 'Juan Pérez' -> 'juan perez'; 'Cafetería Dulce Aroma' -> completo.
    """
    norm = normalize_merchant(merchant)
    if not norm:
        return ""
    first = norm.split(" ")[0]
    if first != norm and first not in GENERIC_WORDS and keyword_category_hint(first):
        return first
    return norm


def merchant_matches_key(merchant_norm: str, key: str) -> bool:
    """El comercio coincide si es igual a la clave o empieza por ella como palabra completa."""
    return bool(key) and (merchant_norm == key or merchant_norm.startswith(key + " "))


# ------------------------------------------------------------------------------
# Montos
# ------------------------------------------------------------------------------

def parse_amount(value: Union[str, float, int, Decimal, None]) -> Optional[Decimal]:
    """
    Convierte montos en distintos formatos a Decimal positivo:
    3.75 | "3,75" | "$1,234.56" | "1.234,56" | "USD 12" -> Decimal. Devuelve None si no es válido.
    """
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        try:
            amount = Decimal(str(value))
        except InvalidOperation:
            return None
        return amount.quantize(Decimal("0.01")) if amount > 0 else None

    text = re.sub(r"[^0-9.,]", "", str(value))
    if not text or not re.search(r"\d", text):
        return None

    if "," in text and "." in text:
        # El último separador es el decimal
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        whole, _, frac = text.rpartition(",")
        text = text.replace(",", ".") if len(frac) in (1, 2) else text.replace(",", "")
    elif text.count(".") > 1:
        text = text.replace(".", "")
    elif "." in text:
        whole, _, frac = text.rpartition(".")
        if len(frac) == 3 and whole:          # "1.500" -> mil quinientos
            text = text.replace(".", "")

    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return amount.quantize(Decimal("0.01")) if amount > 0 else None


_AMOUNT = r"(?:\$|USD|US\$|U\$S)\s*([0-9][0-9.,]*[0-9]|[0-9])"


# ------------------------------------------------------------------------------
# Parser de texto
# ------------------------------------------------------------------------------

@dataclass
class ParsedNotification:
    amount: Optional[Decimal]
    merchant: str
    transaction_type: str          # "expense" | "income" | "transfer"
    card_hint: Optional[str] = None  # últimos dígitos de la tarjeta, si la notificación los trae


# "con tu Discover XX 484", "tarjeta TITULAR MC 9742", "Visa ****1234"
_CARD_DIGITS = re.compile(
    r"(?:x{2,}|\*{2,}|tarjeta|discover|visa|mastercard|master|mc|diners|amex)[^\d\n]{0,25}?(\d{3,4})\b",
    re.IGNORECASE,
)
# Prefijos de procesadores de pago: "DLOCAL*UBER RIDES", "PAYPAL *SPOTIFY", "SQ *CAFE"
_PROCESSOR_PREFIX = re.compile(r"^(?:dlocal|paypal|sq|mercadopago|merpago|pp|google|apple)\s*\*\s*", re.IGNORECASE)
_REVERSAL_WORDS = ("anulo", "anulada", "anulado", "anulacion", "reverso", "reversado", "reversada", "devolucion")


def card_hint_from_text(text: str) -> Optional[str]:
    match = _CARD_DIGITS.search(text or "")
    return match.group(1) if match else None


def clean_place(name: str) -> str:
    """'Kfc K071 San Luis Shop, Ruminahui, Pichincha' -> 'Kfc K071 San Luis Shop'; 'DLOCAL*UBER' -> 'UBER'."""
    name = _PROCESSOR_PREFIX.sub("", (name or "").strip())
    if name.count(",") >= 1:
        name = name.split(",")[0]
    return name.strip(" .,;-")


INCOME_WORDS = (
    "recibiste", "te envio", "te pago", "te transfirio", "acredito", "acreditamos", "acreditado",
    "transferencia recibida", "deposito", "abono", "has recibido", "recibio",
)

_TRAILING_NOISE = re.compile(
    r"(\s+(el(?=\s+\d)|con fecha|fecha|a las|por|desde|con tu|con su|con la|con el|tarjeta|cta|cuenta|ref"
    r"|exitosa|exitoso|realizada|realizado|aprobada|aprobado)\b.*)$",
    re.IGNORECASE,
)


def _clean_merchant(text: str) -> str:
    text = text.strip(" .,:;-\"'")
    text = _TRAILING_NOISE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" .,:;-\"'")
    return text[:120]


# Monto con grupo nombrado para los patrones
_A = r"(?:\$|USD|US\$|U\$S)\s*(?P<a>[0-9][0-9.,]*[0-9]|[0-9])"

# Patrones ordenados de más específico a más genérico. Grupos con nombre: m (comercio), a (monto).
# tipo None = se decide por las palabras de ingreso.
_PATTERNS = [
    # DeUna: "Recargaste $1,00 en tu cuenta Deuna!" (dinero propio del banco a DeUna)
    ("transfer", rf"recargaste\s+{_A}\s+(?:en|a)\s+tu\s+cuenta\s+(?P<m>deuna)"),
    # DeUna: "Enviaste $5 a Ana" / "Transferiste $5 a Ana"
    ("expense", rf"enviaste\s+{_A}\s+a\s+(?P<m>.+)"),
    # DeUna: "Pagaste a Juan Pérez, por $4.50 el 17/11"
    ("expense", rf"pagaste\s+a\s+(?P<m>.+?)[,\s]+por\s+{_A}"),
    # DeUna: "Pagaste $4.50 a Cafetería Don Juan"
    ("expense", rf"pagaste\s+{_A}\s+a\s+(?P<m>.+)"),
    # DeUna: "Recibiste de Ana, por $10" / "Recibiste $10 de Ana"
    ("income", rf"recibiste\s+(?:de\s+)?(?P<m>[^$0-9].*?)[,\s]+por\s+{_A}"),
    ("income", rf"recibiste\s+{_A}\s+de\s+(?P<m>.+)"),
    # "Ana te envió $10" / "Ana te pagó $10"
    ("income", rf"(?P<m>[A-Za-z][^,.$]*?)\s+te\s+(?:envio|pago|transfirio)\s+{_A}"),
    # Bancos: "consumo por USD 12.50 en SUPERMAXI" / "compra de $12.50 en X"
    (None, rf"(?:consumo|compra|pago|debito|cargo)[^$0-9]*?{_A}.*?en\s+(?P<m>.+)"),
    # Transferencias: "transferencia de $50 a Juan" / "transferiste $50 a Juan"
    ("expense", rf"transfer\w*[^$0-9]*?{_A}\s+a\s+(?P<m>.+)"),
]
_COMPILED = [(t, re.compile(p, re.IGNORECASE)) for t, p in _PATTERNS]


def parse_notification_text(raw_text: str) -> ParsedNotification:
    """
    Extrae monto, comercio/persona y tipo de una notificación en texto.
    Si no encuentra el monto devuelve amount=None (nunca inventa un valor).
    """
    raw = unicodedata.normalize("NFC", raw_text or "")
    parsed = _parse_notification(raw)
    parsed.card_hint = card_hint_from_text(raw)
    if parsed.merchant:
        parsed.merchant = clean_place(parsed.merchant) or parsed.merchant
    return parsed


def _parse_notification(raw: str) -> ParsedNotification:
    flat = strip_accents(re.sub(r"\s+", " ", raw)).lower()
    # Anulaciones y reversos: el dinero vuelve; nunca se registran como gasto
    if any(w in flat for w in _REVERSAL_WORDS):
        amount_match = re.search(_AMOUNT, raw, re.IGNORECASE)
        return ParsedNotification(parse_amount(amount_match.group(1)) if amount_match else None,
                                  "Anulación de compra", "income")
    # Atajos entrega el título y el cuerpo en líneas separadas: se prueba primero cada línea
    # (de abajo hacia arriba: el cuerpo suele traer más datos), luego el texto completo
    lines = [ln for ln in (re.sub(r"\s+", " ", x).strip() for x in raw.splitlines()) if ln]
    # Apple Wallet: "Banco Pichincha" / "Kfc K071 San Luis Shop, Ruminahui, P..." / "$5.99"
    if len(lines) >= 2 and re.fullmatch(_AMOUNT, lines[-1], re.IGNORECASE):
        return ParsedNotification(parse_amount(re.fullmatch(_AMOUNT, lines[-1], re.IGNORECASE).group(1)),
                                  clean_place(lines[-2]) or lines[-2], "expense")
    if len(lines) > 1:
        for line in reversed(lines):
            parsed = _parse_line(line, strict=True)
            if parsed:
                return parsed
    return _parse_line(re.sub(r"\s+", " ", raw).strip(), strict=False)


def _parse_line(text: str, strict: bool) -> Optional["ParsedNotification"]:
    """Interpreta una línea. Con strict=True devuelve None si ningún patrón conocido coincide."""
    text = re.sub(r"^[^\w$]+", "", text)   # emojis o viñetas al inicio ("✅ Recargaste…")
    # Quitar prefijos tipo "DeUna:" o "Banco Pichincha:"
    text_body = re.sub(r"^[\w\s]{2,30}:\s*", "", text) if ":" in text[:32] else text
    lower = strip_accents(text_body).lower()
    is_income = any(w in lower for w in INCOME_WORDS)

    for tx_type, rx in _COMPILED:
        # Se busca sobre el texto sin tildes (misma longitud en NFC) y se recorta del original
        match = rx.search(strip_accents(text_body))
        if match:
            # Recuperar el comercio desde el texto original (con tildes) usando las mismas posiciones
            merchant = _clean_merchant(text_body[match.start("m"):match.end("m")])
            amount = parse_amount(match.group("a"))
            final_type = tx_type or ("income" if is_income else "expense")
            if final_type == "transfer":
                return ParsedNotification(amount, "Recarga DeUna" if merchant.lower() == "deuna" else f"Recarga {merchant}", "transfer")
            if merchant:
                if final_type == "income" and not merchant.lower().startswith("de:"):
                    merchant = f"De: {merchant}"
                return ParsedNotification(amount, merchant, final_type)

    if strict:
        return None

    # Genérico: primer monto que aparezca
    amount_match = re.search(_AMOUNT, text_body, re.IGNORECASE)
    amount = parse_amount(amount_match.group(1)) if amount_match else None
    if amount is None:
        plain = re.search(r"\b([0-9]+[.,][0-9]{2})\b", text_body)
        amount = parse_amount(plain.group(1)) if plain else None

    merchant = ""
    for connector in (r"\ben\b", r"\ba\b", r"\bde\b"):
        m = re.search(connector + r"\s+(.+)", text_body, re.IGNORECASE)
        if m:
            candidate = _clean_merchant(re.sub(_AMOUNT, "", m.group(1), flags=re.IGNORECASE))
            if candidate and not re.fullmatch(r"[0-9.,\s$]+", candidate):
                merchant = candidate
                break
    if not merchant:
        merchant = _clean_merchant(re.sub(_AMOUNT, "", text_body, flags=re.IGNORECASE))[:40] or "Movimiento sin descripción"

    return ParsedNotification(amount, merchant, "income" if is_income else "expense")


# ------------------------------------------------------------------------------
# Auto-categorización por palabras clave (coincidencia por palabra completa)
# ------------------------------------------------------------------------------

# Clave: inicio del nombre de la categoría (sin tildes). Valor: palabras clave.
KEYWORD_CATEGORY_MAP = {
    "alimentacion": [
        "supermaxi", "megamaxi", "comisariato", "mi comisariato", "tia", "santa maria", "coral",
        "aki", "gran aki", "tuti", "minimarket", "supermercado", "frutas", "carniceria", "panaderia",
    ],
    "restaurantes": [
        "restaurante", "kfc", "mcdonald", "mcdonalds", "sweet & coffee", "sweet and coffee", "cafe",
        "cafeteria", "coffee", "pizza", "pizzeria", "hamburguesa", "burger", "subway", "starbucks",
        "almuerzo", "heladeria", "baskin", "crepes", "mariscos", "chifa", "parrillada", "tropiburger",
        "pedidosya", "rappi", "uber eats",
    ],
    "transporte": [
        "uber", "cabify", "didi", "indrive", "gasolinera", "primax", "terpel", "petroecuador",
        "mobil", "peaje", "parqueadero", "parking", "taller", "mecanica", "llantas", "metro de quito",
    ],
    "salud": [
        "fybeca", "sanasana", "medicity", "farmacia", "farmacias", "cruz azul", "pharmacys",
        "hospital", "clinica", "medico", "laboratorio", "dentista", "odontologo", "optica",
    ],
    "suscripciones": [
        "netflix", "spotify", "youtube", "disney", "prime video", "hbo", "icloud", "apple.com",
        "chatgpt", "openai", "claude", "anthropic",
    ],
    "servicios basicos": [
        "cnt", "claro", "movistar", "tuenti", "netlife", "empresa electrica", "eeq", "agua potable",
        "emaap", "interagua", "luz", "internet",
    ],
    "educacion": [
        "universidad", "uide", "colegio", "escuela", "udla", "usfq", "puce", "espol", "curso",
        "udemy", "platzi", "coursera", "libreria", "copias",
    ],
    "entretenimiento": [
        "cine", "cinemark", "supercines", "multicines", "discoteca", "steam", "playstation",
        "xbox", "nintendo", "concierto", "teatro",
    ],
    "compras": [
        "zara", "h&m", "marathon", "etafashion", "de prati", "quicentro", "san luis shopping",
        "condado shopping", "scalare", "amazon", "aliexpress", "shein", "temu", "kywi", "sukasa",
    ],
}


def keyword_category_hint(merchant: str) -> Optional[str]:
    """Devuelve el prefijo de categoría sugerido ('alimentacion', ...) o None."""
    norm = " " + normalize_merchant(merchant) + " "
    for cat_prefix, keywords in KEYWORD_CATEGORY_MAP.items():
        for kw in keywords:
            kw_norm = normalize_merchant(kw) or kw
            if f" {kw_norm} " in norm:
                return cat_prefix
    return None
