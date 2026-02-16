"""GESTIMA - Tests for Infor import infrastructure

Tests generic import system with Parts, Operations, and ProductionRecords.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.infor_part_importer import PartImporter
from app.services.infor_job_routing_importer import JobRoutingImporter
from app.services.infor_production_importer import ProductionImporter
from app.services.infor_wc_mapper import InforWcMapper
from app.models.part import Part
from app.models.operation import Operation
from app.models.production_record import ProductionRecord
from app.models.work_center import WorkCenter
from app.models.enums import WorkCenterType


@pytest.mark.asyncio
async def test_wc_mapper_basic(db_session: AsyncSession):
    """Test InforWcMapper basic functionality."""
    # Create test WorkCenter
    wc = WorkCenter(
        work_center_number="80000001",
        name="Test WC",
        work_center_type=WorkCenterType.CNC_LATHE
    )
    db_session.add(wc)
    try:
        await db_session.commit()
        await db_session.refresh(wc)
    except Exception:
        await db_session.rollback()
        raise

    # Test mapping
    mapper = InforWcMapper('{"100": "80000001"}')

    # Test successful resolution
    wc_id, warning = await mapper.resolve("100", db_session)
    assert wc_id == wc.id
    assert warning is None

    # Test cache hit
    wc_id2, warning2 = await mapper.resolve("100", db_session)
    assert wc_id2 == wc.id
    assert warning2 is None

    # Test unknown code
    wc_id3, warning3 = await mapper.resolve("999", db_session)
    assert wc_id3 is None
    assert "Neznámý Infor WC kód" in warning3


@pytest.mark.asyncio
async def test_part_importer_basic(db_session: AsyncSession):
    """Test PartImporter preview and execute."""
    importer = PartImporter()

    # Test preview
    test_rows = [
        {
            "Job": "TEST001",
            "Description": "Test Part",
            "DrawingNbr": "DWG001",
            "CustRevision": "A"
        }
    ]

    preview = await importer.preview_import(test_rows, db_session)

    assert preview["valid_count"] == 1
    assert preview["error_count"] == 0
    assert len(preview["rows"]) == 1

    row = preview["rows"][0]
    assert row["mapped_data"]["article_number"] == "TEST001"
    assert row["mapped_data"]["name"] == "Test Part"

    # Test execute (requires duplicate_action field)
    execute_rows = [
        {
            "article_number": "TEST001",
            "name": "Test Part",
            "drawing_number": "DWG001",
            "customer_revision": "A",
            "duplicate_action": "skip"
        }
    ]

    result = await importer.execute_import(execute_rows, db_session)

    assert result["created_count"] == 1
    assert len(result["errors"]) == 0

    # Verify Part was created
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(Part).where(Part.article_number == "TEST001")
    )
    part = db_result.scalar_one_or_none()
    assert part is not None
    assert part.name == "Test Part"
    assert part.part_number.startswith("10")  # Auto-generated


@pytest.mark.asyncio
async def test_routing_importer_basic(db_session: AsyncSession):
    """Test JobRoutingImporter with Part context."""
    # Create test Part
    part = Part(
        part_number="10000001",
        article_number="TEST_ROUTING",
        name="Test Routing Part",
        revision="A",
        status="active",
        length=0.0
    )
    db_session.add(part)
    try:
        await db_session.commit()
        await db_session.refresh(part)
    except Exception:
        await db_session.rollback()
        raise

    # Create test WorkCenter
    wc = WorkCenter(
        work_center_number="80000001",
        name="Test WC",
        work_center_type=WorkCenterType.CNC_LATHE
    )
    db_session.add(wc)
    try:
        await db_session.commit()
        await db_session.refresh(wc)
    except Exception:
        await db_session.rollback()
        raise

    # Test importer with WC mapping
    wc_mapper = InforWcMapper('{"100": "80000001"}')
    importer = JobRoutingImporter(part_id=part.id, wc_mapper=wc_mapper)

    test_rows = [
        {
            "OperNum": "10",
            "Wc": "100",
            "Description": "Turning",
            "SetupHrsTPc": "0.5",
            "RunHrsTPc": "2.0"
        }
    ]

    preview = await importer.preview_import(test_rows, db_session)
    assert preview["valid_count"] == 1

    # Execute
    execute_rows = [
        {
            "seq": 10,
            "name": "Turning",
            "work_center_id": wc.id,
            "setup_time_min": 30.0,
            "operation_time_min": 120.0,
            "duplicate_action": "skip"
        }
    ]

    result = await importer.execute_import(execute_rows, db_session)
    assert result["created_count"] == 1

    # Verify Operation was created
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(Operation).where(
            Operation.part_id == part.id,
            Operation.seq == 10
        )
    )
    operation = db_result.scalar_one_or_none()
    assert operation is not None
    assert operation.name == "Turning"
    assert operation.work_center_id == wc.id


@pytest.mark.asyncio
async def test_production_importer_basic(db_session: AsyncSession):
    """Test ProductionImporter with Part resolution."""
    # Create test Part
    part = Part(
        part_number="10000002",
        article_number="TEST_PROD",
        name="Test Production Part",
        revision="A",
        status="active",
        length=0.0
    )
    db_session.add(part)
    try:
        await db_session.commit()
        await db_session.refresh(part)
    except Exception:
        await db_session.rollback()
        raise

    # Create test WorkCenter
    wc = WorkCenter(
        work_center_number="80000002",
        name="Test WC 2",
        work_center_type=WorkCenterType.CNC_MILL_3AX
    )
    db_session.add(wc)
    try:
        await db_session.commit()
        await db_session.refresh(wc)
    except Exception:
        await db_session.rollback()
        raise

    # Test importer
    wc_mapper = InforWcMapper('{"200": "80000002"}')
    importer = ProductionImporter(wc_mapper=wc_mapper)

    test_rows = [
        {
            "Job": "ORDER001",
            "Item": "TEST_PROD",
            "OperNum": "10",
            "Wc": "200",
            "QtyComplete": "50",
            "RunHrsTPc": "2.0",
            "ActRunHrs": "2.5"
        }
    ]

    preview = await importer.preview_import(test_rows, db_session)
    assert preview["valid_count"] == 1

    # Execute
    execute_rows = [
        {
            "part_id": part.id,
            "infor_order_number": "ORDER001",
            "operation_seq": 10,
            "work_center_id": wc.id,
            "batch_quantity": 50,
            "planned_time_min": 120.0,
            "actual_time_min": 150.0,
            "duplicate_action": "skip"
        }
    ]

    result = await importer.execute_import(execute_rows, db_session)
    assert result["created_count"] == 1

    # Verify ProductionRecord was created
    from sqlalchemy import select
    db_result = await db_session.execute(
        select(ProductionRecord).where(
            ProductionRecord.part_id == part.id,
            ProductionRecord.infor_order_number == "ORDER001"
        )
    )
    record = db_result.scalar_one_or_none()
    assert record is not None
    assert record.batch_quantity == 50
    assert record.source == "infor"
