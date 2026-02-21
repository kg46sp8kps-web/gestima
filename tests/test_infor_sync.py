"""GESTIMA - Tests for Infor Smart Polling Sync Service

Tests sync service dispatch logic, date filter construction,
and state management.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.models.operation import Operation
from app.models.work_center import WorkCenter
from app.models.enums import WorkCenterType
from app.services.infor_sync_service import InforSyncService


@pytest.mark.asyncio
async def test_extract_valid_rows():
    """Test _extract_valid_rows extracts correct rows and sets duplicate_action."""
    service = InforSyncService()

    preview_result = {
        "valid_count": 2,
        "error_count": 1,
        "duplicate_count": 1,
        "rows": [
            {
                "row_index": 0,
                "infor_data": {"Item": "A"},
                "mapped_data": {"article_number": "A", "name": "Part A"},
                "validation": {"is_valid": True, "is_duplicate": False, "errors": [], "warnings": []},
            },
            {
                "row_index": 1,
                "infor_data": {"Item": "B"},
                "mapped_data": {"article_number": "B", "name": "Part B"},
                "validation": {"is_valid": False, "is_duplicate": False, "errors": ["Missing field"], "warnings": []},
            },
            {
                "row_index": 2,
                "infor_data": {"Item": "C"},
                "mapped_data": {"article_number": "C", "name": "Part C"},
                "validation": {"is_valid": True, "is_duplicate": True, "errors": [], "warnings": ["Exists"]},
            },
        ],
    }

    valid = service._extract_valid_rows(preview_result)

    # Row 0 (valid) and Row 2 (duplicate but valid) should be extracted
    assert len(valid) == 2
    assert valid[0]["article_number"] == "A"
    assert valid[0]["duplicate_action"] == "update"
    assert valid[1]["article_number"] == "C"
    assert valid[1]["duplicate_action"] == "update"


@pytest.mark.asyncio
async def test_extract_valid_rows_empty():
    """Test _extract_valid_rows with no valid rows."""
    service = InforSyncService()
    result = service._extract_valid_rows({"rows": []})
    assert result == []


@pytest.mark.asyncio
async def test_dispatch_step_empty_rows(db_session: AsyncSession):
    """Test _dispatch_step returns empty result for empty rows."""
    service = InforSyncService()
    result = await service._dispatch_step("parts", [], db_session)
    assert result["created_count"] == 0
    assert result["updated_count"] == 0
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_dispatch_step_unknown_step(db_session: AsyncSession):
    """Test _dispatch_step returns error for unknown step name."""
    service = InforSyncService()
    result = await service._dispatch_step("unknown_step", [{"foo": "bar"}], db_session)
    assert "Unknown step" in result["errors"][0]


@pytest.mark.asyncio
async def test_dispatch_step_documents_no_client(db_session: AsyncSession):
    """Test documents dispatch requires client."""
    service = InforSyncService()
    result = await service._dispatch_step("documents", [{"doc": "data"}], db_session, client=None)
    assert len(result["errors"]) == 1
    assert "client" in result["errors"][0].lower()


@pytest.mark.asyncio
async def test_dispatch_operations_no_matching_parts(db_session: AsyncSession):
    """Test operations dispatch skips rows for unknown article numbers."""
    from app.services.infor_sync_dispatchers import dispatch_operations

    rows = [
        {"DerJobItem": "NONEXISTENT-123", "OperNum": "10", "Wc": "100"},
        {"DerJobItem": "NONEXISTENT-456", "OperNum": "20", "Wc": "200"},
    ]

    result = await dispatch_operations(rows, db_session)
    assert result["created_count"] == 0
    assert result["updated_count"] == 0


@pytest.mark.asyncio
async def test_dispatch_operations_with_part(db_session: AsyncSession):
    """Test operations dispatch creates operations for existing parts."""
    from app.services.infor_sync_dispatchers import dispatch_operations

    # Create test WorkCenter
    wc = WorkCenter(
        work_center_number="80000001",
        name="Test WC",
        work_center_type=WorkCenterType.CNC_LATHE,
    )
    db_session.add(wc)
    await db_session.flush()

    # Create test Part
    part = Part(
        part_number="10000001",
        article_number="TEST-SYNC-001",
        name="Test Part",
        created_by="test",
    )
    db_session.add(part)
    try:
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise

    rows = [
        {
            "DerJobItem": "TEST-SYNC-001",
            "OperNum": "10",
            "Wc": "SH2",
            "DerRunMchHrs": "60",
            "DerRunLbrHrs": "60",
            "JshSetupHrs": "0.5",
            "JshSchedHrs": "0.5",
        },
    ]

    with patch.dict("app.config.settings.__dict__", {"INFOR_WC_MAPPING": '{"SH2": "80000001"}'}):
        result = await dispatch_operations(rows, db_session)

    assert result["created_count"] == 1
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_dispatch_production_no_matching_parts(db_session: AsyncSession):
    """Test production dispatch skips rows for unknown article numbers."""
    from app.services.infor_sync_dispatchers import dispatch_production

    rows = [
        {
            "Job": "ORDER001",
            "JobItem": "NONEXISTENT",
            "OperNum": "10",
            "Wc": "100",
            "JobQtyReleased": "50",
        },
    ]

    result = await dispatch_production(rows, db_session)
    assert result["created_count"] == 0


@pytest.mark.asyncio
async def test_dispatch_material_inputs_no_matching_parts(db_session: AsyncSession):
    """Test material inputs dispatch skips rows for unknown article numbers."""
    from app.services.infor_sync_dispatchers import dispatch_material_inputs

    rows = [
        {"ItmItem": "NONEXISTENT", "Item": "11SMn30-D50", "OperNum": "10"},
    ]

    result = await dispatch_material_inputs(rows, db_session)
    assert result["created_count"] == 0


@pytest.mark.asyncio
async def test_dispatch_material_inputs_empty():
    """Test material inputs dispatch returns empty for no rows."""
    from app.services.infor_sync_dispatchers import dispatch_material_inputs

    result = await dispatch_material_inputs([], None)
    assert result["created_count"] == 0


@pytest.mark.asyncio
async def test_dispatch_documents_empty():
    """Test documents dispatch returns empty for no rows."""
    from app.services.infor_sync_dispatchers import dispatch_documents

    result = await dispatch_documents([], None, None)
    assert result["created_count"] == 0


@pytest.mark.asyncio
async def test_service_start_stop():
    """Test sync service start/stop lifecycle."""
    service = InforSyncService()
    assert service.running is False

    # Mock _ensure_default_steps to avoid DB access
    service._ensure_default_steps = AsyncMock()

    await service.start()
    assert service.running is True

    await service.stop()
    assert service.running is False


@pytest.mark.asyncio
async def test_service_double_start():
    """Test that starting an already running service is a no-op."""
    service = InforSyncService()
    service._ensure_default_steps = AsyncMock()

    await service.start()
    assert service.running is True

    # Second start should not error
    await service.start()
    assert service.running is True

    await service.stop()


@pytest.mark.asyncio
async def test_default_steps_config():
    """Test that DEFAULT_STEPS has all 6 required steps."""
    from app.services.infor_sync_service import DEFAULT_STEPS

    step_names = [s["step_name"] for s in DEFAULT_STEPS]
    assert "parts" in step_names
    assert "materials" in step_names
    assert "documents" in step_names
    assert "operations" in step_names
    assert "material_inputs" in step_names
    assert "production" in step_names
    assert len(DEFAULT_STEPS) == 6

    # Verify all steps have required fields
    for step in DEFAULT_STEPS:
        assert "step_name" in step
        assert "ido_name" in step
        assert "properties" in step
        assert "date_field" in step
        assert "interval_seconds" in step
        assert step["interval_seconds"] >= 10


@pytest.mark.asyncio
async def test_sync_state_model():
    """Test SyncState pydantic schemas."""
    from app.models.sync_state import SyncStateUpdate

    # Valid update
    update = SyncStateUpdate(enabled=True, interval_seconds=60)
    assert update.enabled is True
    assert update.interval_seconds == 60

    # Interval validation (min 10, max 3600)
    with pytest.raises(Exception):
        SyncStateUpdate(interval_seconds=5)

    with pytest.raises(Exception):
        SyncStateUpdate(interval_seconds=5000)
