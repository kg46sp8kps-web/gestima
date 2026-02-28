"""GESTIMA — Workshop Order Overview (DB mirror of IteRybPrehledZakazekView)

Lokální SQLite tabulka pro přehled zakázek — eliminuje live Infor HTTP volání.
Plněna přes InforSyncService (inkrementální diff sync přes RecordDate watermark).
"""

from sqlalchemy import Boolean, Column, Float, Index, Integer, String, Text, UniqueConstraint

from app.database import AuditMixin, Base


class WorkshopOrderOverview(Base, AuditMixin):
    """Mirror IteRybPrehledZakazekView pro dispečerský přehled zakázek."""

    __tablename__ = "workshop_order_overviews"
    __table_args__ = (
        UniqueConstraint("co_num", "co_line", "co_release", name="uq_woo_co_line_rel"),
        Index("ix_woo_item", "item"),
        Index("ix_woo_due_date", "due_date"),
    )

    id = Column(Integer, primary_key=True)
    co_num = Column(String(20), nullable=False)
    co_line = Column(String(10), nullable=False)
    co_release = Column(String(10), nullable=False, default="0")
    customer_code = Column(String(20))
    customer_name = Column(String(100))
    delivery_name = Column(String(100))
    item = Column(String(60))
    description = Column(String(200))
    stat = Column(String(5))
    due_date = Column(String(30))
    promise_date = Column(String(30))
    confirm_date = Column(String(30))
    qty_ordered = Column(Float)
    qty_shipped = Column(Float)
    qty_on_hand = Column(Float)
    qty_available = Column(Float)
    qty_wip = Column(Float)
    job = Column(String(30))
    suffix = Column(String(5))
    job_count = Column(Integer)
    material_ready = Column(Boolean, default=False)
    # JSON blob pro flat operační/materiálové sloupce z view
    # (Wc01-10, Comp01-10, Wip01-10, Mat01-03, MatComp01-03)
    raw_data = Column(Text)
    record_date = Column(String(30))
