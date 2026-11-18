"""Seguridad: contraseña, bloqueo por intentos, token del webhook, CORS y configuración de producción."""

import pytest

from app.config import Settings
from tests.conftest import PASSWORD


def test_cambiar_contrasena_exige_la_actual(api):
    assert api.put("/auth/me", {"password": "NuevaClave456!"}).status_code == 400
    assert api.put("/auth/me", {"password": "NuevaClave456!", "current_password": "mala"}).status_code == 400
    assert api.put("/auth/me", {"full_name": "Solo Nombre"}).status_code == 200
    assert api.put("/auth/me", {"password": "NuevaClave456!", "current_password": PASSWORD}).status_code == 200
    r = api.client.post("/api/v1/auth/login", json={"email": api.email, "password": "NuevaClave456!"})
    assert r.status_code == 200


def test_bloqueo_por_correo_aunque_cambie_la_ip(api):
    codes = [
        api.client.post("/api/v1/auth/login", headers={"X-Forwarded-For": f"10.0.0.{i}"},
                        json={"email": api.email, "password": "incorrecta"}).status_code
        for i in range(6)
    ]
    assert codes == [401] * 5 + [429]
    # Ni con la contraseña correcta mientras dura el bloqueo
    assert api.client.post("/api/v1/auth/login", json={"email": api.email, "password": PASSWORD}).status_code == 429


def test_webhook_solo_acepta_el_token_en_la_cabecera(api):
    data = api.get("/webhooks/my-token").json()
    assert "token=" not in data["webhook_url"]
    r = api.client.post(f"/api/v1/webhooks/ios?token={data['webhook_token']}", json={"amount": 1, "merchant": "x"})
    assert r.status_code == 401
    assert api.hook({"amount": 1, "merchant": "Tienda"}, token=data["webhook_token"]).status_code == 201


def test_cors_cerrado_a_otros_origenes(client):
    r = client.get("/api/v1/health", headers={"Origin": "https://malicioso.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_produccion_rechaza_secret_key_debil():
    with pytest.raises(RuntimeError):
        Settings(_env_file=None, APP_ENV="production",
                 SECRET_KEY="cambiar_esta_clave_secreta_por_una_segura_en_produccion_123456789").validate_for_runtime()


def test_produccion_ignora_cors_comodin():
    s = Settings(_env_file=None, APP_ENV="production", SECRET_KEY="x" * 48, ALLOWED_ORIGINS="*,https://otro.example")
    s.validate_for_runtime()
    assert s.cors_origins == ["https://otro.example"]


def test_docs_y_debug_apagados_por_defecto():
    s = Settings(_env_file=None)
    assert s.ENABLE_DOCS is False
    assert s.DEBUG is False


def test_paginas_cargan_y_portada_redirige(client):
    assert client.get("/", follow_redirects=False).headers["location"] == "/dashboard"
    for path in ["/login", "/register", "/dashboard", "/pending", "/transactions", "/accounts", "/cards", "/budgets"]:
        assert client.get(path).status_code == 200, path
    pending = client.get("/pending").text
    assert "webhookToken" in pending and "Simular" not in pending
