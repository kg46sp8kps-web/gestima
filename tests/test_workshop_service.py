"""Tests for workshop service reverse-engineered flow."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.models.enums import WorkshopTransType
from app.models.workshop_transaction import WorkshopTransaction
from app.services import workshop_service


def _tx(**overrides):
    data = {
        "infor_job": "16VP09/055",
        "infor_suffix": "0",
        "infor_item": "SZ-M-2016-003",
        "oper_num": "10",
        "wc": "SH2A",
        "trans_type": WorkshopTransType.STOP,
        "qty_completed": 3,
        "qty_scrapped": 0,
        "qty_moved": 2,
        "actual_hours": 1.25,
        "oper_complete": True,
        "job_complete": False,
    }
    data.update(overrides)
    return WorkshopTransaction(**data)


def test_build_sfc34_params_shape():
    tx = _tx(trans_type=WorkshopTransType.QTY_COMPLETE)

    params = workshop_service._build_sfc34_params(tx, "demo")

    assert len(params) == 20
    assert params[0] == "demo"
    assert params[1] == ""
    assert params[2] == "16VP09/055"
    assert params[16] == "SH2A"


def test_build_dcsfc_candidates_use_infor_item():
    tx = _tx(infor_item="ITEM-ABC")

    candidates = workshop_service._build_dcsfc_mchtrx_candidates(tx, "demo")

    assert len(candidates) >= 2
    assert candidates[0][7] == "ITEM-ABC"
    assert candidates[0][3] in {"J", "1"}


def test_normalize_queue_row_jbr_fields():
    row = {
        "Job": " 22VP10/250 ",
        "Suffix": " 1 ",
        "OperNum": " 20 ",
        "Wc": " SH2A ",
        "Dil": " 10390029 ",
        "Nazev": " Hřídel ",
        "VpMnoz": "8.00000000",
        "Kusy": "5.00000000",
        "OpDatumSt": "2026-02-27T06:00:00",
        "OpDatumSp": "2026-02-27T07:30:20",
    }

    normalized = workshop_service._normalize_queue_row(row)

    assert normalized is not None
    assert normalized["Job"] == "22VP10/250"
    assert normalized["Suffix"] == "1"
    assert normalized["OperNum"] == "20"
    assert normalized["Wc"] == "SH2A"
    assert normalized["DerJobItem"] == "10390029"
    assert normalized["JobQtyReleased"] == 8.0
    assert normalized["QtyComplete"] == 5.0
    assert normalized["OpDatumSp"] == "2026-02-27T07:30:20"


def test_normalize_queue_row_sljobroutes_dates():
    row = {
        "Job": "17VP08/031",
        "Suffix": "0",
        "OperNum": "10",
        "Wc": "FH4",
        "DerJobItem": "SZ-M-2016-001",
        "JobDescription": "Bracket",
        "DerStartDate": "2026-02-27T06:00:00",
        "DerEndDate": "2026-02-27T07:30:20",
    }

    normalized = workshop_service._normalize_queue_row(row)

    assert normalized is not None
    assert normalized["OpDatumSt"] == "2026-02-27T06:00:00"
    assert normalized["OpDatumSp"] == "2026-02-27T07:30:20"


@pytest.mark.asyncio
async def test_fetch_wc_queue_raises_when_jbr_unavailable():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdJbrDetails":
            raise RuntimeError("IDO not available")
        if kwargs["ido_name"] == "SLJobRoutes":
            raise AssertionError("SLJobRoutes must not be used as fallback for queue")
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    with pytest.raises(RuntimeError, match="JbrDetails queue source unavailable"):
        await workshop_service.fetch_wc_queue(client, wc="SH2A", record_cap=50)


@pytest.mark.asyncio
async def test_fetch_wc_queue_prefers_jbr_schedule_source():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdJbrDetails":
            return {
                "data": [
                    {
                        "Job": "22VP10/300",
                        "Suffix": "0",
                        "OperNum": "10",
                        "Wc": "PS01",
                        "Dil": "300001",
                        "Nazev": "Schedule row A",
                        "VpMnoz": "150.00000000",
                        "Kusy": "140.00000000",
                        "OpDatumSt": "2026-02-27T06:00:00",
                        "OpDatumSp": "2026-02-27T07:30:20",
                    },
                    {
                        "Job": "22VP10/301",
                        "Suffix": "0",
                        "OperNum": "10",
                        "Wc": "PS01",
                        "Dil": "300002",
                        "Nazev": "Should be filtered out",
                        "VpMnoz": "100.00000000",
                        "Kusy": "20.00000000",
                        "OpDatumSt": "2026-02-27T08:00:00",
                        "OpDatumSp": "2026-02-27T09:00:00",
                    },
                ]
            }
        if kwargs["ido_name"] == "SLJobRoutes":
            raise AssertionError("SLJobRoutes should not be called when JBR works")
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    queue = await workshop_service.fetch_wc_queue(client, wc="PS01", record_cap=50)

    assert len(queue) == 2
    assert queue[0]["Job"] == "22VP10/300"
    assert queue[1]["Job"] == "22VP10/301"
    assert queue[0]["OpDatumSt"] == "2026-02-27T06:00:00"
    assert queue[0]["OpDatumSp"] == "2026-02-27T07:30:20"


@pytest.mark.asyncio
async def test_fetch_wc_queue_filters_completed_operations():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Job": "22VP10/300",
                "Suffix": "0",
                "OperNum": "10",
                "Wc": "PS01",
                "VpMnoz": "150.00000000",
                "Kusy": "140.00000000",
                "OpDatumSt": "2026-02-27T06:00:00",
            },
            {
                "Job": "22VP10/301",
                "Suffix": "0",
                "OperNum": "20",
                "Wc": "PS01",
                "VpMnoz": "100.00000000",
                "Kusy": "100.00000000",
                "OpDatumSt": "2026-02-27T07:00:00",
            },
        ]
    }

    queue = await workshop_service.fetch_wc_queue(client, wc="PS01", record_cap=50)

    assert len(queue) == 1
    assert queue[0]["Job"] == "22VP10/300"


@pytest.mark.asyncio
async def test_fetch_job_operations_raises_when_jbr_unavailable():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdJbrDetails":
            raise RuntimeError("IDO not available")
        if kwargs["ido_name"] == "SLJobRoutes":
            raise AssertionError("SLJobRoutes must not be used as fallback for operations")
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    with pytest.raises(RuntimeError, match="JbrDetails operations source unavailable"):
        await workshop_service.fetch_job_operations(client, job="22VP10/300", suffix="0")


@pytest.mark.asyncio
async def test_fetch_job_operations_filters_completed_and_sorts():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Job": "22VP10/300",
                "Suffix": "0",
                "OperNum": "20",
                "Wc": "PS01",
                "VpMnoz": "150.00000000",
                "Kusy": "150.00000000",
                "OpDatumSt": "2026-02-27T08:00:00",
            },
            {
                "Job": "22VP10/300",
                "Suffix": "0",
                "OperNum": "30",
                "Wc": "PS01",
                "VpMnoz": "150.00000000",
                "Kusy": "120.00000000",
                "OpDatumSt": "2026-02-27T09:00:00",
            },
            {
                "Job": "22VP10/300",
                "Suffix": "0",
                "OperNum": "10",
                "Wc": "PS01",
                "VpMnoz": "150.00000000",
                "Kusy": "100.00000000",
                "OpDatumSt": "2026-02-27T07:00:00",
            },
        ]
    }

    operations = await workshop_service.fetch_job_operations(client, job="22VP10/300", suffix="0")

    assert [op["OperNum"] for op in operations] == ["10", "30"]


@pytest.mark.asyncio
async def test_fetch_job_materials_maps_bd_fields():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "MaterialBd": "M-001",
                "DescriptionBd": "Steel bar",
                "TotalConsumptionBd": "12.50000000",
                "QtyPerPcBd": "1.25000000",
                "BatchConsumptionBd": "2.50000000",
            }
        ]
    }

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="17VP08/031",
        suffix="0",
        oper_num="10",
    )

    assert len(materials) == 1
    assert materials[0]["Material"] == "M-001"
    assert materials[0]["Desc"] == "Steel bar"
    assert materials[0]["TotCons"] == 12.5
    assert materials[0]["Qty"] == 1.25
    assert materials[0]["BatchCons"] == 2.5


@pytest.mark.asyncio
async def test_build_qty_policy_context_blocks_non_saw_overrun():
    tx = _tx(
        trans_type=WorkshopTransType.STOP,
        wc="SH2A",
        oper_num="20",
        qty_completed=6,
    )
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {"OperNum": "10", "Wc": "PS01", "JobQtyReleased": "10", "QtyComplete": "1"},
            {"OperNum": "20", "Wc": "SH2A", "JobQtyReleased": "10", "QtyComplete": "5"},
        ]
    }

    ctx = await workshop_service._build_qty_policy_context(tx, client)

    assert ctx is not None
    assert ctx["overrun"] is True
    assert ctx["allow_overrun"] is False
    assert ctx["target_released_qty"] is None


@pytest.mark.asyncio
async def test_build_qty_policy_context_allows_first_saw_overrun_and_targets_vp():
    tx = _tx(
        trans_type=WorkshopTransType.STOP,
        wc="PS01",
        oper_num="10",
        qty_completed=6,
    )
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {"OperNum": "10", "Wc": "PS01", "JobQtyReleased": "10", "QtyComplete": "5"},
            {"OperNum": "20", "Wc": "SH2A", "JobQtyReleased": "10", "QtyComplete": "2"},
        ]
    }

    ctx = await workshop_service._build_qty_policy_context(tx, client)

    assert ctx is not None
    assert ctx["overrun"] is True
    assert ctx["allow_overrun"] is True
    assert ctx["target_released_qty"] == pytest.approx(11.0)


@pytest.mark.asyncio
async def test_build_qty_policy_context_blocks_saw_overrun_on_non_first_operation():
    tx = _tx(
        trans_type=WorkshopTransType.STOP,
        wc="PS01",
        oper_num="20",
        qty_completed=6,
    )
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {"OperNum": "10", "Wc": "PS01", "JobQtyReleased": "10", "QtyComplete": "2"},
            {"OperNum": "20", "Wc": "PS01", "JobQtyReleased": "10", "QtyComplete": "5"},
        ]
    }

    ctx = await workshop_service._build_qty_policy_context(tx, client)

    assert ctx is not None
    assert ctx["overrun"] is True
    assert ctx["allow_overrun"] is False
    assert ctx["target_released_qty"] is None


@pytest.mark.asyncio
async def test_build_qty_policy_context_marks_completed_operation():
    tx = _tx(
        trans_type=WorkshopTransType.START,
        wc="SH2A",
        oper_num="20",
        qty_completed=0,
        qty_scrapped=0,
    )
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {"OperNum": "10", "Wc": "PS01", "JobQtyReleased": "10", "QtyComplete": "5", "QtyScrapped": "0"},
            {"OperNum": "20", "Wc": "SH2A", "JobQtyReleased": "10", "QtyComplete": "9", "QtyScrapped": "1"},
        ]
    }

    ctx = await workshop_service._build_qty_policy_context(tx, client)

    assert ctx is not None
    assert ctx["operation_completed"] is True
    assert ctx["remaining_qty"] == pytest.approx(0.0)
    assert ctx["overrun"] is False


@pytest.mark.asyncio
async def test_sync_sljobs_qty_released_updates_via_update_request():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Job": "16VP09/055",
                "Suffix": "0",
                "QtyReleased": "10.00000000",
                "_ItemId": "PBT=[SLJobs] S=[SLJobs] Job=16VP09/055,Suffix=0",
            }
        ]
    }
    client.execute_update_request.return_value = {"MessageCode": 200}

    await workshop_service._sync_sljobs_qty_released(
        client,
        job="16VP09/055",
        suffix="0",
        target_qty_released=11.0,
    )

    client.execute_update_request.assert_awaited_once()
    kwargs = client.execute_update_request.await_args.kwargs
    assert kwargs["response_mode"] == "summary"
    request_body = kwargs["request_body"]
    assert request_body["IDOName"] == "SLJobs"
    assert request_body["Changes"][0]["Action"] == 2
    assert request_body["Changes"][0]["Properties"][0]["Name"] == "QtyReleased"
    assert request_body["Changes"][0]["Properties"][0]["Value"] == "11.00000000"
