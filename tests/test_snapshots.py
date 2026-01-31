"""GESTIMA - Testy pro Batch Snapshot (ADR-012: Minimal Snapshot)"""

import pytest
import pytest_asyncio
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select

from app.models.batch import Batch
from app.models.part import Part
from app.models.material import MaterialGroup, MaterialItem, MaterialPriceCategory, MaterialPriceTier
from app.models.material_input import MaterialInput  # ADR-024
from app.models.enums import StockShape  # ADR-024
from app.models import User, UserRole
from app.routers.batches_router import freeze_batch, clone_batch, delete_batch


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_user():
    """Mock authenticated user (Operator)"""
    return User(
        id=1,
        username="testuser",
        email="test@example.com",
        role=UserRole.OPERATOR,
        hashed_password="fake_hash"
    )


@pytest.fixture
def mock_admin():
    """Mock authenticated user (Admin)"""
    return User(
        id=2,
        username="admin",
        email="admin@example.com",
        role=UserRole.ADMIN,
        hashed_password="fake_hash"
    )


@pytest_asyncio.fixture
async def sample_materials(db_session):
    """Create sample material group and item (ADR-014: uses price_category_id)"""
    group = MaterialGroup(
        code="11000",
        name="Ocel",
        density=7.85,
        created_by="test"
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)

    # Create price category + tier (ADR-014)
    price_category = MaterialPriceCategory(
        code="SNAPSHOT-TEST",
        name="Snapshot test category",
        created_by="test"
    )
    db_session.add(price_category)
    await db_session.commit()
    await db_session.refresh(price_category)

    tier = MaterialPriceTier(
        price_category_id=price_category.id,
        min_weight=0,
        max_weight=None,
        price_per_kg=80.0,
        created_by="test"
    )
    db_session.add(tier)
    await db_session.commit()

    item = MaterialItem(
     material_number="2000003",  # ADR-017
     code="11300",
        name="Ocel konstrukční",
        material_group_id=group.id,
        price_category_id=price_category.id,
        shape="round_bar",
        diameter=50.0,
        created_by="test"
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    return group, item


@pytest_asyncio.fixture
async def sample_part(db_session, sample_materials):
    """Create a sample part for testing (ADR-024: uses MaterialInput instead of Part.material_item_id)"""
    group, item = sample_materials

    # Get price_category from item
    price_category_id = item.price_category_id

    # Create Part (ADR-024: no material fields on Part anymore)
    part = Part(
        part_number="10000099",  # ADR-017: 8-digit number
        name="Test Snapshot Part",
        length=100.0,
        created_by="test",
        updated_by="test"
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)

    # Create MaterialInput (ADR-024: material data is here now)
    material_input = MaterialInput(
        part_id=part.id,
        seq=1,
        price_category_id=price_category_id,
        material_item_id=item.id,
        stock_shape=StockShape.ROUND_BAR,
        stock_diameter=50.0,
        stock_length=100.0,
        quantity=1,
        created_by="test"
    )
    db_session.add(material_input)
    await db_session.commit()

    return part


@pytest_asyncio.fixture
async def sample_batch(db_session, sample_part):
    """Create a sample batch for testing"""
    batch = Batch(
     batch_number="3000001",  # ADR-017
     part_id=sample_part.id,
        quantity=10,
        material_cost=250.0,
        machining_cost=180.0,
        setup_cost=50.0,
        coop_cost=0.0,
        unit_cost=480.0,
        total_cost=4800.0,
        created_by="test",
        updated_by="test"
    )
    db_session.add(batch)
    await db_session.commit()
    await db_session.refresh(batch)
    return batch


# ============================================================================
# FREEZE BATCH TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
async def test_freeze_batch(db_session, sample_batch, mock_user):
    """Test zmrazení batche - vytvoření snapshotu s aktuálními cenami"""
    initial_frozen_state = sample_batch.is_frozen
    assert initial_frozen_state is False

    # Zmrazit batch
    result = await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    assert result.is_frozen is True
    assert result.frozen_at is not None
    assert result.frozen_by_id == mock_user.id
    assert result.snapshot_data is not None
    assert result.unit_price_frozen == 480.0
    assert result.total_price_frozen == 4800.0

    # Zkontrolovat snapshot strukturu
    snapshot = result.snapshot_data
    assert "frozen_at" in snapshot
    assert "frozen_by" in snapshot
    assert snapshot["frozen_by"] == "testuser"
    assert "costs" in snapshot
    assert snapshot["costs"]["unit_cost"] == 480.0
    assert snapshot["costs"]["total_cost"] == 4800.0
    assert "metadata" in snapshot
    assert snapshot["metadata"]["material_code"] == "11000"
    assert snapshot["metadata"]["material_price_per_kg"] == 80.0


@pytest.mark.asyncio
async def test_freeze_already_frozen_batch(db_session, sample_batch, mock_user):
    """Test pokusu o zmrazení již zmrazeného batche - očekáváme 409 Conflict"""
    # Zmrazit batch poprvé
    await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    # Pokusit se zmrazit znovu
    with pytest.raises(HTTPException) as exc_info:
        await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    assert exc_info.value.status_code == 409
    assert "zmrazena" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_freeze_batch_not_found(db_session, mock_user):
    """Test zmrazení neexistujícího batche - očekáváme 404"""
    with pytest.raises(HTTPException) as exc_info:
        await freeze_batch("9999999", db_session, mock_user)

    assert exc_info.value.status_code == 404


# ============================================================================
# CLONE BATCH TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
async def test_clone_batch(db_session, sample_batch, mock_user):
    """Test klonování batche - vytvoření nové, nezmrazené kopie"""
    # Zmrazit původní batch
    await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    # Klonovat batch
    cloned = await clone_batch(sample_batch.batch_number, db_session, mock_user)

    assert cloned.id != sample_batch.id  # Nový batch
    assert cloned.part_id == sample_batch.part_id
    assert cloned.quantity == sample_batch.quantity
    assert cloned.is_frozen is False  # Klon není zmrazený
    assert cloned.frozen_at is None
    assert cloned.snapshot_data is None
    assert cloned.unit_cost == sample_batch.unit_cost  # Ceny zkopírovány


@pytest.mark.asyncio
async def test_clone_batch_not_found(db_session, mock_user):
    """Test klonování neexistujícího batche - očekáváme 404"""
    with pytest.raises(HTTPException) as exc_info:
        await clone_batch("9999999", db_session, mock_user)

    assert exc_info.value.status_code == 404


# ============================================================================
# DELETE BATCH TESTS (Soft Delete for Frozen)
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
async def test_frozen_batch_soft_delete(db_session, sample_batch, mock_admin):
    """Test smazání frozen batche - soft delete (ADR-012)"""
    # Zmrazit batch
    await freeze_batch(sample_batch.batch_number, db_session, mock_admin)
    batch_id = sample_batch.id  # Keep ID for verification query

    # Smazat frozen batch (returns None = 204 No Content)
    await delete_batch(sample_batch.batch_number, db_session, mock_admin)

    # Zkontrolovat, že batch má deleted_at (soft delete)
    query_result = await db_session.execute(select(Batch).where(Batch.id == batch_id))
    deleted_batch = query_result.scalar_one_or_none()
    assert deleted_batch is not None  # Stále existuje (soft delete)
    assert deleted_batch.deleted_at is not None  # Soft delete timestamp set
    assert deleted_batch.deleted_by == "admin"


@pytest.mark.asyncio
async def test_unfrozen_batch_hard_delete(db_session, sample_batch, mock_admin):
    """Test smazání nezmrazeného batche - hard delete"""
    batch_number = sample_batch.batch_number
    batch_id = sample_batch.id  # Keep ID for verification query

    # Smazat nezmrazený batch (returns None = 204 No Content)
    await delete_batch(batch_number, db_session, mock_admin)

    # Zkontrolovat, že batch už neexistuje (hard delete)
    query_result = await db_session.execute(select(Batch).where(Batch.id == batch_id))
    deleted_batch = query_result.scalar_one_or_none()
    assert deleted_batch is None  # Smazán z DB


# ============================================================================
# PRICE STABILITY TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
async def test_price_stability_after_freeze(db_session, sample_batch, sample_materials, mock_user):
    """Test stability cen po zmrazení - změna ceny materiálu neovlivní frozen batch"""
    _, material_item = sample_materials

    # Zmrazit batch (se současnou cenou 80.0)
    frozen = await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    original_snapshot = frozen.snapshot_data
    assert original_snapshot["metadata"]["material_price_per_kg"] == 80.0

    # Změnit cenu materiálu
    material_item.price_per_kg = 100.0  # Nová cena (+25%)
    await db_session.commit()

    # Načíst batch znovu - snapshot by měl zůstat stejný
    await db_session.refresh(frozen)

    assert frozen.snapshot_data["metadata"]["material_price_per_kg"] == 80.0  # Stará cena
    assert frozen.snapshot_data["costs"]["unit_cost"] == 480.0  # Stará cena
    assert frozen.unit_price_frozen == 480.0  # Redundantní sloupec nezměněn


# ============================================================================
# WARNING VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
async def test_freeze_with_zero_price_logs_warning(db_session, sample_batch, sample_materials, mock_user):
    """Test zmrazení batche s nulovou cenou materiálu - očekáváme warning v snapshotu"""
    _, material_item = sample_materials

    # Nastavit cenu materiálu na 0 (což povede k material_cost = 0)
    material_item.price_per_kg = 0.0
    sample_batch.material_cost = 0.0  # Výsledek výpočtu s nulovou cenou
    await db_session.commit()

    # Zmrazit batch
    frozen = await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    # Zkontrolovat, že snapshot obsahuje warnings
    assert frozen.snapshot_data is not None
    assert "warnings" in frozen.snapshot_data
    warnings = frozen.snapshot_data["warnings"]
    assert len(warnings) > 0

    # Zkontrolovat konkrétní warning o nákladech na materiál
    material_warning = [w for w in warnings if "Náklady na materiál" in w]
    assert len(material_warning) == 1
    assert "0.0 Kč" in material_warning[0]

    # Freeze by měl proběhnout i s warningem (neblokovat)
    assert frozen.is_frozen is True


@pytest.mark.asyncio
@pytest.mark.critical
async def test_freeze_with_zero_costs_logs_warnings(db_session, sample_batch, mock_user):
    """Test zmrazení batche s nulovými náklady - očekáváme warnings v snapshotu"""
    # Nastavit náklady na 0
    sample_batch.material_cost = 0.0
    sample_batch.machining_cost = 0.0
    sample_batch.total_cost = 0.0
    await db_session.commit()

    # Zmrazit batch
    frozen = await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    # Zkontrolovat, že snapshot obsahuje warnings
    assert frozen.snapshot_data is not None
    assert "warnings" in frozen.snapshot_data
    warnings = frozen.snapshot_data["warnings"]
    assert len(warnings) >= 3  # Minimálně 3 warnings (material, machining, total)

    # Zkontrolovat konkrétní warnings
    assert any("Náklady na materiál: 0.0 Kč" in w for w in warnings)
    assert any("Náklady na obrábění: 0.0 Kč" in w for w in warnings)
    assert any("Celkové náklady: 0.0 Kč" in w for w in warnings)

    # Freeze by měl proběhnout i s warningy (neblokovat)
    assert frozen.is_frozen is True


@pytest.mark.asyncio
async def test_freeze_with_valid_data_no_warnings(db_session, sample_batch, mock_user):
    """Test zmrazení batche s validními daty - očekáváme prázdný seznam warnings"""
    # sample_batch má validní data (cena 80.0, material_cost 250.0, atd.)

    # Zmrazit batch
    frozen = await freeze_batch(sample_batch.batch_number, db_session, mock_user)

    # Zkontrolovat, že snapshot neobsahuje warnings
    assert frozen.snapshot_data is not None
    assert "warnings" in frozen.snapshot_data
    warnings = frozen.snapshot_data["warnings"]
    assert len(warnings) == 0  # Žádné warnings

    # Freeze by měl proběhnout normálně
    assert frozen.is_frozen is True
