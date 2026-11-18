"""
Router de Autenticación y Gestión de Usuarios: Registro, Login, Swagger-Login y Perfil (Me).
Protegido con Limitador de Tasa de Peticiones (Rate Limiting).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserUpdate,
    UserResponse,
    UserAuthResponse
)
from app.auth.security import issue_token, verify_password
from app.auth.dependencies import get_current_active_user
from app.services import user_service
from app.security.rate_limiter import auth_rate_limiter, failed_login_limiter

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post(
    "/register",
    response_model=UserAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    description="Crea una nueva cuenta de usuario con contraseña cifrada y retorna un token JWT inicial."
)
def register(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    # Protección de rate limiting
    auth_rate_limiter.check(request)

    # Verificar si el correo ya está en uso
    existing_user = user_service.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya se encuentra registrado."
        )

    # Crear usuario
    user = user_service.create_user(db, user_in)

    # Generar token JWT de acceso
    access_token = issue_token(user)

    return UserAuthResponse(
        user=user,
        token=Token(access_token=access_token, token_type="bearer"),
        message="Usuario registrado exitosamente."
    )


@router.post(
    "/login",
    response_model=UserAuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión (JSON)",
    description="Autentica las credenciales del usuario y retorna un token JWT junto con su perfil."
)
def login_json(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    # Protección de rate limiting contra fuerza bruta
    auth_rate_limiter.check(request)
    email_key = credentials.email.strip().lower()
    failed_login_limiter.ensure_allowed(email_key)

    user = user_service.authenticate_user(db, email=credentials.email, password=credentials.password)
    if not user:
        failed_login_limiter.hit(email_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario está inactiva."
        )

    failed_login_limiter.reset(email_key)
    access_token = issue_token(user)

    return UserAuthResponse(
        user=user,
        token=Token(access_token=access_token, token_type="bearer"),
        message="Inicio de sesión exitoso."
    )


@router.post(
    "/swagger-login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Login para Swagger UI (OAuth2 Form)",
    description="Endpoint estándar de OAuth2 con datos de formulario para compatibilidad con el botón 'Authorize' de Swagger UI."
)
def login_swagger(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    auth_rate_limiter.check(request)
    email_key = form_data.username.strip().lower()
    failed_login_limiter.ensure_allowed(email_key)

    user = user_service.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        failed_login_limiter.hit(email_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo."
        )

    access_token = issue_token(user)
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtener perfil del usuario autenticado",
    description="Retorna la información del perfil del usuario validando el token JWT recibido en la cabecera."
)
def get_current_user_profile(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar perfil del usuario autenticado",
    description="Permite modificar el nombre completo o la moneda de preferencia del usuario."
)
def update_current_user_profile(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if user_update.password:
        # Mismo límite que el login: evita adivinar la contraseña actual por fuerza bruta
        auth_rate_limiter.check(request)
    return user_service.update_user(db=db, user=current_user, user_in=user_update)


# ------------------------------------------------------------------------------
# Contraseña, sesiones y cuenta
# ------------------------------------------------------------------------------
import hashlib  # noqa: E402
import json  # noqa: E402
import logging  # noqa: E402
import secrets  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.responses import Response  # noqa: E402

from app.auth.security import get_password_hash  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.models.password_reset import PasswordResetToken  # noqa: E402
from app.models.pending import MerchantRule, PendingTransaction  # noqa: E402
from app.schemas.user import (  # noqa: E402
    ChangePasswordRequest, DeleteAccountRequest, ForgotPasswordRequest, ResetPasswordRequest,
)
from app.services import email_service  # noqa: E402

logger = logging.getLogger(__name__)
RESET_TTL = timedelta(minutes=30)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


@router.post("/change-password", response_model=Token, summary="Cambiar contraseña")
def change_password(
    request: Request,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    auth_rate_limiter.check(request)
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1   # cierra las demás sesiones
    db.commit()
    return Token(access_token=issue_token(current_user), token_type="bearer")


@router.post("/logout-all", response_model=Token, summary="Cerrar sesión en todos los dispositivos")
def logout_all(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """Invalida todas las sesiones y devuelve un token nuevo para este dispositivo."""
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    return Token(access_token=issue_token(current_user), token_type="bearer")


@router.post("/forgot-password", summary="Pedir un enlace para recuperar la contraseña")
def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Responde igual exista o no el correo (no revela qué correos están registrados).
    `email_enabled` indica si este servidor puede enviar correos.
    """
    auth_rate_limiter.check(request)
    enabled = email_service.email_enabled()
    user = user_service.get_user_by_email(db, email=data.email.strip().lower())
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(user_id=user.id, token_hash=_hash_token(token),
                                  expires_at=datetime.now(timezone.utc) + RESET_TTL))
        db.commit()
        settings = get_settings()
        base = settings.PUBLIC_BASE_URL.rstrip("/") or str(request.base_url).rstrip("/")
        link = f"{base}/reset-password?token={token}"
        sent = email_service.send_email(
            user.email, "Recupera tu contraseña de FinancialApp",
            f"Hola {user.full_name},\n\nPara crear una contraseña nueva abre este enlace (vale 30 minutos):\n{link}\n\n"
            "Si no lo pediste, ignora este correo: tu contraseña no cambia.",
        )
        if not sent and not settings.is_production:
            # Solo en desarrollo: el enlace queda en el registro del servidor para poder probar el flujo
            logger.warning("Correo no configurado. Enlace de recuperación (solo desarrollo): %s", link)
    return {
        "message": "Si el correo está registrado, te enviamos un enlace para crear una contraseña nueva.",
        "email_enabled": enabled,
    }


@router.post("/reset-password", summary="Crear una contraseña nueva con el enlace recibido")
def reset_password(request: Request, data: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_rate_limiter.check(request)
    invalid = HTTPException(status_code=400, detail="El enlace no es válido o ya caducó. Pide uno nuevo.")
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash_token(data.token)).first()
    now = datetime.now(timezone.utc)
    if not record or record.used_at is not None or _aware(record.expires_at) < now:
        raise invalid
    user = user_service.get_user_by_id(db, user_id=record.user_id)
    if not user or not user.is_active:
        raise invalid
    user.hashed_password = get_password_hash(data.password)
    user.token_version = (user.token_version or 0) + 1
    record.used_at = now
    db.commit()
    failed_login_limiter.reset(user.email)
    return {"message": "Listo. Ya puedes iniciar sesión con tu contraseña nueva."}


@router.get("/me/export", summary="Descargar mis datos (JSON)")
def export_my_data(current_user: User = Depends(get_current_active_user)):
    """Toda la información personal y financiera del usuario en un archivo JSON."""
    def rows(items, fields):
        out = []
        for item in items:
            row = {}
            for f in fields:
                v = getattr(item, f)
                row[f] = v.value if hasattr(v, "value") else (str(v) if v is not None and not isinstance(v, (int, bool, str)) else v)
            out.append(row)
        return out

    data = {
        "exportado": datetime.now(timezone.utc).isoformat(),
        "perfil": {"nombre": current_user.full_name, "correo": current_user.email, "telefono": current_user.phone,
                   "moneda": current_user.currency_preference, "creado": current_user.created_at.isoformat()},
        "cuentas": rows(current_user.accounts, ["id", "name", "bank_name", "account_type", "current_balance", "currency", "is_active"]),
        "tarjetas": rows(current_user.cards, ["id", "name", "bank_name", "card_type", "card_brand", "last_four_digits", "credit_limit", "current_balance"]),
        "categorias_propias": rows(current_user.categories, ["id", "name", "category_type"]),
        "movimientos": rows(current_user.transactions, ["id", "transaction_date", "transaction_type", "amount", "currency", "description", "notes", "payment_method", "source_account_id", "destination_account_id", "card_id", "category_id"]),
        "presupuestos": rows(current_user.budgets, ["id", "category_id", "month", "year", "limit_amount"]),
    }
    return Response(content=json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="mis-datos-financialapp.json"'})


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar mi cuenta y todos mis datos")
def delete_my_account(
    request: Request,
    data: DeleteAccountRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    auth_rate_limiter.check(request)
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña no es correcta.")
    for model in (PendingTransaction, MerchantRule, PasswordResetToken):
        db.query(model).filter(model.user_id == current_user.id).delete(synchronize_session=False)
    db.delete(current_user)   # cuentas, tarjetas, movimientos, categorías y presupuestos se eliminan en cascada
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
