"""Tests for workshop service reverse-engineered flow."""

from __future__ import annotations

from unittest.mock import AsyncMock
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

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


def test_format_infor_datetime_converts_utc_to_workshop_timezone():
    value = datetime(2026, 1, 15, 20, 0, 0, tzinfo=timezone.utc)
    assert workshop_service._format_infor_datetime(value) == "2026-01-15 21:00:00"


def test_build_wrapper_candidates_prefers_timestamp_variant():
    tx = _tx(
        trans_type=WorkshopTransType.SETUP_START,
        started_at=datetime(2026, 2, 28, 10, 57, 47),
    )

    candidates = workshop_service._build_wrapper_candidates(tx, "demo")

    assert len(candidates) == 1
    assert len(candidates[0]) == 25


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


def test_normalize_queue_row_industream_col_fields():
    row = {
        "colJob": "21VP06/077",
        "colSuffix": "0",
        "colOper": "5",
        "colWc": "PSV",
        "colDil": "10001234",
        "colNazev": "Roura",
        "colVpMnoz": "150.00000000",
        "colKusy": "120.00000000",
        "colOpDatumSt": "2026-02-27T06:00:00",
        "colOpDatumSp": "2026-02-27T07:30:20",
    }

    normalized = workshop_service._normalize_queue_row(row)

    assert normalized is not None
    assert normalized["Job"] == "21VP06/077"
    assert normalized["Suffix"] == "0"
    assert normalized["OperNum"] == "5"
    assert normalized["Wc"] == "PSV"
    assert normalized["DerJobItem"] == "10001234"
    assert normalized["JobQtyReleased"] == 150.0
    assert normalized["QtyComplete"] == 120.0


def test_normalize_queue_row_from_compound_job_suffix_oper():
    row = {
        "vJobSuffixOperNum": "21VP06/077;0;5",
        "colWc": "PSV",
        "colVpMnoz": "150.00000000",
        "colKusy": "120.00000000",
        "colOpDatumSt": "2026-02-27T06:00:00",
    }

    normalized = workshop_service._normalize_queue_row(row)

    assert normalized is not None
    assert normalized["Job"] == "21VP06/077"
    assert normalized["Suffix"] == "0"
    assert normalized["OperNum"] == "5"
    assert normalized["Wc"] == "PSV"


def test_normalize_queue_row_from_compound_job_suffix_oper_with_slash_separator():
    row = {
        "vJobSuffixOperNum": "21VP06/077/0/5",
        "colWc": "PSV",
        "colVpMnoz": "150.00000000",
        "colKusy": "120.00000000",
    }

    normalized = workshop_service._normalize_queue_row(row)

    assert normalized is not None
    assert normalized["Job"] == "21VP06/077"
    assert normalized["Suffix"] == "0"
    assert normalized["OperNum"] == "5"


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
                    {
                        "Job": "22VP10/999",
                        "Suffix": "0",
                        "OperNum": "10",
                        "Wc": "SH2A",
                        "Dil": "300999",
                        "Nazev": "Different WC",
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
async def test_fetch_wc_queue_retries_property_sets_on_infor_message_code_error():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] != "IteCzTsdJbrDetails":
            raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")
        props = kwargs.get("properties")
        if props and props[0] == "colJob":
            return {"data": [], "message_code": 450, "message": "Property colJob not found"}
        return {
            "data": [
                {
                    "Job": "22VP10/300",
                    "Suffix": "0",
                    "OperNum": "10",
                    "Wc": "PS01",
                    "VpMnoz": "150.00000000",
                    "Kusy": "140.00000000",
                    "OpDatumSt": "2026-02-27T06:00:00",
                }
            ],
            "message_code": 0,
            "message": "Success",
        }

    client.load_collection.side_effect = _load_collection

    queue = await workshop_service.fetch_wc_queue(client, wc="PS01", record_cap=50)

    assert len(queue) == 1
    assert queue[0]["Job"] == "22VP10/300"


@pytest.mark.asyncio
async def test_fetch_wc_queue_uses_default_properties_when_prop_sets_fail():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] != "IteCzTsdJbrDetails":
            raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")
        if "properties" in kwargs:
            raise RuntimeError("Property colJob not found")
        return {
            "data": [
                {
                    "colJob": "21VP06/077",
                    "colSuffix": "0",
                    "colOper": "5",
                    "colWc": "PSV",
                    "colVpMnoz": "150.00000000",
                    "colKusy": "120.00000000",
                    "colOpDatumSt": "2026-02-27T06:00:00",
                }
            ]
        }

    client.load_collection.side_effect = _load_collection

    queue = await workshop_service.fetch_wc_queue(client, wc="PSV", record_cap=50)

    assert len(queue) == 1
    assert queue[0]["Job"] == "21VP06/077"
    assert queue[0]["OperNum"] == "5"


@pytest.mark.asyncio
async def test_fetch_wc_queue_raises_when_default_properties_return_error_message_code():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] != "IteCzTsdJbrDetails":
            raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")
        if "properties" in kwargs:
            return {"data": [], "message_code": 450, "message": "Property colJob not found"}
        return {"data": [], "message_code": 450, "message": "IDO not available"}

    client.load_collection.side_effect = _load_collection

    with pytest.raises(RuntimeError, match="JbrDetails queue source unavailable"):
        await workshop_service.fetch_wc_queue(client, wc="PSV", record_cap=50)


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

    with pytest.raises(RuntimeError, match="Operations source unavailable"):
        await workshop_service.fetch_job_operations(client, job="22VP10/300", suffix="0")


@pytest.mark.asyncio
async def test_fetch_wc_queue_switches_to_sljobroutes_on_jbr_detail_only_schema():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdJbrDetails":
            if "properties" in kwargs:
                return {"data": [], "message_code": 450, "message": "Property Job not found"}
            return {
                "data": [],
                "message_code": 0,
                "message": "Success",
                "bookmark": "<B><P><p>SessionId</p><p>OperNum</p></P></B>",
            }
        if kwargs["ido_name"] == "SLJobRoutes":
            return {
                "data": [
                    {
                        "Job": "22VP10/300",
                        "Suffix": "0",
                        "OperNum": "10",
                        "Wc": "PS01",
                        "Type": "J",
                        "JobStat": "R",
                        "JobQtyReleased": "150.00000000",
                        "QtyComplete": "140.00000000",
                        "QtyScrapped": "0.00000000",
                        "DerStartDate": "2026-02-27T06:00:00",
                        "DerEndDate": "2026-02-27T07:30:20",
                    }
                ],
                "message_code": 0,
                "message": "Success",
            }
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    queue = await workshop_service.fetch_wc_queue(client, wc="PS01", record_cap=50)

    assert len(queue) == 1
    assert queue[0]["Job"] == "22VP10/300"
    assert queue[0]["OpDatumSt"] == "2026-02-27T06:00:00"


@pytest.mark.asyncio
async def test_fetch_job_operations_switches_to_sljobroutes_on_jbr_detail_only_schema():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdJbrDetails":
            if "properties" in kwargs:
                return {"data": [], "message_code": 450, "message": "Property Job not found"}
            return {
                "data": [],
                "message_code": 0,
                "message": "Success",
                "bookmark": "<B><P><p>SessionId</p><p>OperNum</p></P></B>",
            }
        if kwargs["ido_name"] == "SLJobRoutes":
            return {
                "data": [
                    {
                        "Job": "22VP10/300",
                        "Suffix": "0",
                        "OperNum": "20",
                        "Wc": "PS01",
                        "Type": "J",
                        "JobStat": "R",
                        "JobQtyReleased": "150.00000000",
                        "QtyComplete": "150.00000000",
                        "QtyScrapped": "0.00000000",
                        "DerStartDate": "2026-02-27T08:00:00",
                    },
                    {
                        "Job": "22VP10/300",
                        "Suffix": "0",
                        "OperNum": "10",
                        "Wc": "PS01",
                        "Type": "J",
                        "JobStat": "R",
                        "JobQtyReleased": "150.00000000",
                        "QtyComplete": "100.00000000",
                        "QtyScrapped": "0.00000000",
                        "DerStartDate": "2026-02-27T07:00:00",
                    },
                ],
                "message_code": 0,
                "message": "Success",
            }
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    operations = await workshop_service.fetch_job_operations(client, job="22VP10/300", suffix="0")

    assert [op["OperNum"] for op in operations] == ["10"]


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
async def test_fetch_job_materials_falls_back_to_sljobmatls_um():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "DescriptionBd": "Steel bar",
                        "QtyPerPcBd": "1.25000000",
                    }
                ],
                "message_code": 0,
            }
        if kwargs["ido_name"] == "SLJobmatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "UM": "kg",
                    }
                ],
                "message_code": 0,
            }
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": [], "message_code": 0}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="17VP08/031",
        suffix="0",
        oper_num="10",
    )

    assert len(materials) == 1
    assert materials[0]["Material"] == "M-001"
    assert materials[0]["UM"] == "kg"
    assert materials[0]["UMs"] == ["kg"]


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


@pytest.mark.asyncio
async def test_fetch_wc_queue_supports_job_filter_and_desc_sort():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Job": "22VP10/300",
                "Suffix": "0",
                "OperNum": "10",
                "Wc": "PS01",
                "VpMnoz": "10.00000000",
                "Kusy": "1.00000000",
                "OpDatumSt": "2026-02-27T07:00:00",
            },
            {
                "Job": "22VP10/301",
                "Suffix": "0",
                "OperNum": "10",
                "Wc": "PS01",
                "VpMnoz": "10.00000000",
                "Kusy": "1.00000000",
                "OpDatumSt": "2026-02-27T08:00:00",
            },
            {
                "Job": "17VP08/031",
                "Suffix": "0",
                "OperNum": "10",
                "Wc": "PS01",
                "VpMnoz": "10.00000000",
                "Kusy": "1.00000000",
                "OpDatumSt": "2026-02-27T09:00:00",
            },
        ]
    }

    queue = await workshop_service.fetch_wc_queue(
        client,
        wc="PS01",
        record_cap=50,
        job_filter="22VP10",
        sort_by="Job",
        sort_dir="desc",
    )

    assert [row["Job"] for row in queue] == ["22VP10/301", "22VP10/300"]


@pytest.mark.asyncio
async def test_fetch_job_operations_supports_sort_direction():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Job": "22VP10/300",
                "Suffix": "0",
                "OperNum": "10",
                "Wc": "PS01",
                "VpMnoz": "150.00000000",
                "Kusy": "100.00000000",
                "OpDatumSt": "2026-02-27T07:00:00",
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
        ]
    }

    operations = await workshop_service.fetch_job_operations(
        client,
        job="22VP10/300",
        suffix="0",
        sort_by="OperNum",
        sort_dir="desc",
    )

    assert [op["OperNum"] for op in operations] == ["30", "10"]


@pytest.mark.asyncio
async def test_fetch_job_materials_supports_sort():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "MaterialBd": "M-002",
                "DescriptionBd": "Steel",
                "BatchConsumptionBd": "1.00000000",
            },
            {
                "MaterialBd": "M-001",
                "DescriptionBd": "Alu",
                "BatchConsumptionBd": "2.00000000",
            },
        ]
    }

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="17VP08/031",
        suffix="0",
        oper_num="10",
        sort_by="Material",
        sort_dir="asc",
    )

    assert [row["Material"] for row in materials] == ["M-001", "M-002"]


@pytest.mark.asyncio
async def test_fetch_job_materials_dedupes_same_material_rows():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "Item": "M-001",
                "DescriptionBd": "Steel",
                "QtyPerPcBd": None,
                "BatchConsumptionBd": None,
            },
            {
                "Item": "M-001",
                "DescriptionBd": "Steel",
                "QtyPerPcBd": "12.50000000",
                "BatchConsumptionBd": None,
            },
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
    assert materials[0]["Qty"] == pytest.approx(12.5)


@pytest.mark.asyncio
async def test_fetch_job_materials_collects_available_ums_and_qty_maps():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "DescriptionBd": "Steel",
                        "UM": "kg",
                        "QtyPerPcBd": "1.50000000",
                        "BatchConsumptionBd": "0.75000000",
                    }
                ]
            }
        if kwargs["ido_name"] == "SLJobmatls":
            return {
                "data": [
                    {"Item": "M-001", "UM": "mm", "MatlQtyConv": "250.00000000"},
                    {"Item": "M-001", "UM": "kg", "MatlQtyConv": "1.50000000"},
                ]
            }
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="17VP08/031",
        suffix="0",
        oper_num="10",
    )

    assert len(materials) == 1
    assert materials[0]["UMs"] == ["kg", "mm"]
    assert materials[0]["QtyByUM"] == {"kg": 1.5, "mm": 250.0}
    assert materials[0]["BatchConsByUM"] == {"kg": 0.75}


@pytest.mark.asyncio
async def test_fetch_job_materials_collects_ums_from_slumconvs_without_qty_recompute():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "DescriptionBd": "Steel",
                        "UM": "mm",
                        "QtyPerPcBd": "18.00000000",
                        "BatchConsumptionBd": None,
                    }
                ]
            }
        if kwargs["ido_name"] == "SLJobmatls":
            return {
                "data": [
                    {"Item": "M-001", "UM": "mm", "MatlQtyConv": "18.00000000"},
                ]
            }
        if kwargs["ido_name"] == "SLUmConvs":
            return {
                "data": [
                    {"Item": "M-001", "FromUM": "mm", "ToUM": "kg", "ConvFactor": "0.00012"},
                ]
            }
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="17VP08/031",
        suffix="0",
        oper_num="10",
    )

    assert len(materials) == 1
    assert materials[0]["UM"] == "mm"
    assert materials[0]["UMs"] == ["kg", "mm"]
    assert materials[0]["QtyByUM"] == {"mm": 18.0}
    assert materials[0].get("BatchConsByUM") is None


@pytest.mark.asyncio
async def test_fetch_job_materials_hides_zero_batch_cons():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "MaterialBd": "M-001",
                "DescriptionBd": "Steel",
                "BatchConsumptionBd": "0.00000000",
                "QtyPerPcBd": "2.00000000",
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
    assert materials[0]["BatchCons"] is None


@pytest.mark.asyncio
async def test_fetch_job_materials_uses_sljobmatls_dermatltransqty_for_batch():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "DescriptionBd": "Steel",
                        "BatchConsumptionBd": None,
                        "QtyPerPcBd": "105.00000000",
                        "UM": "mm",
                    }
                ]
            }
        if kwargs["ido_name"] == "SLJobmatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "UM": "mm",
                        "MatlQtyConv": "105.00000000",
                        "DerMatlTransQty": "10395.0000000000000000",
                    }
                ]
            }
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="21VP06/150",
        suffix="0",
        oper_num="5",
    )

    assert len(materials) == 1
    assert materials[0]["BatchCons"] == pytest.approx(10395.0)
    assert materials[0]["BatchConsByUM"] == {"mm": 10395.0}


@pytest.mark.asyncio
async def test_fetch_job_materials_prefers_derqtyissuedconv_over_qtyissued():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {
                "data": [
                    {
                        "Item": "3.3547-DE030-052-L",
                        "DescriptionBd": "Tyc",
                        "UM": "mm",
                        "QtyPerPcBd": None,
                        "QtyIssued": "0.60840000",
                    }
                ]
            }
        if kwargs["ido_name"] == "SLJobmatls":
            return {
                "data": [
                    {
                        "Item": "3.3547-DE030-052-L",
                        "UM": "mm",
                        "MatlQtyConv": "65.00000000",
                        "QtyIssued": "0.60840000",
                        "DerQtyIssuedConv": "130.00000000",
                    }
                ]
            }
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="21VP06/083",
        suffix="0",
        oper_num="5",
    )

    assert len(materials) == 1
    assert materials[0]["QtyIssued"] == pytest.approx(130.0)
    assert materials[0]["UM"] == "mm"


@pytest.mark.asyncio
async def test_fetch_job_materials_keeps_remaining_none_without_explicit_infor_field():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "MaterialBd": "M-001",
                "TotalConsumptionBd": "10.00000000",
                "QtyIssued": "4.50000000",
                "BatchConsumptionBd": "2.00000000",
                "UM": "kg",
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
    assert materials[0]["QtyIssued"] == pytest.approx(4.5)
    assert materials[0]["RemainingCons"] is None


@pytest.mark.asyncio
async def test_fetch_job_materials_collects_um_from_other_job_operations():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {
                "data": [
                    {
                        "Item": "M-001",
                        "DescriptionBd": "Steel",
                        "UM": "mm",
                        "QtyPerPcBd": "250.00000000",
                    }
                ]
            }
        if kwargs["ido_name"] == "SLJobmatls":
            return {
                "data": [
                    {"Item": "M-001", "OperNum": "10", "UM": "mm", "MatlQtyConv": "250.00000000"},
                    {"Item": "M-001", "OperNum": "20", "UM": "kg", "MatlQtyConv": "1.50000000"},
                ]
            }
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        return {"data": []}

    client.load_collection.side_effect = _load_collection

    materials = await workshop_service.fetch_job_materials(
        infor_client=client,
        job="17VP08/031",
        suffix="0",
        oper_num="10",
    )

    assert len(materials) == 1
    assert materials[0]["UMs"] == ["kg", "mm"]


@pytest.mark.asyncio
async def test_post_material_issue_rejects_unknown_material():
    client = AsyncMock()
    client.load_collection.return_value = {
        "data": [
            {
                "MaterialBd": "M-001",
                "DescriptionBd": "Steel bar",
            }
        ]
    }

    with pytest.raises(HTTPException, match="není navázán"):
        await workshop_service.post_material_issue(
            infor_client=client,
            emp_num="demo",
            job="17VP08/031",
            suffix="0",
            oper_num="10",
            material="M-XXX",
            qty=1.0,
            wc="PS01",
        )


@pytest.mark.asyncio
async def test_post_wrapper_flow_setup_skips_mchtrx():
    """Setup start/end only calls WrapperSp — machine is NOT running during setup."""
    tx = _tx(
        trans_type=WorkshopTransType.SETUP_START,
        started_at=datetime(2026, 2, 28, 11, 57, 47),
    )
    client = AsyncMock()
    client.invoke_method_positional.return_value = {"MessageCode": 0, "ReturnValue": "0", "Message": ""}

    await workshop_service._post_wrapper_flow(tx, client, "demo")

    methods = [call.kwargs["method_name"] for call in client.invoke_method_positional.await_args_list]
    assert workshop_service._WRITE_SP_WRAPPER in methods
    assert workshop_service._WRITE_SP_MCHTRX not in methods
    wrapper_call = next(
        call for call in client.invoke_method_positional.await_args_list
        if call.kwargs["method_name"] == workshop_service._WRITE_SP_WRAPPER
    )
    assert wrapper_call.kwargs["positional_values"][18] == "2026-02-28 12:57:47"  # UTC→CET +1h


@pytest.mark.asyncio
async def test_post_wrapper_flow_start_calls_mchtrx():
    tx = _tx(
        trans_type=WorkshopTransType.START,
        started_at=datetime(2026, 2, 28, 11, 57, 47),
    )
    client = AsyncMock()
    client.invoke_method_positional.return_value = {"MessageCode": 0, "ReturnValue": "0", "Message": ""}

    await workshop_service._post_wrapper_flow(tx, client, "demo")

    methods = [call.kwargs["method_name"] for call in client.invoke_method_positional.await_args_list]
    assert workshop_service._WRITE_SP_WRAPPER in methods
    assert workshop_service._WRITE_SP_MCHTRX in methods


@pytest.mark.asyncio
async def test_post_stop_flow_passes_finished_timestamp_to_wrapper():
    tx = _tx(
        trans_type=WorkshopTransType.STOP,
        started_at=datetime(2026, 2, 28, 11, 57, 47),
        finished_at=datetime(2026, 2, 28, 11, 57, 59),
    )
    client = AsyncMock()
    client.invoke_method_positional.return_value = {"MessageCode": 0, "ReturnValue": "0", "Message": ""}

    await workshop_service._post_stop_flow(tx, client, "demo")

    wrapper_call = next(
        call for call in client.invoke_method_positional.await_args_list
        if call.kwargs["method_name"] == workshop_service._WRITE_SP_WRAPPER
    )
    assert wrapper_call.kwargs["positional_values"][18] == "2026-02-28 12:57:59"  # UTC→CET +1h


@pytest.mark.asyncio
async def test_post_material_issue_calls_update_method():
    client = AsyncMock()
    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "SLJobRoutes":
            return {"data": [{"OperNum": "10", "JobQtyReleased": "10", "QtyComplete": "2", "QtyScrapped": "0"}]}
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {"data": [{"MaterialBd": "M-001", "DescriptionBd": "Steel bar", "UM": "kg"}]}
        if kwargs["ido_name"] == "SLJobmatls":
            return {"data": []}
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection
    client.invoke_method_positional.return_value = {
        "MessageCode": 0,
        "ReturnValue": "0",
        "Message": "",
    }

    result = await workshop_service.post_material_issue(
        infor_client=client,
        emp_num="demo",
        job="17VP08/031",
        suffix="0",
        oper_num="10",
        material="M-001",
        qty=1.25,
        wc="PS01",
    )

    methods = [call.kwargs["method_name"] for call in client.invoke_method_positional.await_args_list]
    assert workshop_service._WRITE_SP_INS_VALID_VYDEJ_MAT in methods
    update_calls = [name for name in methods if name == workshop_service._WRITE_SP_UPDATE_DCJMC]
    assert len(update_calls) == 1
    assert result["Material"] == "M-001"
    assert result["QtyIssued"] == pytest.approx(1.25)
    assert result["UM"] == "kg"
    assert result["Whse"] == "MAIN"
    assert result["Location"] == "PRIJEM"


@pytest.mark.asyncio
async def test_post_material_issue_rejects_nonzero_returnvalue_on_update():
    client = AsyncMock()
    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "SLJobRoutes":
            return {"data": [{"OperNum": "10", "JobQtyReleased": "10", "QtyComplete": "2", "QtyScrapped": "0"}]}
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {"data": [{"MaterialBd": "M-001", "DescriptionBd": "Steel bar"}]}
        if kwargs["ido_name"] == "SLJobmatls":
            return {"data": []}
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    async def _invoke(**kwargs):
        method_name = kwargs["method_name"]
        if method_name == workshop_service._WRITE_SP_UPDATE_DCJMC:
            return {
                "MessageCode": 0,
                "ReturnValue": "12345",
                "Message": "",
            }
        return {
            "MessageCode": 0,
            "ReturnValue": "0",
            "Message": "",
        }

    client.invoke_method_positional.side_effect = _invoke

    with pytest.raises(RuntimeError, match="IteCzTsdUpdateDcJmcSp selhalo"):
        await workshop_service.post_material_issue(
            infor_client=client,
            emp_num="demo",
            job="17VP08/031",
            suffix="0",
            oper_num="10",
            material="M-001",
            qty=1.25,
            wc="PS01",
        )


@pytest.mark.asyncio
async def test_post_material_issue_rejects_nonzero_returnvalue_on_ins_valid():
    client = AsyncMock()
    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "SLJobRoutes":
            return {"data": [{"OperNum": "10", "JobQtyReleased": "10", "QtyComplete": "2", "QtyScrapped": "0"}]}
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {"data": [{"MaterialBd": "M-001", "DescriptionBd": "Steel bar"}]}
        if kwargs["ido_name"] == "SLJobmatls":
            return {"data": []}
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    async def _invoke(**kwargs):
        method_name = kwargs["method_name"]
        if method_name == workshop_service._WRITE_SP_INS_VALID_VYDEJ_MAT:
            return {
                "MessageCode": 0,
                "ReturnValue": "12345",
                "Message": "",
            }
        return {"MessageCode": 0, "ReturnValue": "0", "Message": ""}

    client.invoke_method_positional.side_effect = _invoke

    with pytest.raises(RuntimeError, match="IteCzInsValidVydejMatNaVpLotOrScSp selhalo"):
        await workshop_service.post_material_issue(
            infor_client=client,
            emp_num="demo",
            job="17VP08/031",
            suffix="0",
            oper_num="10",
            material="M-001",
            qty=1.25,
            wc="PS01",
        )


@pytest.mark.asyncio
async def test_post_material_issue_rejects_completed_operation():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "SLJobRoutes":
            return {"data": [{"OperNum": "10", "JobQtyReleased": "12", "QtyComplete": "11", "QtyScrapped": "1"}]}
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {"data": [{"MaterialBd": "M-001", "DescriptionBd": "Steel bar"}]}
        if kwargs["ido_name"] == "SLJobmatls":
            return {"data": []}
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    with pytest.raises(HTTPException, match="Operace je již dokončena"):
        await workshop_service.post_material_issue(
            infor_client=client,
            emp_num="demo",
            job="17VP08/031",
            suffix="0",
            oper_num="10",
            material="M-001",
            qty=1.0,
            wc="PS01",
        )


@pytest.mark.asyncio
async def test_post_material_issue_rejects_coop_workcenter():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "SLJobRoutes":
            return {"data": [{"OperNum": "80", "Wc": "KOO/ANOD", "JobQtyReleased": "12", "QtyComplete": "1", "QtyScrapped": "0"}]}
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {"data": [{"MaterialBd": "0005220-KOO", "DescriptionBd": "Kooperace", "UM": "ks"}]}
        if kwargs["ido_name"] == "SLJobmatls":
            return {"data": []}
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    with pytest.raises(HTTPException, match="kooperaci zablokován"):
        await workshop_service.post_material_issue(
            infor_client=client,
            emp_num="demo",
            job="17VP07/041",
            suffix="0",
            oper_num="80",
            material="0005220-KOO",
            qty=1.0,
            wc=None,
        )


@pytest.mark.asyncio
async def test_post_material_issue_rejects_invalid_um():
    client = AsyncMock()

    async def _load_collection(**kwargs):
        if kwargs["ido_name"] == "SLJobRoutes":
            return {"data": [{"OperNum": "10", "JobQtyReleased": "12", "QtyComplete": "1", "QtyScrapped": "0"}]}
        if kwargs["ido_name"] == "IteCzTsdSLJobMatls":
            return {"data": [{"MaterialBd": "M-001", "DescriptionBd": "Steel bar", "UM": "kg"}]}
        if kwargs["ido_name"] == "SLJobmatls":
            return {"data": [{"Item": "M-001", "UM": "kg"}, {"Item": "M-001", "UM": "mm"}]}
        if kwargs["ido_name"] == "SLUmConvs":
            return {"data": []}
        raise AssertionError(f"Unexpected IDO: {kwargs['ido_name']}")

    client.load_collection.side_effect = _load_collection

    with pytest.raises(HTTPException, match="Dostupné jednotky: kg, mm"):
        await workshop_service.post_material_issue(
            infor_client=client,
            emp_num="demo",
            job="17VP08/031",
            suffix="0",
            oper_num="10",
            material="M-001",
            um="ks",
            qty=1.0,
            wc="PS01",
        )


def test_build_view_filter_contains_status_customer_dates_search():
    filter_expr = workshop_service._build_view_filter(
        customer="E000187",
        due_from="2026-02-01",
        due_to="2026-02-28",
        search="7060",
    )

    assert filter_expr is not None
    assert "Stat IN" in filter_expr
    assert "DueDate >=" in filter_expr
    assert "DueDate <=" in filter_expr
    assert "CustNum = 'E000187'" in filter_expr
    assert "CoNum LIKE '%7060%'" in filter_expr


def test_build_view_operations_maps_wc_comp_wip():
    row = {
        "Wc01": "SH2", "Comp01": "1", "Wip01": "1",
        "Wc02": "FV3", "Comp02": "0", "Wip02": "1",
        "Wc03": "OTK", "Comp03": "0", "Wip03": "0",
    }
    ops = workshop_service._build_view_operations(row)
    assert len(ops) == 3
    assert ops[0] == {"oper_num": "10", "wc": "SH2", "status": "done", "state_text": None}
    assert ops[1] == {"oper_num": "20", "wc": "FV3", "status": "in_progress", "state_text": None}
    assert ops[2] == {"oper_num": "30", "wc": "OTK", "status": "idle", "state_text": None}


def test_build_view_operations_stops_at_empty_wc():
    row = {"Wc01": "SH2", "Comp01": "1", "Wip01": "1"}
    ops = workshop_service._build_view_operations(row)
    assert len(ops) == 1


def test_operation_status_done_by_qty():
    status = workshop_service._operation_status(
        {
            "JobQtyReleased": "10.00000000",
            "QtyComplete": "10.00000000",
            "QtyScrapped": "0.00000000",
            "DerRybStavOper": "P",
        }
    )
    assert status == "done"


def test_operation_status_in_progress_by_state():
    status = workshop_service._operation_status(
        {
            "JobQtyReleased": "10.00000000",
            "QtyComplete": "1.00000000",
            "QtyScrapped": "0.00000000",
            "DerRybStavCNCOper": "B",
        }
    )
    assert status == "in_progress"


def test_operation_status_idle_for_non_running_b_words():
    status = workshop_service._operation_status(
        {
            "JobQtyReleased": "10.00000000",
            "QtyComplete": "1.00000000",
            "QtyScrapped": "0.00000000",
            "DerRybStavCNCOper": "BLOK",
        }
    )
    assert status == "idle"


def test_sort_vp_candidates_released_before_firm():
    jobs_by_key = {
        "24VP01/001|0": {"Stat": "F", "DerDueDate": "20260101 00:00:00.000"},
        "24VP01/002|0": {"Stat": "R", "DerDueDate": "20260201 00:00:00.000"},
    }
    out = workshop_service._sort_vp_candidates_by_status(
        ["24VP01/001|0", "24VP01/002|0"],
        jobs_by_key=jobs_by_key,
        routes_by_key={},
    )
    assert out[0] == "24VP01/002|0"


def test_sort_vp_candidates_in_progress_first():
    jobs_by_key = {
        "24VP01/001|0": {"Stat": "R", "DerDueDate": "20260101 00:00:00.000"},
        "24VP01/002|0": {"Stat": "R", "DerDueDate": "20260201 00:00:00.000"},
    }
    routes_by_key = {
        "24VP01/002|0": [
            {"OperNum": "10", "Wc": "SH2", "DerRybStavCNCOper": "B", "JobQtyReleased": "40", "QtyComplete": "1", "QtyScrapped": "0"},
        ],
    }
    out = workshop_service._sort_vp_candidates_by_status(
        ["24VP01/001|0", "24VP01/002|0"],
        jobs_by_key=jobs_by_key,
        routes_by_key=routes_by_key,
    )
    assert out[0] == "24VP01/002|0"


@pytest.mark.asyncio
async def test_fetch_orders_overview_maps_view_fields():
    """Ověří mapování polí z IteRybPrehledZakazekView na výstupní strukturu."""
    client = AsyncMock()

    async def _load_collection(**kwargs):
        assert kwargs["ido_name"] == "IteRybPrehledZakazekView"
        return {
            "data": [
                {
                    "CoNum": "21ZA000466",
                    "CoLine": "1",
                    "CoRelease": "0",
                    "CustNum": "E000187",
                    "CustName": "Gelso AG",
                    "Item": "11049590",
                    "ItemDescription": "Hridel D15",
                    "QtyOrderedConv": "40",
                    "QtyShipped": "0",
                    "QtyWIP": "39",
                    "DueDate": "20210816 00:00:00.000",
                    "PromiseDate": "20210820 00:00:00.000",
                    "ConfirmedDate": "20210815 00:00:00.000",
                    "Stat": "O",
                    "Job": "25VP02/001",
                    "Suffix": "0",
                    "Wc01": "SH2",
                    "Wc02": "FV3",
                    "Comp01": "1",
                    "Comp02": "0",
                    "Wip01": "1",
                    "Wip02": "1",
                    "RecordDate": "20210816 10:00:00.000",
                }
            ],
            "message_code": 0,
            "message": "Success",
        }

    client.load_collection.side_effect = _load_collection

    rows = await workshop_service.fetch_orders_overview(infor_client=client, limit=50)
    assert len(rows) == 1
    r = rows[0]
    assert r["customer_code"] == "E000187"
    assert r["customer_name"] == "Gelso AG"
    assert r["co_num"] == "21ZA000466"
    assert r["item"] == "11049590"
    assert r["description"] == "Hridel D15"
    assert r["qty_ordered"] == 40.0
    assert r["qty_wip"] == 39.0
    assert r["selected_vp_job"] == "25VP02/001"
    assert len(r["vp_candidates"]) == 1
    assert len(r["operations"]) == 2
    assert r["operations"][0]["wc"] == "SH2"
    assert r["operations"][0]["status"] == "done"
    assert r["operations"][1]["wc"] == "FV3"
    assert r["operations"][1]["status"] == "in_progress"


@pytest.mark.asyncio
async def test_fetch_orders_overview_no_job_yields_empty_vp():
    """Řádek bez VP jobu má prázdné vp_candidates."""
    client = AsyncMock()

    async def _load_collection(**kwargs):
        return {
            "data": [
                {
                    "CoNum": "21ZA000525",
                    "CoLine": "1",
                    "CoRelease": "0",
                    "CustNum": "E000999",
                    "CustName": "FAS GmbH",
                    "Item": "10809430",
                    "ItemDescription": "Stellspindel HVD",
                    "QtyOrderedConv": "300",
                    "QtyShipped": "0",
                    "QtyWIP": "1270",
                    "DueDate": "20210913 00:00:00.000",
                    "Stat": "O",
                }
            ],
            "message_code": 0,
            "message": "Success",
        }

    client.load_collection.side_effect = _load_collection

    rows = await workshop_service.fetch_orders_overview(infor_client=client, limit=50)
    assert len(rows) == 1
    assert rows[0]["qty_wip"] == 1270.0
    assert rows[0]["selected_vp_job"] is None
    assert rows[0]["vp_candidates"] == []
    assert rows[0]["operations"] == []
    assert rows[0]["customer_name"] == "FAS GmbH"


@pytest.mark.asyncio
async def test_fetch_orders_overview_completed_job_without_routing_hidden():
    """Job bez routovaných operací (completed) se nezobrazí jako VP kandidát."""
    client = AsyncMock()

    async def _load_collection(**kwargs):
        return {
            "data": [
                {
                    "CoNum": "26ZA000066",
                    "CoLine": "2",
                    "CoRelease": "0",
                    "CustNum": "E000187",
                    "CustName": "Gelso AG",
                    "Item": "0321193",
                    "ItemDescription": "Anschlag",
                    "QtyOrderedConv": "2",
                    "QtyShipped": "0",
                    "QtyWIP": "0",
                    "DueDate": "20260310 00:00:00.000",
                    "Stat": "O",
                    "Job": "14VP11/152",
                    "Suffix": "0",
                    # No Wc columns → job is completed
                }
            ],
            "message_code": 0,
            "message": "Success",
        }

    client.load_collection.side_effect = _load_collection

    rows = await workshop_service.fetch_orders_overview(infor_client=client, limit=50)
    assert len(rows) == 1
    assert rows[0]["selected_vp_job"] is None
    assert rows[0]["vp_candidates"] == []


@pytest.mark.asyncio
async def test_fetch_orders_overview_deduplicates_rows():
    """Duplicitní CoNum|CoLine|CoRelease se deduplikují."""
    client = AsyncMock()

    async def _load_collection(**kwargs):
        row = {
            "CoNum": "21ZA009999",
            "CoLine": "1",
            "CoRelease": "0",
            "CustNum": "E001111",
            "CustName": "Sample Customer",
            "Item": "10806334",
            "ItemDescription": "Pressuering D22",
            "QtyOrderedConv": "500",
            "QtyShipped": "0",
            "QtyWIP": "0",
            "DueDate": "20210913 00:00:00.000",
            "Stat": "O",
        }
        return {"data": [row, dict(row)], "message_code": 0, "message": "Success"}

    client.load_collection.side_effect = _load_collection

    rows = await workshop_service.fetch_orders_overview(infor_client=client, limit=50)
    assert len(rows) == 1
