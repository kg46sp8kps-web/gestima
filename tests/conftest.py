"""GESTIMA - Pytest fixtures"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
def sample_part_data():
    return {
        "part_number": "TEST-001",
        "name": "Testovací hřídel",
        "material_name": "11SMn30",
        "material_group": "automatova_ocel",
        "stock_type": "tyc",
        "stock_diameter": 50.0,
        "stock_length": 120.0,
    }
