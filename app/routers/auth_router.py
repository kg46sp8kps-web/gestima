"""GESTIMA - Authentication Router"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user, create_access_token
from app.config import settings
from app.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    credentials: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Přihlášení uživatele (username + password)

    - Ověří credentials
    - Vytvoří JWT token
    - Nastaví HttpOnly cookie
    - Vrátí status + user info
    """
    try:
        # Authenticate
        user = await authenticate_user(db, credentials.username, credentials.password)

        # Create JWT token
        access_token = create_access_token(
            data={"sub": user.username, "role": user.role.value}
        )

        # Set HttpOnly cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,                          # XSS protection
            secure=settings.SECURE_COOKIE,          # HTTPS only v produkci
            samesite="strict",                      # CSRF protection
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        logger.info(f"User logged in: {user.username}")

        return TokenResponse(
            status="ok",
            username=user.username,
            role=user.role
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při přihlašování")


# ============================================================================
# LOGOUT
# ============================================================================

@router.post("/logout")
async def logout(response: Response):
    """
    Odhlášení uživatele

    - Smaže HttpOnly cookie
    """
    try:
        response.delete_cookie(key="access_token")
        logger.info("User logged out")

        return {"status": "ok", "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba při odhlašování")


# ============================================================================
# CURRENT USER INFO
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Vrátí informace o aktuálně přihlášeném uživateli

    - Vyžaduje validní JWT cookie
    """
    return current_user
