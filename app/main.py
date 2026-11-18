"""
Punto de entrada de FinancialApp (FastAPI).

Arranque: crea tablas, aplica migraciones simples, protege las tablas en Supabase (RLS),
sincroniza los administradores y limpia el registro de actividad antiguo.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

import app.models  # noqa: F401  (registra todos los modelos ORM)
from app.auth.dependencies import user_from_token
from app.auth.session import read_token
from app.config import get_settings
from app.database import Base, SessionLocal, check_db_connection, engine
from app.models.user import User
from app.routers import (
    accounts, admin, analytics, auth, budgets, cards, categories, dashboard, health, pending,
    transactions, webhooks,
)
from app.security.middleware import SecurityHeadersMiddleware
from app.services import category_service, security_events

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()
settings.validate_for_runtime()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

# Columnas agregadas después de crear las tablas (create_all no altera tablas existentes)
POSTGRES_MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_token VARCHAR(64);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_webhook_token ON users (webhook_token);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_auto_confirm BOOLEAN NOT NULL DEFAULT TRUE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(30);",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ;",
]


def _protect_postgres_tables(conn) -> None:
    """
    Supabase publica las tablas del esquema public en su API REST (con la clave "anon").
    Activar Row Level Security sin políticas deja esa vía cerrada: solo la app, que se conecta como
    dueña de las tablas, puede leer y escribir.
    """
    for table in Base.metadata.sorted_tables:
        conn.execute(text(f'ALTER TABLE "{table.name}" ENABLE ROW LEVEL SECURITY;'))  # nombres fijos del código
    # Los roles de la API de Supabase, si existen, quedan sin permisos sobre las tablas
    conn.execute(text("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
                EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated';
                EXECUTE 'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated';
            END IF;
        END $$;
    """))


def _sync_admins(db) -> None:
    """Administradores = correos de ADMIN_EMAILS. Sin la variable no se cambia nada."""
    emails = settings.admin_emails
    if not emails:
        return
    for user in db.query(User).all():
        should = user.email.lower() in emails
        if user.is_superuser != should:
            user.is_superuser = should
            logger.info("Administrador %s: %s", "concedido" if should else "retirado", user.email)
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando {settings.APP_NAME} en modo {settings.APP_ENV}...")
    db_check = check_db_connection()
    if db_check["status"] != "connected":
        logger.warning(f"Aviso de base de datos: {db_check['message']}. ({db_check['error']})")
        yield
        return
    try:
        Base.metadata.create_all(bind=engine)
        if engine.dialect.name == "postgresql":
            try:
                with engine.connect() as conn:
                    for statement in POSTGRES_MIGRATIONS:
                        conn.execute(text(statement))
                    _protect_postgres_tables(conn)
                    conn.commit()
            except Exception as exc:
                logger.error(f"Error aplicando migraciones o protección de tablas: {exc}")
        with SessionLocal() as db:
            category_service.seed_default_categories(db)
            _sync_admins(db)
            purged = security_events.purge_old(db)
            if purged:
                logger.info("Registro de actividad: %s eventos antiguos eliminados.", purged)
        logger.info("Base de datos lista.")
    except Exception as exc:
        logger.error(f"Error inicializando base de datos: {exc}")
    yield
    logger.info(f"Apagando {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="API REST y plataforma web para la gestión financiera personal",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    openapi_url="/openapi.json" if settings.ENABLE_DOCS else None,
)

app.add_middleware(SecurityHeadersMiddleware, production=settings.is_production)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,   # otros sitios nunca reciben la cookie de sesión
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Webhook-Token"],
    )

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))   # autoescape activo: el texto se muestra como texto

for router in (health, auth, accounts, cards, categories, transactions, dashboard, budgets, webhooks,
               pending, analytics, admin):
    app.include_router(router.router, prefix="/api/v1")


# ------------------------------------------------------------------------------ Páginas web

def _session_user(request: Request):
    with SessionLocal() as db:
        user = user_from_token(db, read_token(request)[0])
        if user is not None:
            db.expunge(user)
        return user


def _render(request: Request, template: str, active: str = "", user=None):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "app_name": settings.APP_NAME, "version": settings.VERSION, "active": active,
            "csp_nonce": getattr(request.state, "csp_nonce", ""),
            "current_user": user,
        },
    )


def _public_page(template: str, redirect_if_logged: bool):
    def handler(request: Request):
        if redirect_if_logged:
            user = _session_user(request)
            if user is not None and user.is_active:
                return RedirectResponse("/dashboard", status_code=303)
        return _render(request, template)
    return handler


def _private_page(template: str, active: str, admin_only: bool = False):
    """Sin sesión válida el servidor ni siquiera envía la página: redirige al inicio de sesión."""
    def handler(request: Request):
        user = _session_user(request)
        if user is None or not user.is_active:
            return RedirectResponse("/login", status_code=303)
        if admin_only and not user.is_superuser:
            with SessionLocal() as db:
                security_events.record(db, request, "admin_forbidden", user=user, detail=request.url.path)
            return Response("Not Found", status_code=404, media_type="text/plain")
        return _render(request, template, active, user)
    return handler


PUBLIC_PAGES = {
    "/login": ("login.html", True),
    "/register": ("register.html", True),
    "/forgot-password": ("forgot_password.html", False),
    "/reset-password": ("reset_password.html", False),
    "/terms": ("terms.html", False),
}
PRIVATE_PAGES = {
    "/dashboard": ("dashboard.html", "dashboard"),
    "/pending": ("pending.html", "pending"),
    "/transactions": ("transactions.html", "transactions"),
    "/accounts": ("accounts.html", "accounts"),
    "/cards": ("cards.html", "cards"),
    "/budgets": ("budgets.html", "budgets"),
    "/analytics": ("analytics.html", "analytics"),
    "/settings": ("settings.html", "settings"),
}
for _path, (_template, _redirect) in PUBLIC_PAGES.items():
    app.add_api_route(_path, _public_page(_template, _redirect), methods=["GET"],
                      response_class=HTMLResponse, include_in_schema=False)
for _path, (_template, _active) in PRIVATE_PAGES.items():
    app.add_api_route(_path, _private_page(_template, _active), methods=["GET"],
                      response_class=HTMLResponse, include_in_schema=False)
app.add_api_route("/admin", _private_page("admin.html", "admin", admin_only=True), methods=["GET"],
                  response_class=HTMLResponse, include_in_schema=False)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/dashboard")


@app.get("/api/v1", tags=["API Root"])
def api_root():
    return {"app_name": settings.APP_NAME, "version": settings.VERSION, "status": "online"}
