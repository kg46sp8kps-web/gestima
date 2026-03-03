"""GESTIMA — Infor Job Transaction (DB mirror of Infor SLJobTrans)

Lokální SQLite tabulka pro transakce práce zaměstnanců — zdroj pro plnění norem.
Plněna přes InforSyncService (inkrementální diff sync přes RecordDate watermark).
"""

from sqlalchemy import Column, DateTime, Float, Index, Integer, String

from app.database import Base


class InforJobTransaction(Base):
    """Mirror SLJobTrans — transakce odvedené práce per zaměstnanec."""

    __tablename__ = "infor_job_transactions"
    __table_args__ = (
        Index("ix_ijt_emp_trans_date", "emp_num", "trans_date"),
        Index("ix_ijt_job_suffix_oper", "job", "suffix", "oper_num"),
    )

    id = Column(Integer, primary_key=True)
    trans_num = Column(String(30), nullable=False, unique=True)
    trans_type = Column(String(10))
    trans_date = Column(String(30))
    emp_num = Column(String(20))
    job = Column(String(30), nullable=False)
    suffix = Column(String(5), nullable=False, default="0")
    oper_num = Column(String(10))
    wc = Column(String(20))
    run_hrs_t = Column(Float)
    setup_hrs_t = Column(Float)
    qty_complete = Column(Float)
    qty_scrapped = Column(Float)
    record_date = Column(String(30))
    synced_at = Column(DateTime, nullable=False)
