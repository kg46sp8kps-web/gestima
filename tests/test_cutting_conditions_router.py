"""GESTIMA - Tests for Cutting Conditions Router"""

import pytest
from httpx import AsyncClient

from app.services.cutting_conditions_catalog import seed_cutting_conditions_to_db


@pytest.mark.asyncio
async def test_pivot_table_empty(client: AsyncClient, admin_headers: dict):
    """Test pivot table endpoint returns empty cells when no data seeded."""
    response = await client.get("/api/cutting-conditions/pivot?mode=mid", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "mid"
    assert len(data["materials"]) == 9  # 9 material groups
    assert len(data["operations"]) == 12  # 12 operations (added sawing)
    assert data["cells"] == {}  # Empty if not seeded


@pytest.mark.asyncio
async def test_seed_endpoint(client: AsyncClient, admin_headers: dict):
    """Test seeding from catalog."""
    response = await client.post("/api/cutting-conditions/seed", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert "count" in data
    assert data["count"] > 0  # Should seed many records
    assert "message" in data


@pytest.mark.asyncio
async def test_pivot_table_after_seed(client: AsyncClient, admin_headers: dict, test_db_session):
    """Test pivot table returns data after seeding."""
    # Seed data first
    await seed_cutting_conditions_to_db(test_db_session)

    response = await client.get("/api/cutting-conditions/pivot?mode=mid", headers=admin_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "mid"
    assert len(data["cells"]) > 0  # Should have data

    # Check structure
    first_material = list(data["cells"].keys())[0]
    first_operation = list(data["cells"][first_material].keys())[0]
    cell = data["cells"][first_material][first_operation]

    assert "id" in cell
    assert "Vc" in cell
    assert "f" in cell
    assert "version" in cell


@pytest.mark.asyncio
async def test_update_cutting_condition(client: AsyncClient, admin_headers: dict, test_db_session):
    """Test updating a cutting condition with optimistic locking."""
    # Seed data first
    await seed_cutting_conditions_to_db(test_db_session)

    # Get pivot table to find a record
    response = await client.get("/api/cutting-conditions/pivot?mode=mid", headers=admin_headers)
    data = response.json()

    # Get first cell
    first_material = list(data["cells"].keys())[0]
    first_operation = list(data["cells"][first_material].keys())[0]
    cell = data["cells"][first_material][first_operation]

    # Update it
    update_data = {
        "Vc": cell["Vc"] + 10,  # Increase Vc by 10
        "f": cell["f"],
        "Ap": cell["Ap"],
        "notes": "Test update",
        "version": cell["version"],
    }

    response = await client.put(
        f"/api/cutting-conditions/{cell['id']}",
        json=update_data,
        headers=admin_headers
    )

    assert response.status_code == 200
    updated = response.json()

    assert updated["Vc"] == cell["Vc"] + 10
    assert updated["notes"] == "Test update"
    assert updated["version"] == cell["version"] + 1  # Version incremented


@pytest.mark.asyncio
async def test_update_version_conflict(client: AsyncClient, admin_headers: dict, test_db_session):
    """Test optimistic locking prevents concurrent updates."""
    # Seed data first
    await seed_cutting_conditions_to_db(test_db_session)

    # Get pivot table to find a record
    response = await client.get("/api/cutting-conditions/pivot?mode=mid", headers=admin_headers)
    data = response.json()

    # Get first cell
    first_material = list(data["cells"].keys())[0]
    first_operation = list(data["cells"][first_material].keys())[0]
    cell = data["cells"][first_material][first_operation]

    # Try to update with wrong version
    update_data = {
        "Vc": cell["Vc"] + 10,
        "f": cell["f"],
        "Ap": cell["Ap"],
        "version": 999,  # Wrong version
    }

    response = await client.put(
        f"/api/cutting-conditions/{cell['id']}",
        json=update_data,
        headers=admin_headers
    )

    assert response.status_code == 409  # Conflict


@pytest.mark.asyncio
async def test_update_nonexistent_record(client: AsyncClient, admin_headers: dict):
    """Test updating non-existent record returns 404."""
    update_data = {
        "Vc": 100,
        "f": 0.1,
        "Ap": 1.0,
        "version": 0,
    }

    response = await client.put(
        "/api/cutting-conditions/999999",
        json=update_data,
        headers=admin_headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_endpoints_require_admin(client: AsyncClient, operator_headers: dict):
    """Test that all endpoints require ADMIN role."""
    # Pivot table
    response = await client.get("/api/cutting-conditions/pivot?mode=mid", headers=operator_headers)
    assert response.status_code == 403

    # Seed
    response = await client.post("/api/cutting-conditions/seed", headers=operator_headers)
    assert response.status_code == 403

    # Update
    response = await client.put(
        "/api/cutting-conditions/1",
        json={"Vc": 100, "f": 0.1, "version": 0},
        headers=operator_headers
    )
    assert response.status_code == 403
