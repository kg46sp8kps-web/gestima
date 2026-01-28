"""
GESTIMA - Tests for optimistic locking (ADR-008)

Testy ověřují:
- Version check při concurrent updates
- HTTP 409 při version konfliktu
- Auto-increment version při úspěšném update
- Ochrana před data loss při souběžné editaci
"""

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from app.models.part import Part, PartUpdate
from app.models.operation import Operation, OperationUpdate, ChangeModeRequest, CuttingMode
from app.models.feature import Feature, FeatureUpdate
from app.models.material import MaterialGroup, MaterialItem
from app.models.enums import StockShape, FeatureType
from app.routers.parts_router import update_part
from app.routers.operations_router import update_operation, change_mode
from app.routers.features_router import update_feature
from app.models import User, UserRole


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        role=UserRole.OPERATOR,
        hashed_password="fake_hash"
    )


@pytest_asyncio.fixture
async def sample_part(db_session):
    """Create a sample part for testing"""
    # Use materials already seeded by conftest's db_session fixture
    part = Part(
        part_number="1000001",
        name="Test Part",
        material_item_id=db_session.test_material_item.id,
        created_by="testuser",
        updated_by="testuser"
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    return part


@pytest_asyncio.fixture
async def sample_operation(db_session, sample_part):
    """Create a sample operation for testing"""
    operation = Operation(
        part_id=sample_part.id,
        seq=10,
        name="Test Operation",
        type="turning",
        cutting_mode="mid",
        created_by="testuser",
        updated_by="testuser"
    )
    db_session.add(operation)
    await db_session.commit()
    await db_session.refresh(operation)
    return operation


@pytest_asyncio.fixture
async def sample_feature(db_session, sample_operation):
    """Create a sample feature for testing"""
    feature = Feature(
        operation_id=sample_operation.id,
        seq=1,
        feature_type=FeatureType.FACE,
        from_diameter=50.0,
        to_diameter=48.0,
        length=10.0,
        created_by="testuser",
        updated_by="testuser"
    )
    db_session.add(feature)
    await db_session.commit()
    await db_session.refresh(feature)
    return feature


# ============================================================================
# PART OPTIMISTIC LOCKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_part_update_success_increments_version(db_session, sample_part, mock_user):
    """Test: Successful update increments version"""
    initial_version = sample_part.version

    update_data = PartUpdate(
        name="Updated Name",
        version=initial_version
    )

    updated_part = await update_part(sample_part.part_number, update_data, db_session, mock_user)

    assert updated_part.name == "Updated Name"
    assert updated_part.version == initial_version + 1


@pytest.mark.asyncio
async def test_part_update_version_conflict_raises_409(db_session, sample_part, mock_user):
    """Test: Update with outdated version raises HTTP 409"""
    # Simulate another user updating the part
    sample_part.name = "Changed by other user"
    sample_part.version += 1
    await db_session.commit()

    # Try to update with old version (should fail)
    update_data = PartUpdate(
        name="My update",
        version=0  # Outdated version
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_part(sample_part.part_number, update_data, db_session, mock_user)

    assert exc_info.value.status_code == 409
    assert "změněna jiným uživatelem" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_part_concurrent_updates_one_fails(db_session, sample_part, mock_user):
    """Test: Concurrent updates - second one fails with 409"""
    initial_version = sample_part.version

    # First update (succeeds)
    update_data_1 = PartUpdate(
        name="Update 1",
        version=initial_version
    )
    updated_1 = await update_part(sample_part.part_number, update_data_1, db_session, mock_user)
    assert updated_1.version == initial_version + 1

    # Second update with old version (fails)
    update_data_2 = PartUpdate(
        name="Update 2",
        version=initial_version  # Stale version
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_part(sample_part.part_number, update_data_2, db_session, mock_user)

    assert exc_info.value.status_code == 409


# ============================================================================
# OPERATION OPTIMISTIC LOCKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_operation_update_success_increments_version(db_session, sample_operation, mock_user):
    """Test: Successful operation update increments version"""
    initial_version = sample_operation.version

    update_data = OperationUpdate(
        name="Updated Operation",
        version=initial_version
    )

    updated_op = await update_operation(sample_operation.id, update_data, db_session, mock_user)

    assert updated_op.name == "Updated Operation"
    assert updated_op.version == initial_version + 1


@pytest.mark.asyncio
async def test_operation_update_version_conflict_raises_409(db_session, sample_operation, mock_user):
    """Test: Operation update with outdated version raises HTTP 409"""
    # Simulate another update
    sample_operation.name = "Changed by other user"
    sample_operation.version += 1
    await db_session.commit()

    # Try to update with old version
    update_data = OperationUpdate(
        name="My update",
        version=0  # Outdated
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_operation(sample_operation.id, update_data, db_session, mock_user)

    assert exc_info.value.status_code == 409
    assert "změněna jiným uživatelem" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_operation_change_mode_version_check(db_session, sample_operation, mock_user):
    """Test: Change mode endpoint checks version"""
    initial_version = sample_operation.version

    # Simulate another update
    sample_operation.cutting_mode = "high"
    sample_operation.version += 1
    await db_session.commit()

    # Try to change mode with old version (using Pydantic model)
    data = ChangeModeRequest(
        cutting_mode=CuttingMode.LOW,
        version=initial_version  # Outdated
    )

    with pytest.raises(HTTPException) as exc_info:
        await change_mode(sample_operation.id, data, db_session, mock_user)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_operation_change_mode_missing_version_raises_validation_error(db_session, sample_operation, mock_user):
    """Test: Change mode without version raises Pydantic ValidationError"""
    from pydantic import ValidationError

    # Missing version field triggers Pydantic validation
    with pytest.raises(ValidationError) as exc_info:
        ChangeModeRequest(cutting_mode=CuttingMode.LOW)  # version missing

    assert "version" in str(exc_info.value).lower()


# ============================================================================
# FEATURE OPTIMISTIC LOCKING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_feature_update_success_increments_version(db_session, sample_feature, mock_user):
    """Test: Successful feature update increments version"""
    initial_version = sample_feature.version

    update_data = FeatureUpdate(
        length=15.0,
        version=initial_version
    )

    updated_feature = await update_feature(sample_feature.id, update_data, db_session, mock_user)

    assert updated_feature.length == 15.0
    assert updated_feature.version == initial_version + 1


@pytest.mark.asyncio
async def test_feature_update_version_conflict_raises_409(db_session, sample_feature, mock_user):
    """Test: Feature update with outdated version raises HTTP 409"""
    # Simulate another update
    sample_feature.length = 20.0
    sample_feature.version += 1
    await db_session.commit()

    # Try to update with old version
    update_data = FeatureUpdate(
        length=25.0,
        version=0  # Outdated
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_feature(sample_feature.id, update_data, db_session, mock_user)

    assert exc_info.value.status_code == 409
    assert "změněna jiným uživatelem" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_feature_concurrent_updates_one_fails(db_session, sample_feature, mock_user):
    """Test: Concurrent feature updates - second one fails"""
    initial_version = sample_feature.version

    # First update (succeeds)
    update_data_1 = FeatureUpdate(
        length=12.0,
        version=initial_version
    )
    updated_1 = await update_feature(sample_feature.id, update_data_1, db_session, mock_user)
    assert updated_1.version == initial_version + 1

    # Second update with old version (fails)
    update_data_2 = FeatureUpdate(
        length=18.0,
        version=initial_version  # Stale
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_feature(sample_feature.id, update_data_2, db_session, mock_user)

    assert exc_info.value.status_code == 409


# ============================================================================
# VERSION AUTO-INCREMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_version_auto_increments_on_db_update(db_session):
    """Test: SQLAlchemy event listener auto-increments version on update"""
    # Use materials already seeded by conftest's db_session fixture
    # Create part
    part = Part(
        part_number="TEST-VERSION",
        name="Test",
        material_item_id=db_session.test_material_item.id,
        created_by="test",
        updated_by="test"
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)

    assert part.version == 0  # Initial version

    # Update part
    part.name = "Updated"
    await db_session.commit()
    await db_session.refresh(part)

    assert part.version == 1  # Auto-incremented by event listener

    # Update again
    part.name = "Updated Again"
    await db_session.commit()
    await db_session.refresh(part)

    assert part.version == 2  # Auto-incremented again
