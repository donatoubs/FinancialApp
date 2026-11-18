"""Movimientos: saldos, reversión exacta, edición y propiedad de cuentas/tarjetas."""

from app.utils.dates import today_local


def test_no_se_puede_usar_la_cuenta_de_otro_usuario(api, other_api):
    ajena = other_api.account()
    r = api.post("/transactions", {"transaction_type": "expense", "amount": "5", "description": "x",
                                   "source_account_id": ajena, "category_id": api.category(), "payment_method": "debit_card"})
    assert r.status_code == 400
    assert "no te pertenece" in r.json()["detail"]


def test_pagar_de_mas_y_borrar_revierte_exacto(api):
    cuenta = api.account()
    tarjeta = api.card(balance="50")
    r = api.post("/transactions", {"transaction_type": "card_payment", "amount": "80", "description": "pago",
                                   "source_account_id": cuenta, "card_id": tarjeta, "payment_method": "bank_transfer"})
    assert r.status_code == 201
    assert api.card_balance(tarjeta) == -30.0            # saldo a favor
    api.delete(f"/transactions/{r.json()['id']}")
    assert api.card_balance(tarjeta) == 50.0             # vuelve exactamente


def test_editar_puede_quitar_la_tarjeta_y_mover_el_gasto(api):
    cuenta = api.account()
    tarjeta = api.card(balance="50")
    tx = api.post("/transactions", {"transaction_type": "expense", "amount": "20", "description": "compra",
                                    "card_id": tarjeta, "category_id": api.category(), "payment_method": "credit_card"}).json()
    r = api.put(f"/transactions/{tx['id']}", {"card_id": None, "source_account_id": cuenta, "payment_method": "debit_card"})
    assert r.status_code == 200
    assert r.json()["card_id"] is None
    assert api.card_balance(tarjeta) == 50.0
    assert api.account_balance(cuenta) == 80.0


def test_editar_valida_propiedad_y_campos_obligatorios(api, other_api):
    cuenta = api.account()
    tx = api.post("/transactions", {"transaction_type": "expense", "amount": "5", "description": "x",
                                    "source_account_id": cuenta, "category_id": api.category(), "payment_method": "debit_card"}).json()
    assert api.put(f"/transactions/{tx['id']}", {"source_account_id": other_api.account()}).status_code == 400
    assert api.put(f"/transactions/{tx['id']}", {"amount": None}).status_code == 400


def test_fecha_por_defecto_es_la_de_ecuador(api):
    cuenta = api.account()
    tx = api.post("/transactions", {"transaction_type": "income", "amount": "10", "description": "x",
                                    "source_account_id": cuenta, "category_id": api.category("Sueldo"),
                                    "payment_method": "bank_transfer"}).json()
    assert tx["transaction_date"] == today_local().isoformat()
