"""GESTIMA - Autentizace a autorizace"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
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


# ============================================================================
# PIN UTILITIES
# ============================================================================

def get_pin_hash(pin: str) -> str:
    """Vytvoří bcrypt hash PINu"""
    return pwd_context.hash(pin)


def get_pin_check(pin: str) -> str:
    """SHA256 hash PINu pro rychlý DB lookup (ne pro bezpečnost — bcrypt zůstává)."""
    return hashlib.sha256(pin.encode()).hexdigest()


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Ověří PIN proti hashi"""
    return pwd_context.verify(plain_pin, hashed_pin)


async def authenticate_user_by_pin(db: AsyncSession, pin: str) -> User:
    """
    Autentizuje uživatele pomocí PINu.

    Fast path: SHA256 lookup (pin_check) → 1 bcrypt verify (~250ms).
    Fallback: pro uživatele bez pin_check (pre-migrace) → N-iteration + lazy backfill.
    """
    pin_sha = get_pin_check(pin)

    # Fast path: lookup by pin_check (SHA256)
    result = await db.execute(
        select(User).where(
            User.is_active == True,
            User.pin_check == pin_sha,
            User.deleted_at.is_(None),
        )
    )
    fast_matches = list(result.scalars().all())

    # Bcrypt verify fast-path matches
    matched = [u for u in fast_matches if verify_pin(pin, u.pin_hash)]

    # Fallback: users with pin_hash but no pin_check (pre-migration, lazy backfill)
    if not matched:
        fallback_result = await db.execute(
            select(User).where(
                User.is_active == True,
                User.pin_hash.isnot(None),
                User.pin_check.is_(None),
                User.deleted_at.is_(None),
            )
        )
        fallback_users = list(fallback_result.scalars().all())
        for user in fallback_users:
            if verify_pin(pin, user.pin_hash):
                user.pin_check = pin_sha
                matched.append(user)
        # Single commit for all backfills
        if any(u.pin_check for u in fallback_users if u.pin_check is not None):
            await db.commit()
            logger.info("Lazy backfill pin_check for %d user(s)", len(matched))

    if len(matched) == 0:
        logger.warning("PIN login attempt failed: no matching user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neplatný PIN",
        )

    if len(matched) > 1:
        logger.error(f"PIN collision detected for users: {[u.username for u in matched]}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="PIN kolize — kontaktujte administrátora",
        )

    user = matched[0]
    logger.info(f"User authenticated by PIN: {user.username}")
    return user


async def backfill_pin_checks(db: AsyncSession) -> int:
    """Eagerly backfill pin_check for all users — call from admin or startup.

    Cannot derive PIN from bcrypt hash, so this only works for users whose
    pin_check was already set via lazy backfill or admin PIN set.
    Returns count of users still missing pin_check (need to re-set PIN via admin).
    """
    result = await db.execute(
        select(User).where(
            User.pin_hash.isnot(None),
            User.pin_check.is_(None),
            User.deleted_at.is_(None),
        )
    )
    orphans = list(result.scalars().all())
    if orphans:
        logger.warning(
            "Users with pin_hash but no pin_check (need admin PIN re-set): %s",
            [u.username for u in orphans],
        )
    return len(orphans)


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


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    role: UserRole,
    email: Optional[str] = None
) -> User:
    """
    Vytvoří nového uživatele

    Args:
        db: Database session
        username: Username (unique)
        password: Plain text password (bude hashováno)
        role: UserRole
        email: Email (optional)

    Returns:
        Vytvořený User object

    Raises:
        HTTPException(409): Pokud username již existuje
    """
    # Check duplicate username
    existing = await db.execute(
        select(User).where(User.username == username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # Check duplicate email (only if provided)
    if email:
        existing_email = await db.execute(
            select(User).where(User.email == email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
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

    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"User created: {username} (role: {role})")
        return user
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError creating user {username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists (duplicate username or email)",
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(f"Database error creating user {username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating user",
        )
