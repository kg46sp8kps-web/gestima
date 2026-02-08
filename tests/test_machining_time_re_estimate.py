"""Tests for machining time re-estimation endpoint.

ADR-040: Machining Time Estimation System

Tests:
- Re-estimate with different material
- Material validation
- File not found error
- Stock type validation

NOTE: These tests are SKIPPED if OCCT (pythonocc-core) is not available.
"""

import pytest
import pytest_asyncio
from pathlib import Path
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.material import MaterialGroup
from app.gestima_app import app

# Disable rate limiting for tests
from app.config import settings
settings.RATE_LIMIT_ENABLED = False


@pytest_asyncio.fixture
async def test_db_session():
    """Create in-memory database with material groups for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Create test material groups with cutting parameters
        materials = [
            MaterialGroup(
                code="OCEL-AUTO",
                name="Ocel automatová",
                density=7.85,
                iso_group="P",
                hardness_hb=180.0,
                mrr_milling_roughing=300.0,
                mrr_milling_finishing=180.0,
                deep_pocket_penalty=1.5,
                thin_wall_penalty=2.2,
                created_by="test"
            ),
            MaterialGroup(
                code="HLINIK",
                name="Hliník",
                density=2.70,
                iso_group="N",
                hardness_hb=60.0,
                mrr_milling_roughing=800.0,
                mrr_milling_finishing=400.0,
                deep_pocket_penalty=1.3,
                thin_wall_penalty=1.8,
                created_by="test"
            ),
        ]

        for mat in materials:
            session.add(mat)

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        yield session


@pytest_asyncio.fixture
async def client(test_db_session):
    """Async test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_re_estimate_file_not_found(client, test_db_session):
    """Test re-estimation with non-existent file."""
    response = await client.post(
        "/api/machining-time/re-estimate",
        json={
            "filename": "nonexistent_file_12345.step",
            "material_code": "OCEL-AUTO",
            "stock_type": "bbox"
        }
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_re_estimate_invalid_material(client, test_db_session):
    """Test re-estimation with invalid material code."""
    drawings_dir = Path("uploads/drawings")
    step_files = list(drawings_dir.glob("**/*.step"))

    if not step_files:
        pytest.skip("No STEP files found for testing")

    test_file = step_files[0].name

    response = await client.post(
        "/api/machining-time/re-estimate",
        json={
            "filename": test_file,
            "material_code": "INVALID-MATERIAL",
            "stock_type": "bbox"
        }
    )

    assert response.status_code == 400
    assert "Unknown material code" in response.json()["detail"]


@pytest.mark.asyncio
async def test_re_estimate_invalid_stock_type(client, test_db_session):
    """Test re-estimation with invalid stock type."""
    drawings_dir = Path("uploads/drawings")
    step_files = list(drawings_dir.glob("**/*.step"))

    if not step_files:
        pytest.skip("No STEP files found for testing")

    test_file = step_files[0].name

    response = await client.post(
        "/api/machining-time/re-estimate",
        json={
            "filename": test_file,
            "material_code": "OCEL-AUTO",
            "stock_type": "invalid_type"
        }
    )

    assert response.status_code == 422  # Pydantic validation error
