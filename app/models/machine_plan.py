"""GESTIMA - MachinePlanEntry model

Lokalni poradnik (playlist) pro mistrovske planovani operaci na pracovisti.
DB uklada POUZE poradi (position). Cerstva data (qty, popis, datumy) se vzdy
ctou z Inforu. Princip: DB = poradnik, Infor = zdroj dat.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, UniqueConstraint

from app.database import Base, AuditMixin


class MachinePlanEntry(Base, AuditMixin):
    """Lokalni zaznam poradi operace v planu stroje."""
    __tablename__ = "machine_plan_entries"
    __table_args__ = (
        UniqueConstraint(
            "wc", "infor_job", "infor_suffix", "oper_num",
            name="uq_machine_plan_wc_job_suffix_oper",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    wc = Column(String(20), nullable=False, index=True)
    infor_job = Column(String(30), nullable=False)
    infor_suffix = Column(String(5), nullable=False, default="0")
    oper_num = Column(String(10), nullable=False)
    position = Column(Integer, nullable=False, default=0)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class MachinePlanOperationKey(BaseModel):
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    oper_num: str = Field(..., min_length=1, max_length=10)


class MachinePlanReorderRequest(BaseModel):
    """Bulk prerazeni pozic — mistr pretahl DnD."""
    wc: str = Field(..., min_length=1, max_length=20)
    ordered_keys: List[MachinePlanOperationKey]


class MachinePlanAddRequest(BaseModel):
    """Pridat operaci do planu."""
    wc: str = Field(..., min_length=1, max_length=20)
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    oper_num: str = Field(..., min_length=1, max_length=10)
    position: Optional[int] = None


class MachinePlanRemoveRequest(BaseModel):
    """Odebrat operaci z planu."""
    wc: str = Field(..., min_length=1, max_length=20)
    job: str = Field(..., min_length=1, max_length=30)
    suffix: str = Field("0", max_length=5)
    oper_num: str = Field(..., min_length=1, max_length=10)
