"""
Sesión web en una cookie HttpOnly.

El token nunca queda al alcance de JavaScript (ni en localStorage ni en document.cookie), así que
un script inyectado no puede robarlo. La cookie es:
- HttpOnly: invisible para JavaScript.
- Secure (en producción): solo viaja por HTTPS.
- SameSite=Lax: otros sitios no pueden enviarla en peticiones POST/PUT/DELETE.

Además, toda petición que modifica datos con la cookie debe traer la cabecera X-Requested-With,
que un formulario de otro sitio no puede añadir (protección CSRF adicional).

La API sigue aceptando "Authorization: Bearer <token>" para Swagger e integraciones.
"""

from datetime import timedelta
from typing import Optional, Tuple

from fastapi import Request, Response

from app.auth.security import issue_token
from app.config import get_settings

SESSION_COOKIE = "fa_session"
CSRF_HEADER = "X-Requested-With"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def session_lifetime(remember: bool) -> timedelta:
    settings = get_settings()
    return timedelta(days=settings.SESSION_REMEMBER_DAYS) if remember else timedelta(hours=settings.SESSION_HOURS)


def start_session(response: Response, user, remember: bool = True) -> str:
    """Emite el token y lo guarda en la cookie. Devuelve el token (para clientes de la API)."""
    lifetime = session_lifetime(remember)
    token = issue_token(user, expires_delta=lifetime, remember=remember)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(lifetime.total_seconds()) if remember else None,   # sin max_age: se borra al cerrar el navegador
        httponly=True,
        secure=get_settings().is_production,
        samesite="lax",
        path="/",
    )
    return token


def renew_session(request: Request, response: Response, user) -> str:
    """Tras invalidar las sesiones (nueva contraseña, cerrar sesiones), mantiene viva la de este dispositivo."""
    from app.auth.security import decode_access_token
    token, _ = read_token(request)
    payload = decode_access_token(token) if token else None
    return start_session(response, user, remember=bool(payload.get("rm", True)) if payload else True)


def end_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=get_settings().is_production, samesite="lax")


def read_token(request: Request) -> Tuple[Optional[str], bool]:
    """Token de la petición y si vino de la cookie (True) o de la cabecera Authorization (False)."""
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None, False
    cookie = request.cookies.get(SESSION_COOKIE)
    return (cookie or None), True


def csrf_ok(request: Request, from_cookie: bool) -> bool:
    """Las peticiones que modifican datos con cookie deben venir de la propia app."""
    if not from_cookie or request.method in SAFE_METHODS:
        return True
    return bool(request.headers.get(CSRF_HEADER))
