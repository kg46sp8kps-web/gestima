"""Tests for operator terminal active-jobs pairing logic."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models.enums import WorkshopTransType, WorkshopTxStatus
from app.models.workshop_transaction import WorkshopTransaction
from app.services import operator_service


def _tx(
    *,
    created_at: datetime,
    trans_type: WorkshopTransType,
    status: WorkshopTxStatus,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    job: str = "21VP05/043",
    suffix: str = "0",
    oper: str = "10",
    username: str = "operator",
) -> WorkshopTransaction:
    return WorkshopTransaction(
        infor_job=job,
        infor_suffix=suffix,
        infor_item="ITEM-001",
        oper_num=oper,
        wc="PS01",
        trans_type=trans_type,
        status=status,
        qty_completed=0,
        qty_scrapped=0,
        qty_moved=0,
        oper_complete=False,
        job_complete=False,
        started_at=started_at,
        finished_at=finished_at,
        created_at=created_at,
        updated_at=created_at,
        created_by=username,
        updated_by=username,
    )


@pytest.mark.asyncio
async def test_get_active_jobs_ignores_failed_stop(db_session):
    base = datetime(2026, 2, 28, 10, 0, 0)
    db_session.add_all([
        _tx(
            created_at=base,
            trans_type=WorkshopTransType.START,
            status=WorkshopTxStatus.POSTED,
            started_at=base,
        ),
        _tx(
            created_at=base + timedelta(minutes=5),
            trans_type=WorkshopTransType.STOP,
            status=WorkshopTxStatus.FAILED,
            started_at=base,
            finished_at=base + timedelta(minutes=5),
        ),
    ])
    await db_session.commit()

    active = await operator_service.get_active_jobs(db_session, "operator")

    assert len(active) == 1
    assert active[0]["job"] == "21VP05/043"
    assert active[0]["oper_num"] == "10"
    assert active[0]["trans_type"] == "start"


@pytest.mark.asyncio
async def test_get_active_jobs_keeps_latest_cycle_for_same_operation(db_session):
    base = datetime(2026, 2, 28, 11, 0, 0)
    db_session.add_all([
        _tx(
            created_at=base,
            trans_type=WorkshopTransType.START,
            status=WorkshopTxStatus.POSTED,
            started_at=base,
        ),
        _tx(
            created_at=base + timedelta(minutes=10),
            trans_type=WorkshopTransType.STOP,
            status=WorkshopTxStatus.POSTED,
            started_at=base,
            finished_at=base + timedelta(minutes=10),
        ),
        _tx(
            created_at=base + timedelta(minutes=20),
            trans_type=WorkshopTransType.START,
            status=WorkshopTxStatus.POSTED,
            started_at=base + timedelta(minutes=20),
        ),
    ])
    await db_session.commit()

    active = await operator_service.get_active_jobs(db_session, "operator")

    assert len(active) == 1
    assert active[0]["trans_type"] == "start"
    assert active[0]["started_at"].startswith("2026-02-28T11:20:00")


@pytest.mark.asyncio
async def test_get_active_jobs_uses_only_posted_transactions(db_session):
    base = datetime(2026, 2, 28, 12, 0, 0)
    db_session.add_all([
        _tx(
            created_at=base,
            trans_type=WorkshopTransType.START,
            status=WorkshopTxStatus.PENDING,
            started_at=base,
        ),
        _tx(
            created_at=base + timedelta(minutes=1),
            trans_type=WorkshopTransType.SETUP_START,
            status=WorkshopTxStatus.FAILED,
            started_at=base + timedelta(minutes=1),
            oper="20",
        ),
    ])
    await db_session.commit()

    active = await operator_service.get_active_jobs(db_session, "operator")
    assert active == []


@pytest.mark.asyncio
async def test_get_transaction_alerts_marks_failed_stop_as_running_blocker(db_session):
    base = datetime(2026, 2, 28, 13, 0, 0)
    db_session.add_all([
        _tx(
            created_at=base,
            trans_type=WorkshopTransType.START,
            status=WorkshopTxStatus.POSTED,
            started_at=base,
            job="22VP01/001",
            oper="10",
        ),
        _tx(
            created_at=base + timedelta(minutes=7),
            trans_type=WorkshopTransType.STOP,
            status=WorkshopTxStatus.FAILED,
            started_at=base,
            finished_at=base + timedelta(minutes=7),
            job="22VP01/001",
            oper="10",
        ),
    ])
    await db_session.commit()

    alerts = await operator_service.get_transaction_alerts(db_session, "operator", limit=20)

    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["trans_type"] == "stop"
    assert alert["status"] == "failed"
    assert alert["severity"] == "error"
    assert alert["retry_allowed"] is True
    assert alert["blocks_running"] is True


@pytest.mark.asyncio
async def test_get_transaction_alerts_warns_pending_or_posting(db_session):
    base = datetime(2026, 2, 28, 14, 0, 0)
    db_session.add_all([
        _tx(
            created_at=base,
            trans_type=WorkshopTransType.START,
            status=WorkshopTxStatus.POSTING,
            started_at=base,
            job="22VP01/002",
            oper="20",
        ),
        _tx(
            created_at=base + timedelta(minutes=1),
            trans_type=WorkshopTransType.SETUP_START,
            status=WorkshopTxStatus.PENDING,
            started_at=base + timedelta(minutes=1),
            job="22VP01/003",
            oper="5",
        ),
    ])
    await db_session.commit()

    alerts = await operator_service.get_transaction_alerts(db_session, "operator", limit=20)
    statuses = {a["status"]: a for a in alerts}

    assert statuses["posting"]["severity"] == "warning"
    assert statuses["posting"]["retry_allowed"] is False
    assert statuses["pending"]["severity"] == "warning"
    assert statuses["pending"]["retry_allowed"] is True
