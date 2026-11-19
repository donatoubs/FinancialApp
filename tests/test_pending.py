"""Bandeja de pendientes: webhook del iPhone, duplicados, aprendizaje por comercio y aislamiento."""


def _pending(api, pending_id):
    return next(p for p in api.get("/pending").json() if p["id"] == pending_id)


def test_sin_cuentas_el_pago_queda_pendiente(api):
    r = api.hook({"raw_text": "DeUna: Pagaste $2.50 a Cafetería Dulce Aroma", "source": "deuna"})
    assert r.status_code == 201
    assert r.json()["status"] == "pending"


def test_apple_pay_sugiere_tarjeta_y_categoria(api):
    visa = api.card(name="Visa Guayaquil", last4="4321")
    d = api.hook({"amount": "$3,75", "merchant": "Supermaxi La Carolina", "card": "Visa •••• 4321"}).json()
    assert d["status"] == "pending"
    p = _pending(api, d["pending_id"])
    assert p["suggested_card_id"] == visa
    assert p["suggested_category_name"].startswith("Alimentaci")
    assert p["suggested_rule_key"] == "Supermaxi"


def test_duplicado_se_ignora(api):
    body = {"amount": 10, "merchant": "Fybeca"}
    assert api.hook(body).json()["status"] == "pending"
    assert api.hook(body).json()["status"] == "duplicate"


def test_confirmar_aprende_y_el_siguiente_se_registra_solo(api):
    visa = api.card(name="Visa Guayaquil", last4="4321")
    d = api.hook({"amount": "3,75", "merchant": "Supermaxi La Carolina", "card": "4321"}).json()
    p = _pending(api, d["pending_id"])
    r = api.post(f"/pending/{p['id']}/confirm", {"amount": "3.75", "category_id": p["suggested_category_id"],
                                                 "card_id": visa, "description": "Supermaxi", "remember": True,
                                                 "remember_key": "Supermaxi"})
    assert r.status_code == 201
    assert api.card_balance(visa) == 3.75
    # No se puede confirmar dos veces
    assert api.post(f"/pending/{p['id']}/confirm", {"amount": "3.75", "category_id": p["suggested_category_id"],
                                                    "card_id": visa, "description": "x"}).status_code == 400
    # Otra sucursal del mismo comercio se registra sola
    d2 = api.hook({"amount": 10, "merchant": "SUPERMAXI EL BOSQUE"}).json()
    assert d2["status"] == "registered"
    assert api.card_balance(visa) == 13.75


def test_desactivar_registro_automatico(api):
    visa = api.card()
    d = api.hook({"amount": 5, "merchant": "Kywi Norte", "card": "4321"}).json()
    p = _pending(api, d["pending_id"])
    api.post(f"/pending/{p['id']}/confirm", {"amount": "5", "category_id": p["suggested_category_id"],
                                             "card_id": visa, "description": "Kywi", "remember_key": "Kywi"})
    api.put("/pending/settings", {"auto_confirm_known": False})
    assert api.hook({"amount": 6, "merchant": "Kywi Sur"}).json()["status"] == "pending"


def test_debito_descuenta_de_la_cuenta_vinculada(api):
    cuenta = api.account(name="Ahorros Pichincha")
    debito = api.card(name="Débito", card_type="debit", last4="9999", brand="Mastercard", account_id=cuenta, limit="0")
    d = api.hook({"raw_text": "DeUna: Pagaste a Juan Pérez, por $4.50 el 17/11", "source": "deuna"}).json()
    assert d["account_or_card"] == "Cuenta Ahorros Pichincha"
    p = _pending(api, d["pending_id"])
    r = api.post(f"/pending/{p['id']}/confirm", {"amount": "4.50", "category_id": p["suggested_category_id"],
                                                 "card_id": debito, "description": "Juan", "remember": False})
    assert r.status_code == 201
    assert api.account_balance(cuenta) == 95.5


def test_sin_monto_queda_pendiente_sin_inventar(api):
    d = api.hook({"raw_text": "Banco Pichincha: Consumo en KFC Quicentro", "source": "bank"}).json()
    assert d["amount"] is None
    assert d["status"] == "pending"


def test_atajo_con_categoria_elegida_registra_al_instante(api):
    api.card(last4="4321")
    d = api.hook({"amount": 1.25, "merchant": "Tienda Don Pepe", "category": "Otros Gastos",
                  "card": "4321", "auto_register": True}).json()
    assert d["status"] == "registered"
    assert d["category"] == "Otros Gastos"


def test_descartar_y_olvidar_regla(api):
    d = api.hook({"amount": 2, "merchant": "Tuti"}).json()
    assert api.post(f"/pending/{d['pending_id']}/discard").status_code == 200
    assert api.get("/pending/count").json()["pending"] == 0


def test_otro_usuario_no_ve_ni_toca_pendientes_ajenos(api, other_api):
    d = api.hook({"amount": 2, "merchant": "Tuti"}).json()
    assert other_api.get("/pending").json() == []
    assert other_api.post(f"/pending/{d['pending_id']}/discard").status_code == 404


def test_token_invalido(client):
    r = client.post("/api/v1/webhooks/ios", headers={"X-Webhook-Token": "fin_falso"}, json={"amount": 1, "merchant": "x"})
    assert r.status_code == 401


def test_recarga_deuna_se_confirma_como_transferencia(api):
    banco = api.account(name="Ahorros", balance="100.00")
    deuna = api.account(name="DeUna", bank="DeUna", balance="0.00", account_type="savings")
    r = api.hook({"raw_text": "✅ Recargaste $5,00\nRecargaste $5,00 en tu cuenta Deuna! el 18 nov 2026", "source": "deuna"})
    assert r.status_code == 201 and r.json()["status"] == "pending"
    p = next(x for x in api.get("/pending").json() if x["merchant"] == "Recarga DeUna")
    assert p["transaction_type"] == "transfer"

    # Sin cuenta destino no se puede confirmar
    bad = api.post(f"/pending/{p['id']}/confirm", {"transaction_type": "transfer", "amount": "5", "description": "Recarga DeUna",
                                                   "source_account_id": banco})
    assert bad.status_code == 400
    ok = api.post(f"/pending/{p['id']}/confirm", {"transaction_type": "transfer", "amount": "5", "description": "Recarga DeUna",
                                                  "source_account_id": banco, "destination_account_id": deuna})
    assert ok.status_code == 201, ok.text
    assert api.account_balance(banco) == 95.0
    assert api.account_balance(deuna) == 5.0


def test_atajo_deuna_pagaste_con_categoria_se_registra_en_la_cuenta_deuna(api):
    api.account(name="Ahorros", bank="Banco Guayaquil")
    deuna = api.account(name="DeUna", bank="DeUna", balance="20.00")
    d = api.hook({"raw_text": "✅ Pagaste $3,25\nPagaste $3,25 a Tienda Doña Rosa", "source": "deuna",
                  "category": "Alimentación", "auto_register": True}).json()
    assert d["status"] == "registered", d
    assert d["category"].startswith("Alimentaci")
    assert api.account_balance(deuna) == 16.75


def test_revisar_despues_no_cae_en_otros(api):
    api.account(name="DeUna", bank="DeUna")
    d = api.hook({"raw_text": "Pagaste $2,00 a Tienda X", "source": "deuna",
                  "category": "Revisar después", "auto_register": True}).json()
    assert d["status"] == "pending"
    assert "No encontré la categoría" in d["message"]


def test_ingreso_sin_categoria_no_se_registra_solo(api):
    api.account(name="DeUna", bank="DeUna")
    d = api.hook({"raw_text": "Recibiste $10,00 de Ana López", "source": "deuna",
                  "category": "", "auto_register": True}).json()
    assert d["status"] == "pending"


def test_sin_cuenta_deuna_avisa_por_que_queda_pendiente(api):
    api.account(name="Ahorros", bank="Banco Guayaquil")
    api.account(name="Corriente", bank="Produbanco")
    d = api.hook({"raw_text": "Pagaste $2,00 a Tienda X", "source": "deuna",
                  "category": "Alimentación", "auto_register": True}).json()
    assert d["status"] == "pending"
    assert "crea una cuenta llamada DeUna" in d["message"]
