"""GESTIMA — Workshop Job Materials Cache

Lazy cache pro materiály operací (z Inforu IteCzTsdSLJobMatls + SLJobmatls).
Plněno on-demand: první požadavek → Infor fetch + uložení, další → DB read.
Invalidace: po materiálovém odvodu nebo po TTL (15 min).
"""

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.database import Base


class WorkshopJobMaterialCache(Base):
    """Cache materiálů pro job+suffix+oper — JSON blob."""

    __tablename__ = "workshop_job_material_cache"
    __table_args__ = (
        UniqueConstraint("job", "suffix", "oper_num", name="uq_wjmc_job_suffix_oper"),
    )

    id = Column(Integer, primary_key=True)
    job = Column(String(30), nullable=False, index=True)
    suffix = Column(String(5), nullable=False, default="0")
    oper_num = Column(String(10), nullable=False)
    data_json = Column(Text, nullable=False)  # JSON array of material dicts
    synced_at = Column(DateTime, nullable=False)  # UTC timestamp of last Infor fetch
