"""
GESTIMA - Tests for error handling and transaction safety

Testy ověřují:
- Transaction rollback při chybách
- Logging při chybách
- Správné HTTP status kódy
- Ochrana proti data corruption
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException

from app.models.part import Part, PartCreate
from app.routers.parts_router import create_part, update_part, delete_part


@pytest.mark.asyncio
async def test_create_part_integrity_error_rollback():
    """Test: IntegrityError triggers rollback and returns 409"""
    # Arrange
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock(side_effect=IntegrityError("test", "test", "test"))
    db_mock.rollback = AsyncMock()

    data = PartCreate(part_number="TEST-001", name="Test Part")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_part(data, db_mock)

    assert exc_info.value.status_code == 409
    assert "Konflikt dat" in exc_info.value.detail
    db_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_create_part_sqlalchemy_error_rollback():
    """Test: SQLAlchemyError triggers rollback and returns 500"""
    # Arrange
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock(side_effect=SQLAlchemyError("Database error"))
    db_mock.rollback = AsyncMock()

    data = PartCreate(part_number="TEST-002", name="Test Part 2")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_part(data, db_mock)

    assert exc_info.value.status_code == 500
    assert "Chyba databáze" in exc_info.value.detail
    db_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_update_part_rollback_on_error():
    """Test: Update rollback when commit fails"""
    # Arrange
    db_mock = AsyncMock()
    existing_part = Part(id=1, part_number="TEST-003", name="Original")
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_part)))
    db_mock.commit = AsyncMock(side_effect=SQLAlchemyError("Commit failed"))
    db_mock.rollback = AsyncMock()

    from app.models.part import PartUpdate
    data = PartUpdate(name="Updated Name")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_part(1, data, db_mock)

    assert exc_info.value.status_code == 500
    db_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_delete_part_integrity_error_with_children():
    """Test: Delete fails with 409 when part has dependent records"""
    # Arrange
    db_mock = AsyncMock()
    existing_part = Part(id=1, part_number="TEST-004", name="Part with operations")
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_part)))
    db_mock.delete = AsyncMock()
    db_mock.commit = AsyncMock(side_effect=IntegrityError("Foreign key constraint", "test", "test"))
    db_mock.rollback = AsyncMock()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_part(1, db_mock)

    assert exc_info.value.status_code == 409
    assert "závislé záznamy" in exc_info.value.detail
    db_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_error_logging_on_integrity_error():
    """Test: Integrity errors are logged"""
    # Arrange
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock(side_effect=IntegrityError("test", "test", "test"))
    db_mock.rollback = AsyncMock()

    data = PartCreate(part_number="TEST-005", name="Test Part")

    # Act
    with patch('app.routers.parts_router.logger') as mock_logger:
        with pytest.raises(HTTPException):
            await create_part(data, db_mock)

        # Assert: logger.error was called
        mock_logger.error.assert_called()
        call_args = mock_logger.error.call_args
        assert "Integrity error" in str(call_args)


@pytest.mark.asyncio
async def test_success_logging_on_create():
    """Test: Successful operations are logged"""
    # Arrange
    db_mock = AsyncMock()

    # Mock execute to return None (no existing part)
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()

    # Mock refresh to set id on the part object
    async def mock_refresh(obj):
        obj.id = 1
    db_mock.refresh = mock_refresh

    data = PartCreate(part_number="TEST-006", name="Test Part")

    # Act
    with patch('app.routers.parts_router.logger') as mock_logger:
        result = await create_part(data, db_mock)

        # Assert: logger.info was called for success
        assert mock_logger.info.called
        call_args = str(mock_logger.info.call_args)
        assert "Created part" in call_args or "TEST-006" in call_args


@pytest.mark.asyncio
async def test_db_helpers_soft_delete_rollback():
    """Test: soft_delete rollbacks on error"""
    from app.db_helpers import soft_delete

    # Arrange
    db_mock = AsyncMock()
    db_mock.commit = AsyncMock(side_effect=SQLAlchemyError("Commit failed"))
    db_mock.rollback = AsyncMock()

    part = Part(id=1, part_number="TEST-007", name="Test")

    # Act & Assert
    with pytest.raises(SQLAlchemyError):
        await soft_delete(db_mock, part, deleted_by="test_user")

    db_mock.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_db_helpers_restore_rollback():
    """Test: restore rollbacks on error"""
    from app.db_helpers import restore

    # Arrange
    db_mock = AsyncMock()
    db_mock.commit = AsyncMock(side_effect=SQLAlchemyError("Commit failed"))
    db_mock.rollback = AsyncMock()

    part = Part(id=1, part_number="TEST-008", name="Test")

    # Act & Assert
    with pytest.raises(SQLAlchemyError):
        await restore(db_mock, part)

    db_mock.rollback.assert_called_once()


@pytest.mark.critical
@pytest.mark.asyncio
async def test_transaction_atomicity():
    """
    CRITICAL: Test that failed transactions don't leave partial changes

    Tento test ověřuje, že při chybě v commit() nedojde k partial update dat.
    """
    from app.models.part import PartCreate

    # Arrange
    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    original_part = Part(id=1, part_number="ORIGINAL", name="Original Name")
    db_mock.add = MagicMock()

    # Simulace: commit selže
    db_mock.commit = AsyncMock(side_effect=SQLAlchemyError("Transaction failed"))
    db_mock.rollback = AsyncMock()

    data = PartCreate(part_number="NEW", name="New Name")

    # Act
    with pytest.raises(HTTPException):
        await create_part(data, db_mock)

    # Assert: rollback MUSÍ být volán
    db_mock.rollback.assert_called_once()

    # Assert: v produkci by se mělo ověřit, že data v DB zůstala nezměněná
    # (toto nelze přímo testovat s mockem, ale princip je důležitý)
