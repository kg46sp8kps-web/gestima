"""GESTIMA - Seed data pro Material Hierarchy (ADR-011, ADR-014)"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialGroup, MaterialItem, MaterialPriceCategory
from app.models.enums import StockShape
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)


async def seed_materials(db: AsyncSession):
    """
    Vytvoření základních MaterialGroups a MaterialItems při inicializaci DB (ADR-011, ADR-014).
    Spustí se pouze pokud tabulky jsou prázdné.

    REQUIRES: MaterialPriceCategories must be seeded first (run seed_price_categories.py).
    """
    # Check if already seeded
    result = await db.execute(select(MaterialGroup))
    existing_groups = result.scalars().all()

    if existing_groups:
        logger.info(f"Material groups already seeded ({len(existing_groups)} groups found)")
        return

    logger.info("Seeding material groups and items...")

    # Load price categories (ADR-014)
    result = await db.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.deleted_at.is_(None)))
    price_categories = {cat.code: cat for cat in result.scalars().all()}

    if not price_categories:
        logger.error("❌ Price categories not found. Run seed_price_categories.py first!")
        raise ValueError("Price categories must be seeded before materials")

    # ========== MATERIAL GROUPS ==========

    groups_data = [
        {"code": "11xxx", "name": "Ocel konstrukční (automatová)", "density": 7.85},
        {"code": "S235", "name": "Ocel konstrukční (S235)", "density": 7.85},
        {"code": "C45", "name": "Ocel konstrukční (C45)", "density": 7.85},
        {"code": "42CrMo4", "name": "Ocel legovaná (42CrMo4)", "density": 7.85},
        {"code": "16MnCr5", "name": "Ocel legovaná (16MnCr5)", "density": 7.80},
        {"code": "X5CrNi18-10", "name": "Nerez (304)", "density": 7.90},
        {"code": "X2CrNiMo17-12-2", "name": "Nerez (316L)", "density": 8.00},
        {"code": "6060", "name": "Hliník (6060)", "density": 2.70},
        {"code": "7075", "name": "Hliník (7075 dural)", "density": 2.81},
        {"code": "CuZn37", "name": "Mosaz (CuZn37)", "density": 8.40},
        {"code": "CuZn39Pb3", "name": "Mosaz (automatová)", "density": 8.50},
        {"code": "PA6", "name": "Plasty (PA6)", "density": 1.14},
        {"code": "POM", "name": "Plasty (POM)", "density": 1.42},
    ]

    groups = {}
    for data in groups_data:
        group = MaterialGroup(
            code=data["code"],
            name=data["name"],
            density=data["density"],
            created_by="system"
        )
        db.add(group)
        groups[data["code"]] = group

    await db.flush()  # Získat IDs pro items

    # ========== MATERIAL ITEMS ==========

    # ADR-014: Mapping materiálů na price categories
    def get_price_category_code(group_code: str, shape: StockShape) -> str:
        """Map material group + shape to price category code."""
        # Ocel automatová/konstrukční
        if group_code in ["11xxx", "S235", "C45", "42CrMo4", "16MnCr5"]:
            if shape == StockShape.ROUND_BAR:
                return "OCEL-KRUHOVA"
            elif shape in [StockShape.FLAT_BAR, StockShape.SQUARE_BAR]:
                return "OCEL-PLOCHA"
            elif shape == StockShape.PLATE:
                return "OCEL-DESKY"
            elif shape == StockShape.TUBE:
                return "OCEL-TRUBKA"
        # Nerez
        elif group_code in ["X5CrNi18-10", "X2CrNiMo17-12-2"]:
            if shape == StockShape.ROUND_BAR:
                return "NEREZ-KRUHOVA"
            elif shape in [StockShape.FLAT_BAR, StockShape.SQUARE_BAR]:
                return "NEREZ-PLOCHA"
        # Hliník
        elif group_code in ["6060", "7075"]:
            if shape in [StockShape.PLATE, StockShape.SQUARE_BAR]:
                return "HLINIK-DESKY"
            elif shape == StockShape.ROUND_BAR:
                return "HLINIK-KRUHOVA"
            elif shape == StockShape.FLAT_BAR:
                return "HLINIK-PLOCHA"
        # Mosaz/bronz
        elif group_code in ["CuZn37", "CuZn39Pb3"]:
            return "MOSAZ-BRONZ"
        # Plasty
        elif group_code in ["PA6", "POM"]:
            if shape in [StockShape.PLATE, StockShape.SQUARE_BAR]:
                return "PLASTY-DESKY"
            elif shape == StockShape.ROUND_BAR:
                return "PLASTY-TYCE"

        # Default fallback (kruhová ocel)
        logger.warning(f"No price category mapping for {group_code} + {shape}, using OCEL-KRUHOVA")
        return "OCEL-KRUHOVA"

    items_data = [
        # Ocel automatová 11xxx - kruhové tyče
        {"code": "11SMn30-D16", "name": "11SMn30 ⌀16 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 16},
        {"code": "11SMn30-D20", "name": "11SMn30 ⌀20 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 20},
        {"code": "11SMn30-D25", "name": "11SMn30 ⌀25 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 25},
        {"code": "11SMn30-D30", "name": "11SMn30 ⌀30 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 30},
        {"code": "11SMn30-D40", "name": "11SMn30 ⌀40 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 40},

        # S235 - konstrukční ocel
        {"code": "S235JR-D50", "name": "S235JR ⌀50 mm - tyč kruhová ocel konstrukční", "group": "S235", "shape": StockShape.ROUND_BAR, "diameter": 50},
        {"code": "S235JR-PLT10", "name": "S235JR 10 mm - plech válcovaný", "group": "S235", "shape": StockShape.PLATE, "thickness": 10},

        # C45 - konstrukční ocel
        {"code": "C45-D25", "name": "C45 ⌀25 mm - tyč kruhová ocel", "group": "C45", "shape": StockShape.ROUND_BAR, "diameter": 25},
        {"code": "C45-D32", "name": "C45 ⌀32 mm - tyč kruhová ocel", "group": "C45", "shape": StockShape.ROUND_BAR, "diameter": 32},
        {"code": "C45-SQ30", "name": "C45 30×30 mm - tyč čtvercová", "group": "C45", "shape": StockShape.SQUARE_BAR, "width": 30},

        # 42CrMo4 - legovaná ocel
        {"code": "42CrMo4-D40", "name": "42CrMo4 ⌀40 mm - tyč kruhová legovaná", "group": "42CrMo4", "shape": StockShape.ROUND_BAR, "diameter": 40},

        # Nerez 304
        {"code": "AISI304-D16", "name": "AISI 304 ⌀16 mm - tyč kruhová nerez", "group": "X5CrNi18-10", "shape": StockShape.ROUND_BAR, "diameter": 16},
        {"code": "AISI304-D20", "name": "AISI 304 ⌀20 mm - tyč kruhová nerez", "group": "X5CrNi18-10", "shape": StockShape.ROUND_BAR, "diameter": 20},

        # Hliník 6060
        {"code": "6060-D20", "name": "AlMgSi 6060 ⌀20 mm - tyč kruhová hliník", "group": "6060", "shape": StockShape.ROUND_BAR, "diameter": 20},
        {"code": "6060-D25", "name": "AlMgSi 6060 ⌀25 mm - tyč kruhová hliník", "group": "6060", "shape": StockShape.ROUND_BAR, "diameter": 25},
        {"code": "6060-SQ50", "name": "AlMgSi 6060 50×50 mm - tyč čtvercová hliník", "group": "6060", "shape": StockShape.SQUARE_BAR, "width": 50},

        # Hliník 7075 (dural)
        {"code": "7075-D30", "name": "AlZnMgCu 7075 ⌀30 mm - tyč kruhová dural", "group": "7075", "shape": StockShape.ROUND_BAR, "diameter": 30},

        # Mosaz
        {"code": "MS63-D20", "name": "Mosaz Ms63 ⌀20 mm - tyč kruhová", "group": "CuZn37", "shape": StockShape.ROUND_BAR, "diameter": 20},
        {"code": "MS63-HEX24", "name": "Mosaz Ms63 24 mm - tyč šestihranná", "group": "CuZn37", "shape": StockShape.HEXAGONAL_BAR, "diameter": 24},

        # Plasty
        {"code": "PA6-D40", "name": "PA6 černý ⌀40 mm - tyč kruhová polyamid", "group": "PA6", "shape": StockShape.ROUND_BAR, "diameter": 40},
        {"code": "POM-D30", "name": "POM bílý ⌀30 mm - tyč kruhová", "group": "POM", "shape": StockShape.ROUND_BAR, "diameter": 30},
    ]

    # Generate material_numbers in batch (ADR-017)
    material_numbers = await NumberGenerator.generate_material_numbers_batch(db, len(items_data))
    logger.info(f"Generated {len(material_numbers)} material numbers")

    for idx, data in enumerate(items_data):
        # ADR-014: Map to price category
        price_category_code = get_price_category_code(data["group"], data["shape"])
        price_category = price_categories.get(price_category_code)

        if not price_category:
            logger.error(f"Price category '{price_category_code}' not found for {data['code']}")
            continue

        item = MaterialItem(
            material_number=material_numbers[idx],
            code=data["code"],
            name=data["name"],
            material_group_id=groups[data["group"]].id,
            price_category_id=price_category.id,
            shape=data["shape"],
            diameter=data.get("diameter"),
            width=data.get("width"),
            thickness=data.get("thickness"),
            created_by="system"
        )
        db.add(item)

    await db.commit()

    logger.info(f"✓ Seeded {len(groups_data)} material groups")
    logger.info(f"✓ Seeded {len(items_data)} material items")
