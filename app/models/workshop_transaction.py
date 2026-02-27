"""GESTIMA - WorkshopTransaction model

Lokální buffer pro dílnické transakce před odesláním do Inforu.
Dělníci odvádějí kusy/čas přes Gestima Dílna terminál;
transakce se ukládají lokálně (status=pending) a odesílají
do Inforu přes stored procedure IteCzTsdUpdateDcSfc34Sp.

SP parametry (18 params potvrzen typovým testem, @TTransType pozice NEZNÁMÁ):
  IteCzTsdUpdateDcSfc34Sp(EmpNum, MultiJob, Job, Suffix[Int16], OperNum,
    QtyComp, QtyScrap, QtyMove, Hours, Complete, Close,
    IssueParent, Location, Lot, ReasonCode, SerNumList, Wc, Infobar)
  Viz ADR-051 pro stav — @TTransType pozice bude doplněna po zjištění.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum as SAEnum

from app.database import Base, AuditMixin
from app.models.enums import WorkshopTransType, WorkshopTxStatus


class WorkshopTransaction(Base, AuditMixin):
    """Dílnická transakce — lokální buffer před odesláním do Inforu."""
    __tablename__ = "workshop_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # Infor identifikace zakázky
    infor_job = Column(String(30), nullable=False, index=True)    # Číslo zakázky, např. "16VP09/055"
    infor_suffix = Column(String(5), nullable=True, default="0")   # Suffix dávky, default "0"
    infor_item = Column(String(30), nullable=True)                 # DerJobItem — číslo dílu z Infor (@TItem v DcSfcMchtrxSp)
    oper_num = Column(String(10), nullable=False)                   # Číslo operace, např. "10"
    wc = Column(String(20), nullable=True)                         # Pracoviště (@TWc v SP)

    # Typ transakce
    trans_type = Column(SAEnum(WorkshopTransType), nullable=False)

    # Hodnoty transakce
    qty_completed = Column(Float, nullable=True)             # Počet odvedených kusů (@TcQtuQtyComp)
    qty_scrapped = Column(Float, nullable=True)              # Počet zmetků (@TcQtuQtyScrap)
    qty_moved = Column(Float, nullable=True)                 # Přesunuté kusy (@TcQtuQtyMove)
    scrap_reason = Column(String(50), nullable=True)         # Kód důvodu zmetku (@TReasonCode)
    actual_hours = Column(Float, nullable=True)              # Odpracované hodiny (@THours)

    # Příznaky dokončení
    oper_complete = Column(Boolean, default=False, nullable=False)  # Operace dokončena (@TComplete)
    job_complete = Column(Boolean, default=False, nullable=False)   # VP dokončeno (@TClose)

    # Časovač (pro start/stop transakce)
    started_at = Column(DateTime, nullable=True)             # Kdy byl spuštěn časovač
    finished_at = Column(DateTime, nullable=True)            # Kdy byl zastaven

    # Status vůči Inforu
    status = Column(
        SAEnum(WorkshopTxStatus),
        default=WorkshopTxStatus.PENDING,
        nullable=False,
        index=True
    )
    error_msg = Column(String(500), nullable=True)           # Chybová zpráva z Inforu
    posted_at = Column(DateTime, nullable=True)              # Kdy bylo odesláno do Inforu

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version
    # created_by = username dělníka (z JWT)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class WorkshopTransactionCreate(BaseModel):
    """Schema pro vytvoření transakce (uložení do bufferu)."""
    infor_job: str = Field(..., min_length=1, max_length=30)
    infor_suffix: str = Field("0", max_length=5)
    infor_item: Optional[str] = Field(None, max_length=30)
    oper_num: str = Field(..., min_length=1, max_length=10)
    wc: Optional[str] = Field(None, max_length=20)
    trans_type: WorkshopTransType
    qty_completed: Optional[float] = Field(None, ge=0)
    qty_scrapped: Optional[float] = Field(None, ge=0)
    qty_moved: Optional[float] = Field(None, ge=0)
    scrap_reason: Optional[str] = Field(None, max_length=50)
    actual_hours: Optional[float] = Field(None, ge=0)
    oper_complete: bool = False
    job_complete: bool = False
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class WorkshopTransactionResponse(BaseModel):
    """Schema pro odpověď s transakcí."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    infor_job: str
    infor_suffix: Optional[str]
    infor_item: Optional[str]
    oper_num: str
    wc: Optional[str]
    trans_type: WorkshopTransType
    qty_completed: Optional[float]
    qty_scrapped: Optional[float]
    qty_moved: Optional[float]
    scrap_reason: Optional[str]
    actual_hours: Optional[float]
    oper_complete: bool
    job_complete: bool
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status: WorkshopTxStatus
    error_msg: Optional[str]
    posted_at: Optional[datetime]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    version: int
