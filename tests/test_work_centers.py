"""
Tests for WorkCenter model and API (ADR-021)

Test coverage:
- WorkCenter model and computed properties
- WorkCenterType enum
- Schema validation (Create, Update, Response)
- Sequential number generation (80XXXXXX)
- API endpoints (CRUD)
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_center import (
    WorkCenter,
    WorkCenterCreate,
    WorkCenterUpdate,
    WorkCenterResponse
)
from app.models.enums import WorkCenterType
from app.services.number_generator import NumberGenerator


@pytest.mark.asyncio
class TestWorkCenterModel:
    """Test WorkCenter SQLAlchemy model"""

    async def test_create_work_center_minimal(self, db_session: AsyncSession):
        """Create work center with minimal required fields"""
        wc = WorkCenter(
            work_center_number="80000001",
            name="Test CNC",
            work_center_type=WorkCenterType.CNC_LATHE,
            created_by="test"
        )
        db_session.add(wc)
        await db_session.commit()
        await db_session.refresh(wc)

        assert wc.id is not None
        assert wc.work_center_number == "80000001"
        assert wc.name == "Test CNC"
        assert wc.work_center_type == WorkCenterType.CNC_LATHE
        assert wc.is_active is True
        assert wc.priority == 99
        assert wc.version == 0  # AuditMixin default

    async def test_create_work_center_full(self, db_session: AsyncSession):
        """Create work center with all fields"""
        wc = WorkCenter(
            work_center_number="80000002",
            name="Full Test CNC",
            work_center_type=WorkCenterType.CNC_MILL_5AX,
            hourly_rate_amortization=500.0,
            hourly_rate_labor=300.0,
            hourly_rate_tools=200.0,
            hourly_rate_overhead=200.0,
            max_workpiece_diameter=200.0,
            max_workpiece_length=400.0,
            axes=5,
            is_active=True,
            priority=10,
            notes="Test notes",
            created_by="test"
        )
        db_session.add(wc)
        await db_session.commit()
        await db_session.refresh(wc)

        assert wc.hourly_rate_amortization == 500.0
        assert wc.axes == 5
        assert wc.notes == "Test notes"

    async def test_hourly_rate_total_computed(self, db_session: AsyncSession):
        """Test computed hourly_rate_total property"""
        wc = WorkCenter(
            work_center_number="80000003",
            name="Rate Test",
            work_center_type=WorkCenterType.CNC_LATHE,
            hourly_rate_amortization=400.0,
            hourly_rate_labor=300.0,
            hourly_rate_tools=150.0,
            hourly_rate_overhead=150.0,
            created_by="test"
        )
        db_session.add(wc)
        await db_session.commit()

        # hourly_rate_total = 400 + 300 + 150 + 150 = 1000
        assert wc.hourly_rate_total == 1000.0

    async def test_hourly_rate_total_none_when_partial(self, db_session: AsyncSession):
        """hourly_rate_total should be None if any rate is missing"""
        wc = WorkCenter(
            work_center_number="80000004",
            name="Partial Rate Test",
            work_center_type=WorkCenterType.QUALITY_CONTROL,
            hourly_rate_labor=300.0,  # Only labor, rest None
            created_by="test"
        )
        db_session.add(wc)
        await db_session.commit()

        assert wc.hourly_rate_total is None

    async def test_unique_work_center_number(self, db_session: AsyncSession):
        """Work center number must be unique"""
        wc1 = WorkCenter(
            work_center_number="80000005",
            name="First",
            work_center_type=WorkCenterType.SAW,
            created_by="test"
        )
        db_session.add(wc1)
        await db_session.commit()

        # Attempt to create duplicate
        wc2 = WorkCenter(
            work_center_number="80000005",  # Same number
            name="Second",
            work_center_type=WorkCenterType.SAW,
            created_by="test"
        )
        db_session.add(wc2)

        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()


@pytest.mark.asyncio
class TestWorkCenterSchemas:
    """Test Pydantic schemas for WorkCenter"""

    def test_work_center_create_minimal(self):
        """WorkCenterCreate with minimal fields"""
        wc = WorkCenterCreate(
            name="Test CNC",
            work_center_type=WorkCenterType.CNC_LATHE
        )
        assert wc.name == "Test CNC"
        assert wc.work_center_type == WorkCenterType.CNC_LATHE
        assert wc.work_center_number is None  # Optional, auto-generated

    def test_work_center_create_with_number(self):
        """WorkCenterCreate with provided number"""
        wc = WorkCenterCreate(
            work_center_number="80123456",
            name="Test CNC",
            work_center_type=WorkCenterType.CNC_LATHE
        )
        assert wc.work_center_number == "80123456"

    def test_work_center_create_invalid_number_format(self):
        """WorkCenterCreate should reject invalid number format"""
        with pytest.raises(ValidationError):
            WorkCenterCreate(
                work_center_number="12345678",  # Doesn't start with 80
                name="Test CNC",
                work_center_type=WorkCenterType.CNC_LATHE
            )

    def test_work_center_create_invalid_number_length(self):
        """WorkCenterCreate should reject wrong length number"""
        with pytest.raises(ValidationError):
            WorkCenterCreate(
                work_center_number="8012345",  # 7 digits, not 8
                name="Test CNC",
                work_center_type=WorkCenterType.CNC_LATHE
            )

    def test_work_center_create_invalid_type(self):
        """WorkCenterCreate should reject invalid type"""
        with pytest.raises(ValidationError):
            WorkCenterCreate(
                name="Test",
                work_center_type="INVALID_TYPE"
            )

    def test_work_center_update_partial(self):
        """WorkCenterUpdate allows partial updates"""
        wc = WorkCenterUpdate(
            name="Updated Name",
            version=1
        )
        assert wc.name == "Updated Name"
        assert wc.work_center_type is None  # Not provided
        assert wc.version == 1

    def test_work_center_update_requires_version(self):
        """WorkCenterUpdate requires version for optimistic locking"""
        with pytest.raises(ValidationError):
            WorkCenterUpdate(name="No Version")

    def test_work_center_response_from_orm(self, db_session):
        """WorkCenterResponse.from_orm should include computed fields"""
        # Create a mock WorkCenter-like object
        class MockWC:
            id = 1
            work_center_number = "80000001"
            name = "Test"
            work_center_type = WorkCenterType.CNC_LATHE
            subtype = None
            hourly_rate_amortization = 400.0
            hourly_rate_labor = 300.0
            hourly_rate_tools = 150.0
            hourly_rate_overhead = 150.0
            max_workpiece_diameter = 100.0
            max_workpiece_length = 200.0
            min_workpiece_diameter = None
            axes = 3
            max_bar_diameter = None
            max_cut_diameter = None
            bar_feed_max_length = None
            has_bar_feeder = False
            has_sub_spindle = False
            has_milling = False
            max_milling_tools = None
            suitable_for_series = True
            suitable_for_single = True
            setup_base_min = 30.0
            setup_per_tool_min = 3.0
            is_active = True
            priority = 10
            notes = "Test"
            version = 1
            created_at = None
            updated_at = None
            last_rate_changed_at = None
            batches_recalculated_at = None
            needs_batch_recalculation = False

            @property
            def hourly_rate_setup(self):
                return 850.0

            @property
            def hourly_rate_operation(self):
                return 1000.0

            @property
            def hourly_rate_total(self):
                return 1000.0

        mock_wc = MockWC()
        # Simulate required attributes
        from datetime import datetime
        mock_wc.created_at = datetime.now()
        mock_wc.updated_at = datetime.now()

        response = WorkCenterResponse.from_orm(mock_wc)

        assert response.hourly_rate_total == 1000.0
        assert response.hourly_rate_setup == 850.0
        assert response.work_center_number == "80000001"


class TestWorkCenterTypeEnum:
    """Test WorkCenterType enum"""

    def test_all_types_exist(self):
        """All expected work center types should exist"""
        expected_types = [
            "CNC_LATHE",
            "CNC_MILL_3AX",
            "CNC_MILL_4AX",
            "CNC_MILL_5AX",
            "SAW",
            "DRILL",
            "QUALITY_CONTROL",
            "MANUAL_ASSEMBLY",
            "EXTERNAL",
        ]
        actual_types = [t.value for t in WorkCenterType]

        for expected in expected_types:
            assert expected in actual_types, f"Missing type: {expected}"

    def test_type_count(self):
        """Should have exactly 9 work center types"""
        assert len(WorkCenterType) == 9


@pytest.mark.asyncio
class TestWorkCenterNumberGeneration:
    """Test sequential number generation for work centers"""

    async def test_generate_work_center_number_format(self, db_session: AsyncSession):
        """Work center number should be 8-digit starting with 80"""
        number = await NumberGenerator.generate_work_center_number(db_session)

        assert len(number) == 8, "Work center number must be 8 digits"
        assert number.isdigit(), "Work center number must be numeric"
        assert number.startswith('80'), "Work center number must start with 80"
        assert 80000001 <= int(number) <= 80999999, "Number out of range"

    async def test_generate_first_work_center_number(self, db_session: AsyncSession):
        """First work center should be 80000001"""
        number = await NumberGenerator.generate_work_center_number(db_session)
        assert number == "80000001", "First work center should be 80000001"

    async def test_generate_sequential_numbers(self, db_session: AsyncSession):
        """Work center numbers should be sequential"""
        # Create first work center
        wc1 = WorkCenter(
            work_center_number="80000001",
            name="First",
            work_center_type=WorkCenterType.CNC_LATHE,
            created_by="test"
        )
        db_session.add(wc1)
        await db_session.commit()

        # Generate next number
        number = await NumberGenerator.generate_work_center_number(db_session)
        assert number == "80000002", "Second number should be 80000002"

        # Create second and generate third
        wc2 = WorkCenter(
            work_center_number=number,
            name="Second",
            work_center_type=WorkCenterType.CNC_MILL_3AX,
            created_by="test"
        )
        db_session.add(wc2)
        await db_session.commit()

        number3 = await NumberGenerator.generate_work_center_number(db_session)
        assert number3 == "80000003", "Third number should be 80000003"

    async def test_generate_after_gap(self, db_session: AsyncSession):
        """Should continue from max, even with gaps"""
        # Create work center with number 80000010 (gap)
        wc = WorkCenter(
            work_center_number="80000010",
            name="Gap Test",
            work_center_type=WorkCenterType.SAW,
            created_by="test"
        )
        db_session.add(wc)
        await db_session.commit()

        # Next should be 80000011
        number = await NumberGenerator.generate_work_center_number(db_session)
        assert number == "80000011", "Should continue from max number"


@pytest.mark.asyncio
class TestWorkCenterAPI:
    """Test WorkCenter API endpoints"""

    async def test_get_work_centers_empty(self, client, admin_headers):
        """GET /api/work-centers should return empty list initially"""
        response = await client.get("/api/work-centers/", headers=admin_headers)
        assert response.status_code == 200
        assert response.json() == []

    async def test_create_work_center(self, client, admin_headers):
        """POST /api/work-centers should create work center"""
        data = {
            "name": "API Test CNC",
            "work_center_type": "CNC_LATHE",
            "hourly_rate_amortization": 400.0,
            "hourly_rate_labor": 300.0,
            "hourly_rate_tools": 150.0,
            "hourly_rate_overhead": 150.0,
        }
        response = await client.post("/api/work-centers/", json=data, headers=admin_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["name"] == "API Test CNC"
        assert result["work_center_type"] == "CNC_LATHE"
        assert result["work_center_number"].startswith("80")
        assert len(result["work_center_number"]) == 8
        assert result["hourly_rate_total"] == 1000.0

    async def test_create_work_center_with_number(self, client, admin_headers):
        """POST /api/work-centers with provided number"""
        data = {
            "work_center_number": "80999999",
            "name": "Specific Number CNC",
            "work_center_type": "CNC_MILL_5AX",
        }
        response = await client.post("/api/work-centers/", json=data, headers=admin_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["work_center_number"] == "80999999"

    async def test_get_work_center_by_number(self, client, admin_headers):
        """GET /api/work-centers/{number} should return work center"""
        # First create one
        data = {
            "name": "Get Test CNC",
            "work_center_type": "SAW",
        }
        create_response = await client.post("/api/work-centers/", json=data, headers=admin_headers)
        wc_number = create_response.json()["work_center_number"]

        # Then get it
        response = await client.get(f"/api/work-centers/{wc_number}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Get Test CNC"

    async def test_get_work_center_not_found(self, client, admin_headers):
        """GET /api/work-centers/{number} should return 404 for non-existent"""
        response = await client.get("/api/work-centers/80888888", headers=admin_headers)
        assert response.status_code == 404

    async def test_update_work_center(self, client, admin_headers):
        """PUT /api/work-centers/{number} should update work center"""
        # Create
        data = {
            "name": "Update Test",
            "work_center_type": "DRILL",
        }
        create_response = await client.post("/api/work-centers/", json=data, headers=admin_headers)
        result = create_response.json()
        wc_number = result["work_center_number"]
        version = result["version"]

        # Update
        update_data = {
            "name": "Updated Name",
            "priority": 5,
            "version": version
        }
        response = await client.put(f"/api/work-centers/{wc_number}", json=update_data, headers=admin_headers)

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["priority"] == 5
        assert response.json()["version"] == version + 1

    async def test_update_work_center_version_conflict(self, client, admin_headers):
        """PUT with wrong version should return 409"""
        # Create
        data = {
            "name": "Version Test",
            "work_center_type": "EXTERNAL",
        }
        create_response = await client.post("/api/work-centers/", json=data, headers=admin_headers)
        wc_number = create_response.json()["work_center_number"]

        # Update with wrong version
        update_data = {
            "name": "Won't Work",
            "version": 999  # Wrong version
        }
        response = await client.put(f"/api/work-centers/{wc_number}", json=update_data, headers=admin_headers)

        assert response.status_code == 409

    async def test_delete_work_center(self, client, admin_headers):
        """DELETE /api/work-centers/{number} should delete work center"""
        # Create
        data = {
            "name": "Delete Test",
            "work_center_type": "QUALITY_CONTROL",
        }
        create_response = await client.post("/api/work-centers/", json=data, headers=admin_headers)
        wc_number = create_response.json()["work_center_number"]

        # Delete
        response = await client.delete(f"/api/work-centers/{wc_number}", headers=admin_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = await client.get(f"/api/work-centers/{wc_number}", headers=admin_headers)
        assert get_response.status_code == 404

    async def test_get_work_center_types(self, client, admin_headers):
        """GET /api/work-centers/types should return all types"""
        response = await client.get("/api/work-centers/types", headers=admin_headers)

        assert response.status_code == 200
        types = response.json()
        assert len(types) == 9

        type_values = [t["value"] for t in types]
        assert "CNC_LATHE" in type_values
        assert "CNC_MILL_5AX" in type_values
        assert "EXTERNAL" in type_values

    async def test_search_work_centers(self, client, admin_headers):
        """GET /api/work-centers/search should filter results"""
        # Create test data
        await client.post("/api/work-centers/", json={
            "name": "Search Test Lathe",
            "work_center_type": "CNC_LATHE"
        }, headers=admin_headers)
        await client.post("/api/work-centers/", json={
            "name": "Search Test Mill",
            "work_center_type": "CNC_MILL_3AX"
        }, headers=admin_headers)

        # Search by name
        response = await client.get("/api/work-centers/search?search=Lathe", headers=admin_headers)
        assert response.status_code == 200
        result = response.json()
        assert result["total"] >= 1
        assert any("Lathe" in wc["name"] for wc in result["work_centers"])

    async def test_filter_by_type(self, client, admin_headers):
        """GET /api/work-centers should filter by type"""
        # Create test data
        await client.post("/api/work-centers/", json={
            "name": "Type Filter Lathe",
            "work_center_type": "CNC_LATHE"
        }, headers=admin_headers)
        await client.post("/api/work-centers/", json={
            "name": "Type Filter Mill",
            "work_center_type": "CNC_MILL_3AX"
        }, headers=admin_headers)

        # Filter by type
        response = await client.get("/api/work-centers/?work_center_type=CNC_LATHE", headers=admin_headers)
        assert response.status_code == 200
        results = response.json()
        assert all(wc["work_center_type"] == "CNC_LATHE" for wc in results)

    async def test_requires_authentication(self, client):
        """API endpoints should require authentication"""
        response = await client.get("/api/work-centers/")
        assert response.status_code == 401

    async def test_delete_requires_admin(self, client, operator_headers, admin_headers):
        """DELETE should require admin role"""
        # Create as admin
        create_response = await client.post("/api/work-centers/", json={
            "name": "Admin Only Delete",
            "work_center_type": "SAW"
        }, headers=admin_headers)
        wc_number = create_response.json()["work_center_number"]

        # Try to delete as operator
        response = await client.delete(f"/api/work-centers/{wc_number}", headers=operator_headers)
        assert response.status_code == 403
