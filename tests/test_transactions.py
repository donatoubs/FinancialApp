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


def test_buscar_por_descripcion_o_nota(api):
    cuenta = api.account()
    cat = api.category()
    for desc, notes in [("Supermaxi Norte", None), ("Fybeca", "medicina para la gripe"), ("Kfc", None)]:
        api.post("/transactions", {"transaction_type": "expense", "amount": "3", "description": desc, "notes": notes,
                                   "source_account_id": cuenta, "category_id": cat, "payment_method": "debit_card"})
    assert [t["description"] for t in api.get("/transactions?q=supermaxi").json()] == ["Supermaxi Norte"]
    assert [t["description"] for t in api.get("/transactions?q=GRIPE").json()] == ["Fybeca"]
    assert api.get("/transactions?q=nada-coincide").json() == []


def test_paginacion_sin_repetir(api):
    cuenta = api.account()
    cat = api.category()
    for i in range(7):
        api.post("/transactions", {"transaction_type": "expense", "amount": "1", "description": f"Gasto {i}",
                                   "source_account_id": cuenta, "category_id": cat, "payment_method": "debit_card"})
    primera = api.get("/transactions?limit=5&offset=0").json()
    segunda = api.get("/transactions?limit=5&offset=5").json()
    assert len(primera) == 5 and len(segunda) == 2
    assert not {t["id"] for t in primera} & {t["id"] for t in segunda}


def test_editar_cambiando_tipo_como_lo_envia_el_formulario(api):
    origen = api.account(name="Ahorros", balance="100")
    destino = api.account(name="Corriente", balance="0")
    tarjeta = api.card(balance="0")
    tx = api.post("/transactions", {"transaction_type": "expense", "amount": "20", "description": "compra",
                                    "card_id": tarjeta, "category_id": api.category(), "payment_method": "credit_card"}).json()
    assert api.card_balance(tarjeta) == 20.0
    # El formulario envía todos los campos; los que no aplican van en null
    r = api.put(f"/transactions/{tx['id']}", {
        "transaction_type": "transfer", "amount": "30.00", "currency": "USD", "description": "ahorro",
        "notes": None, "transaction_date": tx["transaction_date"], "category_id": None,
        "source_account_id": origen, "destination_account_id": destino, "card_id": None,
        "payment_method": "bank_transfer",
    })
    assert r.status_code == 200, r.text
    assert api.card_balance(tarjeta) == 0.0          # se revirtió el gasto con tarjeta
    assert api.account_balance(origen) == 70.0
    assert api.account_balance(destino) == 30.0
