"""GESTIMA — Workshop Job Route (DB mirror of Infor SLJobRoutes Type='J')

Lokální SQLite tabulka pro workshop data — eliminuje live Infor HTTP volání.
Plněna přes InforSyncService (inkrementální diff sync přes RecordDate watermark).
"""

from sqlalchemy import Column, Float, Index, Integer, String, UniqueConstraint

from app.database import AuditMixin, Base


class WorkshopJobRoute(Base, AuditMixin):
    """Mirror SLJobRoutes (Type='J') pro workshop use — fronta práce + plán stroje."""

    __tablename__ = "workshop_job_routes"
    __table_args__ = (
        UniqueConstraint("job", "suffix", "oper_num", name="uq_wjr_job_suffix_oper"),
        Index("ix_wjr_wc", "wc"),
        Index("ix_wjr_job_stat", "job_stat"),
    )

    id = Column(Integer, primary_key=True)
    job = Column(String(30), nullable=False)
    suffix = Column(String(5), nullable=False, default="0")
    oper_num = Column(String(10), nullable=False)
    wc = Column(String(20))
    job_stat = Column(String(5))                  # R/F/S/W/C
    der_job_item = Column(String(60))             # DerJobItem (artikl)
    job_description = Column(String(200))         # JobDescription (popis)
    job_qty_released = Column(Float)
    qty_complete = Column(Float)
    qty_scrapped = Column(Float)
    jsh_setup_hrs = Column(Float)
    der_run_mch_hrs = Column(Float)
    op_datum_st = Column(String(30))              # ISO date string (plánovaný začátek)
    op_datum_sp = Column(String(30))              # ISO date string (plánovaný konec)
    record_date = Column(String(30))              # Infor RecordDate pro watermark

    # JBR (IteCzTsdJbrDetails) — stavová data pro odvádění práce
    jbr_state = Column(String(50), nullable=True)       # State z JBR
    jbr_state_asd = Column(String(50), nullable=True)   # StateAsd (autom. stav)
    jbr_lze_dokoncit = Column(String(10), nullable=True) # LzeDokoncit flag
    jbr_plan_flag = Column(String(10), nullable=True)    # PlanFlag
    jbr_synced_at = Column(String(30), nullable=True)    # Timestamp poslední JBR sync
