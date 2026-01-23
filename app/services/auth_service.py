"""GESTIMA - Autentizace a autorizace"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.config import settings
from app.models import User, UserRole

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Ověří heslo proti hashi"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Vytvoří bcrypt hash hesla"""
    return pwd_context.hash(password)


# ============================================================================
# JWT UTILITIES
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Vytvoří JWT token

    Args:
        data: Data pro JWT payload (musí obsahovat "sub" - username)
        expires_delta: Volitelná custom expiraci (default: 30 min z config)

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Ověří JWT token a vrátí payload

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict

    Raises:
        HTTPException(401): Pokud token není validní
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


# ============================================================================
# USER AUTHENTICATION
# ============================================================================

async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    """
    Autentizuje uživatele (username + password)

    Args:
        db: Database session
        username: Username
        password: Plain text password

    Returns:
        User object pokud autentizace uspěla

    Raises:
        HTTPException(401): Pokud autentizace selhala
    """
    # Najít uživatele
    result = await db.execute(
        select(User).where(
            User.username == username,
            User.deleted_at.is_(None)  # Soft delete check
        )
    )
    user = result.scalar_one_or_none()

    # Check existence
    if not user:
        logger.warning(f"Login attempt for non-existent user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Check password
    if not verify_password(password, user.hashed_password):
        logger.warning(f"Invalid password for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    logger.info(f"User authenticated: {username}")
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """
    Najde uživatele podle username

    Args:
        db: Database session
        username: Username

    Returns:
        User object nebo None
    """
    result = await db.execute(
        select(User).where(
            User.username == username,
            User.deleted_at.is_(None)
        )
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, username: str, email: str, password: str, role: UserRole) -> User:
    """
    Vytvoří nového uživatele

    Args:
        db: Database session
        username: Username (unique)
        email: Email (unique)
        password: Plain text password (bude hashováno)
        role: UserRole

    Returns:
        Vytvořený User object

    Raises:
        HTTPException(409): Pokud username nebo email již existuje
    """
    # Check duplicates
    existing = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    # Create user
    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        is_active=True,
        created_by="system",  # CLI create-admin command
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"User created: {username} (role: {role})")
    return user
