"""
Autenticación y cuenta del usuario.

- Sesión web en cookie HttpOnly (ver app/auth/session.py); la API también acepta Bearer.
- Límite de intentos por IP y bloqueo por correo tras contraseñas incorrectas.
- Cada acción sensible queda en el registro de actividad (app/services/security_events.py).
"""

import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.auth.security import get_password_hash, issue_token, verify_password
from app.auth.session import end_session, renew_session, start_session
from app.config import get_settings
from app.database import get_db
from app.models.password_reset import PasswordResetToken
from app.models.pending import MerchantRule, PendingTransaction
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import (
    ChangePasswordRequest, DeleteAccountRequest, ForgotPasswordRequest, ResetPasswordRequest,
    UserAuthResponse, UserCreate, UserLogin, UserResponse, UserUpdate,
)
from app.security.rate_limiter import auth_rate_limiter, client_ip, failed_login_limiter
from app.services import email_service, security_events, user_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])
logger = logging.getLogger(__name__)
RESET_TTL = timedelta(minutes=30)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _apply_admin_list(user: User) -> None:
    """ADMIN_EMAILS decide quién es administrador (también para cuentas creadas después del arranque)."""
    emails = get_settings().admin_emails
    if emails:
        user.is_superuser = user.email.lower() in emails


def _limit_ip(request: Request, db: Session, email: str = None) -> None:
    """Límite por IP; si se supera, queda registrado."""
    try:
        auth_rate_limiter.check(request)
    except HTTPException:
        security_events.record(db, request, "rate_limited", email=email, detail=request.url.path)
        raise


def _check_credentials(request: Request, db: Session, email: str, password: str) -> User:
    """Valida correo y contraseña con bloqueo por intentos. Devuelve el usuario o lanza 401/403/429."""
    _limit_ip(request, db, email)
    email_key = email.strip().lower()
    try:
        failed_login_limiter.ensure_allowed(email_key)
    except HTTPException:
        security_events.record(db, request, "login_locked", email=email_key, detail="Intento durante el bloqueo")
        raise

    user = user_service.authenticate_user(db, email=email_key, password=password)
    if not user:
        known = user_service.get_user_by_email(db, email_key)
        security_events.record(db, request, "login_failed", user=known, email=email_key)
        try:
            failed_login_limiter.hit(email_key)
        except HTTPException:
            security_events.record(db, request, "login_locked", user=known, email=email_key,
                                   detail="Demasiadas contraseñas incorrectas")
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        security_events.record(db, request, "login_inactive", user=user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta de usuario está desactivada.")

    failed_login_limiter.reset(email_key)
    event = "login_new_ip" if security_events.is_new_ip(db, user.id, client_ip(request)) else "login_success"
    security_events.record(db, request, event, user=user, commit=False)
    user.last_login_at = datetime.now(timezone.utc)
    _apply_admin_list(user)
    db.commit()
    db.refresh(user)
    return user


# ------------------------------------------------------------------------------ Registro e inicio de sesión

@router.post("/register", response_model=UserAuthResponse, status_code=status.HTTP_201_CREATED,
             summary="Registrar un nuevo usuario")
def register(request: Request, response: Response, user_in: UserCreate, db: Session = Depends(get_db)):
    _limit_ip(request, db, user_in.email)
    if user_service.get_user_by_email(db, email=user_in.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El correo electrónico ya se encuentra registrado.")
    user = user_service.create_user(db, user_in)
    user.last_login_at = datetime.now(timezone.utc)
    _apply_admin_list(user)
    security_events.record(db, request, "register", user=user, commit=False)
    security_events.record(db, request, "login_success", user=user, commit=False)
    db.commit()
    db.refresh(user)
    token = start_session(response, user, remember=True)
    return UserAuthResponse(user=user, token=Token(access_token=token, token_type="bearer"),
                            message="Usuario registrado exitosamente.")


@router.post("/login", response_model=UserAuthResponse, summary="Iniciar sesión")
def login(request: Request, response: Response, credentials: UserLogin, db: Session = Depends(get_db)):
    user = _check_credentials(request, db, credentials.email, credentials.password)
    token = start_session(response, user, remember=credentials.remember)
    return UserAuthResponse(user=user, token=Token(access_token=token, token_type="bearer"),
                            message="Inicio de sesión exitoso.")


@router.post("/swagger-login", response_model=Token, summary="Login para Swagger UI (OAuth2 Form)")
def login_swagger(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _check_credentials(request, db, form_data.username, form_data.password)
    return Token(access_token=issue_token(user), token_type="bearer")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión en este dispositivo")
def logout(request: Request, db: Session = Depends(get_db)):
    from app.auth.dependencies import user_from_token
    from app.auth.session import read_token
    user = user_from_token(db, read_token(request)[0])
    if user:
        security_events.record(db, request, "logout", user=user)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    end_session(response)
    return response


# ------------------------------------------------------------------------------ Perfil

@router.get("/me", response_model=UserResponse, summary="Perfil del usuario autenticado")
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserResponse, summary="Actualizar el perfil")
def update_me(request: Request, response: Response, user_update: UserUpdate,
              current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    changing_password = bool(user_update.password)
    if changing_password:
        _limit_ip(request, db, current_user.email)
    user = user_service.update_user(db=db, user=current_user, user_in=user_update)
    if changing_password:
        security_events.record(db, request, "password_changed", user=user)
        renew_session(request, response, user)
    return user


@router.get("/me/activity", summary="Historial de accesos y cambios de seguridad de mi cuenta")
def my_activity(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    return [security_events.serialize(e) for e in security_events.for_user(db, current_user.id)]


# ------------------------------------------------------------------------------ Contraseña y sesiones

@router.post("/change-password", response_model=Token, summary="Cambiar contraseña")
def change_password(request: Request, response: Response, data: ChangePasswordRequest,
                    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _limit_ip(request, db, current_user.email)
    if not verify_password(data.current_password, current_user.hashed_password):
        security_events.record(db, request, "login_failed", user=current_user, detail="Contraseña actual incorrecta al cambiarla")
        raise HTTPException(status_code=400, detail="La contraseña actual no es correcta.")
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.token_version = (current_user.token_version or 0) + 1   # cierra las demás sesiones
    security_events.record(db, request, "password_changed", user=current_user, commit=False)
    db.commit()
    return Token(access_token=renew_session(request, response, current_user), token_type="bearer")


@router.post("/logout-all", response_model=Token, summary="Cerrar sesión en todos los demás dispositivos")
def logout_all(request: Request, response: Response,
               current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    current_user.token_version = (current_user.token_version or 0) + 1
    security_events.record(db, request, "logout_all", user=current_user, commit=False)
    db.commit()
    return Token(access_token=renew_session(request, response, current_user), token_type="bearer")


@router.post("/forgot-password", summary="Pedir un enlace para recuperar la contraseña")
def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Responde igual exista o no el correo (no revela qué correos están registrados)."""
    _limit_ip(request, db, data.email)
    enabled = email_service.email_enabled()
    user = user_service.get_user_by_email(db, email=data.email)
    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(user_id=user.id, token_hash=_hash_token(token),
                                  expires_at=datetime.now(timezone.utc) + RESET_TTL))
        security_events.record(db, request, "password_reset_requested", user=user, commit=False)
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
    return {"message": "Si el correo está registrado, te enviamos un enlace para crear una contraseña nueva.",
            "email_enabled": enabled}


@router.post("/reset-password", summary="Crear una contraseña nueva con el enlace recibido")
def reset_password(request: Request, data: ResetPasswordRequest, db: Session = Depends(get_db)):
    _limit_ip(request, db)
    invalid = HTTPException(status_code=400, detail="El enlace no es válido o ya caducó. Pide uno nuevo.")
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == _hash_token(data.token)).first()
    now = datetime.now(timezone.utc)
    if not record or record.used_at is not None or _aware(record.expires_at) < now:
        security_events.record(db, request, "password_reset_invalid")
        raise invalid
    user = user_service.get_user_by_id(db, user_id=record.user_id)
    if not user or not user.is_active:
        raise invalid
    user.hashed_password = get_password_hash(data.password)
    user.token_version = (user.token_version or 0) + 1
    record.used_at = now
    security_events.record(db, request, "password_reset_done", user=user, commit=False)
    db.commit()
    failed_login_limiter.reset(user.email)
    response = Response(content=json.dumps({"message": "Listo. Ya puedes iniciar sesión con tu contraseña nueva."}),
                        media_type="application/json")
    end_session(response)
    return response


# ------------------------------------------------------------------------------ Datos y cuenta

@router.get("/me/export", summary="Descargar mis datos (JSON)")
def export_my_data(request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
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
    security_events.record(db, request, "data_exported", user=current_user)
    return Response(content=json.dumps(data, ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="mis-datos-financialapp.json"'})


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar mi cuenta y todos mis datos")
def delete_my_account(request: Request, data: DeleteAccountRequest,
                      current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _limit_ip(request, db, current_user.email)
    if not verify_password(data.password, current_user.hashed_password):
        security_events.record(db, request, "login_failed", user=current_user, detail="Contraseña incorrecta al eliminar la cuenta")
        raise HTTPException(status_code=400, detail="La contraseña no es correcta.")
    security_events.record(db, request, "account_deleted", user=current_user, commit=False)
    for model in (PendingTransaction, MerchantRule, PasswordResetToken):
        db.query(model).filter(model.user_id == current_user.id).delete(synchronize_session=False)
    db.delete(current_user)   # cuentas, tarjetas, movimientos, categorías y presupuestos se eliminan en cascada
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    end_session(response)
    return response
