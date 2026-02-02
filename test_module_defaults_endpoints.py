"""Test module_defaults endpoints

Test suite for ModuleDefaults API (ADR-031).

Run:
    pytest test_module_defaults_endpoints.py -v
"""

import pytest
from app.database import async_session, init_db
from app.models.module_defaults import ModuleDefaults
from sqlalchemy import select, text


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    """Initialize database before tests"""
    await init_db()
    yield


@pytest.fixture
async def clean_module_defaults():
    """Clean module_defaults table before each test"""
    async with async_session() as session:
        await session.execute(text("DELETE FROM module_defaults"))
        await session.commit()
    yield


# ============================================================================
# CREATE/UPDATE (UPSERT) TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_module_defaults_success(client, clean_module_defaults, admin_headers):
    """Test creating new module defaults"""
    payload = {
        "module_type": "part-main",
        "default_width": 800,
        "default_height": 600,
        "settings": {"splitPosition": 50}
    }

    response = await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["module_type"] == "part-main"
    assert data["default_width"] == 800
    assert data["default_height"] == 600
    assert data["settings"]["splitPosition"] == 50
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_module_defaults_validation_width_too_small(client, clean_module_defaults, admin_headers):
    """Test width validation (< 200)"""
    payload = {
        "module_type": "part-pricing",
        "default_width": 100,  # Invalid: < 200
        "default_height": 600
    }

    response = await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_create_module_defaults_validation_width_too_large(client, clean_module_defaults, admin_headers):
    """Test width validation (> 3000)"""
    payload = {
        "module_type": "part-pricing",
        "default_width": 3500,  # Invalid: > 3000
        "default_height": 600
    }

    response = await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_update_existing_module_defaults_upsert(client, clean_module_defaults, admin_headers):
    """Test updating existing defaults via POST (upsert)"""
    # Create first
    payload1 = {
        "module_type": "part-operations",
        "default_width": 800,
        "default_height": 600
    }
    response1 = await client.post("/api/module-defaults", json=payload1, headers=admin_headers)
    assert response1.status_code == 201

    # Update via POST (upsert)
    payload2 = {
        "module_type": "part-operations",
        "default_width": 1000,
        "default_height": 800,
        "settings": {"newSetting": True}
    }
    response2 = await client.post("/api/module-defaults", json=payload2, headers=admin_headers)

    assert response2.status_code == 201  # Same code for upsert
    data = response2.json()
    assert data["default_width"] == 1000
    assert data["default_height"] == 800
    assert data["settings"]["newSetting"] is True


# ============================================================================
# GET TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_module_defaults_success(client, clean_module_defaults, admin_headers):
    """Test getting module defaults"""
    # Create first
    payload = {
        "module_type": "part-material",
        "default_width": 700,
        "default_height": 500
    }
    await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    # Get
    response = await client.get("/api/module-defaults/part-material", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["module_type"] == "part-material"
    assert data["default_width"] == 700
    assert data["default_height"] == 500


@pytest.mark.asyncio
async def test_get_module_defaults_not_found(client, clean_module_defaults, admin_headers):
    """Test getting non-existent module defaults"""
    response = await client.get("/api/module-defaults/non-existent", headers=admin_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# UPDATE (PATCH) TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_update_module_defaults_partial(client, clean_module_defaults, admin_headers):
    """Test partial update via PUT"""
    # Create first
    payload_create = {
        "module_type": "part-pricing",
        "default_width": 800,
        "default_height": 600,
        "settings": {"oldSetting": "value"}
    }
    await client.post("/api/module-defaults", json=payload_create, headers=admin_headers)

    # Partial update (only width)
    payload_update = {
        "default_width": 1200
    }
    response = await client.put("/api/module-defaults/part-pricing", json=payload_update, headers=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["default_width"] == 1200
    assert data["default_height"] == 600  # Unchanged
    assert data["settings"]["oldSetting"] == "value"  # Unchanged


@pytest.mark.asyncio
async def test_update_module_defaults_not_found(client, clean_module_defaults, admin_headers):
    """Test updating non-existent module defaults"""
    payload = {
        "default_width": 900
    }
    response = await client.put("/api/module-defaults/non-existent", json=payload, headers=admin_headers)

    assert response.status_code == 404


# ============================================================================
# DELETE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_delete_module_defaults_success(client, clean_module_defaults, admin_headers):
    """Test soft delete"""
    # Create first
    payload = {
        "module_type": "part-detail",
        "default_width": 800,
        "default_height": 600
    }
    await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    # Delete
    response = await client.delete("/api/module-defaults/part-detail", headers=admin_headers)

    assert response.status_code == 204

    # Verify soft delete (should not be found)
    get_response = await client.get("/api/module-defaults/part-detail", headers=admin_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_module_defaults_not_found(client, clean_module_defaults, admin_headers):
    """Test deleting non-existent module defaults"""
    response = await client.delete("/api/module-defaults/non-existent", headers=admin_headers)

    assert response.status_code == 404


# ============================================================================
# SETTINGS VALIDATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_create_module_defaults_invalid_settings_type(client, clean_module_defaults, admin_headers):
    """Test settings validation (must be JSON object)"""
    payload = {
        "module_type": "part-test",
        "default_width": 800,
        "default_height": 600,
        "settings": "not a dict"  # Invalid: must be dict
    }

    response = await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    # This should fail at Pydantic validation
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_module_defaults_null_settings(client, clean_module_defaults, admin_headers):
    """Test creating defaults with null settings (allowed)"""
    payload = {
        "module_type": "part-null-settings",
        "default_width": 800,
        "default_height": 600,
        "settings": None
    }

    response = await client.post("/api/module-defaults", json=payload, headers=admin_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["settings"] is None
