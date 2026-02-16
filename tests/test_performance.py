"""
Performance tests - měření latence API endpoints.

Target: < 100ms pro všechny operace
"""
import pytest
import pytest_asyncio
import time
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.gestima_app import app
from app.dependencies import get_current_user, get_db
from app.models import User, UserRole
from app.models.part import Part
from app.models.material import MaterialGroup, MaterialItem, MaterialPriceCategory, MaterialPriceTier
from app.models.material_input import MaterialInput
from app.models.enums import StockShape
from app.database import Base


def mock_current_user():
    """Mock authenticated user for performance tests."""
    return User(
        id=1,
        username="test_perf_user",
        email="perf@test.com",
        role=UserRole.ADMIN,
        is_active=True,
        hashed_password="fake_hash",
        created_by="test"
    )


@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Setup in-memory DB engine for performance tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_test_data(test_engine):
    """Setup test data once for all performance tests."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create MaterialGroup
        group = MaterialGroup(
            code="11xxx",
            name="Ocel automatová",
            density=7.85,
            created_by="test"
        )
        session.add(group)
        await session.flush()

        # Create PriceCategory + Tiers
        price_category = MaterialPriceCategory(
            code="TEST-OCEL",
            name="Test ocel",
            created_by="test"
        )
        session.add(price_category)
        await session.flush()

        tier = MaterialPriceTier(
            price_category_id=price_category.id,
            min_weight=0,
            max_weight=100,
            price_per_kg=30.0,
            created_by="test"
        )
        session.add(tier)

        # Create MaterialItem
        material_item = MaterialItem(
            material_number="2000015",  # ADR-017
            code="11SMn30-D50",
            name="11SMn30 ⌀50 mm",
            material_group_id=group.id,
            price_category_id=price_category.id,
            shape=StockShape.ROUND_BAR,
            diameter=50.0,
            created_by="test"
        )
        session.add(material_item)
        await session.flush()

        # Create Part (ADR-024: no material fields on Part)
        part = Part(
            part_number="1000100",  # ADR-017
            name="Test Part for Performance",
            length=100.0,
            created_by="test"
        )
        session.add(part)
        await session.flush()

        # Create MaterialInput (ADR-024: material data here)
        mi = MaterialInput(
            part_id=part.id,
            seq=1,
            price_category_id=price_category.id,
            material_item_id=material_item.id,
            stock_shape=StockShape.ROUND_BAR,
            stock_diameter=50.0,
            stock_length=100.0,
            quantity=1,
            created_by="test"
        )
        session.add(mi)
        await session.commit()


@pytest.fixture
def client(test_engine):
    """Test client s autentizovaným uživatelem a test DB."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_current_user] = mock_current_user
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_part_detail_latency(client):
    """Změřit latenci načtení detailu dílu."""
    # Warmup
    client.get("/api/parts/1000100/full")

    # Measure
    start = time.perf_counter()
    response = client.get("/api/parts/1000100/full")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Part detail latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"


def test_operations_list_latency(client):
    """Změřit latenci načtení operací."""
    client.get("/api/operations/part/1")

    start = time.perf_counter()
    response = client.get("/api/operations/part/1")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Operations list latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"


def test_batches_list_latency(client):
    """Změřit latenci načtení batchů."""
    client.get("/api/batches/part/1")

    start = time.perf_counter()
    response = client.get("/api/batches/part/1")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Batches list latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"


def test_parts_list_latency(client):
    """Změřit latenci načtení seznamu dílů."""
    client.get("/parts")

    start = time.perf_counter()
    response = client.get("/parts")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Parts list latency: {latency_ms:.1f}ms")
    # Parts list může být delší (rendering), ale ne moc
    assert latency_ms < 200, f"Too slow! {latency_ms:.1f}ms > 200ms"


def test_stock_cost_calculation_latency(client):
    """Změřit latenci výpočtu ceny polotovaru."""
    client.get("/api/parts/1000100/stock-cost")

    start = time.perf_counter()
    response = client.get("/api/parts/1000100/stock-cost")
    latency_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    print(f"\n✓ Stock cost calculation latency: {latency_ms:.1f}ms")
    assert latency_ms < 100, f"Too slow! {latency_ms:.1f}ms > 100ms"
