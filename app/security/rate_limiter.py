"""
Módulo de Limitación de Tasa de Peticiones (Rate Limiting) en memoria para protección contra ataques de fuerza bruta y DDoS.
"""

import time
from collections import defaultdict
from typing import Dict, Tuple, List
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """
    Limitador de tasa basado en ventana deslizante (sliding window) por IP del cliente.
    """

    def __init__(self, requests_limit: int = 10, window_seconds: int = 60):
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        # Almacena una lista de marcas de tiempo por cada IP
        self._clients: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_requests(self, client_ip: str, now: float) -> None:
        """Elimina registros fuera de la ventana de tiempo."""
        cutoff = now - self.window_seconds
        self._clients[client_ip] = [ts for ts in self._clients[client_ip] if ts > cutoff]

    def check(self, request: Request, custom_limit: int = None, custom_window: int = None) -> None:
        """
        Comprueba si la petición actual excede el límite configurado.
        Lanza HTTPException(429 Too Many Requests) si se sobrepasa.
        """
        limit = custom_limit or self.requests_limit
        window = custom_window or self.window_seconds
        
        # Obtener IP del cliente (considerando proxies inversos como Nginx/Cloudflare)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"

        now = time.time()
        cutoff = now - window

        # Limpiar registros antiguos
        timestamps = [ts for ts in self._clients[client_ip] if ts > cutoff]
        
        if len(timestamps) >= limit:
            retry_after = int(window - (now - timestamps[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Límite de peticiones excedido. Intenta nuevamente en {retry_after} segundos.",
                headers={"Retry-After": str(max(1, retry_after))}
            )

        timestamps.append(now)
        self._clients[client_ip] = timestamps


# Limitador estricto para autenticación (10 intentos por minuto)
auth_rate_limiter = InMemoryRateLimiter(requests_limit=10, window_seconds=60)

# Limitador general para la API (120 peticiones por minuto)
api_rate_limiter = InMemoryRateLimiter(requests_limit=120, window_seconds=60)
