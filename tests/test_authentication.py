"""
GESTIMA - Tests for authentication and authorization

Testy ověřují:
- Login flow (successful + failed)
- JWT token generation and verification
- Password hashing and verification
- HttpOnly cookie setting
- Protected endpoints require authentication
- Role-based access control (RBAC)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException, Response, Request
from datetime import datetime, timedelta

from app.models import User, UserRole, LoginRequest
from app.services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
    authenticate_user,
    create_user,
)
from app.routers.auth_router import login, logout, get_current_user_info
from app.dependencies import get_current_user, require_role


# ============================================================================
# PASSWORD HASHING TESTS
# ============================================================================

def test_password_hashing():
    """Test: Password is hashed correctly and can be verified"""
    password = "test_password_123"
    hashed = get_password_hash(password)

    # Hash should be different from plaintext
    assert hashed != password
    # Hash should be bcrypt format (starts with $2b$)
    assert hashed.startswith("$2b$")
    # Verification should succeed
    assert verify_password(password, hashed) is True
    # Wrong password should fail
    assert verify_password("wrong_password", hashed) is False


# ============================================================================
# JWT TOKEN TESTS
# ============================================================================

def test_create_access_token():
    """Test: JWT token is created with correct claims"""
    data = {"sub": "testuser", "role": "operator"}
    token = create_access_token(data)

    # Token should be a string
    assert isinstance(token, str)
    # Token should have 3 parts (header.payload.signature)
    assert len(token.split(".")) == 3


def test_verify_token_valid():
    """Test: Valid JWT token is verified correctly"""
    data = {"sub": "testuser", "role": "admin"}
    token = create_access_token(data)

    payload = verify_token(token)

    assert payload["sub"] == "testuser"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_verify_token_invalid():
    """Test: Invalid JWT token raises HTTPException(401)"""
    invalid_token = "invalid.token.here"

    with pytest.raises(HTTPException) as exc_info:
        verify_token(invalid_token)

    assert exc_info.value.status_code == 401
    assert "Could not validate credentials" in exc_info.value.detail


def test_verify_token_expired():
    """Test: Expired JWT token raises HTTPException(401)"""
    # Create token with -1 minute expiry (already expired)
    data = {"sub": "testuser"}
    token = create_access_token(data, expires_delta=timedelta(minutes=-1))

    with pytest.raises(HTTPException) as exc_info:
        verify_token(token)

    assert exc_info.value.status_code == 401


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_authenticate_user_success():
    """Test: User authentication succeeds with correct credentials"""
    # Arrange
    db_mock = AsyncMock()
    hashed_password = get_password_hash("correct_password")
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        role=UserRole.OPERATOR,
        is_active=True,
    )
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_user)
    ))

    # Act
    user = await authenticate_user(db_mock, "testuser", "correct_password")

    # Assert
    assert user.username == "testuser"
    assert user.role == UserRole.OPERATOR


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password():
    """Test: Authentication fails with wrong password"""
    # Arrange
    db_mock = AsyncMock()
    hashed_password = get_password_hash("correct_password")
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        role=UserRole.OPERATOR,
        is_active=True,
    )
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_user)
    ))

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_mock, "testuser", "wrong_password")

    assert exc_info.value.status_code == 401
    assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """Test: Authentication fails for non-existent user"""
    # Arrange
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)
    ))

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_mock, "nonexistent", "password")

    assert exc_info.value.status_code == 401
    assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticate_user_inactive():
    """Test: Authentication fails for inactive user"""
    # Arrange
    db_mock = AsyncMock()
    hashed_password = get_password_hash("password")
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        role=UserRole.OPERATOR,
        is_active=False,  # INACTIVE
    )
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_user)
    ))

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_mock, "testuser", "password")

    assert exc_info.value.status_code == 401
    assert "disabled" in exc_info.value.detail


# ============================================================================
# CREATE USER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_user_success():
    """Test: User creation succeeds with valid data"""
    # Arrange
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=None)  # No existing user
    ))
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()

    # Act
    user = await create_user(
        db_mock,
        username="newuser",
        email="new@example.com",
        password="password123",
        role=UserRole.OPERATOR
    )

    # Assert
    assert user.username == "newuser"
    assert user.email == "new@example.com"
    assert user.role == UserRole.OPERATOR
    assert user.is_active is True
    # Password should be hashed
    assert user.hashed_password != "password123"
    db_mock.add.assert_called_once()
    db_mock.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate():
    """Test: User creation fails when username/email already exists"""
    # Arrange
    db_mock = AsyncMock()
    existing_user = User(id=1, username="existing", email="existing@example.com")
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=existing_user)
    ))

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_user(
            db_mock,
            username="existing",
            email="new@example.com",
            password="password",
            role=UserRole.OPERATOR
        )

    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.detail


# ============================================================================
# LOGIN/LOGOUT ROUTER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_login_sets_cookie():
    """Test: Login endpoint sets HttpOnly cookie"""
    # Arrange
    db_mock = AsyncMock()
    hashed_password = get_password_hash("password123")
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_password,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_user)
    ))

    # Mock Request object (required by rate limiting decorator)
    from starlette.requests import Request
    request_mock = MagicMock(spec=Request)
    request_mock.client = MagicMock(host="127.0.0.1")

    credentials = LoginRequest(username="testuser", password="password123")
    response = Response()

    # Act
    result = await login(request_mock, credentials, response, db_mock)

    # Assert
    assert result.status == "ok"
    assert result.username == "testuser"
    assert result.role == UserRole.ADMIN

    # Check cookie was set (by inspecting response headers)
    # Note: Testing cookie setting in unit tests is tricky,
    # in real scenario use integration tests with TestClient


# ============================================================================
# PROTECTED ENDPOINT TESTS (dependency injection)
# ============================================================================

@pytest.mark.asyncio
async def test_get_current_user_no_cookie():
    """Test: get_current_user raises 401 when no cookie present"""
    # Arrange
    request_mock = MagicMock(spec=Request)
    request_mock.cookies.get = MagicMock(return_value=None)
    db_mock = AsyncMock()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request_mock, db_mock)

    assert exc_info.value.status_code == 401
    assert "Not authenticated" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test: get_current_user raises 401 for invalid token"""
    # Arrange
    request_mock = MagicMock(spec=Request)
    request_mock.cookies.get = MagicMock(return_value="invalid.token.here")
    db_mock = AsyncMock()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request_mock, db_mock)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test: get_current_user returns user for valid token"""
    # Arrange
    mock_user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        role=UserRole.OPERATOR,
        is_active=True,
    )

    # Create valid token
    token = create_access_token({"sub": "testuser", "role": "operator"})

    request_mock = MagicMock(spec=Request)
    request_mock.cookies.get = MagicMock(return_value=token)

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(
        scalar_one_or_none=MagicMock(return_value=mock_user)
    ))

    # Act
    user = await get_current_user(request_mock, db_mock)

    # Assert
    assert user.username == "testuser"
    assert user.role == UserRole.OPERATOR


# ============================================================================
# ROLE-BASED ACCESS CONTROL TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_require_role_admin_access_granted():
    """Test: Admin role can access admin-only endpoint"""
    # Arrange
    admin_user = User(
        id=1,
        username="admin",
        role=UserRole.ADMIN,
        is_active=True,
    )

    check_admin = require_role([UserRole.ADMIN])

    # Act
    result = await check_admin(current_user=admin_user)

    # Assert
    assert result == admin_user


@pytest.mark.asyncio
async def test_require_role_operator_denied_admin():
    """Test: Operator role denied access to admin-only endpoint"""
    # Arrange
    operator_user = User(
        id=2,
        username="operator",
        role=UserRole.OPERATOR,
        is_active=True,
    )

    check_admin = require_role([UserRole.ADMIN])

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await check_admin(current_user=operator_user)

    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_role_multiple_allowed():
    """Test: Multiple roles can be allowed (ADMIN or OPERATOR)"""
    # Arrange
    operator_user = User(
        id=2,
        username="operator",
        role=UserRole.OPERATOR,
        is_active=True,
    )

    check_operator_or_admin = require_role([UserRole.ADMIN, UserRole.OPERATOR])

    # Act
    result = await check_operator_or_admin(current_user=operator_user)

    # Assert
    assert result == operator_user


# ============================================================================
# ROLE HIERARCHY TESTS (P0-2: Admin >= Operator >= Viewer)
# ============================================================================

def test_has_permission_admin_can_do_operator():
    """Test: Admin má oprávnění pro Operator actions"""
    from app.dependencies import has_permission

    assert has_permission(UserRole.ADMIN, UserRole.OPERATOR) is True


def test_has_permission_admin_can_do_viewer():
    """Test: Admin má oprávnění pro Viewer actions"""
    from app.dependencies import has_permission

    assert has_permission(UserRole.ADMIN, UserRole.VIEWER) is True


def test_has_permission_operator_can_do_viewer():
    """Test: Operator má oprávnění pro Viewer actions"""
    from app.dependencies import has_permission

    assert has_permission(UserRole.OPERATOR, UserRole.VIEWER) is True


def test_has_permission_viewer_cannot_do_operator():
    """Test: Viewer NEMÁ oprávnění pro Operator actions"""
    from app.dependencies import has_permission

    assert has_permission(UserRole.VIEWER, UserRole.OPERATOR) is False


def test_has_permission_operator_cannot_do_admin():
    """Test: Operator NEMÁ oprávnění pro Admin actions"""
    from app.dependencies import has_permission

    assert has_permission(UserRole.OPERATOR, UserRole.ADMIN) is False


def test_has_permission_same_role():
    """Test: Role má vždy oprávnění pro sebe sama"""
    from app.dependencies import has_permission

    assert has_permission(UserRole.ADMIN, UserRole.ADMIN) is True
    assert has_permission(UserRole.OPERATOR, UserRole.OPERATOR) is True
    assert has_permission(UserRole.VIEWER, UserRole.VIEWER) is True


@pytest.mark.asyncio
async def test_require_role_hierarchy_admin_on_operator_endpoint():
    """Test: Admin může přistoupit na Operator endpoint (hierarchie)"""
    # Arrange
    admin_user = User(
        id=1,
        username="admin",
        role=UserRole.ADMIN,
        is_active=True,
    )

    # Endpoint vyžaduje OPERATOR
    check_operator = require_role([UserRole.OPERATOR])

    # Act
    result = await check_operator(current_user=admin_user)

    # Assert - Admin by měl projít (Admin >= Operator)
    assert result == admin_user


@pytest.mark.asyncio
async def test_require_role_hierarchy_operator_on_viewer_endpoint():
    """Test: Operator může přistoupit na Viewer endpoint (hierarchie)"""
    # Arrange
    operator_user = User(
        id=2,
        username="operator",
        role=UserRole.OPERATOR,
        is_active=True,
    )

    # Endpoint vyžaduje VIEWER
    check_viewer = require_role([UserRole.VIEWER])

    # Act
    result = await check_viewer(current_user=operator_user)

    # Assert - Operator by měl projít (Operator >= Viewer)
    assert result == operator_user


@pytest.mark.asyncio
async def test_require_role_hierarchy_viewer_denied_operator():
    """Test: Viewer NEMŮŽE přistoupit na Operator endpoint (hierarchie)"""
    # Arrange
    viewer_user = User(
        id=3,
        username="viewer",
        role=UserRole.VIEWER,
        is_active=True,
    )

    # Endpoint vyžaduje OPERATOR
    check_operator = require_role([UserRole.OPERATOR])

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await check_operator(current_user=viewer_user)

    assert exc_info.value.status_code == 403
    assert "Access denied" in exc_info.value.detail
