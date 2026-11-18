"""Cuenta del usuario: contraseña, sesiones, recuperación por correo, exportar y eliminar."""

import re

from app.services import email_service
from tests.conftest import PASSWORD


def _login(client, email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_cambiar_contrasena_invalida_tokens_anteriores(api):
    old_headers = dict(api.headers)
    r = api.post("/auth/change-password", {"current_password": "mala", "new_password": "NuevaClave456!"})
    assert r.status_code == 400

    r = api.post("/auth/change-password", {"current_password": PASSWORD, "new_password": "NuevaClave456!"})
    assert r.status_code == 200, r.text
    new_token = r.json()["access_token"]

    # El token viejo ya no sirve; el nuevo sí
    assert api.client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    assert api.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200
    assert _login(api.client, api.email, PASSWORD).status_code == 401
    assert _login(api.client, api.email, "NuevaClave456!").status_code == 200


def test_cerrar_sesion_en_todos_los_dispositivos(api):
    other_device = _login(api.client, api.email, PASSWORD).json()["token"]["access_token"]
    r = api.post("/auth/logout-all")
    assert r.status_code == 200
    assert api.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other_device}"}).status_code == 401
    assert api.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).status_code == 200


def test_telefono_en_el_perfil(api):
    assert api.put("/auth/me", {"phone": "+593 99 123 4567"}).json()["phone"] == "+593 99 123 4567"
    assert api.put("/auth/me", {"phone": "<script>"}).status_code == 422


def test_recuperar_contrasena_con_enlace(api, monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "send_email", lambda to, subject, text: sent.append((to, text)) or True)
    session_token = dict(api.headers)

    r = api.client.post("/api/v1/auth/forgot-password", json={"email": api.email.upper()})
    assert r.status_code == 200
    assert len(sent) == 1 and sent[0][0] == api.email
    token = re.search(r"token=([\w-]+)", sent[0][1]).group(1)

    assert api.client.post("/api/v1/auth/reset-password", json={"token": "enlace-inventado-que-no-existe-123", "password": "OtraClave789!"}).status_code == 400
    assert api.client.post("/api/v1/auth/reset-password", json={"token": token, "password": "OtraClave789!"}).status_code == 200
    # El enlace solo sirve una vez y cierra las sesiones abiertas
    assert api.client.post("/api/v1/auth/reset-password", json={"token": token, "password": "OtraMas789!!"}).status_code == 400
    assert api.client.get("/api/v1/auth/me", headers=session_token).status_code == 401
    assert _login(api.client, api.email, "OtraClave789!").status_code == 200


def test_recuperar_no_revela_si_el_correo_existe(client, monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "send_email", lambda *a: sent.append(a) or True)
    r = client.post("/api/v1/auth/forgot-password", json={"email": "nadie-registrado@example.com"})
    assert r.status_code == 200
    assert "Si el correo está registrado" in r.json()["message"]
    assert sent == []


def test_exportar_mis_datos(api):
    api.account(name="Ahorros casa")
    r = api.get("/auth/me/export")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("content-disposition", "")
    data = r.json()
    assert data["perfil"]["correo"] == api.email
    assert [c["name"] for c in data["cuentas"]] == ["Ahorros casa"]


def test_eliminar_cuenta_exige_contrasena(api, other_api):
    api.account()
    api.hook({"amount": 3.5, "merchant": "Tienda"})
    assert api.client.request("DELETE", "/api/v1/auth/me", headers=api.headers, json={"password": "mala"}).status_code == 400
    r = api.client.request("DELETE", "/api/v1/auth/me", headers=api.headers, json={"password": PASSWORD})
    assert r.status_code == 204
    assert _login(api.client, api.email, PASSWORD).status_code == 401
    # Los datos de otros usuarios siguen intactos
    assert other_api.get("/auth/me").status_code == 200


def test_registro_exige_celular(client):
    base = {"email": "celular-obligatorio@example.com", "password": PASSWORD, "full_name": "Ana Pérez"}
    assert client.post("/api/v1/auth/register", json=base).status_code == 422
    assert client.post("/api/v1/auth/register", json={**base, "phone": "123"}).status_code == 422
    r = client.post("/api/v1/auth/register", json={**base, "phone": "099  123 4567"})
    assert r.status_code == 201, r.text
    assert r.json()["user"]["phone"] == "099 123 4567"
