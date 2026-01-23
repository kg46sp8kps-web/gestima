"""GESTIMA - FastAPI Dependencies"""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserRole
from app.services.auth_service import verify_token, get_user_by_username

logger = logging.getLogger(__name__)


# ============================================================================
# ROLE HIERARCHY
# ============================================================================

ROLE_HIERARCHY = {
    UserRole.ADMIN: 3,
    UserRole.OPERATOR: 2,
    UserRole.VIEWER: 1
}


def has_permission(user_role: UserRole, required_role: UserRole) -> bool:
    """
    Kontrola oprávnění podle hierarchie rolí.

    Admin >= Operator >= Viewer

    Args:
        user_role: Role uživatele
        required_role: Minimální požadovaná role

    Returns:
        True pokud user_role >= required_role

    Example:
        has_permission(UserRole.ADMIN, UserRole.OPERATOR) -> True
        has_permission(UserRole.VIEWER, UserRole.OPERATOR) -> False
    """
    return ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[required_role]


# ============================================================================
# AUTHENTICATION DEPENDENCY
# ============================================================================

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency: Vrátí aktuálního přihlášeného uživatele z JWT cookie

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException(401): Pokud není cookie nebo token není validní
    """
    # Read token from HttpOnly cookie
    token = request.cookies.get("access_token")

    if not token:
        logger.warning("No access_token cookie found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Verify JWT token
    payload = verify_token(token)  # Raises HTTPException(401) if invalid

    # Extract username from payload
    username: Optional[str] = payload.get("sub")
    if not username:
        logger.error("JWT payload missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    # Get user from database
    user = await get_user_by_username(db, username)
    if not user:
        logger.warning(f"User not found: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Check active
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    return user


# ============================================================================
# AUTHORIZATION DEPENDENCIES
# ============================================================================

def require_role(allowed_roles: list[UserRole]):
    """
    Dependency factory: Vytvoří dependency která kontroluje roli uživatele.

    Používá role hierarchy: Admin >= Operator >= Viewer
    (Admin může vše co Operator, Operator vše co Viewer)

    Args:
        allowed_roles: List povolených rolí (např. [UserRole.OPERATOR])
                      Uživatel musí mít alespoň nejnižší z uvedených rolí

    Returns:
        Dependency function

    Example:
        @router.put("/api/parts/{part_id}")
        async def update_part(
            current_user: User = Depends(require_role([UserRole.OPERATOR]))
        ):
            # Admin i Operator mohou editovat
            ...
    """
    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        # Najít minimální požadovanou roli z allowed_roles
        min_required_role = min(allowed_roles, key=lambda r: ROLE_HIERARCHY[r])

        # Kontrola oprávnění pomocí hierarchie
        if not has_permission(current_user.role, min_required_role):
            logger.warning(
                f"User {current_user.username} (role: {current_user.role}) "
                f"attempted unauthorized access (required: >={min_required_role.value})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {min_required_role.value} or higher",
            )
        return current_user

    return _check_role


# ============================================================================
# OPTIONAL AUTHENTICATION (pro public endpoints s optional user context)
# ============================================================================

async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency: Vrátí uživatele pokud je přihlášen, jinak None

    Užitečné pro endpointy které mohou být public ale mění chování podle user context

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User object nebo None
    """
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
