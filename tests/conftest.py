"""
Configuración común de pruebas: base SQLite temporal (nunca toca PostgreSQL),
cliente HTTP de FastAPI y ayudantes para crear usuarios, cuentas y tarjetas.

Ejecutar:  pytest
"""

import os
import tempfile
import uuid

import pytest

# La base de pruebas se define ANTES de importar la app (la configuración se lee al importar)
_DB_DIR = tempfile.mkdtemp(prefix="financialapp-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_DB_DIR, "test.db").replace("\\", "/")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "clave-solo-para-pruebas-" + "x" * 32)

from fastapi.testclient import TestClient  # noqa: E402

import app.main as main_module  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.security import rate_limiter  # noqa: E402
from app.services import category_service  # noqa: E402

PASSWORD = "Password123!"


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        category_service.seed_default_categories(db)
    # Sin "with": no se ejecuta el ciclo de vida (las migraciones ALTER son solo de PostgreSQL)
    return TestClient(main_module.app)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Cada prueba empieza sin intentos acumulados en los limitadores en memoria."""
    for limiter in (rate_limiter.auth_rate_limiter, rate_limiter.failed_login_limiter, rate_limiter.webhook_rate_limiter):
        limiter._hits.clear()
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


class Api:
    """Ayudante para llamar a la API como un usuario recién registrado."""

    def __init__(self, client: TestClient):
        self.client = client
        self.email = f"user-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/v1/auth/register", json={"email": self.email, "password": PASSWORD, "full_name": "Usuario Prueba"})
        assert r.status_code == 201, r.text
        self.headers = {"Authorization": "Bearer " + r.json()["token"]["access_token"]}

    def get(self, path, **kw):
        return self.client.get(f"/api/v1{path}", headers=self.headers, **kw)

    def post(self, path, json=None, **kw):
        return self.client.post(f"/api/v1{path}", headers=self.headers, json=json, **kw)

    def put(self, path, json=None):
        return self.client.put(f"/api/v1{path}", headers=self.headers, json=json)

    def delete(self, path):
        return self.client.delete(f"/api/v1{path}", headers=self.headers)

    def account(self, name="Ahorros", bank="Banco Pichincha", balance="100.00", account_type="savings"):
        r = self.post("/accounts", {"name": name, "bank_name": bank, "account_type": account_type, "current_balance": balance})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def card(self, name="Visa", card_type="credit", last4="4321", brand="Visa", balance="0", limit="1000", account_id=None):
        body = {"name": name, "bank_name": "Banco Guayaquil", "card_type": card_type, "card_brand": brand,
                "last_four_digits": last4, "credit_limit": limit, "current_balance": balance}
        if account_id:
            body["bank_account_id"] = account_id
        r = self.post("/cards", body)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def category(self, prefix="Alimentaci"):
        return next(c["id"] for c in self.get("/categories").json() if c["name"].startswith(prefix))

    def webhook_token(self):
        return self.get("/webhooks/my-token").json()["webhook_token"]

    def hook(self, body, token=None):
        return self.client.post("/api/v1/webhooks/ios", headers={"X-Webhook-Token": token or self.webhook_token()}, json=body)

    def card_balance(self, card_id):
        return float(next(c for c in self.get("/cards").json() if c["id"] == card_id)["current_balance"])

    def account_balance(self, account_id):
        return float(next(a for a in self.get("/accounts").json() if a["id"] == account_id)["current_balance"])


@pytest.fixture
def api(client):
    return Api(client)


@pytest.fixture
def other_api(client):
    return Api(client)
