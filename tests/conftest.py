"""GESTIMA - Pytest fixtures"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.material import MaterialGroup, MaterialItem
from app.models.enums import StockShape


@pytest_asyncio.fixture
async def db_session():
    """Create in-memory database with seeded materials (ADR-011)"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Seed MaterialGroup and MaterialItem for tests (ADR-011)
        group = MaterialGroup(
            code="11xxx",
            name="Ocel automatová",
            density=7.85,
            created_by="test"
        )
        session.add(group)
        await session.flush()

        item = MaterialItem(
            code="11SMn30-D50",
            name="11SMn30 ⌀50 mm - tyč kruhová",
            material_group_id=group.id,
            shape=StockShape.ROUND_BAR,
            diameter=50.0,
            price_per_kg=45.50,
            created_by="test"
        )
        session.add(item)
        await session.commit()

        # Attach to session for easy access in tests
        session.test_material_group = group
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
