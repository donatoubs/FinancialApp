"""
Middleware de seguridad HTTP.

- HTTPS forzado en producción (redirección 308 y HSTS).
- Content-Security-Policy con nonce por petición: el navegador solo ejecuta los scripts de la app
  (los que llevan el nonce de esa respuesta) y los de cdn.jsdelivr.net. Un script inyectado (XSS)
  no tiene el nonce y no se ejecuta; tampoco los atributos onclick="..." ni los enlaces javascript:.
- Cabeceras OWASP: nosniff, sin iframes de otros sitios, referrer limitado, permisos del navegador cerrados.
- Las respuestas de la API (datos personales) no se guardan en caché.
"""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, production: bool = False):
        super().__init__(app)
        self.production = production

    async def dispatch(self, request: Request, call_next) -> Response:
        # HTTPS obligatorio (Render termina TLS y avisa el protocolo original en X-Forwarded-Proto)
        if self.production and request.headers.get("x-forwarded-proto", "https") == "http":
            return RedirectResponse(str(request.url.replace(scheme="https")), status_code=308)

        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response: Response = await call_next(request)

        h = response.headers
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["X-XSS-Protection"] = "0"   # obsoleta; la protección real es la CSP
        h["Referrer-Policy"] = "strict-origin-when-cross-origin"
        h["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        h["Cross-Origin-Opener-Policy"] = "same-origin"
        if self.production:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.url.path.startswith("/api/"):
            h["Cache-Control"] = "no-store"

        if request.url.path.startswith(("/docs", "/redoc")):
            return response   # Swagger (solo en desarrollo) usa scripts propios en línea
        h["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
            "script-src-attr 'none'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
            + ("; upgrade-insecure-requests" if self.production else "")
        )
        return response
