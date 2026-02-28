"""Tests for Production Planner service."""

from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, date
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.production_priority import ProductionPriority
from app.services import production_planner_service
from app.services.production_planner_service import (
    _add_work_hours,
    _clamp_to_work_start,
    _compute_duration_hrs,
    _derive_tier,
    _schedule_operations,
)


@pytest_asyncio.fixture
async def db():
    """In-memory DB for production planner tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


def _infor_row(job="22VP10", suffix="250", oper="10", wc="SH2A", **kw):
    """Helper: fake Infor operation row.

    DerRunMchHrs = ks/hod (pieces per machine hour), default 20 = 3min/ks.
    JshSetupHrs = setup in hours, default 0.5h = 30min.
    """
    row = {
        "Job": job,
        "Suffix": suffix,
        "OperNum": oper,
        "Wc": wc,
        "DerJobItem": kw.get("item", "DK-1234"),
        "JobDescription": kw.get("desc", "Hřídel"),
        "JobQtyReleased": kw.get("qty_released", 100),
        "QtyComplete": kw.get("qty_complete", 0),
        "QtyScrapped": kw.get("qty_scrapped", 0),
        "JshSetupHrs": kw.get("setup_hrs", 0.5),
        "DerRunMchHrs": kw.get("run_hrs", 20.0),  # ks/hod
        "JobStat": kw.get("stat", "R"),
        "OpDatumSt": kw.get("start", "2026-03-01"),
        "OpDatumSp": kw.get("end", "2026-03-05"),
    }
    row.update(kw)
    return row


def _mock_infor_client(machine_plan_rows, co_items_rows=None):
    """Create mock infor client that returns specified data."""
    client = AsyncMock()

    async def mock_load_collection(**kwargs):
        ido_name = kwargs.get("ido_name", "")
        if ido_name == "SLCoitems":
            return {"data": co_items_rows or [], "message_code": 0}
        return {"data": machine_plan_rows, "message_code": 0}

    client.load_collection.side_effect = mock_load_collection
    return client


# ============================================================================
# fetch_planner_data
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_planner_data_basic(db):
    """Basic fetch returns VP-grouped data."""
    rows = [
        _infor_row(oper="10", wc="SH2A"),
        _infor_row(oper="20", wc="FR1B"),
    ]

    client = _mock_infor_client(rows)
    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, client)

    assert len(result["vps"]) == 1
    vp = result["vps"][0]
    assert vp["job"] == "22VP10"
    assert vp["suffix"] == "250"
    assert len(vp["operations"]) == 2
    assert vp["priority"] == 100
    assert vp["is_hot"] is False
    assert "time_range" in result


@pytest.mark.asyncio
async def test_fetch_planner_data_multiple_vps(db):
    """Multiple VPs are grouped correctly."""
    rows = [
        _infor_row(job="22VP10", suffix="250", oper="10"),
        _infor_row(job="22VP10", suffix="251", oper="10"),
        _infor_row(job="22VP20", suffix="0", oper="10"),
    ]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert len(result["vps"]) == 3


@pytest.mark.asyncio
async def test_fetch_planner_data_with_priority(db):
    """Local priority is merged into VP data."""
    # Seed priority
    entry = ProductionPriority(
        infor_job="22VP10", infor_suffix="250",
        priority=50, is_hot=False, created_by="test",
    )
    db.add(entry)
    await db.commit()

    rows = [_infor_row()]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert result["vps"][0]["priority"] == 50


@pytest.mark.asyncio
async def test_fetch_planner_data_hot_sort(db):
    """Hot VP sorts to top."""
    entry = ProductionPriority(
        infor_job="22VP20", infor_suffix="0",
        priority=100, is_hot=True, created_by="test",
    )
    db.add(entry)
    await db.commit()

    rows = [
        _infor_row(job="22VP10", suffix="250", oper="10"),
        _infor_row(job="22VP20", suffix="0", oper="10"),
    ]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert result["vps"][0]["job"] == "22VP20"
    assert result["vps"][0]["is_hot"] is True


@pytest.mark.asyncio
async def test_fetch_planner_data_op_status(db):
    """Operation status detection."""
    rows = [
        _infor_row(oper="10", qty_released=100, qty_complete=100),  # done
        _infor_row(oper="20", qty_released=100, qty_complete=50),   # in_progress
        _infor_row(oper="30", qty_released=100, qty_complete=0),    # idle
    ]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    ops = result["vps"][0]["operations"]
    assert ops[0]["status"] == "done"
    assert ops[1]["status"] == "in_progress"
    assert ops[2]["status"] == "idle"


@pytest.mark.asyncio
async def test_fetch_planner_data_done_vps_at_end(db):
    """All-done VPs sort to the end."""
    rows = [
        _infor_row(job="22VP10", suffix="250", oper="10", qty_released=100, qty_complete=100),
        _infor_row(job="22VP20", suffix="0", oper="10", qty_released=100, qty_complete=0),
    ]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    # VP20 (idle) should be before VP10 (done)
    assert result["vps"][0]["job"] == "22VP20"
    assert result["vps"][1]["job"] == "22VP10"


@pytest.mark.asyncio
async def test_fetch_planner_data_empty(db):
    """No data from Infor returns empty."""
    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert result["vps"] == []
    assert "time_range" in result


# ============================================================================
# set_priority
# ============================================================================

@pytest.mark.asyncio
async def test_set_priority_new(db):
    """Create new priority entry."""
    entry = await production_planner_service.set_priority(db, "22VP10", "250", 50, "mistr")
    assert entry.infor_job == "22VP10"
    assert entry.infor_suffix == "250"
    assert entry.priority == 50


@pytest.mark.asyncio
async def test_set_priority_update(db):
    """Update existing priority."""
    await production_planner_service.set_priority(db, "22VP10", "250", 50, "mistr")
    entry = await production_planner_service.set_priority(db, "22VP10", "250", 30, "mistr")
    assert entry.priority == 30


@pytest.mark.asyncio
async def test_set_priority_case_insensitive(db):
    """Job is uppercased for consistent matching."""
    entry = await production_planner_service.set_priority(db, "22vp10", "250", 50, "mistr")
    assert entry.infor_job == "22VP10"


# ============================================================================
# set_hot
# ============================================================================

@pytest.mark.asyncio
async def test_set_hot_new(db):
    """Set hot on new VP."""
    entry = await production_planner_service.set_hot(db, "22VP10", "250", True, "mistr")
    assert entry.is_hot is True


@pytest.mark.asyncio
async def test_set_hot_allows_multiple(db):
    """Setting hot=True on multiple VPs keeps all hot."""
    await production_planner_service.set_hot(db, "22VP10", "250", True, "mistr")
    await production_planner_service.set_hot(db, "22VP20", "0", True, "mistr")

    from sqlalchemy import select
    result = await db.execute(select(ProductionPriority).where(ProductionPriority.is_hot.is_(True)))
    hot_entries = result.scalars().all()
    assert len(hot_entries) == 2


@pytest.mark.asyncio
async def test_set_hot_toggle_off(db):
    """Toggle hot off."""
    await production_planner_service.set_hot(db, "22VP10", "250", True, "mistr")
    entry = await production_planner_service.set_hot(db, "22VP10", "250", False, "mistr")
    assert entry.is_hot is False


@pytest.mark.asyncio
async def test_set_hot_preserves_priority(db):
    """Setting hot doesn't change priority."""
    await production_planner_service.set_priority(db, "22VP10", "250", 42, "mistr")
    entry = await production_planner_service.set_hot(db, "22VP10", "250", True, "mistr")
    assert entry.priority == 42
    assert entry.is_hot is True


# ============================================================================
# _fetch_co_deadlines
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_co_deadlines_empty():
    """No items → empty result."""
    result = await production_planner_service._fetch_co_deadlines(AsyncMock(), [])
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_co_deadlines_basic():
    """Basic CO lookup returns deadline info."""
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Item": "DK-1234",
                "CoNum": "CO001",
                "CoLine": "1",
                "DueDate": "2026-03-15",
                "PromiseDate": None,
                "CustName": "SIEMENS",
                "QtyOrderedConv": 100,
                "QtyShipped": 0,
            }
        ],
    }

    result = await production_planner_service._fetch_co_deadlines(client, ["DK-1234"])
    assert "DK-1234" in result
    assert result["DK-1234"]["co_num"] == "CO001"
    assert result["DK-1234"]["customer_name"] == "SIEMENS"


@pytest.mark.asyncio
async def test_fetch_co_deadlines_multiple_cos_takes_nearest():
    """Multiple COs on same Item → pick nearest DueDate."""
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {"Item": "DK-1234", "CoNum": "CO001", "DueDate": "2026-03-15", "CoCustNum": "A", "QtyOrdered": 100, "QtyShipped": 0, "CoLine": "1", "PromiseDate": None},
            {"Item": "DK-1234", "CoNum": "CO002", "DueDate": "2026-03-10", "CoCustNum": "B", "QtyOrdered": 50, "QtyShipped": 0, "CoLine": "1", "PromiseDate": None},
        ],
    }

    result = await production_planner_service._fetch_co_deadlines(client, ["DK-1234"])
    # Nearest DueDate = CO002 (3-10)
    assert result["DK-1234"]["co_num"] == "CO002"


# ============================================================================
# Edge cases
# ============================================================================

@pytest.mark.asyncio
async def test_vp_without_operations_skipped(db):
    """VP with no operations after grouping is skipped."""
    rows = [
        _infor_row(job="22VP10", suffix="250", oper="10"),
    ]
    # Add a row with missing job — will be skipped
    rows.append({"Job": None, "OperNum": "10"})

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert len(result["vps"]) == 1


@pytest.mark.asyncio
async def test_delay_calculation(db):
    """VP sched_end after CO due → is_delayed with delay_days.

    CO deadline set in the past so any scheduled op will be delayed.
    """
    rows = [
        _infor_row(item="DK-1234", end="2026-03-20"),
    ]

    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {"Item": "DK-1234", "CoNum": "CO001", "DueDate": "2025-01-01", "CoCustNum": "X",
             "QtyOrdered": 100, "QtyShipped": 0, "CoLine": "1", "PromiseDate": None},
        ],
    }

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, client)

    vp = result["vps"][0]
    assert vp["is_delayed"] is True
    assert vp["delay_days"] is not None and vp["delay_days"] > 0


# ============================================================================
# Scheduling helpers — unit tests
# ============================================================================


class TestClampToWorkStart:
    def test_weekday_during_shift(self):
        # Wednesday 10:00 → stays
        dt = datetime(2026, 3, 4, 10, 0)  # Wednesday
        assert _clamp_to_work_start(dt) == dt

    def test_weekday_before_shift(self):
        # Wednesday 05:00 → 07:00
        dt = datetime(2026, 3, 4, 5, 0)
        result = _clamp_to_work_start(dt)
        assert result.hour == 7
        assert result.minute == 0

    def test_weekday_after_shift(self):
        # Wednesday 16:00 → Thursday 07:00
        dt = datetime(2026, 3, 4, 16, 0)
        result = _clamp_to_work_start(dt)
        assert result.day == 5
        assert result.hour == 7

    def test_saturday(self):
        # Saturday → Monday 07:00
        dt = datetime(2026, 3, 7, 10, 0)  # Saturday
        result = _clamp_to_work_start(dt)
        assert result.weekday() == 0  # Monday
        assert result.hour == 7

    def test_sunday(self):
        # Sunday → Monday 07:00
        dt = datetime(2026, 3, 8, 10, 0)  # Sunday
        result = _clamp_to_work_start(dt)
        assert result.weekday() == 0
        assert result.hour == 7

    def test_friday_after_shift(self):
        # Friday 15:30 → Monday 07:00
        dt = datetime(2026, 3, 6, 15, 30)  # Friday
        result = _clamp_to_work_start(dt)
        assert result.weekday() == 0  # Monday
        assert result.day == 9
        assert result.hour == 7


class TestAddWorkHours:
    def test_basic_4h(self):
        """4h from 07:00 → 11:00 same day."""
        start = datetime(2026, 3, 2, 7, 0)  # Monday
        result = _add_work_hours(start, 4.0)
        assert result == datetime(2026, 3, 2, 11, 0)

    def test_full_day(self):
        """8h from 07:00 → 15:00 same day."""
        start = datetime(2026, 3, 2, 7, 0)
        result = _add_work_hours(start, 8.0)
        assert result == datetime(2026, 3, 2, 15, 0)

    def test_cross_day(self):
        """12h from 07:00 → next day 11:00."""
        start = datetime(2026, 3, 2, 7, 0)  # Monday
        result = _add_work_hours(start, 12.0)
        # 8h on Monday = 15:00, 4h left on Tuesday = 11:00
        assert result == datetime(2026, 3, 3, 11, 0)

    def test_weekend_skip(self):
        """Work starting Friday 11:00 with 8h → Monday 11:00."""
        start = datetime(2026, 3, 6, 11, 0)  # Friday
        result = _add_work_hours(start, 8.0)
        # 4h on Friday = 15:00, 4h left on Monday = 11:00
        assert result == datetime(2026, 3, 9, 11, 0)

    def test_zero_hours(self):
        """0 hours → same time."""
        start = datetime(2026, 3, 2, 10, 0)
        result = _add_work_hours(start, 0)
        assert result == start

    def test_multi_day(self):
        """24h from Monday 07:00 → 3 full days later = Thursday 07:00."""
        start = datetime(2026, 3, 2, 7, 0)  # Monday
        result = _add_work_hours(start, 24.0)
        # Mon 8h + Tue 8h + Wed 8h = 24h → Thu 07:00 wait, that's exactly
        # Mon: 07→15 (8h), Tue: 07→15 (8h), Wed: 07→15 (8h) = 24h done at Wed 15:00
        assert result == datetime(2026, 3, 4, 15, 0)


class TestComputeDurationHrs:
    def test_normal(self):
        """setup=0.5h, 20 ks/hod, 100ks → 0.5 + 100/20 = 5.5h."""
        assert _compute_duration_hrs(0.5, 20.0, 100.0) == 5.5

    def test_no_pcs_per_hour(self):
        """No pcs_per_hour → setup only (if setup > 0)."""
        assert _compute_duration_hrs(1.0, None, 100.0) == 1.0

    def test_zero_pcs_per_hour(self):
        """Zero pcs_per_hour → setup only."""
        assert _compute_duration_hrs(0.5, 0, 100.0) == 0.5

    def test_all_none_fallback(self):
        """All None → DEFAULT_OP_HOURS."""
        assert _compute_duration_hrs(None, None, None) == 2.0

    def test_zero_qty(self):
        """Zero qty → setup only."""
        assert _compute_duration_hrs(0.5, 20.0, 0) == 0.5

    def test_no_setup(self):
        """No setup, just run: 100ks / 20 ks/h = 5h."""
        assert _compute_duration_hrs(None, 20.0, 100.0) == 5.0


# ============================================================================
# _schedule_operations — integration tests
# ============================================================================


def _make_vp(job, suffix, ops, priority=100, is_hot=False, co_due_date=None):
    """Helper: build a VP dict for scheduling tests."""
    return {
        "job": job,
        "suffix": suffix,
        "item": "DK-1234",
        "description": "Test",
        "priority": priority,
        "is_hot": is_hot,
        "co_due_date": co_due_date,
        "operations": ops,
    }


def _make_op(oper_num, wc, status="idle", setup_hrs=0.5, pcs_per_hour=20.0,
             qty_released=100, start_date=None, end_date=None):
    """Helper: build an operation dict."""
    return {
        "oper_num": str(oper_num),
        "wc": wc,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "setup_hrs": setup_hrs,
        "pcs_per_hour": pcs_per_hour,
        "qty_released": qty_released,
        "qty_complete": 0,
    }


def test_schedule_sequential_within_vp():
    """Operations within a VP are scheduled sequentially (10 → 20 → 30)."""
    ops = [
        _make_op(10, "SH2A", setup_hrs=0.5, pcs_per_hour=100, qty_released=100),  # 0.5 + 1 = 1.5h
        _make_op(20, "FR1B", setup_hrs=0.5, pcs_per_hour=100, qty_released=100),  # 1.5h
        _make_op(30, "BRU", setup_hrs=0.5, pcs_per_hour=100, qty_released=100),   # 1.5h
    ]
    vps = [_make_vp("22VP10", "250", ops)]
    now = datetime(2026, 3, 2, 7, 0)  # Monday

    _schedule_operations(vps, now=now)

    op10 = ops[0]
    op20 = ops[1]
    op30 = ops[2]

    # Each op = 1.5h. All on different WCs so WC doesn't block.
    # VP sequence: 10 starts at 07:00, ends 08:30
    #              20 starts at 08:30, ends 10:00
    #              30 starts at 10:00, ends 11:30
    assert op10["sched_start"] is not None
    assert op20["sched_start"] is not None
    assert op30["sched_start"] is not None

    # Op20 must start after op10 ends
    assert op20["sched_start"] >= op10["sched_end"]
    # Op30 must start after op20 ends
    assert op30["sched_start"] >= op20["sched_end"]


def test_schedule_wc_capacity():
    """Two VPs on the same WC don't overlap."""
    ops1 = [_make_op(10, "SH2A", setup_hrs=1.0, pcs_per_hour=50, qty_released=100)]  # 1+2=3h
    ops2 = [_make_op(10, "SH2A", setup_hrs=1.0, pcs_per_hour=50, qty_released=100)]  # 3h
    vps = [
        _make_vp("22VP10", "250", ops1, priority=10),
        _make_vp("22VP20", "0", ops2, priority=20),
    ]
    now = datetime(2026, 3, 2, 7, 0)

    _schedule_operations(vps, now=now)

    # VP10 (prio 10) comes first → 07:00-10:00
    # VP20 (prio 20) must start after 10:00
    assert ops2[0]["sched_start"] >= ops1[0]["sched_end"]


def test_schedule_hot_first():
    """Hot VP is scheduled before non-hot regardless of priority."""
    ops_normal = [_make_op(10, "SH2A", setup_hrs=0, pcs_per_hour=100, qty_released=100)]
    ops_hot = [_make_op(10, "SH2A", setup_hrs=0, pcs_per_hour=100, qty_released=100)]

    # Hot VP comes first in list (pre-sorted by caller)
    vps = [
        _make_vp("22VP20", "0", ops_hot, priority=999, is_hot=True),
        _make_vp("22VP10", "250", ops_normal, priority=1),
    ]
    now = datetime(2026, 3, 2, 7, 0)

    _schedule_operations(vps, now=now)

    # Hot VP should start at 07:00, normal after it
    assert ops_hot[0]["sched_start"] <= ops_normal[0]["sched_start"]


def test_schedule_done_ops_keep_dates():
    """Done operations keep Infor dates and update horizons."""
    ops = [
        _make_op(10, "SH2A", status="done", start_date="2026-02-25", end_date="2026-02-26"),
        _make_op(20, "FR1B", status="idle", setup_hrs=0, pcs_per_hour=100, qty_released=100),
    ]
    vps = [_make_vp("22VP10", "250", ops)]
    now = datetime(2026, 3, 2, 7, 0)

    _schedule_operations(vps, now=now)

    # Done op keeps Infor dates
    assert "2026-02-25" in ops[0]["sched_start"]
    assert "2026-02-26" in ops[0]["sched_end"]

    # Idle op is scheduled after done op's horizon
    assert ops[1]["sched_start"] is not None


def test_schedule_missing_hours_fallback():
    """Operation without hours gets DEFAULT_OP_HOURS = 2h."""
    ops = [_make_op(10, "SH2A", setup_hrs=None, pcs_per_hour=None, qty_released=None)]
    vps = [_make_vp("22VP10", "250", ops)]
    now = datetime(2026, 3, 2, 7, 0)

    _schedule_operations(vps, now=now)

    assert ops[0]["duration_hrs"] == 2.0
    assert ops[0]["sched_start"] is not None
    assert ops[0]["sched_end"] is not None


def test_schedule_weekend_skip():
    """Operation that would span into weekend skips to Monday."""
    # Friday 13:00, 4h remaining → 2h fit Friday, 2h on Monday
    ops = [_make_op(10, "SH2A", setup_hrs=0, pcs_per_hour=25, qty_released=100)]  # 4h
    vps = [_make_vp("22VP10", "250", ops)]
    now = datetime(2026, 3, 6, 13, 0)  # Friday 13:00

    _schedule_operations(vps, now=now)

    end = datetime.fromisoformat(ops[0]["sched_end"])
    # Friday has 2h left (13-15), then 2h on Monday = Mon 09:00
    assert end.weekday() == 0  # Monday
    assert end == datetime(2026, 3, 9, 9, 0)


def test_wc_lanes_built():
    """wc_lanes structure is returned correctly."""
    ops = [
        _make_op(10, "SH2A"),
        _make_op(20, "FR1B"),
        _make_op(30, "SH2A"),
    ]
    vps = [_make_vp("22VP10", "250", ops)]
    now = datetime(2026, 3, 2, 7, 0)

    wc_lanes = _schedule_operations(vps, now=now)

    assert isinstance(wc_lanes, list)
    wc_names = [lane["wc"] for lane in wc_lanes]
    assert "SH2A" in wc_names
    assert "FR1B" in wc_names

    # SH2A lane should have 2 ops
    sh2a = next(l for l in wc_lanes if l["wc"] == "SH2A")
    assert len(sh2a["ops"]) == 2

    # FR1B lane should have 1 op
    fr1b = next(l for l in wc_lanes if l["wc"] == "FR1B")
    assert len(fr1b["ops"]) == 1

    # Each op has sched_start/sched_end
    for lane in wc_lanes:
        for op in lane["ops"]:
            assert "sched_start" in op
            assert "sched_end" in op
            assert "duration_hrs" in op


def test_schedule_correct_duration_from_pcs_per_hour():
    """Duration is correctly computed as setup + qty/pcs_per_hour."""
    # setup=0.5h, 20 ks/hod, 100ks → 0.5 + 100/20 = 5.5h
    ops = [_make_op(10, "SH2A", setup_hrs=0.5, pcs_per_hour=20.0, qty_released=100)]
    vps = [_make_vp("22VP10", "250", ops)]
    now = datetime(2026, 3, 2, 7, 0)

    _schedule_operations(vps, now=now)

    assert ops[0]["duration_hrs"] == 5.5
    # 5.5h from 07:00 → 12:30
    assert ops[0]["sched_end"] == datetime(2026, 3, 2, 12, 30).isoformat()


@pytest.mark.asyncio
async def test_fetch_includes_wc_lanes(db):
    """fetch_planner_data returns wc_lanes key."""
    rows = [_infor_row(oper="10", wc="SH2A")]
    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert "wc_lanes" in result
    assert isinstance(result["wc_lanes"], list)


@pytest.mark.asyncio
async def test_fetch_ops_have_sched_fields(db):
    """Operations in VP response have sched_start/sched_end/duration_hrs."""
    rows = [_infor_row(oper="10", wc="SH2A")]
    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    op = result["vps"][0]["operations"][0]
    assert "sched_start" in op
    assert "sched_end" in op
    assert "duration_hrs" in op
    assert op["sched_start"] is not None
    assert op["sched_end"] is not None
    assert op["duration_hrs"] > 0


# ============================================================================
# set_tier
# ============================================================================

@pytest.mark.asyncio
async def test_set_tier_hot(db):
    """set_tier('hot') sets priority=5 and is_hot=True."""
    entry = await production_planner_service.set_tier(db, "22VP10", "250", "hot", "mistr")
    assert entry.priority == 5
    assert entry.is_hot is True


@pytest.mark.asyncio
async def test_set_tier_urgent(db):
    """set_tier('urgent') sets priority=20 and is_hot=False."""
    entry = await production_planner_service.set_tier(db, "22VP10", "250", "urgent", "mistr")
    assert entry.priority == 20
    assert entry.is_hot is False


@pytest.mark.asyncio
async def test_set_tier_normal(db):
    """set_tier('normal') sets priority=100 and is_hot=False."""
    entry = await production_planner_service.set_tier(db, "22VP10", "250", "normal", "mistr")
    assert entry.priority == 100
    assert entry.is_hot is False


@pytest.mark.asyncio
async def test_set_tier_multiple_hot_allowed(db):
    """Multiple VPs can be set to hot tier simultaneously."""
    await production_planner_service.set_tier(db, "22VP10", "250", "hot", "mistr")
    await production_planner_service.set_tier(db, "22VP20", "0", "hot", "mistr")

    from sqlalchemy import select
    result = await db.execute(select(ProductionPriority).where(ProductionPriority.is_hot.is_(True)))
    hot_entries = result.scalars().all()
    assert len(hot_entries) == 2


@pytest.mark.asyncio
async def test_set_tier_overwrites_existing(db):
    """set_tier overwrites previous tier on same VP."""
    await production_planner_service.set_tier(db, "22VP10", "250", "hot", "mistr")
    entry = await production_planner_service.set_tier(db, "22VP10", "250", "normal", "mistr")
    assert entry.priority == 100
    assert entry.is_hot is False


# ============================================================================
# _derive_tier
# ============================================================================

def test_derive_tier_hot():
    assert _derive_tier(5, True) == 'hot'


def test_derive_tier_urgent():
    assert _derive_tier(20, False) == 'urgent'


def test_derive_tier_normal():
    assert _derive_tier(100, False) == 'normal'


def test_derive_tier_hot_overrides_priority():
    """is_hot=True always means hot, regardless of priority number."""
    assert _derive_tier(100, True) == 'hot'


def test_derive_tier_low_priority_is_urgent():
    """Priority <= 20 without hot flag → urgent."""
    assert _derive_tier(15, False) == 'urgent'
    assert _derive_tier(1, False) == 'urgent'


# ============================================================================
# fetch_planner_data — tier + ops fields
# ============================================================================

@pytest.mark.asyncio
async def test_fetch_planner_data_includes_tier(db):
    """VP data includes tier, ops_done, ops_total."""
    rows = [
        _infor_row(oper="10", wc="SH2A", qty_released=100, qty_complete=100),
        _infor_row(oper="20", wc="FR1B", qty_released=100, qty_complete=0),
    ]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    vp = result["vps"][0]
    assert vp["tier"] == "normal"
    assert vp["ops_total"] == 2
    assert vp["ops_done"] == 1


@pytest.mark.asyncio
async def test_fetch_planner_data_tier_hot(db):
    """VP with hot priority has tier='hot'."""
    entry = ProductionPriority(
        infor_job="22VP10", infor_suffix="250",
        priority=5, is_hot=True, created_by="test",
    )
    db.add(entry)
    await db.commit()

    rows = [_infor_row()]

    with patch.object(production_planner_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = rows
        result = await production_planner_service.fetch_planner_data(db, AsyncMock())

    assert result["vps"][0]["tier"] == "hot"
