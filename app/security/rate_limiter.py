"""
Limitación de intentos en memoria (ventana deslizante).

- Por IP: login, registro, cambio de contraseña y webhook.
- Por correo: bloquea temporalmente una cuenta tras varios intentos fallidos de login,
  aunque el atacante cambie de IP.

Nota: el estado vive en memoria de cada proceso. Con varios workers cada uno cuenta por
separado (el límite efectivo se multiplica por el número de workers); para un uso
personal/familiar es suficiente. Para algo mayor, mover esto a Redis.
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import HTTPException, Request, status

from app.config import get_settings

MAX_TRACKED_KEYS = 10_000   # evita que la memoria crezca sin límite


def client_ip(request: Request) -> str:
    """
    IP del cliente. Solo se confía en X-Forwarded-For si TRUST_PROXY está activo (Render, Docker
    detrás de un proxy), y en ese caso se toma la ÚLTIMA IP de la lista: la que agregó el proxy
    propio. Las primeras las escribe el cliente y se pueden falsificar.
    """
    if get_settings().TRUST_PROXY:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


class InMemoryRateLimiter:
    def __init__(self, requests_limit: int, window_seconds: int, message: str = "Demasiados intentos."):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self.message = message
        self._hits: Dict[str, List[float]] = defaultdict(list)

    def _prune(self, now: float) -> None:
        if len(self._hits) < MAX_TRACKED_KEYS:
            return
        cutoff = now - self.window_seconds
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
            del self._hits[key]

    def _recent(self, key: str, now: float) -> List[float]:
        cutoff = now - self.window_seconds
        hits = [t for t in self._hits.get(key, []) if t > cutoff]
        if hits:
            self._hits[key] = hits
        else:
            self._hits.pop(key, None)
        return hits

    def _raise(self, oldest: float, now: float) -> None:
        retry_after = max(1, int(self.window_seconds - (now - oldest)) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{self.message} Intenta de nuevo en {retry_after} segundos.",
            headers={"Retry-After": str(retry_after)},
        )

    def hit(self, key: str) -> None:
        """Cuenta un intento para `key` y lanza 429 si ya superó el límite."""
        now = time.time()
        self._prune(now)
        hits = self._recent(key, now)
        if len(hits) >= self.requests_limit:
            self._raise(hits[0], now)
        hits.append(now)
        self._hits[key] = hits

    def check(self, request: Request) -> None:
        """Cuenta un intento para la IP de la petición."""
        self.hit(client_ip(request))

    def ensure_allowed(self, key: str) -> None:
        """Lanza 429 si `key` está bloqueada, sin contar un intento nuevo."""
        now = time.time()
        hits = self._recent(key, now)
        if len(hits) >= self.requests_limit:
            self._raise(hits[0], now)

    def reset(self, key: Optional[str]) -> None:
        if key:
            self._hits.pop(key, None)


# 10 intentos de login/registro por minuto y por IP
auth_rate_limiter = InMemoryRateLimiter(10, 60, "Demasiados intentos.")

# 5 contraseñas incorrectas por correo en 15 minutos bloquean esa cuenta temporalmente
failed_login_limiter = InMemoryRateLimiter(5, 15 * 60, "Demasiados intentos fallidos para esta cuenta.")

# 60 pagos por minuto y por IP desde los atajos del iPhone
webhook_rate_limiter = InMemoryRateLimiter(60, 60, "Demasiados envíos desde el atajo.")
