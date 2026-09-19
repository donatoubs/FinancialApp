"""
Middleware de Seguridad HTTP y Monitoreo de Rendimiento.
Inyecta cabeceras de seguridad recomendadas por OWASP.
"""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Inyecta cabeceras de seguridad HTTP en todas las respuestas para proteger la aplicación
    contra ataques XSS, Clickjacking, MIME-sniffing y filtración de datos de referencia.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000

        # Cabeceras de seguridad OWASP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Cabecera de rendimiento
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

        # Content-Security-Policy (Permite Bootstrap, Chart.js, Bootstrap Icons y scripts inline del dashboard)
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy

        return response
