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
            "Item": "TEST001",
            "Description": "Test Part",
            "DrawingNbr": "DWG001",
            "Revision": "A"
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

    # Infor Type='J' field names (new correct mapping)
    # DerRunMchHrs=30 → planned_time_min = 60/30 = 2.0 min/ks
    # DerRunLbrHrs=15 → planned_labor_time_min = 60/15 = 4.0 min/ks
    # manning plán = (Mch/Lbr)*100 = (30/15)*100 = 200% (2 obsluhy na stroj)
    # RunHrsTMch=1.8 → actual_run_machine_min=108, actual_time_min=108/50=2.16
    # RunHrsTLbr=2.0 → actual_run_labor_min=120, actual_labor_time_min=120/50=2.4
    # manning real = (Lbr/Mch)*100 = (2.0/1.8)*100 = 111.1%
    test_rows = [
        {
            "Job": "ORDER001",
            "JobItem": "TEST_PROD",
            "OperNum": "10",
            "Wc": "200",
            "JobQtyReleased": "50",
            "DerRunMchHrs": "30.0",    # 60/30 = 2.0 min/ks planned machine
            "DerRunLbrHrs": "15.0",    # 60/15 = 4.0 min/ks planned labor, manning=200%
            "JshSetupHrs": "0.5",      # planned_setup_min = 30
            "SetupHrsT": "0.6",        # actual_setup_min = 36
            "RunHrsTMch": "1.8",       # actual_run_machine_min = 108, actual_time_min = 108/50 = 2.16
            "RunHrsTLbr": "2.0",       # actual_run_labor_min = 120, actual_labor_time_min = 120/50 = 2.4
        }
    ]

    preview = await importer.preview_import(test_rows, db_session)
    assert preview["valid_count"] == 1

    # Verify preview mapped_data contains all per-piece fields
    staged = preview["rows"][0]
    assert staged["mapped_data"]["planned_time_min"] == pytest.approx(2.0, abs=0.01)
    assert staged["mapped_data"]["planned_labor_time_min"] == pytest.approx(4.0, abs=0.01)
    assert staged["mapped_data"]["planned_setup_min"] == pytest.approx(30.0, abs=0.1)
    assert staged["mapped_data"]["actual_time_min"] == pytest.approx(2.16, abs=0.01)
    assert staged["mapped_data"]["actual_labor_time_min"] == pytest.approx(2.4, abs=0.01)
    # Manning plán = (Mch/Lbr)*100 → (30/15)*100 = 200%
    assert staged["mapped_data"]["manning_coefficient"] == pytest.approx(200.0, abs=0.1)
    # Actual manning = (RunLbr/RunMch)*100 → (2.0/1.8)*100 = 111.1%
    assert staged["mapped_data"]["actual_manning_coefficient"] == pytest.approx(111.1, abs=0.2)

    # Execute — rows come with mapped fields (as produced by preview)
    execute_rows = [
        {
            "part_id": part.id,
            "infor_order_number": "ORDER001",
            "operation_seq": 10,
            "work_center_id": wc.id,
            "batch_quantity": 50,
            "planned_time_min": 2.0,
            "planned_labor_time_min": 4.0,
            "planned_setup_min": 30.0,
            "actual_time_min": 2.16,
            "actual_labor_time_min": 2.4,
            "actual_setup_min": 36.0,
            "actual_run_machine_min": 108.0,
            "actual_run_labor_min": 120.0,
            "manning_coefficient": 200.0,
            "actual_manning_coefficient": 111.1,
            "duplicate_action": "skip",
        }
    ]

    result = await importer.execute_import(execute_rows, db_session)
    assert result["created_count"] == 1

    # Verify ProductionRecord was created with ALL fields (planned + actual per-piece)
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
    # Planned per-piece
    assert record.planned_time_min == pytest.approx(2.0, abs=0.01)
    assert record.planned_labor_time_min == pytest.approx(4.0, abs=0.01)
    assert record.planned_setup_min == pytest.approx(30.0, abs=0.1)
    # Actual per-piece
    assert record.actual_time_min == pytest.approx(2.16, abs=0.01)
    assert record.actual_labor_time_min == pytest.approx(2.4, abs=0.01)
    assert record.actual_setup_min == pytest.approx(36.0, abs=0.1)
    # Actual batch totals
    assert record.actual_run_machine_min == pytest.approx(108.0, abs=0.1)
    assert record.actual_run_labor_min == pytest.approx(120.0, abs=0.1)
    # Manning plán = (Mch/Lbr)*100 = 200%
    assert record.manning_coefficient == pytest.approx(200.0, abs=0.1)
    # Manning real = (RunLbr/RunMch)*100 = 111.1%
    assert record.actual_manning_coefficient == pytest.approx(111.1, abs=0.2)
