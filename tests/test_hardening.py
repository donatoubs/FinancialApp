"""Blindaje: sesión en cookie HttpOnly, CSRF, CSP, panel de administración y registro de actividad."""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.models.security_event import SecurityEvent
from app.models.user import User
from tests.conftest import PASSWORD

CSRF = {"X-Requested-With": "FinancialApp"}


@pytest.fixture
def browser(client):
    """Navegador nuevo (sin cookies compartidas con otras pruebas)."""
    return TestClient(main_module.app)


def _register(browser, email=None):
    email = email or f"web-{uuid.uuid4().hex[:8]}@example.com"
    r = browser.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD, "full_name": "Persona Web", "phone": "0991234567"})
    assert r.status_code == 201, r.text
    return email


# ------------------------------------------------------------------ Sesión en cookie

def test_login_pone_cookie_httponly(browser):
    email = _register(browser)
    browser.cookies.clear()
    r = browser.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD, "remember": False})
    cookie = r.headers["set-cookie"]
    assert "fa_session=" in cookie and "HttpOnly" in cookie and "samesite=lax" in cookie.lower()
    assert "Max-Age" not in cookie   # sin "mantener sesión": se borra al cerrar el navegador
    assert browser.get("/api/v1/auth/me").status_code == 200


def test_cookie_sin_cabecera_csrf_no_puede_modificar(browser):
    _register(browser)
    assert browser.put("/api/v1/auth/me", json={"full_name": "Atacante"}).status_code == 403
    assert browser.put("/api/v1/auth/me", json={"full_name": "Yo Mismo"}, headers=CSRF).status_code == 200


def test_logout_borra_la_cookie(browser):
    _register(browser)
    assert browser.post("/api/v1/auth/logout", headers=CSRF).status_code == 204
    assert browser.get("/api/v1/auth/me").status_code == 401


def test_paginas_privadas_redirigen_sin_sesion(browser):
    r = browser.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    _register(browser)
    assert browser.get("/dashboard").status_code == 200
    # Con sesión, el login lleva directo al resumen
    assert browser.get("/login", follow_redirects=False).headers["location"] == "/dashboard"


def test_cambiar_contrasena_mantiene_esta_sesion_y_cierra_las_demas(browser, client):
    email = _register(browser)
    other = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()["token"]["access_token"]
    r = browser.post("/api/v1/auth/change-password", json={"current_password": PASSWORD, "new_password": "OtraClave789x"}, headers=CSRF)
    assert r.status_code == 200
    assert browser.get("/api/v1/auth/me").status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {other}"}).status_code == 401


# ------------------------------------------------------------------ Contraseñas y datos de entrada

@pytest.mark.parametrize("bad", ["solamenteletras", "12345678", "password123", "aaaa1111"])
def test_contrasenas_debiles_rechazadas(client, bad):
    r = client.post("/api/v1/auth/register", json={"email": f"d-{uuid.uuid4().hex[:6]}@example.com", "password": bad,
                                                   "full_name": "Débil", "phone": "0991234567"})
    assert r.status_code == 422


def test_color_e_icono_no_aceptan_html(api):
    assert api.post("/categories", {"name": "Mala", "category_type": "expense", "color": '#000"><img src=x>', "icon": "bi-tag"}).status_code == 422
    assert api.post("/categories", {"name": "Mala", "category_type": "expense", "color": "#112233", "icon": 'bi-tag" onmouseover="x'}).status_code == 422
    assert api.post("/categories", {"name": "Buena", "category_type": "expense", "color": "#112233", "icon": "bi-cup-hot"}).status_code == 201


# ------------------------------------------------------------------ Cabeceras

def test_csp_con_nonce_sin_unsafe_inline_en_scripts(browser):
    r = browser.get("/login")
    csp = r.headers["content-security-policy"]
    nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
    script_src = re.search(r"script-src ([^;]+)", csp).group(1)
    assert "unsafe-inline" not in script_src
    assert f'nonce="{nonce}"' in r.text
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_api_no_se_guarda_en_cache(api):
    assert api.get("/auth/me").headers["cache-control"] == "no-store"


# ------------------------------------------------------------------ Registro de actividad

def test_eventos_de_login_y_historial(api, db):
    api.client.post("/api/v1/auth/login", json={"email": api.email, "password": "incorrecta1"})
    api.client.post("/api/v1/auth/login", json={"email": api.email, "password": PASSWORD})
    types = [e["event_type"] for e in api.get("/auth/me/activity").json()]
    assert "login_failed" in types and any(t in types for t in ("login_success", "login_new_ip"))
    failed = db.query(SecurityEvent).filter(SecurityEvent.email == api.email, SecurityEvent.event_type == "login_failed").first()
    assert failed.severity == "warning"


def test_bloqueo_queda_registrado_como_critico(api, db):
    for _ in range(6):
        api.client.post("/api/v1/auth/login", json={"email": api.email, "password": "incorrecta1"})
    ev = db.query(SecurityEvent).filter(SecurityEvent.email == api.email, SecurityEvent.event_type == "login_locked").first()
    assert ev is not None and ev.severity == "critical"


def test_tokens_del_atajo_invalidos_bloquean_la_ip(api):
    codes = [api.hook({"amount": 1, "merchant": "x"}, token=f"falso-{i}").status_code for i in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


# ------------------------------------------------------------------ Panel de administración

def _make_admin(db, email):
    user = db.query(User).filter(User.email == email).first()
    user.is_superuser = True
    db.commit()


def test_rutas_admin_invisibles_para_usuarios_normales(api, db):
    assert api.get("/admin/overview").status_code == 404
    assert api.get("/admin/users").status_code == 404
    ev = db.query(SecurityEvent).filter(SecurityEvent.email == api.email, SecurityEvent.event_type == "admin_forbidden").first()
    assert ev is not None and ev.severity == "critical"


def test_pagina_admin_404_para_usuario_normal(browser):
    _register(browser)
    assert browser.get("/admin").status_code == 404


def test_admin_ve_resumen_y_desactiva_cuentas(api, other_api, db):
    _make_admin(db, api.email)
    overview = api.get("/admin/overview").json()
    assert overview["users"]["total"] >= 2
    users = api.get(f"/admin/users?q={other_api.email}").json()
    target = users["items"][0]
    assert target["email"] == other_api.email and "transactions" in target
    assert "current_balance" not in str(users)   # sin montos de otras personas

    assert api.post(f"/admin/users/{target['id']}/deactivate").status_code == 200
    assert other_api.get("/auth/me").status_code == 401          # sus sesiones se cerraron
    r = other_api.client.post("/api/v1/auth/login", json={"email": other_api.email, "password": PASSWORD})
    assert r.status_code == 403
    assert api.post(f"/admin/users/{target['id']}/activate").status_code == 200
    r = other_api.client.post("/api/v1/auth/login", json={"email": other_api.email, "password": PASSWORD})
    assert r.status_code == 200
    # Ve en su historial que un administrador actuó
    other_api.headers = {"Authorization": "Bearer " + r.json()["token"]["access_token"]}
    assert any(e["event_type"] == "admin_user_deactivated" for e in other_api.get("/auth/me/activity").json())


def test_admin_no_puede_desactivarse_a_si_mismo(api, db):
    _make_admin(db, api.email)
    me = api.get("/auth/me").json()
    assert api.post(f"/admin/users/{me['id']}/deactivate").status_code == 400
