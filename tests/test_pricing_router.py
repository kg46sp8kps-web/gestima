"""GESTIMA - Pricing Router API Tests (ADR-022: BatchSets)

Tests for pricing_router.py endpoints:
- BatchSet CRUD (list, get, create, update, delete)
- BatchSet operations (freeze, recalculate, clone)
- Batch management (add to set, remove from set)
- Freeze loose batches workflow

Test coverage:
- Happy path for all endpoints
- Error cases (404, 409, 410)
- Role-based access control
- Optimistic locking
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
async def test_part(client: AsyncClient, admin_headers):
    """Create a test part for batch set tests."""
    # First create a material item (needed for parts)
    # The test_db_session fixture already creates materials

    data = {
        "name": "Pricing Test Part",
        "description": "Part for pricing router tests"
    }

    response = await client.post("/api/parts/", json=data, headers=admin_headers)
    assert response.status_code == 200, f"Failed to create part: {response.json()}"
    return response.json()


@pytest.fixture
async def test_batch_set(client: AsyncClient, admin_headers, test_part):
    """Create a test batch set."""
    data = {"part_id": test_part["id"]}
    response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)
    assert response.status_code == 200, f"Failed to create batch set: {response.json()}"
    return response.json()


@pytest.fixture
async def test_batch_set_with_batches(client: AsyncClient, admin_headers, test_part):
    """Create a batch set with multiple batches (fresh for each test)."""
    # Create a new batch set for this test
    data = {"part_id": test_part["id"]}
    response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)
    assert response.status_code == 200, f"Failed to create batch set: {response.json()}"
    batch_set = response.json()
    set_id = batch_set["id"]

    # Add batches with different quantities
    for qty in [1, 10, 100]:
        response = await client.post(
            f"/api/pricing/batch-sets/{set_id}/batches",
            params={"quantity": qty},
            headers=admin_headers
        )
        assert response.status_code == 200, f"Failed to add batch: {response.json()}"

    # Return the updated batch set
    response = await client.get(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)
    return response.json()


# =============================================================================
# BATCH SET CRUD TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_batch_set(client: AsyncClient, admin_headers, test_part):
    """Test creating a new batch set."""
    data = {"part_id": test_part["id"]}

    response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)

    assert response.status_code == 200
    result = response.json()
    assert result["set_number"].startswith("35")  # ADR-022: 35XXXXXX range
    assert len(result["set_number"]) == 8
    assert result["part_id"] == test_part["id"]
    assert result["status"] == "draft"
    assert result["frozen_at"] is None


@pytest.mark.asyncio
async def test_create_batch_set_invalid_part(client: AsyncClient, admin_headers):
    """Test creating batch set with non-existent part returns 404."""
    data = {"part_id": 999999}

    response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)

    assert response.status_code == 404
    assert "nenalezen" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_all_batch_sets(client: AsyncClient, admin_headers, test_batch_set):
    """Test listing all batch sets."""
    response = await client.get("/api/pricing/batch-sets", headers=admin_headers)

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)
    assert len(result) >= 1

    # Check structure
    batch_set = result[0]
    assert "id" in batch_set
    assert "set_number" in batch_set
    assert "status" in batch_set
    assert "batch_count" in batch_set


@pytest.mark.asyncio
async def test_list_batch_sets_filter_by_status(client: AsyncClient, admin_headers, test_batch_set):
    """Test filtering batch sets by status."""
    # Filter draft
    response = await client.get("/api/pricing/batch-sets?status=draft", headers=admin_headers)

    assert response.status_code == 200
    for bs in response.json():
        assert bs["status"] == "draft"


@pytest.mark.asyncio
async def test_list_batch_sets_for_part(client: AsyncClient, admin_headers, test_batch_set, test_part):
    """Test listing batch sets for specific part."""
    part_id = test_part["id"]

    response = await client.get(f"/api/pricing/part/{part_id}/batch-sets", headers=admin_headers)

    assert response.status_code == 200
    result = response.json()
    assert len(result) >= 1
    for bs in result:
        assert bs["part_id"] == part_id


@pytest.mark.asyncio
async def test_get_batch_set(client: AsyncClient, admin_headers, test_batch_set):
    """Test getting single batch set with batches."""
    set_id = test_batch_set["id"]

    response = await client.get(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)

    assert response.status_code == 200
    result = response.json()
    assert result["id"] == set_id
    assert "batches" in result
    assert isinstance(result["batches"], list)


@pytest.mark.asyncio
async def test_get_batch_set_not_found(client: AsyncClient, admin_headers):
    """Test getting non-existent batch set returns 404."""
    response = await client.get("/api/pricing/batch-sets/999999", headers=admin_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_batch_set_name(client: AsyncClient, admin_headers, test_batch_set):
    """Test updating batch set name."""
    set_id = test_batch_set["id"]
    version = test_batch_set["version"]

    update_data = {
        "name": "Custom Price Set Name",
        "version": version
    }

    response = await client.put(
        f"/api/pricing/batch-sets/{set_id}",
        json=update_data,
        headers=admin_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert result["name"] == "Custom Price Set Name"
    assert result["version"] == version + 1


@pytest.mark.asyncio
async def test_update_batch_set_version_conflict(client: AsyncClient, admin_headers, test_batch_set):
    """Test optimistic locking on batch set update."""
    set_id = test_batch_set["id"]

    update_data = {
        "name": "Should Fail",
        "version": 999  # Wrong version
    }

    response = await client.put(
        f"/api/pricing/batch-sets/{set_id}",
        json=update_data,
        headers=admin_headers
    )

    assert response.status_code == 409
    assert "jiným uživatelem" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_batch_set(client: AsyncClient, admin_headers, test_part):
    """Test soft deleting batch set (ADMIN only)."""
    # Create a batch set to delete
    data = {"part_id": test_part["id"]}
    create_response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)
    set_id = create_response.json()["id"]

    # Delete
    response = await client.delete(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)

    assert response.status_code == 204

    # Verify deleted (should return 404)
    get_response = await client.get(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_batch_set_operator_denied(client: AsyncClient, operator_headers, test_batch_set):
    """Test that operators cannot delete batch sets (ADMIN only)."""
    set_id = test_batch_set["id"]

    response = await client.delete(f"/api/pricing/batch-sets/{set_id}", headers=operator_headers)

    assert response.status_code == 403


# =============================================================================
# BATCH SET OPERATIONS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_freeze_batch_set(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test freezing a batch set with batches."""
    set_id = test_batch_set_with_batches["id"]

    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/freeze",
        headers=admin_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "frozen"
    assert result["frozen_at"] is not None

    # All batches should be frozen
    for batch in result["batches"]:
        assert batch["is_frozen"] is True


@pytest.mark.asyncio
async def test_freeze_empty_batch_set_fails(client: AsyncClient, admin_headers, test_batch_set):
    """Test that freezing empty batch set returns 400."""
    set_id = test_batch_set["id"]

    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/freeze",
        headers=admin_headers
    )

    assert response.status_code == 400
    assert "prázdnou" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_freeze_already_frozen_batch_set_fails(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test that freezing already frozen set returns 409."""
    set_id = test_batch_set_with_batches["id"]

    # First freeze
    await client.post(f"/api/pricing/batch-sets/{set_id}/freeze", headers=admin_headers)

    # Try to freeze again
    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/freeze",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert "zmrazena" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_recalculate_batch_set(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test recalculating all batches in a set."""
    set_id = test_batch_set_with_batches["id"]

    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/recalculate",
        headers=admin_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert "batches" in result


@pytest.mark.asyncio
async def test_recalculate_frozen_batch_set_fails(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test that recalculating frozen set returns 409."""
    set_id = test_batch_set_with_batches["id"]

    # Freeze first
    await client.post(f"/api/pricing/batch-sets/{set_id}/freeze", headers=admin_headers)

    # Try to recalculate
    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/recalculate",
        headers=admin_headers
    )

    assert response.status_code == 409
    assert "zmrazenou" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_clone_batch_set(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test cloning a batch set."""
    original_id = test_batch_set_with_batches["id"]
    original_batch_count = len(test_batch_set_with_batches["batches"])

    response = await client.post(
        f"/api/pricing/batch-sets/{original_id}/clone",
        headers=admin_headers
    )

    assert response.status_code == 200
    clone = response.json()

    # Clone should be different
    assert clone["id"] != original_id
    assert clone["set_number"] != test_batch_set_with_batches["set_number"]
    assert clone["status"] == "draft"  # Clone is always draft

    # Verify clone has batches
    clone_detail = await client.get(f"/api/pricing/batch-sets/{clone['id']}", headers=admin_headers)
    assert len(clone_detail.json()["batches"]) == original_batch_count


@pytest.mark.asyncio
async def test_clone_frozen_batch_set(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test that frozen batch sets can be cloned."""
    set_id = test_batch_set_with_batches["id"]

    # Freeze original
    await client.post(f"/api/pricing/batch-sets/{set_id}/freeze", headers=admin_headers)

    # Clone should still work
    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/clone",
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"


# =============================================================================
# BATCH MANAGEMENT TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_add_batch_to_set(client: AsyncClient, admin_headers, test_batch_set):
    """Test adding a batch to a set."""
    set_id = test_batch_set["id"]

    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/batches",
        params={"quantity": 50},
        headers=admin_headers
    )

    assert response.status_code == 200
    batch = response.json()
    assert batch["quantity"] == 50
    assert batch["batch_set_id"] == set_id
    assert batch["batch_number"].startswith("30")  # ADR-017: Batches = 30XXXXXX


@pytest.mark.asyncio
async def test_add_batch_to_frozen_set_fails(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test that adding batch to frozen set returns 409."""
    set_id = test_batch_set_with_batches["id"]

    # Freeze set
    await client.post(f"/api/pricing/batch-sets/{set_id}/freeze", headers=admin_headers)

    # Try to add batch
    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/batches",
        params={"quantity": 200},
        headers=admin_headers
    )

    assert response.status_code == 409
    assert "zmrazené" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_batch_invalid_quantity(client: AsyncClient, admin_headers, test_batch_set):
    """Test that invalid quantity returns 422."""
    set_id = test_batch_set["id"]

    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/batches",
        params={"quantity": 0},  # Invalid: must be > 0
        headers=admin_headers
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_remove_batch_from_set(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test removing a batch from a set."""
    set_id = test_batch_set_with_batches["id"]
    batch_id = test_batch_set_with_batches["batches"][0]["id"]

    response = await client.delete(
        f"/api/pricing/batch-sets/{set_id}/batches/{batch_id}",
        headers=admin_headers
    )

    assert response.status_code == 204

    # Verify batch count decreased
    get_response = await client.get(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)
    assert len(get_response.json()["batches"]) == 2  # Was 3, now 2


@pytest.mark.asyncio
async def test_remove_batch_from_frozen_set_fails(client: AsyncClient, admin_headers, test_batch_set_with_batches):
    """Test that removing batch from frozen set returns 409."""
    set_id = test_batch_set_with_batches["id"]
    batch_id = test_batch_set_with_batches["batches"][0]["id"]

    # Freeze set
    await client.post(f"/api/pricing/batch-sets/{set_id}/freeze", headers=admin_headers)

    # Try to remove batch
    response = await client.delete(
        f"/api/pricing/batch-sets/{set_id}/batches/{batch_id}",
        headers=admin_headers
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_remove_batch_not_in_set(client: AsyncClient, admin_headers, test_batch_set):
    """Test removing non-existent batch returns 404."""
    set_id = test_batch_set["id"]

    response = await client.delete(
        f"/api/pricing/batch-sets/{set_id}/batches/999999",
        headers=admin_headers
    )

    assert response.status_code == 404


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_batch_set_unauthenticated(client: AsyncClient):
    """Test that unauthenticated requests are rejected."""
    # Use a fake part_id - the auth check should happen before part validation
    data = {"part_id": 1}

    response = await client.post("/api/pricing/batch-sets", json=data)

    # Should be rejected as unauthenticated (401)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operator_can_create_batch_set(client: AsyncClient, operator_headers, test_part):
    """Test that operators can create batch sets."""
    data = {"part_id": test_part["id"]}

    response = await client.post("/api/pricing/batch-sets", json=data, headers=operator_headers)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_operator_can_freeze_batch_set(client: AsyncClient, operator_headers, test_batch_set_with_batches):
    """Test that operators can freeze batch sets."""
    set_id = test_batch_set_with_batches["id"]

    response = await client.post(
        f"/api/pricing/batch-sets/{set_id}/freeze",
        headers=operator_headers
    )

    assert response.status_code == 200


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================

@pytest.mark.asyncio
async def test_update_deleted_batch_set_fails(client: AsyncClient, admin_headers, test_part):
    """Test that updating deleted batch set returns 410."""
    # Create and delete a batch set
    data = {"part_id": test_part["id"]}
    create_response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)
    batch_set = create_response.json()
    set_id = batch_set["id"]

    # Delete it
    await client.delete(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)

    # Try to update
    update_data = {"name": "Should Fail", "version": batch_set["version"]}
    response = await client.put(
        f"/api/pricing/batch-sets/{set_id}",
        json=update_data,
        headers=admin_headers
    )

    # Should return 404 (deleted sets are not found) or 410 (gone)
    assert response.status_code in [404, 410]


@pytest.mark.asyncio
async def test_double_delete_batch_set(client: AsyncClient, admin_headers, test_part):
    """Test that deleting already deleted set returns appropriate error."""
    # Create and delete
    data = {"part_id": test_part["id"]}
    create_response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)
    set_id = create_response.json()["id"]

    # First delete
    response1 = await client.delete(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)
    assert response1.status_code == 204

    # Second delete
    response2 = await client.delete(f"/api/pricing/batch-sets/{set_id}", headers=admin_headers)
    assert response2.status_code in [404, 410]


@pytest.mark.asyncio
async def test_batch_set_number_format(client: AsyncClient, admin_headers, test_part):
    """Test that generated batch set numbers follow ADR-017 format."""
    data = {"part_id": test_part["id"]}

    response = await client.post("/api/pricing/batch-sets", json=data, headers=admin_headers)

    assert response.status_code == 200
    set_number = response.json()["set_number"]

    # ADR-017: BatchSets use 35XXXXXX range
    assert len(set_number) == 8
    assert set_number.startswith("35")
    assert 35000000 <= int(set_number) <= 35999999
