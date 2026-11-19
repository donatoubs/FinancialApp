"""Lectura de notificaciones (DeUna, bancos) y formatos de montos."""

from decimal import Decimal

import pytest

from app.services.notification_parser import (
    keyword_category_hint,
    parse_amount,
    parse_notification_text,
    suggest_rule_key,
)
from app.utils.formatting import fmt_money, fmt_percent


@pytest.mark.parametrize("text, amount, merchant, tx_type", [
    ("DeUna: Pagaste a Juan Pérez, por $4.50 el 17/11/2026", "4.50", "Juan Pérez", "expense"),
    ("DeUna: Pagaste $2.50 a Cafetería Dulce Aroma", "2.50", "Cafetería Dulce Aroma", "expense"),
    ("Recibiste de María López, por $15,00 el 17/11", "15.00", "De: María López", "income"),
    ("DeUna: Recibiste $20 de Carlos", "20.00", "De: Carlos", "income"),
    ("Ana Torres te envió $12.30", "12.30", "De: Ana Torres", "income"),
    ("Banco Pichincha: Consumo por USD 1,234.56 en SUPERMAXI EL BOSQUE con tu tarjeta Visa", "1234.56", "SUPERMAXI EL BOSQUE", "expense"),
    ("Transferencia de $50.00 a Pedro Gómez exitosa", "50.00", "Pedro Gómez", "expense"),
    # Formato real de Atajos: título y cuerpo en líneas separadas, con emoji
    ("✅ Recargaste $0,01\nRecargaste $0,01 en tu cuenta Deuna! el 18 nov 2026", "0.01", "Recarga DeUna", "transfer"),
    ("✅ Pagaste $3,25\nPagaste $3,25 a Tienda Doña Rosa", "3.25", "Tienda Doña Rosa", "expense"),
    ("✅ Recibiste $10,00\nRecibiste $10,00 de Ana López", "10.00", "De: Ana López", "income"),
])
def test_notificaciones(text, amount, merchant, tx_type):
    parsed = parse_notification_text(text)
    assert parsed.amount == Decimal(amount)
    assert parsed.merchant == merchant
    assert parsed.transaction_type == tx_type


def test_sin_monto_no_inventa_valor():
    assert parse_notification_text("Consumo en KFC Quicentro").amount is None


@pytest.mark.parametrize("raw, expected", [
    ("3,75", "3.75"), ("$1,234.56", "1234.56"), ("1.234,56", "1234.56"), ("1.500", "1500.00"),
    (3.75, "3.75"), ("0", None), ("abc", None),
])
def test_parse_amount(raw, expected):
    result = parse_amount(raw)
    assert (str(result) if result is not None else None) == expected


def test_palabras_clave_por_palabra_completa():
    assert keyword_category_hint("Supermaxi La Carolina") == "alimentacion"
    assert keyword_category_hint("Maxi Pizza") == "restaurantes"     # "max" ya no confunde
    assert keyword_category_hint("Fybeca 23") == "salud"


def test_clave_de_comercio():
    assert suggest_rule_key("Supermaxi La Carolina") == "supermaxi"     # marca: todas las sucursales
    assert suggest_rule_key("Juan Pérez") == "juan perez"               # persona: nombre completo


def test_formatos_del_servidor():
    assert fmt_money(1260) == "$1.260,00"
    assert fmt_money(-1234.5) == "−$1.234,50"
    assert fmt_percent(84.0) == "84%"
    assert fmt_percent(10.5) == "10,5%"


@pytest.mark.parametrize("text, amount, merchant, tx_type, card", [
    # blu Diners Club
    ("Notificación de consumo: hiciste una compra.\nHola! Consumiste $ 0,52 en DLOCAL*UBER RIDES Mr con tu "
     "Discover XX 484 . Si no lo hiciste, escribe un SMS con BLOQUEO 31004 al 365.", "0.52", "UBER RIDES Mr", "expense", "484"),
    ("¡Se anuló tu compra!\nHola! La transaccion con tu tarjeta Discover 484 por el valor de USD 0,52 fue anulada "
     "el 2026-11-15 19:34", "0.52", "Anulación de compra", "income", "484"),
    # Banco del Pacífico
    ("Consumo realizado\nPacifico informa que a las 15:39 realizo un consumo con su tarjeta TITULAR MC 9742 de $5.23 "
     "en ATIMASA ESTACION DE SERVICIO A", "5.23", "ATIMASA ESTACION DE SERVICIO A", "expense", "9742"),
    # Apple Wallet (Banco Pichincha)
    ("Banco Pichincha\nKfc K071 San Luis Shop, Ruminahui, Pichincha\n$5.99", "5.99", "Kfc K071 San Luis Shop", "expense", None),
    ("Banco Pichincha\nTrip, Quito, Pichincha\n$60.00", "60.00", "Trip", "expense", None),
])
def test_notificaciones_de_bancos(text, amount, merchant, tx_type, card):
    parsed = parse_notification_text(text)
    assert parsed.amount == Decimal(amount)
    assert parsed.merchant == merchant
    assert parsed.transaction_type == tx_type
    assert parsed.card_hint == card
