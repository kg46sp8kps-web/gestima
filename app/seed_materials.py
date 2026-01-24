"""GESTIMA - Seed data pro Material Hierarchy (ADR-011)"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialGroup, MaterialItem
from app.models.enums import StockShape

logger = logging.getLogger(__name__)


async def seed_materials(db: AsyncSession):
    """
    Vytvoření základních MaterialGroups a MaterialItems při inicializaci DB.
    Spustí se pouze pokud tabulky jsou prázdné.
    """
    # Check if already seeded
    result = await db.execute(select(MaterialGroup))
    existing_groups = result.scalars().all()

    if existing_groups:
        logger.info(f"Material groups already seeded ({len(existing_groups)} groups found)")
        return

    logger.info("Seeding material groups and items...")

    # ========== MATERIAL GROUPS ==========

    groups_data = [
        {"code": "11xxx", "name": "Ocel automatová (11xxx)", "density": 7.85},
        {"code": "S235", "name": "Ocel konstrukční S235JR", "density": 7.85},
        {"code": "C45", "name": "Ocel konstrukční C45", "density": 7.85},
        {"code": "42CrMo4", "name": "Ocel legovaná 42CrMo4", "density": 7.85},
        {"code": "16MnCr5", "name": "Ocel cementační 16MnCr5", "density": 7.80},
        {"code": "X5CrNi18-10", "name": "Nerez austenit. (304)", "density": 7.90},
        {"code": "X2CrNiMo17-12-2", "name": "Nerez austenit. (316)", "density": 8.00},
        {"code": "6060", "name": "Hliník 6060-T6", "density": 2.70},
        {"code": "7075", "name": "Hliník 7075-T6 (dural)", "density": 2.81},
        {"code": "CuZn37", "name": "Mosaz CuZn37 (Ms63)", "density": 8.40},
        {"code": "CuZn39Pb3", "name": "Mosaz automatová CuZn39Pb3", "density": 8.50},
        {"code": "PA6", "name": "Polyamid 6 (PA6)", "density": 1.14},
        {"code": "POM", "name": "Polyoxymethylen (POM)", "density": 1.42},
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

    items_data = [
        # Ocel automatová 11xxx - kruhové tyče
        {"code": "11SMn30-D16", "name": "11SMn30 ⌀16 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 16, "price": 45.00},
        {"code": "11SMn30-D20", "name": "11SMn30 ⌀20 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 20, "price": 45.50},
        {"code": "11SMn30-D25", "name": "11SMn30 ⌀25 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 25, "price": 46.00},
        {"code": "11SMn30-D30", "name": "11SMn30 ⌀30 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 30, "price": 47.00},
        {"code": "11SMn30-D40", "name": "11SMn30 ⌀40 mm - tyč kruhová ocel automatová", "group": "11xxx", "shape": StockShape.ROUND_BAR, "diameter": 40, "price": 48.50},

        # S235 - konstrukční ocel
        {"code": "S235JR-D50", "name": "S235JR ⌀50 mm - tyč kruhová ocel konstrukční", "group": "S235", "shape": StockShape.ROUND_BAR, "diameter": 50, "price": 42.00},
        {"code": "S235JR-PLT10", "name": "S235JR 10 mm - plech válcovaný", "group": "S235", "shape": StockShape.PLATE, "thickness": 10, "price": 38.00},

        # C45 - konstrukční ocel
        {"code": "C45-D25", "name": "C45 ⌀25 mm - tyč kruhová ocel", "group": "C45", "shape": StockShape.ROUND_BAR, "diameter": 25, "price": 55.00},
        {"code": "C45-D32", "name": "C45 ⌀32 mm - tyč kruhová ocel", "group": "C45", "shape": StockShape.ROUND_BAR, "diameter": 32, "price": 56.00},
        {"code": "C45-SQ30", "name": "C45 30×30 mm - tyč čtvercová", "group": "C45", "shape": StockShape.SQUARE_BAR, "width": 30, "price": 58.00},

        # 42CrMo4 - legovaná ocel
        {"code": "42CrMo4-D40", "name": "42CrMo4 ⌀40 mm - tyč kruhová legovaná", "group": "42CrMo4", "shape": StockShape.ROUND_BAR, "diameter": 40, "price": 85.00},

        # Nerez 304
        {"code": "AISI304-D16", "name": "AISI 304 ⌀16 mm - tyč kruhová nerez", "group": "X5CrNi18-10", "shape": StockShape.ROUND_BAR, "diameter": 16, "price": 180.00},
        {"code": "AISI304-D20", "name": "AISI 304 ⌀20 mm - tyč kruhová nerez", "group": "X5CrNi18-10", "shape": StockShape.ROUND_BAR, "diameter": 20, "price": 185.00},

        # Hliník 6060
        {"code": "6060-D20", "name": "AlMgSi 6060 ⌀20 mm - tyč kruhová hliník", "group": "6060", "shape": StockShape.ROUND_BAR, "diameter": 20, "price": 120.00},
        {"code": "6060-D25", "name": "AlMgSi 6060 ⌀25 mm - tyč kruhová hliník", "group": "6060", "shape": StockShape.ROUND_BAR, "diameter": 25, "price": 122.00},
        {"code": "6060-SQ50", "name": "AlMgSi 6060 50×50 mm - tyč čtvercová hliník", "group": "6060", "shape": StockShape.SQUARE_BAR, "width": 50, "price": 125.00},

        # Hliník 7075 (dural)
        {"code": "7075-D30", "name": "AlZnMgCu 7075 ⌀30 mm - tyč kruhová dural", "group": "7075", "shape": StockShape.ROUND_BAR, "diameter": 30, "price": 280.00},

        # Mosaz
        {"code": "MS63-D20", "name": "Mosaz Ms63 ⌀20 mm - tyč kruhová", "group": "CuZn37", "shape": StockShape.ROUND_BAR, "diameter": 20, "price": 250.00},
        {"code": "MS63-HEX24", "name": "Mosaz Ms63 24 mm - tyč šestihranná", "group": "CuZn37", "shape": StockShape.HEXAGONAL_BAR, "diameter": 24, "price": 255.00},

        # Plasty
        {"code": "PA6-D40", "name": "PA6 černý ⌀40 mm - tyč kruhová polyamid", "group": "PA6", "shape": StockShape.ROUND_BAR, "diameter": 40, "price": 320.00},
        {"code": "POM-D30", "name": "POM bílý ⌀30 mm - tyč kruhová", "group": "POM", "shape": StockShape.ROUND_BAR, "diameter": 30, "price": 380.00},
    ]

    for data in items_data:
        item = MaterialItem(
            code=data["code"],
            name=data["name"],
            material_group_id=groups[data["group"]].id,
            shape=data["shape"],
            diameter=data.get("diameter"),
            width=data.get("width"),
            thickness=data.get("thickness"),
            price_per_kg=data["price"],
            created_by="system"
        )
        db.add(item)

    await db.commit()

    logger.info(f"✓ Seeded {len(groups_data)} material groups")
    logger.info(f"✓ Seeded {len(items_data)} material items")
