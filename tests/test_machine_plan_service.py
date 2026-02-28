"""Tests for Machine Plan DnD service."""

from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.machine_plan import MachinePlanEntry
from app.models.production_priority import ProductionPriority
from app.services import machine_plan_service


@pytest_asyncio.fixture
async def db():
    """In-memory DB for machine plan tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


def _infor_row(job="VP001", suffix="0", oper="10", wc="SH2A", **kw):
    """Helper: fake Infor row."""
    row = {
        "Job": job,
        "Suffix": suffix,
        "OperNum": oper,
        "Wc": wc,
        "DerJobItem": kw.get("item", "ITEM-1"),
        "JobDescription": kw.get("desc", "Test job"),
        "JobQtyReleased": kw.get("qty_released", 100),
        "QtyComplete": kw.get("qty_complete", 0),
        "QtyScrapped": kw.get("qty_scrapped", 0),
        "JobStat": kw.get("stat", "R"),
        "OpDatumSt": "2026-03-01",
        "OpDatumSp": "2026-03-02",
    }
    row.update(kw)
    return row


def _mock_get_plan_patches():
    """Common patches for get_plan tests: mock Infor + CO deadlines."""
    return (
        patch.object(machine_plan_service.workshop_service, "fetch_machine_plan", new_callable=AsyncMock),
        patch.object(machine_plan_service, "_fetch_co_deadlines", new_callable=AsyncMock),
    )


async def _seed_entries(db, wc, entries):
    """Seed MachinePlanEntry rows. entries = list of (job, suffix, oper, position)."""
    for job, suffix, oper, pos in entries:
        e = MachinePlanEntry(
            wc=wc, infor_job=job, infor_suffix=suffix, oper_num=oper,
            position=pos, created_by="test",
        )
        db.add(e)
    await db.commit()


async def _seed_priority(db, job, suffix="0", priority=100, is_hot=False):
    """Seed ProductionPriority row."""
    p = ProductionPriority(
        infor_job=job, infor_suffix=suffix,
        priority=priority, is_hot=is_hot,
        created_by="test",
    )
    db.add(p)
    await db.commit()


# ============================================================================
# get_plan — Released = planned, F/S/W = unassigned
# ============================================================================

@pytest.mark.asyncio
async def test_get_plan_released_items_auto_planned(db):
    """Released (R) items go to planned, no local DB entries needed."""
    infor_rows = [_infor_row(oper="10"), _infor_row(oper="20")]

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = {}
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    assert len(result["planned"]) == 2
    assert len(result["unassigned"]) == 0


@pytest.mark.asyncio
async def test_get_plan_backlog_items_unassigned(db):
    """Non-released (F/S/W) items go to unassigned."""
    infor_rows = [
        _infor_row(job="VP001", oper="10", stat="R"),
        _infor_row(job="VP002", oper="10", stat="F"),
        _infor_row(job="VP003", oper="10", stat="S"),
        _infor_row(job="VP004", oper="10", stat="W"),
    ]

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = {}
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    assert len(result["planned"]) == 1
    assert result["planned"][0]["Job"] == "VP001"
    assert len(result["unassigned"]) == 3


@pytest.mark.asyncio
async def test_get_plan_hot_before_dnd(db):
    """Hot items always above DnD-positioned items."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 0),  # DnD position 0
    ])
    await _seed_priority(db, "VP002", priority=5, is_hot=True)

    infor_rows = [
        _infor_row(job="VP001", oper="10", item="DND-ITEM"),
        _infor_row(job="VP002", oper="10", item="HOT-ITEM"),
    ]

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = {}
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    jobs = [r["Job"] for r in result["planned"]]
    # VP002 (hot) first, even though VP001 has DnD position 0
    assert jobs == ["VP002", "VP001"]


@pytest.mark.asyncio
async def test_get_plan_dnd_positioned_items_before_auto(db):
    """Non-hot DnD-positioned items appear before auto-sorted items."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "20", 0),  # DnD position: Op 20 first
    ])

    infor_rows = [
        _infor_row(oper="10", item="LATE"),
        _infor_row(oper="20", item="EARLY"),
    ]

    co_map = {
        "LATE": {"co_due_date": date(2026, 3, 1), "co_num": "ZA1"},
        "EARLY": {"co_due_date": date(2026, 4, 1), "co_num": "ZA2"},
    }

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = co_map
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    assert len(result["planned"]) == 2
    # DnD item (Op 20) first, then auto-sorted (Op 10)
    assert result["planned"][0]["OperNum"] == "20"
    assert result["planned"][0]["_position"] == 0
    assert result["planned"][1]["OperNum"] == "10"


@pytest.mark.asyncio
async def test_get_plan_stale_entry_soft_deleted(db):
    """Local entry without Infor counterpart → auto soft-delete."""
    await _seed_entries(db, "SH2A", [
        ("VP999", "0", "10", 0),  # not in Infor
    ])

    infor_rows = [_infor_row(oper="10")]  # VP001, not VP999

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = {}
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    # VP001 (R) goes to planned
    assert len(result["planned"]) == 1
    assert len(result["unassigned"]) == 0


@pytest.mark.asyncio
async def test_get_plan_completed_operation_removed(db):
    """Completed operation → removed from both planned and unassigned."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 0),
    ])

    # Completed: QtyComplete >= JobQtyReleased
    infor_rows = [_infor_row(oper="10", qty_released=100, qty_complete=100)]

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = {}
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    assert len(result["planned"]) == 0
    assert len(result["unassigned"]) == 0


# ============================================================================
# Enrichment: OrderDueDate + priority/hot
# ============================================================================

@pytest.mark.asyncio
async def test_get_plan_enriches_with_order_due_date(db):
    """Released items enriched with OrderDueDate from CO lookup."""
    infor_rows = [_infor_row(oper="10", item="PART-A")]

    co_map = {"PART-A": {"co_due_date": date(2026, 3, 15), "co_num": "26ZA000100"}}

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = co_map
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    row = result["planned"][0]
    assert row["OrderDueDate"] == "2026-03-15"
    assert row["CoNum"] == "26ZA000100"
    assert row["Tier"] == "normal"
    assert row["IsHot"] is False


@pytest.mark.asyncio
async def test_get_plan_enriches_with_hot_priority(db):
    """Hot VP marked with IsHot=True and Tier=hot from DB priority."""
    await _seed_priority(db, "VP001", priority=5, is_hot=True)

    infor_rows = [_infor_row(oper="10")]

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = {}
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    row = result["planned"][0]
    assert row["IsHot"] is True
    assert row["Tier"] == "hot"
    assert row["Priority"] == 5


@pytest.mark.asyncio
async def test_get_plan_planned_sorted_hot_first_then_due_date(db):
    """Planned sorting: hot first, then by OrderDueDate ASC."""
    await _seed_priority(db, "VP003", priority=5, is_hot=True)

    infor_rows = [
        _infor_row(job="VP001", oper="10", item="LATE"),
        _infor_row(job="VP002", oper="10", item="EARLY"),
        _infor_row(job="VP003", oper="10", item="HOT-ITEM"),
    ]

    co_map = {
        "LATE": {"co_due_date": date(2026, 4, 20), "co_num": "ZA1"},
        "EARLY": {"co_due_date": date(2026, 3, 5), "co_num": "ZA2"},
        "HOT-ITEM": {"co_due_date": date(2026, 5, 1), "co_num": "ZA3"},
    }

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = co_map
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    jobs = [r["Job"] for r in result["planned"]]
    # VP003 (hot) first, then VP002 (early due), then VP001 (late due)
    assert jobs == ["VP003", "VP002", "VP001"]


@pytest.mark.asyncio
async def test_get_plan_no_due_date_sorted_last(db):
    """Items without OrderDueDate sorted after those with dates."""
    infor_rows = [
        _infor_row(job="VP001", oper="10", item="NO-ORDER"),
        _infor_row(job="VP002", oper="10", item="HAS-ORDER"),
    ]

    co_map = {
        "HAS-ORDER": {"co_due_date": date(2026, 3, 10), "co_num": "ZA1"},
    }

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = co_map
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    jobs = [r["Job"] for r in result["planned"]]
    assert jobs == ["VP002", "VP001"]  # HAS-ORDER first, NO-ORDER last


@pytest.mark.asyncio
async def test_get_plan_stopped_vps_in_unassigned(db):
    """Stopped VP (JobStat=S) goes to unassigned, not planned."""
    infor_rows = [
        _infor_row(job="VP001", oper="10", stat="S", item="PART-S"),
        _infor_row(job="VP002", oper="10", stat="R", item="PART-R"),
    ]

    co_map = {
        "PART-S": {"co_due_date": date(2026, 3, 1), "co_num": "ZA1"},
        "PART-R": {"co_due_date": date(2026, 4, 1), "co_num": "ZA2"},
    }

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = co_map
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    # VP002 (R) in planned, VP001 (S) in unassigned
    assert len(result["planned"]) == 1
    assert result["planned"][0]["Job"] == "VP002"
    assert len(result["unassigned"]) == 1
    assert result["unassigned"][0]["Job"] == "VP001"


@pytest.mark.asyncio
async def test_get_plan_unassigned_s_sorted_after_f(db):
    """In unassigned: F items before S items."""
    infor_rows = [
        _infor_row(job="VP001", oper="10", stat="S", item="PART-S"),
        _infor_row(job="VP002", oper="10", stat="F", item="PART-F"),
    ]

    co_map = {
        "PART-S": {"co_due_date": date(2026, 3, 1), "co_num": "ZA1"},
        "PART-F": {"co_due_date": date(2026, 4, 1), "co_num": "ZA2"},
    }

    mock_infor, mock_co = _mock_get_plan_patches()
    with mock_infor as m_fetch, mock_co as m_co:
        m_fetch.return_value = infor_rows
        m_co.return_value = co_map
        result = await machine_plan_service.get_plan(db, "SH2A", AsyncMock())

    jobs = [r["Job"] for r in result["unassigned"]]
    # VP002 (F) before VP001 (S) — S always at end
    assert jobs == ["VP002", "VP001"]


# ============================================================================
# reorder
# ============================================================================

@pytest.mark.asyncio
async def test_reorder_creates_and_updates(db):
    """Reorder creates new entries and updates existing."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 0),
    ])

    ordered = [
        {"job": "VP001", "suffix": "0", "oper_num": "20"},  # new
        {"job": "VP001", "suffix": "0", "oper_num": "10"},  # existing, new position
    ]

    count = await machine_plan_service.reorder(db, "SH2A", ordered, "mistr")
    assert count == 2


@pytest.mark.asyncio
async def test_reorder_restores_soft_deleted(db):
    """Reorder restores a soft-deleted entry."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 0),
    ])
    # Soft-delete the entry
    from sqlalchemy import select
    result = await db.execute(select(MachinePlanEntry))
    entry = result.scalar_one()
    entry.deleted_at = datetime.utcnow()
    await db.commit()

    ordered = [{"job": "VP001", "suffix": "0", "oper_num": "10"}]
    count = await machine_plan_service.reorder(db, "SH2A", ordered, "mistr")
    assert count == 1

    # Verify restored
    result = await db.execute(select(MachinePlanEntry))
    entry = result.scalar_one()
    assert entry.deleted_at is None
    assert entry.position == 0


# ============================================================================
# add_to_plan
# ============================================================================

@pytest.mark.asyncio
async def test_add_to_plan_new(db):
    """Add a new entry to the plan."""
    entry = await machine_plan_service.add_to_plan(db, "SH2A", "VP001", "0", "10", "mistr")
    assert entry.wc == "SH2A"
    assert entry.infor_job == "VP001"
    assert entry.position == 0


@pytest.mark.asyncio
async def test_add_to_plan_auto_position(db):
    """Auto-position = MAX + 1."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 5),
    ])

    entry = await machine_plan_service.add_to_plan(db, "SH2A", "VP001", "0", "20", "mistr")
    assert entry.position == 6


@pytest.mark.asyncio
async def test_add_to_plan_restores_deleted(db):
    """Adding an already-soft-deleted entry restores it."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 0),
    ])
    from sqlalchemy import select
    result = await db.execute(select(MachinePlanEntry))
    entry = result.scalar_one()
    entry.deleted_at = datetime.utcnow()
    await db.commit()

    restored = await machine_plan_service.add_to_plan(db, "SH2A", "VP001", "0", "10", "mistr")
    assert restored.deleted_at is None


# ============================================================================
# remove_from_plan
# ============================================================================

@pytest.mark.asyncio
async def test_remove_from_plan(db):
    """Remove entry from plan → soft-delete."""
    await _seed_entries(db, "SH2A", [
        ("VP001", "0", "10", 0),
    ])

    removed = await machine_plan_service.remove_from_plan(db, "SH2A", "VP001", "0", "10", "mistr")
    assert removed is True


@pytest.mark.asyncio
async def test_remove_from_plan_not_found(db):
    """Remove non-existent entry → returns False."""
    removed = await machine_plan_service.remove_from_plan(db, "SH2A", "NOPE", "0", "10", "mistr")
    assert removed is False
