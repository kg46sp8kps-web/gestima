"""GESTIMA - Workshop Service

Dílnická aplikace napojená na Infor CloudSuite Industrial.
Dělníci odvádějí kusy/čas přes Gestima Dílna terminál (iPad).

Tok dat:
  Infor SLJobRoutes → Gestima Dílna → WorkshopTransaction (status=pending)
  → Infor SP → Infor (status=posted/failed)

Zápis do Inforu — DVA různé SP (potvrzeno IL bytecode analýzou InduStream.Forms.Std.dll):

  A) IteCzTsdUpdateDcSfcWrapperSp (25 params) — pro START/STOP akce:
     Použití: ZahajitNastaveni("1"), UkoncitNastaveni("2"), ZahajitPraci("3")
     Infor vytvoří/uzavře otevřenou labor transakci.
     TransType je na pozici 3 (index 3, 0-based).

  B) IteCzTsdUpdateDcSfc34Sp (20 params) — pro ODVODY (Module_01120 OdvodKusu):
     Použití: stop, qty_complete, scrap, time
     Pozice 1 (index 1) je PRÁZDNÝ STRING — TransType se NEPOSÍLÁ!
     Chybějící poz.18=@TStroj, poz.19=@TDatumTransakce("0")

  @TTransType mapování (z IL bytecode InduStream.Forms.Std.dll):
    '1' = ZahajitNastaveni  (setup_start — WrapperSp)
    '2' = UkoncitNastaveni  (setup_end   — WrapperSp)
    '3' = ZahajitPraci      (start       — WrapperSp)
    '4' = UkoncitPraci      (stop/qty/scrap/time — SFC34, ale TransType se NEPOSÍLÁ)

Infobar chování Inforu:
  SP vrací infobar="0" nebo infobar="" pro úspěch.
  Pouze neprázdný string != "0" signalizuje chybu.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workshop_transaction import WorkshopTransaction, WorkshopTransactionCreate
from app.models.enums import WorkshopTxStatus
from app.models.user import User
from app.db_helpers import set_audit, safe_commit

logger = logging.getLogger(__name__)

# Vlastnosti zakázky z Infor SLJobRoutes
# Potvrzeno z: infor_job_routing_importer.py + Infor REST API discovery 2026-02-26
_JOB_ROUTE_PROPS = [
    "Job",
    "Suffix",
    "Type",
    "Wc",               # Pracoviště — lowercase c (Wc, ne WC!)
    "OperNum",
    "DerJobItem",       # Číslo dílu (ne Item)
    "JobDescription",   # Popis (ne ItemDescription)
    "JobStat",          # Status: R=Released, F=Firm, C=Closed (ne Status!)
    "JobQtyReleased",   # Vydané množství (ne Qty)
    "QtyComplete",
    "QtyScrapped",
    "JshSetupHrs",
    "DerRunMchHrs",
    # SchedStartDate/SchedFinishDate nejsou na IteCzSLJobRoutes IDO (MessageCode 450)
    # Toto IDO je custom wrapper IteCzSLJobRoutes, ne standardní SLJobRoutes
]

# Numerická pole z Infor — vracena jako string "4.00000000", parsujeme na float
_NUMERIC_JOB_FIELDS = [
    "JobQtyReleased", "QtyComplete", "QtyScrapped", "JshSetupHrs", "DerRunMchHrs",
]
_NUMERIC_OPER_FIELDS = [
    "JobQtyReleased", "QtyComplete", "QtyScrapped",
]
_NUMERIC_MATERIAL_FIELDS = [
    "TotCons", "Qty", "BatchCons",
]

# IDO a SP pro zápis transakcí
# Potvrzeno IL bytecode analýzou InduStream.Forms.Std.dll (2026-02-26)
_WRITE_IDO = "IteCzTsdStd"
_WRITE_SP_SFC34 = "IteCzTsdUpdateDcSfc34Sp"         # 20 params — OdvodKusu
_WRITE_SP_WRAPPER = "IteCzTsdUpdateDcSfcWrapperSp"  # 25 params — Start/Stop
_WRITE_SP_MCHTRX = "IteCzTsdUpdateMchtrxSp"         # 9 params — strojová transakce (souběžně se WrapperSp)

# Trans typy co jdou přes WrapperSp (Start akce)
_WRAPPER_TRANS_TYPES = {"setup_start", "setup_end", "start"}


async def fetch_wc_queue(
    infor_client,
    wc: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Načte frontu práce pro pracoviště — flat seznam operací (bez deduplikace).

    Na rozdíl od fetch_open_jobs() každý řádek = jedna operace (1:1 s SLJobRoutes).
    Sekundární JbrDetails query přidá OpDatumSt/OpDatumSp.

    Filter:
      - Type = 'J' → výrobní zakázky
      - JobStat = 'R' OR 'F' → aktivní
      - Volitelně dle wc → filtr pracoviště

    Vrací pole s klíči: Job, Suffix, OperNum, Wc, DerJobItem, JobDescription,
    JobQtyReleased, QtyComplete, QtyScrapped, JshSetupHrs, DerRunMchHrs,
    OpDatumSt, OpDatumSp
    """
    filter_parts = ["Type = 'J'", "(JobStat = 'R' OR JobStat = 'F')"]
    if wc:
        safe_wc = wc.strip().replace("'", "''")
        filter_parts.append(f"Wc = '{safe_wc}'")

    infor_filter = " AND ".join(filter_parts)

    result = await infor_client.load_collection(
        ido_name="SLJobRoutes",
        properties=_JOB_ROUTE_PROPS,
        filter=infor_filter,
        order_by="Job ASC, OperNum ASC",
        record_cap=record_cap,
    )

    rows = result.get("data", [])

    # Strip whitespace
    str_fields = ["Job", "Suffix", "Type", "Wc", "OperNum", "DerJobItem", "JobStat", "JobDescription"]
    for row in rows:
        for field in str_fields:
            if isinstance(row.get(field), str):
                row[field] = row[field].strip()

    # Parsuj čísla z Infor string formátu "4.00000000" na float
    for row in rows:
        for field in _NUMERIC_JOB_FIELDS:
            val = row.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    row[field] = round(float(val), 4)
                except (ValueError, TypeError):
                    row[field] = None

    # Sekundární query: plánované datumy z IteCzTsdJbrDetails (non-fatal)
    date_map: dict = {}
    try:
        jbr_filter_parts = []
        if wc:
            safe_wc = wc.strip().replace("'", "''")
            jbr_filter_parts.append(f"Wc = '{safe_wc}'")
        jbr_filter = " AND ".join(jbr_filter_parts) if jbr_filter_parts else ""

        dates_kwargs: Dict[str, Any] = dict(
            ido_name="IteCzTsdJbrDetails",
            properties=["Job", "Suffix", "OperNum", "OpDatumSt", "OpDatumSp"],
            order_by="OpDatumSt ASC",
            record_cap=record_cap,
        )
        if jbr_filter:
            dates_kwargs["filter"] = jbr_filter

        dates_result = await infor_client.load_collection(**dates_kwargs)
        for drow in dates_result.get("data", []):
            job_key = (drow.get("Job") or "").strip()
            suffix_key = (drow.get("Suffix") or "").strip()
            op_key = (drow.get("OperNum") or "").strip()
            date_map[(job_key, suffix_key, op_key)] = {
                "OpDatumSt": (drow.get("OpDatumSt") or "").strip() or None,
                "OpDatumSp": (drow.get("OpDatumSp") or "").strip() or None,
            }
    except Exception as date_exc:
        logger.debug(f"JbrDetails date fetch for queue failed (non-fatal): {date_exc}")

    # Složit výsledek — jeden dict na řádek SLJobRoutes
    queue: List[Dict[str, Any]] = []
    for row in rows:
        job_key = row.get("Job") or ""
        suffix_key = row.get("Suffix") or ""
        op_key = row.get("OperNum") or ""
        dates = date_map.get((job_key, suffix_key, op_key), {})
        queue.append({
            "Job": row.get("Job"),
            "Suffix": row.get("Suffix"),
            "OperNum": row.get("OperNum"),
            "Wc": row.get("Wc"),
            "DerJobItem": row.get("DerJobItem"),
            "JobDescription": row.get("JobDescription"),
            "JobQtyReleased": row.get("JobQtyReleased"),
            "QtyComplete": row.get("QtyComplete"),
            "QtyScrapped": row.get("QtyScrapped"),
            "JshSetupHrs": row.get("JshSetupHrs"),
            "DerRunMchHrs": row.get("DerRunMchHrs"),
            "OpDatumSt": dates.get("OpDatumSt"),
            "OpDatumSp": dates.get("OpDatumSp"),
        })

    return queue


async def fetch_open_jobs(
    infor_client,
    wc_filter: Optional[str] = None,
    record_cap: int = 200,
) -> List[Dict[str, Any]]:
    """
    Načte otevřené zakázky z Inforu (SLJobRoutes) — jedna položka na zakázku.

    SLJobRoutes vrací 1 řádek na operaci — deduplikujeme Python-side
    tak, že pro každý Job+Suffix zachováme pouze první výskyt (nejnižší OperNum).

    Filter:
      - Type = 'J' → výrobní zakázky (ne 'S' = service!)
      - JobStat = 'R' → released
      - Volitelně dle wc_filter → filtr pracoviště

    Poznámka: načítáme 8× více řádků než record_cap, protože
    průměrný job má ~5–10 operací. Po deduplikaci vrátíme max record_cap jobů.
    """
    # Type='J' = výrobní zakázky; JobStat R=Released, F=Firm Planned (obě jsou aktivní)
    filter_parts = ["Type = 'J'", "(JobStat = 'R' OR JobStat = 'F')"]
    if wc_filter:
        safe_wc = wc_filter.strip().replace("'", "''")
        filter_parts.append(f"Wc = '{safe_wc}'")

    infor_filter = " AND ".join(filter_parts)

    # Načteme více řádků, protože každý job má více operací (průměr ~5–10 op/job)
    fetch_cap = min(record_cap * 12, 5000)

    result = await infor_client.load_collection(
        ido_name="SLJobRoutes",
        properties=_JOB_ROUTE_PROPS,
        filter=infor_filter,
        order_by="Job ASC, OperNum ASC",
        record_cap=fetch_cap,
    )

    rows = result.get("data", [])

    # Ořež whitespace v string polích (Infor vrací "         2" místo "2")
    str_fields = ["Job", "Suffix", "Type", "Wc", "OperNum", "DerJobItem", "JobStat", "JobDescription"]
    for row in rows:
        for field in str_fields:
            if isinstance(row.get(field), str):
                row[field] = row[field].strip()

    # Parsuj čísla z Infor string formátu "4.00000000" na float
    for row in rows:
        for field in _NUMERIC_JOB_FIELDS:
            val = row.get(field)
            if isinstance(val, str) and val.strip():
                try:
                    row[field] = round(float(val), 4)
                except (ValueError, TypeError):
                    row[field] = None

    # Deduplikace: zachovej první výskyt každého Job+Suffix (nejnižší OperNum)
    seen: set = set()
    unique_jobs: List[Dict[str, Any]] = []
    for row in rows:
        key = (row.get("Job"), row.get("Suffix"))
        if key not in seen:
            seen.add(key)
            unique_jobs.append(row)
            if len(unique_jobs) >= record_cap:
                break

    return unique_jobs


async def fetch_job_operations(
    infor_client,
    job: str,
    suffix: str = "0",
) -> List[Dict[str, Any]]:
    """
    Načte operace konkrétní zakázky ze SLJobRoutes.

    Poznámka: SLJobOpers IDO v tomto Infor neexistuje (MessageCode 450).
    Operace čteme přímo ze SLJobRoutes — každý řádek je jedna operace.
    Filtrujeme dle Job+Suffix, řadíme dle OperNum.

    Pole jsou remapována na WorkshopOperation interface:
      JobQtyReleased → QtyReleased
      QtyScrapped    → ScrapQty
    """
    safe_job = job.strip().replace("'", "''")
    safe_suffix = suffix.strip().replace("'", "''")

    result = await infor_client.load_collection(
        ido_name="SLJobRoutes",
        properties=["Job", "Suffix", "OperNum", "Wc", "JobQtyReleased", "QtyComplete", "QtyScrapped",
                    "JshSetupHrs", "DerRunMchHrs"],
        filter=f"Job = '{safe_job}' AND Suffix = '{safe_suffix}'",
        order_by="OperNum ASC",
        record_cap=100,
    )

    rows = result.get("data", [])

    # Sekundární query: plánované datumy z IteCzTsdJbrDetails (OpDatumSt/OpDatumSp)
    # IDO JbrDetails je primárně fronta práce, ale filter Job+Suffix funguje pro konkrétní zakázku.
    # Non-fatal — pokud IDO není k dispozici nebo filtr selže, datumy jsou None.
    date_map: dict = {}
    try:
        dates_result = await infor_client.load_collection(
            ido_name="IteCzTsdJbrDetails",
            properties=["Job", "Suffix", "OperNum", "OpDatumSt", "OpDatumSp"],
            filter=f"Job = '{safe_job}' AND Suffix = '{safe_suffix}'",
            order_by="OperNum ASC",
            record_cap=100,
        )
        for drow in dates_result.get("data", []):
            op_key = (drow.get("OperNum") or "").strip()
            date_map[op_key] = {
                "OpDatumSt": (drow.get("OpDatumSt") or "").strip() or None,
                "OpDatumSp": (drow.get("OpDatumSp") or "").strip() or None,
            }
    except Exception as date_exc:
        logger.debug(f"JbrDetails date fetch failed (non-fatal, job={job}): {date_exc}")

    # Strip whitespace + remap pole na WorkshopOperation interface + parsuj čísla
    operations = []
    for row in rows:
        qty_released = row.get("JobQtyReleased")
        qty_complete = row.get("QtyComplete")
        scrap_qty = row.get("QtyScrapped")

        # Parsuj čísla z Infor string formátu "4.00000000" na float
        for name, val in [("JobQtyReleased", qty_released), ("QtyComplete", qty_complete), ("QtyScrapped", scrap_qty)]:
            if isinstance(val, str) and val.strip():
                try:
                    parsed = round(float(val), 4)
                    if name == "JobQtyReleased":
                        qty_released = parsed
                    elif name == "QtyComplete":
                        qty_complete = parsed
                    elif name == "QtyScrapped":
                        scrap_qty = parsed
                except (ValueError, TypeError):
                    pass

        # Setup a run hodiny
        setup_hrs = row.get("JshSetupHrs")
        run_hrs = row.get("DerRunMchHrs")
        for name, val in [("JshSetupHrs", setup_hrs), ("DerRunMchHrs", run_hrs)]:
            if isinstance(val, str) and val.strip():
                try:
                    parsed = round(float(val), 4)
                    if name == "JshSetupHrs":
                        setup_hrs = parsed
                    else:
                        run_hrs = parsed
                except (ValueError, TypeError):
                    pass

        oper_num_key = (row.get("OperNum") or "").strip()
        oper_dates = date_map.get(oper_num_key, {})
        operations.append({
            "Job": (row.get("Job") or "").strip(),
            "Suffix": (row.get("Suffix") or "").strip(),
            "OperNum": oper_num_key,
            "Wc": (row.get("Wc") or "").strip(),
            "QtyReleased": qty_released,
            "QtyComplete": qty_complete,
            "ScrapQty": scrap_qty,
            "SetupHrs": setup_hrs,
            "RunHrs": run_hrs,
            "OpDatumSt": oper_dates.get("OpDatumSt"),   # Plánovaný začátek operace
            "OpDatumSp": oper_dates.get("OpDatumSp"),   # Plánovaný konec operace
        })

    return operations


async def fetch_job_materials(
    infor_client,
    job: str,
    suffix: str = "0",
    oper_num: str = "0",
) -> List[Dict[str, Any]]:
    """
    Načte materiálovou spotřebu k operaci zakázky z IteCzTsdSLJobMatls.

    IDO IteCzTsdSLJobMatls obsahuje materiály potřebné k odvedení
    na konkrétní operaci. Filtr dle Job + Suffix + OperNum.

    Pole: Material, Desc, TotCons, Qty, BatchCons
    """
    safe_job = job.strip().replace("'", "''")
    safe_suffix = suffix.strip().replace("'", "''")
    safe_oper = oper_num.strip().replace("'", "''")

    try:
        # Správné field names potvrzeny IL bytecode analýzou (2026-02-26):
        # IteCzTsdSLJobMatls IDO používá interně CLM SP → pole jsou Item + DerItemDescription
        # (NE Material + Desc, to jsou pole starého standardního SLJobMatl IDO)
        result = await infor_client.load_collection(
            ido_name="IteCzTsdSLJobMatls",
            properties=["Item", "DerItemDescription", "TotCons", "Qty", "BatchCons"],
            filter=f"Job = '{safe_job}' AND Suffix = '{safe_suffix}' AND OperNum = '{safe_oper}'",
            record_cap=50,
        )
        rows = result.get("data", [])

        # Remapuj Infor field names na WorkshopMaterial interface + strip + parsuj čísla
        materials = []
        for row in rows:
            item = (row.get("Item") or "").strip()
            desc = (row.get("DerItemDescription") or "").strip() or None
            mat: dict = {
                "Material": item,
                "Desc": desc,
            }
            for field in _NUMERIC_MATERIAL_FIELDS:
                val = row.get(field)
                if isinstance(val, str) and val.strip():
                    try:
                        mat[field] = round(float(val), 4)
                    except (ValueError, TypeError):
                        mat[field] = None
                else:
                    mat[field] = val if isinstance(val, (int, float)) else None
            materials.append(mat)

        return materials

    except Exception as exc:
        # IteCzTsdSLJobMatls nemusí být nakonfigurováno na všech instancích
        logger.warning(f"fetch_job_materials failed (job={job} oper={oper_num}): {exc}")
        return []


async def create_transaction(
    db: AsyncSession,
    data: WorkshopTransactionCreate,
    current_user: User,
) -> WorkshopTransaction:
    """
    Uloží dílnickou transakci do lokálního bufferu (status=pending).

    Args:
        db: DB session
        data: Data transakce
        current_user: Aktuálně přihlášený uživatel

    Returns:
        WorkshopTransaction s status=pending
    """
    tx = WorkshopTransaction(
        infor_job=data.infor_job,
        infor_suffix=data.infor_suffix,
        oper_num=data.oper_num,
        wc=data.wc,
        trans_type=data.trans_type,
        qty_completed=data.qty_completed,
        qty_scrapped=data.qty_scrapped,
        qty_moved=data.qty_moved,
        scrap_reason=data.scrap_reason,
        actual_hours=data.actual_hours,
        oper_complete=data.oper_complete,
        job_complete=data.job_complete,
        started_at=data.started_at,
        finished_at=data.finished_at,
        status=WorkshopTxStatus.PENDING,
    )
    set_audit(tx, current_user.username)
    db.add(tx)
    await safe_commit(db, tx, "vytvoření dílnické transakce")
    logger.info(
        f"Workshop transaction created: job={data.infor_job} oper={data.oper_num} "
        f"type={data.trans_type} by={current_user.username}"
    )
    return tx


async def post_transaction_to_infor(
    db: AsyncSession,
    tx_id: int,
    infor_client,
    current_user: User,
) -> WorkshopTransaction:
    """
    Odešle transakci do Inforu přes IteCzTsdUpdateDcSfc34Sp.

    Zápis přes GET /json/method/IteCzTsdStd/IteCzTsdUpdateDcSfc34Sp?parms=...
    18 pozičních parametrů potvrzeno cascade discovery.

    Nastaví status=posting během odesílání, pak posted/failed.

    Args:
        db: DB session
        tx_id: ID transakce
        infor_client: InforAPIClient instance
        current_user: Uživatel spouštějící odeslání

    Returns:
        Aktualizovaná WorkshopTransaction

    Raises:
        HTTPException 404: Transakce nenalezena
        HTTPException 409: Transakce není ve stavu pending/failed
    """
    from fastapi import HTTPException

    result = await db.execute(
        select(WorkshopTransaction).where(
            WorkshopTransaction.id == tx_id,
            WorkshopTransaction.deleted_at.is_(None)
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transakce nenalezena")

    if tx.status not in (WorkshopTxStatus.PENDING, WorkshopTxStatus.FAILED):
        raise HTTPException(
            status_code=409,
            detail=f"Transakci nelze odeslat — aktuální status: {tx.status}"
        )

    # Nastav status=posting
    tx.status = WorkshopTxStatus.POSTING
    set_audit(tx, current_user.username, is_update=True)
    await safe_commit(db, tx, "nastavení posting statusu")

    # Urči správný SP podle typu transakce
    emp_num = getattr(current_user, "infor_emp_num", None) or current_user.username
    trans_type_val = tx.trans_type.value if hasattr(tx.trans_type, "value") else str(tx.trans_type)

    if trans_type_val in _WRAPPER_TRANS_TYPES:
        # Start/Stop akce → WrapperSp (25 params, TransType na poz.3)
        sp_name = _WRITE_SP_WRAPPER
        params = _build_wrapper_params(tx, emp_num)
    else:
        # Odvody (qty/scrap/time/stop) → SFC34 (20 params, poz.1=prázdný)
        sp_name = _WRITE_SP_SFC34
        params = _build_sfc34_params(tx, emp_num)

    try:
        logger.info(
            f"Posting to Infor {sp_name}: job={tx.infor_job} oper={tx.oper_num} "
            f"type={tx.trans_type} emp={emp_num} wc={tx.wc}"
        )
        response = await infor_client.invoke_method_positional(
            ido_name=_WRITE_IDO,
            method_name=sp_name,
            positional_values=params,
        )

        # Zkontroluj chybu v odpovědi Inforu
        infobar = (response.get("ReturnValue") or "").strip()
        msg_code = response.get("MessageCode", 0)
        msg = response.get("Message", "")

        if msg_code != 0:
            raise RuntimeError(f"Infor chyba (kód {msg_code}): {infobar or msg}")
        # Infor vrací infobar="0" nebo infobar="" pro ÚSPĚCH — oba jsou OK.
        # Pouze neprázdný string != "0" signalizuje skutečnou chybu z SP.
        if infobar and infobar not in ("0", "null", "NULL", "0.00"):
            raise RuntimeError(f"Infor SP chyba: {infobar}")

        # Úspěch
        tx.status = WorkshopTxStatus.POSTED
        tx.posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        tx.error_msg = None
        logger.info(f"Transaction {tx_id} posted to Infor successfully")

        # WrapperSp Start akce → souběžně MchtrxSp pro sledování strojových časů (non-fatal)
        if trans_type_val in _WRAPPER_TRANS_TYPES:
            try:
                mch_params = _build_mchtrx_params(tx, emp_num)
                mch_resp = await infor_client.invoke_method_positional(
                    ido_name=_WRITE_IDO,
                    method_name=_WRITE_SP_MCHTRX,
                    positional_values=mch_params,
                )
                mch_infobar = (mch_resp.get("ReturnValue") or "").strip()
                if mch_infobar and mch_infobar not in ("0", "null", "NULL", "0.00"):
                    logger.warning(f"MchtrxSp warning (non-fatal, tx={tx_id}): {mch_infobar}")
                else:
                    logger.info(f"MchtrxSp OK (tx={tx_id})")
            except Exception as mch_exc:
                logger.warning(f"MchtrxSp failed (non-fatal, tx={tx_id}): {mch_exc}")

    except Exception as exc:
        # Chyba — uložit zprávu, ponechat status=failed
        tx.status = WorkshopTxStatus.FAILED
        tx.error_msg = str(exc)[:500]
        logger.error(f"Transaction {tx_id} failed to post: {exc}")

    set_audit(tx, current_user.username, is_update=True)
    await safe_commit(db, tx, "aktualizace statusu transakce")
    return tx


async def list_my_transactions(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
) -> List[WorkshopTransaction]:
    """
    Vrátí transakce aktuálně přihlášeného dělníka (seřazené sestupně).

    Args:
        db: DB session
        current_user: Přihlášený uživatel
        skip: Offset pro stránkování
        limit: Limit výsledků
    """
    result = await db.execute(
        select(WorkshopTransaction)
        .where(
            WorkshopTransaction.created_by == current_user.username,
            WorkshopTransaction.deleted_at.is_(None)
        )
        .order_by(WorkshopTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


def _trans_type_code_wrapper(trans_type) -> str:
    """
    Mapuje WorkshopTransType na číselný kód @TTransType pro WrapperSp.

    Kódy potvrzeny z IL bytecode InduStream.Forms.Std.dll (2026-02-26).
    WrapperSp používá POUZE typy 1/2/3 (Start akce).
    Typ 4 (UkoncitPraci) jde přes SFC34 bez TransType.
    """
    val = trans_type.value if hasattr(trans_type, "value") else str(trans_type)
    _MAP = {
        "setup_start": "1",   # ZahajitNastaveni
        "setup_end":   "2",   # UkoncitNastaveni
        "start":       "3",   # ZahajitPraci
    }
    return _MAP.get(val, "3")


def _build_wrapper_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    """
    Sestaví 25 pozičních parametrů pro IteCzTsdUpdateDcSfcWrapperSp.

    Použití: ZahajitNastaveni("1"), UkoncitNastaveni("2"), ZahajitPraci("3")

    Pořadí (index 0–24, potvrzeno IL bytecode InduStream.Forms.Std.dll):
     0:  (prázdný)
     1:  EmpNum
     2:  MultiJobFlag ("0" = single job)
     3:  TransType ("1"/"2"/"3")
     4:  JobNum
     5:  JobSuffix (Int16)
     6:  OperNum
     7-9: QtyComplete/Scrap/Moved (prázdné pro Start akce)
    10:  Complete flag ("0")
    11:  Close flag ("0")
    12:  IssueParent ("0")
    13-16: Location/Lot/ReasonCode/SerNumList (prázdné)
    17:  Wc (prázdné — machine tracking jde zvlášť přes MchtrxSp)
    18:  (prázdný)
    19:  SourceModul (kód modulu: "01100"/"01110"/"01111")
    20:  IdMachine (prázdné — Gestima nezná ID stroje)
    21:  ResId (prázdné)
    22:  (flag "0")
    23:  Mode ("T" = TSD terminal mode — NIKDY source_modul, to způsobí infobar=16!)
    24:  Infobar (OUTPUT — vstup prázdný)
    """
    trans_type_val = tx.trans_type.value if hasattr(tx.trans_type, "value") else str(tx.trans_type)
    trans_type_str = _trans_type_code_wrapper(tx.trans_type)

    _SOURCE_MODUL_MAP = {
        "setup_start": "01110",   # ZahajitNastaveni
        "setup_end":   "01111",   # UkoncitNastaveni
        "start":       "01100",   # ZahajitPraci
    }
    source_modul = _SOURCE_MODUL_MAP.get(trans_type_val, "01100")

    return [
        "",                                    # 0:  (prázdný)
        emp_num,                               # 1:  EmpNum
        "0",                                   # 2:  MultiJobFlag (default = single job)
        trans_type_str,                        # 3:  TransType ("1"/"2"/"3")
        tx.infor_job,                          # 4:  JobNum
        tx.infor_suffix or "0",                # 5:  JobSuffix (Int16)
        tx.oper_num,                           # 6:  OperNum
        "",                                    # 7:  QtyComplete (prázdné pro Start)
        "",                                    # 8:  QtyScrap
        "",                                    # 9:  QtyMoved
        "0",                                   # 10: Complete flag
        "0",                                   # 11: Close flag
        "0",                                   # 12: IssueParent
        "",                                    # 13: Location
        "",                                    # 14: Lot
        "",                                    # 15: ReasonCode
        "",                                    # 16: SerNumList
        "",                                    # 17: Wc (machine tracking zvlášť)
        "",                                    # 18: (prázdný)
        source_modul,                          # 19: SourceModul
        "",                                    # 20: IdMachine (Gestima nezná)
        "",                                    # 21: ResId
        "0",                                   # 22: (flag)
        "T",                                   # 23: Mode ("T" = TSD terminal mode — NIKDY source_modul, to způsobí infobar=16!)
        "",                                    # 24: Infobar (OUTPUT)
    ]


def _build_mchtrx_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    """
    Sestaví 9 pozičních parametrů pro IteCzTsdUpdateMchtrxSp.

    Voláno SOUBĚŽNĚ s WrapperSp pro Start akce (setup_start, setup_end, start).
    Sleduje strojové časy — nezávislé na labor transakci z WrapperSp.
    Chyba je pouze WARNING — neblokuje hlavní transakci.

    Pořadí (index 0–8, potvrzeno IL bytecode InduStream.Forms.Std.dll):
     0:  EmpNum
     1:  TransType ("H" = hours/machine tracking)
     2:  JobNum
     3:  JobSuffix
     4:  OperNum
     5:  Wc (pracoviště)
     6:  Stroj (ID stroje — "" = Gestima nezná)
     7:  OldEmpNum ("" = single operator, bez multi-VP)
     8:  Infobar (OUTPUT — vstup prázdný)
    """
    return [
        emp_num,                    # 0: EmpNum
        "H",                        # 1: TransType ("H" = machine hours tracking)
        tx.infor_job,               # 2: JobNum
        tx.infor_suffix or "0",    # 3: JobSuffix
        tx.oper_num,                # 4: OperNum
        tx.wc or "",                # 5: Wc
        "",                         # 6: Stroj (Gestima nezná ID stroje)
        "",                         # 7: OldEmpNum (single operator)
        "",                         # 8: Infobar (OUTPUT)
    ]


def _build_sfc34_params(tx: WorkshopTransaction, emp_num: str) -> List[str]:
    """
    Sestaví 20 pozičních parametrů pro IteCzTsdUpdateDcSfc34Sp.

    Použití: POUZE pro odvody (stop, qty_complete, scrap, time) — Module_01120 OdvodKusu.
    NIKOLI pro Start/Stop session akce — ty jdou přes WrapperSp.

    KRITICKÉ: Pozice 1 (index 1) je PRÁZDNÝ STRING — TransType se do SFC34 NEPOSÍLÁ!
    Potvrzeno IL bytecode InduStream.Forms.Std.dll: ldc.i4.1 + ldstr "" na offset 0x000ACBA1.

    Pořadí (index 0–19):
     0:  @TEmpNum           — číslo zaměstnance
     1:  (PRÁZDNÝ STRING)   — NE TransType! Infor si TransType="4" odvodí interně.
     2:  @TJobNum           — číslo zakázky (String, může obsahovat lomítka)
     3:  @TJobSuffix        — suffix zakázky (Int16 — pouze číslo, ne "001"!)
     4:  @TOperNum          — číslo operace
     5:  @TcQtuQtyComp      — odvedené kusy
     6:  @TcQtuQtyScrap     — zmetky
     7:  @TcQtuQtyMove      — přesunuté kusy
     8:  @THours            — odpracované hodiny
     9:  @TComplete         — operace dokončena ("1"/"0")
    10:  @TClose            — VP dokončena ("1"/"0")
    11:  @TIssueParent      — vydej na nadřazenou VP ("0" = ne)
    12:  @TLocation         — cílové místo skladu
    13:  @TLot              — šarže výrobku
    14:  @TReasonCode       — kód příčiny zmetku
    15:  @SerNumList        — seznam sériových čísel
    16:  @TWc               — pracoviště
    17:  @Infobar           — výstupní zpráva SP (vstup prázdný)
    18:  @TStroj            — ID stroje (prázdné — Gestima nezná)
    19:  @TDatumTransakce   — datum transakce ("0" = aktuální datum v Inforu)
    """
    # Pokud actual_hours None a máme start/stop, dopočítej z timestampů
    actual_hours = tx.actual_hours
    if actual_hours is None and tx.started_at and tx.finished_at:
        delta = tx.finished_at - tx.started_at
        actual_hours = round(delta.total_seconds() / 3600, 4)

    return [
        emp_num,                               # 0: @TEmpNum
        "",                                    # 1: (PRÁZDNÝ — NE TransType!)
        tx.infor_job,                          # 2: @TJobNum
        tx.infor_suffix or "0",                # 3: @TJobSuffix (Int16)
        tx.oper_num,                           # 4: @TOperNum
        str(tx.qty_completed or 0),            # 5: @TcQtuQtyComp
        str(tx.qty_scrapped or 0),             # 6: @TcQtuQtyScrap
        str(tx.qty_moved or 0),                # 7: @TcQtuQtyMove
        str(actual_hours or 0),                # 8: @THours
        "1" if tx.oper_complete else "0",      # 9: @TComplete
        "1" if tx.job_complete else "0",       # 10: @TClose
        "0",                                   # 11: @TIssueParent
        "",                                    # 12: @TLocation
        "",                                    # 13: @TLot
        tx.scrap_reason or "",                 # 14: @TReasonCode
        "",                                    # 15: @SerNumList
        tx.wc or "",                           # 16: @TWc
        "",                                    # 17: @Infobar (OUTPUT)
        "",                                    # 18: @TStroj (Gestima nezná ID stroje)
        "",                                    # 19: @TDatumTransakce ("" = aktuální datum v Inforu; "0" crashuje — DateTime parse error 460)
    ]
