"""
Punto de entrada principal de la aplicación FastAPI.
Configuración de middleware CORS, montaje de archivos estáticos, plantillas Jinja2 y registro de enrutadores.
"""

from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.routers import health, auth, accounts, cards, categories, transactions, dashboard, budgets, webhooks
from app.database import engine, SessionLocal, Base, check_db_connection
from app.services import category_service
import app.models  # Asegura que todos los modelos ORM se registren

# Configuración básica de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Rutas del sistema de archivos para frontend
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación (inicio y apagado).
    Crea las tablas en PostgreSQL e inserta categorías por defecto si la base de datos está disponible.
    """
    logger.info(f"Iniciando {settings.APP_NAME} en modo {settings.APP_ENV}...")
    
    # Comprobación inicial y creación de tablas
    db_check = check_db_connection()
    if db_check["status"] == "connected":
        logger.info("Base de datos conectada correctamente. Creando tablas si no existen...")
        try:
            Base.metadata.create_all(bind=engine)

            # Migración automática segura para columnas nuevas en tablas existentes
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS webhook_token VARCHAR(64);"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_webhook_token ON users (webhook_token);"))
                conn.commit()

            logger.info("Esquemas de base de datos verificados y sincronizados.")
            
            # Sembrar categorías predeterminadas
            with SessionLocal() as db:
                category_service.seed_default_categories(db)
                logger.info("Categorías base del sistema inicializadas.")
        except Exception as exc:
            logger.error(f"Error inicializando base de datos: {exc}")
    else:
        logger.warning(f"Aviso de base de datos: {db_check['message']}. ({db_check['error']})")
    
    yield
    logger.info(f"Apagando {settings.APP_NAME}...")


# Instancia de FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API REST y Plataforma Web para la Gestión Financiera Personal",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None
)

from app.security.middleware import SecurityHeadersMiddleware

# Configuración de Middlewares de Seguridad y CORS
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de archivos estáticos
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configuración del motor de plantillas Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ------------------------------------------------------------------------------
# REGISTRO DE RUTAS / ENDPOINTS DE LA API REST
# ------------------------------------------------------------------------------

# Router de diagnóstico y healthcheck en /api/v1/health
app.include_router(health.router, prefix="/api/v1")

# Router de autenticación en /api/v1/auth
app.include_router(auth.router, prefix="/api/v1")

# Router de cuentas bancarias en /api/v1/accounts
app.include_router(accounts.router, prefix="/api/v1")

# Router de tarjetas de crédito y débito en /api/v1/cards
app.include_router(cards.router, prefix="/api/v1")

# Router de categorías en /api/v1/categories
app.include_router(categories.router, prefix="/api/v1")

# Router de movimientos financieros en /api/v1/transactions
app.include_router(transactions.router, prefix="/api/v1")

# Router del Dashboard en /api/v1/dashboard
app.include_router(dashboard.router, prefix="/api/v1")

# Router de Presupuestos y Reportes en /api/v1/budgets
app.include_router(budgets.router, prefix="/api/v1")

# Router de Webhooks para iOS (Apple Wallet & DeUna) en /api/v1/webhooks
app.include_router(webhooks.router, prefix="/api/v1")


# ------------------------------------------------------------------------------
# RUTAS DE INTERFAZ WEB (FRONTEND)
# ------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, summary="Página de inicio")
def home(request: Request):
    """
    Renderiza la interfaz inicial de la aplicación.
    """
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION,
            "env": settings.APP_ENV
        }
    )


@app.get("/login", response_class=HTMLResponse, summary="Página de Login")
def login_page(request: Request):
    """
    Renderiza la vista de inicio de sesión.
    """
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/register", response_class=HTMLResponse, summary="Página de Registro")
def register_page(request: Request):
    """
    Renderiza la vista de registro de usuario.
    """
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/dashboard", response_class=HTMLResponse, summary="Dashboard Principal")
def dashboard_page(request: Request):
    """
    Renderiza el Dashboard principal con gráficos, métricas y estadísticas consolidadas.
    """
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/accounts", response_class=HTMLResponse, summary="Gestión de Cuentas Bancarias")
def accounts_page(request: Request):
    """
    Renderiza el panel de gestión de cuentas bancarias y efectivo.
    """
    return templates.TemplateResponse(
        request=request,
        name="accounts.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/cards", response_class=HTMLResponse, summary="Gestión de Tarjetas")
def cards_page(request: Request):
    """
    Renderiza el panel de gestión de tarjetas de crédito y débito.
    """
    return templates.TemplateResponse(
        request=request,
        name="cards.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/transactions", response_class=HTMLResponse, summary="Gestión de Movimientos")
def transactions_page(request: Request):
    """
    Renderiza el panel de gestión de movimientos financieros.
    """
    return templates.TemplateResponse(
        request=request,
        name="transactions.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/budgets", response_class=HTMLResponse, summary="Gestión de Presupuestos y Reportes")
def budgets_page(request: Request):
    """
    Renderiza el panel de presupuestos mensuales, alertas y reportes financieros.
    """
    return templates.TemplateResponse(
        request=request,
        name="budgets.html",
        context={
            "app_name": settings.APP_NAME,
            "version": settings.VERSION
        }
    )


@app.get("/api/v1", tags=["API Root"])
def api_root():
    """
    Endpoint raíz de la API v1 con metadatos y enlaces de utilidad.
    """
    return {
        "app_name": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "auth_url": "/api/v1/auth",
        "accounts_url": "/api/v1/accounts",
        "cards_url": "/api/v1/cards",
        "categories_url": "/api/v1/categories",
        "transactions_url": "/api/v1/transactions",
        "dashboard_url": "/api/v1/dashboard",
        "budgets_url": "/api/v1/budgets"
    }
