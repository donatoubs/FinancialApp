"""
Dependencias de autenticación: usuario actual (cookie de sesión o cabecera Bearer) y administrador.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.auth.session import csrf_ok, read_token
from app.database import get_db
from app.models.user import User
from app.services import user_service

# Solo para que Swagger muestre el botón "Authorize"; el token se lee en read_token (cabecera o cookie)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/swagger-login", auto_error=False)


def user_from_token(db: Session, token: Optional[str]) -> Optional[User]:
    """Usuario dueño de un token válido y vigente, o None."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    user = user_service.get_user_by_id(db, user_id=user_id)
    # Sesiones cerradas a distancia, por cambio de contraseña o por el administrador
    if user is None or payload.get("tv", 0) != (user.token_version or 0):
        return None
    return user


def get_current_user(
    request: Request,
    _swagger: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    token, from_cookie = read_token(request)
    user = user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación inválidas o sesión expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not csrf_ok(request, from_cookie):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Petición rechazada (origen no verificado).")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="La cuenta de usuario está desactivada.")
    return current_user


def get_current_admin(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Solo administradores. A cualquier otro usuario se le responde 404 (como si la ruta no existiera)
    y el intento queda registrado como actividad sospechosa.
    """
    if not current_user.is_superuser:
        from app.services import security_events
        security_events.record(db, request, "admin_forbidden", user=current_user, detail=request.url.path)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return current_user
