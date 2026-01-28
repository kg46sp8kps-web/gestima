"""GESTIMA - Pytest fixtures"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.material import MaterialGroup, MaterialItem
from app.models.config import SystemConfig
from app.models import User
from app.models.enums import StockShape, UserRole
from app.gestima_app import app
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest_asyncio.fixture
async def db_session():
    """Create in-memory database with seeded materials (ADR-011)"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed MaterialGroup, PriceCategory, PriceTiers and MaterialItem for tests (ADR-011, ADR-014)
        from app.models.material import MaterialPriceCategory, MaterialPriceTier

        group = MaterialGroup(
            code="11xxx",
            name="Ocel automatová",
            density=7.85,
            created_by="test"
        )
        session.add(group)
        await session.flush()

        # Create price category with tiers (ADR-014)
        price_category = MaterialPriceCategory(
            code="TEST-OCEL",
            name="Test ocel - kruhová tyč",
            created_by="test"
        )
        session.add(price_category)
        await session.flush()

        # Create price tiers
        tiers = [
            MaterialPriceTier(price_category_id=price_category.id, min_weight=0, max_weight=15, price_per_kg=49.4, created_by="test"),
            MaterialPriceTier(price_category_id=price_category.id, min_weight=15, max_weight=100, price_per_kg=34.5, created_by="test"),
            MaterialPriceTier(price_category_id=price_category.id, min_weight=100, max_weight=None, price_per_kg=26.3, created_by="test"),
        ]
        for tier in tiers:
            session.add(tier)
        await session.flush()

        item = MaterialItem(
            material_number="2000001",  # ADR-017: 7-digit material number (2XXXXXX range)
            code="11SMn30-D50",
            name="11SMn30 ⌀50 mm - tyč kruhová",
            material_group_id=group.id,
            price_category_id=price_category.id,
            shape=StockShape.ROUND_BAR,
            diameter=50.0,
            created_by="test"
        )
        session.add(item)
        await session.commit()

        # Attach to session for easy access in tests
        session.test_material_group = group
        session.test_price_category = price_category
        session.test_material_item = item

        yield session


@pytest.fixture
def sample_part_data():
    """
    Sample Part data factory (ADR-011).
    Usage: sample_part_data(material_item_id=session.test_material_item.id)
    """
    def _create(material_item_id=1):
        return {
            "part_number": "TEST-001",
            "name": "Testovací hřídel",
            "material_item_id": material_item_id,
            "length": 120.0,
        }
    return _create


@pytest_asyncio.fixture
async def test_db_session():
    """Enhanced db_session with users and system config for API tests"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create test users
        admin_user = User(
            username="admin",
            hashed_password=pwd_context.hash("admin123"),
            role=UserRole.ADMIN,
            created_by="system"
        )
        operator_user = User(
            username="operator",
            hashed_password=pwd_context.hash("operator123"),
            role=UserRole.OPERATOR,
            created_by="system"
        )
        session.add(admin_user)
        session.add(operator_user)
        await session.flush()

        # Create SystemConfig entries
        configs = [
            SystemConfig(
                key="overhead_coefficient",
                value_float=1.20,
                description="Administrativní režie (1.20 = +20%)",
                created_by="system",
                version=1
            ),
            SystemConfig(
                key="margin_coefficient",
                value_float=1.25,
                description="Marže na práci (1.25 = +25%)",
                created_by="system",
                version=1
            ),
            SystemConfig(
                key="stock_coefficient",
                value_float=1.15,
                description="Skladový koeficient (1.15 = +15%)",
                created_by="system",
                version=1
            ),
            SystemConfig(
                key="coop_coefficient",
                value_float=1.10,
                description="Kooperační koeficient (1.10 = +10%)",
                created_by="system",
                version=1
            ),
        ]
        for config in configs:
            session.add(config)
        await session.commit()

        session.test_admin = admin_user
        session.test_operator = operator_user

        yield session


@pytest_asyncio.fixture
async def client(test_db_session):
    """HTTP client for API testing"""
    from app.database import get_db

    # Override get_db dependency to use test database
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient):
    """Get admin authentication token"""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    # Token is set in cookie
    token = response.cookies.get("access_token")
    assert token is not None, "access_token cookie not set"
    return token


@pytest_asyncio.fixture
async def operator_token(client: AsyncClient):
    """Get operator authentication token"""
    response = await client.post("/api/auth/login", json={
        "username": "operator",
        "password": "operator123"
    })
    assert response.status_code == 200
    # Token is set in cookie
    token = response.cookies.get("access_token")
    assert token is not None, "access_token cookie not set"
    return token


@pytest_asyncio.fixture
async def admin_headers(admin_token):
    """Admin authentication headers"""
    return {"Cookie": f"access_token={admin_token}"}


@pytest_asyncio.fixture
async def operator_headers(operator_token):
    """Operator authentication headers"""
    return {"Cookie": f"access_token={operator_token}"}
