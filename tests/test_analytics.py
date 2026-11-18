"""Analíticas: comparación de meses, categorías, comercios y hábitos calculados de datos reales."""

from app.utils.dates import today_local


def _expense(api, account, desc, amount, day, cat):
    r = api.post("/transactions", {"transaction_type": "expense", "amount": str(amount), "description": desc,
                                   "source_account_id": account, "category_id": cat, "payment_method": "debit_card",
                                   "transaction_date": day})
    assert r.status_code == 201, r.text


def test_analiticas_del_mes(api):
    today = today_local()
    first = today.replace(day=1)
    prev_month_day = (first.replace(day=1) - __import__("datetime").timedelta(days=1)).replace(day=10)
    cuenta = api.account(balance="1000")
    comida = api.category("Alimentaci")
    _expense(api, cuenta, "Supermaxi", 50, first.isoformat(), comida)
    _expense(api, cuenta, "Supermaxi Norte", 30, first.isoformat(), comida)
    _expense(api, cuenta, "Fybeca", 20, first.isoformat(), api.category("Salud"))
    _expense(api, cuenta, "Supermaxi", 40, prev_month_day.isoformat(), comida)

    d = api.get(f"/analytics?month={today.month}&year={today.year}").json()
    assert d["summary"]["expense"] == 100.0
    assert d["summary"]["previous_expense"] == 40.0
    assert d["summary"]["expense_delta"] == 150.0
    assert len(d["history"]) == 12 and d["history"][-1]["expense"] == 100.0
    food = next(c for c in d["categories"] if c["name"].startswith("Alimentaci"))
    assert food["amount"] == 80.0 and food["previous"] == 40.0
    # "Supermaxi" y "Supermaxi Norte" son comercios distintos; el primero lidera
    assert d["top_merchants"][0]["name"] == "Supermaxi" and d["top_merchants"][0]["amount"] == 50.0
    assert d["habits"]["largest"]["amount"] == 50.0
    assert d["habits"]["expense_count"] == 3


def test_analiticas_de_otro_usuario_no_se_mezclan(api, other_api):
    cuenta = other_api.account(balance="100")
    _expense(other_api, cuenta, "Gasto ajeno", 99, today_local().isoformat(), other_api.category())
    assert api.get("/analytics").json()["summary"]["expense"] == 0.0


def test_pagina_analiticas_carga(client):
    assert client.get("/analytics").status_code == 200
