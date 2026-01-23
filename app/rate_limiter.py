"""GESTIMA - Rate Limiting pomocí slowapi"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request

from app.config import settings


def get_user_or_ip(request: Request) -> str:
    """
    Identifikace klienta pro rate limiting.
    Pokud je uživatel přihlášen, použij user_id, jinak IP.
    """
    # Zkus získat user_id z request state (nastaveno auth middleware)
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"

    # Fallback na IP adresu
    return get_remote_address(request)


# Limiter instance
limiter = Limiter(
    key_func=get_user_or_ip,
    default_limits=[settings.RATE_LIMIT_DEFAULT] if settings.RATE_LIMIT_ENABLED else [],
    enabled=settings.RATE_LIMIT_ENABLED,
)


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Nastaví rate limiting na FastAPI aplikaci.

    Volat po vytvoření app instance v gestima_app.py.
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
