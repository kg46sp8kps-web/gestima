"""GESTIMA - Material Norm Auto-Mapping Service (ADR-015)"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MaterialNorm, MaterialGroup, MaterialPriceCategory
from app.models.enums import StockShape


# ========== SERVICE FUNCTIONS ==========

async def search_norms(
    db: AsyncSession,
    query: str,
    limit: int = 50
) -> list[MaterialNorm]:
    """
    Vyhledej normy podle kódu (case-insensitive, partial match).
    Hledá napříč všemi 4 sloupci: W.Nr, EN ISO, ČSN, AISI.

    Args:
        db: Async database session
        query: Hledaný text (např. "1.4", "c45", "11109")
        limit: Max počet výsledků (default 50)

    Returns:
        List MaterialNorm (sorted by id)

    Example:
        >>> norms = await search_norms(db, "c45")
        >>> for norm in norms:
        >>>     print(f"W.Nr: {norm.w_nr}, EN ISO: {norm.en_iso}, ČSN: {norm.csn}, AISI: {norm.aisi}")
        # W.Nr: 1.0503, EN ISO: C45, ČSN: 12050, AISI: 1045
    """
    result = await db.execute(
        select(MaterialNorm)
        .options(selectinload(MaterialNorm.material_group))
        .where(
            (func.upper(MaterialNorm.w_nr).like(f"%{query.upper()}%")) |
            (func.upper(MaterialNorm.en_iso).like(f"%{query.upper()}%")) |
            (func.upper(MaterialNorm.csn).like(f"%{query.upper()}%")) |
            (func.upper(MaterialNorm.aisi).like(f"%{query.upper()}%"))
        )
        .where(MaterialNorm.deleted_at.is_(None))
        .order_by(MaterialNorm.id)
        .limit(limit)
    )
    return list(result.scalars().all())
