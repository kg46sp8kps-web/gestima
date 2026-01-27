"""GESTIMA - Material Norm Auto-Mapping Service (ADR-015)"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import MaterialNorm, MaterialGroup, MaterialPriceCategory
from app.models.enums import StockShape


# ========== SHAPE → PRICE CATEGORY MAPPING ==========

# Mapping: (MaterialGroup.code, StockShape) → MaterialPriceCategory.code
SHAPE_TO_PRICE_CATEGORY = {
    # Ocel konstrukční (S235, C45, 42CrMo4, 16MnCr5, 11xxx)
    ("S235", StockShape.ROUND_BAR): "OCEL-KRUHOVA",
    ("S235", StockShape.HEXAGONAL_BAR): "OCEL-KRUHOVA",
    ("S235", StockShape.SQUARE_BAR): "OCEL-PLOCHA",
    ("S235", StockShape.FLAT_BAR): "OCEL-PLOCHA",
    ("S235", StockShape.PLATE): "OCEL-DESKY",
    ("S235", StockShape.TUBE): "OCEL-TRUBKA",

    ("C45", StockShape.ROUND_BAR): "OCEL-KRUHOVA",
    ("C45", StockShape.HEXAGONAL_BAR): "OCEL-KRUHOVA",
    ("C45", StockShape.SQUARE_BAR): "OCEL-PLOCHA",
    ("C45", StockShape.FLAT_BAR): "OCEL-PLOCHA",
    ("C45", StockShape.PLATE): "OCEL-DESKY",
    ("C45", StockShape.TUBE): "OCEL-TRUBKA",

    ("42CrMo4", StockShape.ROUND_BAR): "OCEL-KRUHOVA",
    ("42CrMo4", StockShape.HEXAGONAL_BAR): "OCEL-KRUHOVA",
    ("42CrMo4", StockShape.SQUARE_BAR): "OCEL-PLOCHA",
    ("42CrMo4", StockShape.FLAT_BAR): "OCEL-PLOCHA",
    ("42CrMo4", StockShape.PLATE): "OCEL-DESKY",
    ("42CrMo4", StockShape.TUBE): "OCEL-TRUBKA",

    ("16MnCr5", StockShape.ROUND_BAR): "OCEL-KRUHOVA",
    ("16MnCr5", StockShape.HEXAGONAL_BAR): "OCEL-KRUHOVA",
    ("16MnCr5", StockShape.SQUARE_BAR): "OCEL-PLOCHA",
    ("16MnCr5", StockShape.FLAT_BAR): "OCEL-PLOCHA",
    ("16MnCr5", StockShape.PLATE): "OCEL-DESKY",
    ("16MnCr5", StockShape.TUBE): "OCEL-TRUBKA",

    ("11xxx", StockShape.ROUND_BAR): "OCEL-KRUHOVA",
    ("11xxx", StockShape.HEXAGONAL_BAR): "OCEL-KRUHOVA",
    ("11xxx", StockShape.SQUARE_BAR): "OCEL-PLOCHA",
    ("11xxx", StockShape.FLAT_BAR): "OCEL-PLOCHA",
    ("11xxx", StockShape.PLATE): "OCEL-DESKY",
    ("11xxx", StockShape.TUBE): "OCEL-TRUBKA",

    # Nerez (X5CrNi18-10, X2CrNiMo17-12-2)
    ("X5CrNi18-10", StockShape.ROUND_BAR): "NEREZ-KRUHOVA",
    ("X5CrNi18-10", StockShape.HEXAGONAL_BAR): "NEREZ-KRUHOVA",
    ("X5CrNi18-10", StockShape.SQUARE_BAR): "NEREZ-PLOCHA",
    ("X5CrNi18-10", StockShape.FLAT_BAR): "NEREZ-PLOCHA",
    ("X5CrNi18-10", StockShape.PLATE): "NEREZ-PLOCHA",
    ("X5CrNi18-10", StockShape.TUBE): "NEREZ-KRUHOVA",

    ("X2CrNiMo17-12-2", StockShape.ROUND_BAR): "NEREZ-KRUHOVA",
    ("X2CrNiMo17-12-2", StockShape.HEXAGONAL_BAR): "NEREZ-KRUHOVA",
    ("X2CrNiMo17-12-2", StockShape.SQUARE_BAR): "NEREZ-PLOCHA",
    ("X2CrNiMo17-12-2", StockShape.FLAT_BAR): "NEREZ-PLOCHA",
    ("X2CrNiMo17-12-2", StockShape.PLATE): "NEREZ-PLOCHA",
    ("X2CrNiMo17-12-2", StockShape.TUBE): "NEREZ-KRUHOVA",

    # Hliník (6060, 7075)
    ("6060", StockShape.ROUND_BAR): "HLINIK-KRUHOVA",
    ("6060", StockShape.HEXAGONAL_BAR): "HLINIK-KRUHOVA",
    ("6060", StockShape.SQUARE_BAR): "HLINIK-PLOCHA",
    ("6060", StockShape.FLAT_BAR): "HLINIK-PLOCHA",
    ("6060", StockShape.PLATE): "HLINIK-DESKY",
    ("6060", StockShape.TUBE): "HLINIK-KRUHOVA",

    ("7075", StockShape.ROUND_BAR): "HLINIK-KRUHOVA",
    ("7075", StockShape.HEXAGONAL_BAR): "HLINIK-KRUHOVA",
    ("7075", StockShape.SQUARE_BAR): "HLINIK-PLOCHA",
    ("7075", StockShape.FLAT_BAR): "HLINIK-PLOCHA",
    ("7075", StockShape.PLATE): "HLINIK-DESKY",
    ("7075", StockShape.TUBE): "HLINIK-KRUHOVA",

    # Mosaz (CuZn37, CuZn39Pb3)
    ("CuZn37", StockShape.ROUND_BAR): "MOSAZ-BRONZ",
    ("CuZn37", StockShape.HEXAGONAL_BAR): "MOSAZ-BRONZ",
    ("CuZn37", StockShape.SQUARE_BAR): "MOSAZ-BRONZ",
    ("CuZn37", StockShape.FLAT_BAR): "MOSAZ-BRONZ",
    ("CuZn37", StockShape.PLATE): "MOSAZ-BRONZ",
    ("CuZn37", StockShape.TUBE): "MOSAZ-BRONZ",

    ("CuZn39Pb3", StockShape.ROUND_BAR): "MOSAZ-BRONZ",
    ("CuZn39Pb3", StockShape.HEXAGONAL_BAR): "MOSAZ-BRONZ",
    ("CuZn39Pb3", StockShape.SQUARE_BAR): "MOSAZ-BRONZ",
    ("CuZn39Pb3", StockShape.FLAT_BAR): "MOSAZ-BRONZ",
    ("CuZn39Pb3", StockShape.PLATE): "MOSAZ-BRONZ",
    ("CuZn39Pb3", StockShape.TUBE): "MOSAZ-BRONZ",

    # Plasty (PA6, POM)
    ("PA6", StockShape.ROUND_BAR): "PLASTY-TYCE",
    ("PA6", StockShape.SQUARE_BAR): "PLASTY-TYCE",
    ("PA6", StockShape.PLATE): "PLASTY-DESKY",

    ("POM", StockShape.ROUND_BAR): "PLASTY-TYCE",
    ("POM", StockShape.SQUARE_BAR): "PLASTY-TYCE",
    ("POM", StockShape.PLATE): "PLASTY-DESKY",
}


# ========== SERVICE FUNCTIONS ==========

async def auto_assign_group(
    db: AsyncSession,
    norm_code: str
) -> MaterialGroup:
    """
    Auto-assign MaterialGroup z normy (vyhledání napříč všemi 4 sloupci).

    Vyhledání je case-insensitive (1.4301 = 1.4301, c45 = C45).
    Hledá v: W.Nr, EN ISO, ČSN, AISI.

    Args:
        db: Async database session
        norm_code: Kód normy (např. "1.4301", "C45", "12050", "11109")

    Returns:
        MaterialGroup instance

    Raises:
        ValueError: Norma není v DB, musí být přidána přes Admin → Material Norms

    Example:
        >>> # User zadá MaterialItem code "1.0036-HR005w05-T"
        >>> # Extrahuje "1.0036" a hledá v conversion table
        >>> group = await auto_assign_group(db, "1.0036")
        >>> print(group.name)  # "Ocel konstrukční"

        >>> # Nebo zadá "D20 11109"
        >>> # Extrahuje "11109" a najde v ČSN sloupci
        >>> group = await auto_assign_group(db, "11109")
        >>> print(group.name)  # "Ocel konstrukční"
    """
    # Search across all 4 columns (W.Nr, EN ISO, ČSN, AISI) - case-insensitive
    result = await db.execute(
        select(MaterialNorm)
        .options(selectinload(MaterialNorm.material_group))
        .where(
            (func.upper(MaterialNorm.w_nr) == norm_code.upper()) |
            (func.upper(MaterialNorm.en_iso) == norm_code.upper()) |
            (func.upper(MaterialNorm.csn) == norm_code.upper()) |
            (func.upper(MaterialNorm.aisi) == norm_code.upper())
        )
        .where(MaterialNorm.deleted_at.is_(None))
    )
    norm = result.scalar_one_or_none()

    if not norm:
        raise ValueError(
            f"Neznámá norma: {norm_code}. "
            f"Přidej ji v Admin → Material Norms nebo kontaktuj administrátora."
        )

    return norm.material_group


async def auto_assign_price_category(
    db: AsyncSession,
    group_code: str,
    shape: StockShape
) -> MaterialPriceCategory:
    """
    Auto-assign MaterialPriceCategory z (MaterialGroup.code, StockShape).

    Args:
        db: Async database session
        group_code: Kód MaterialGroup (např. "C45", "X5CrNi18-10")
        shape: Tvar polotovaru

    Returns:
        MaterialPriceCategory instance

    Raises:
        ValueError: Kombinace (group, shape) není v mappingu

    Example:
        >>> category = await auto_assign_price_category(db, "C45", StockShape.ROUND_BAR)
        >>> print(category.code)  # "OCEL-KRUHOVA"

        >>> category = await auto_assign_price_category(db, "X5CrNi18-10", StockShape.FLAT_BAR)
        >>> print(category.code)  # "NEREZ-PLOCHA"
    """
    # Najít MaterialPriceCategory code z mappingu
    category_code = SHAPE_TO_PRICE_CATEGORY.get((group_code, shape))

    if not category_code:
        raise ValueError(
            f"Neznámá kombinace: MaterialGroup '{group_code}' + shape '{shape}'. "
            f"Kontaktuj administrátora pro přidání mappingu."
        )

    # Načíst MaterialPriceCategory z DB
    result = await db.execute(
        select(MaterialPriceCategory)
        .where(MaterialPriceCategory.code == category_code)
        .where(MaterialPriceCategory.deleted_at.is_(None))
    )
    category = result.scalar_one_or_none()

    if not category:
        raise ValueError(
            f"MaterialPriceCategory '{category_code}' neexistuje v DB. "
            f"Kontaktuj administrátora."
        )

    return category


async def auto_assign_categories(
    db: AsyncSession,
    norm_code: str,
    shape: StockShape
) -> tuple[MaterialGroup, MaterialPriceCategory]:
    """
    Auto-assign MaterialGroup + MaterialPriceCategory z (norma, tvar).

    Kombinuje auto_assign_group() + auto_assign_price_category().

    Args:
        db: Async database session
        norm_code: Kód normy (např. "1.4301", "C45")
        shape: Tvar polotovaru

    Returns:
        Tuple (MaterialGroup, MaterialPriceCategory)

    Raises:
        ValueError: Norma nebo kombinace (group, shape) není v mappingu

    Example:
        >>> group, category = await auto_assign_categories(db, "1.4301", StockShape.ROUND_BAR)
        >>> print(group.code)  # "X5CrNi18-10"
        >>> print(category.code)  # "NEREZ-KRUHOVA"

        >>> group, category = await auto_assign_categories(db, "C45", StockShape.PLATE)
        >>> print(group.code)  # "C45"
        >>> print(category.code)  # "OCEL-DESKY"
    """
    # 1. Najít MaterialGroup z normy
    group = await auto_assign_group(db, norm_code)

    # 2. Najít MaterialPriceCategory z (group, shape)
    category = await auto_assign_price_category(db, group.code, shape)

    return (group, category)


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
