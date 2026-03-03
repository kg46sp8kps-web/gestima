"""GESTIMA - Seed data for development/demo

Tento skript vytváří demo data při každém startu aplikace.
Demo záznamy mají v notes "DEMO" pro snadnou identifikaci a mazání.

KRITICKÉ: Demo data MUSÍ dodržovat ADR-017 v2.0 (8-digit random numbering: 10XXXXXX)
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.models.material import MaterialItem
from app.models.material_input import MaterialInput
from app.models.enums import StockShape, UserRole
from app.models.user import User
from app.services.number_generator import NumberGenerator

logger = logging.getLogger(__name__)


async def seed_demo_parts(db: AsyncSession):
    """Vytvoř demo parts pokud neexistují

    Demo parts mají v notes "DEMO" a dají se snadno smazat a znovu vytvořit.

    IMPORTANT: Uses NumberGenerator to comply with ADR-017 v2.0 (8-digit format: 10XXXXXX)
    """
    try:
        # Zjisti jestli máme nějaký materiál
        result = await db.execute(select(MaterialItem).limit(1))
        material = result.scalar_one_or_none()

        if not material:
            logger.warning("No materials found - skipping demo parts creation")
            return

        # Check if demo parts already exist (by article_number prefix)
        result = await db.execute(
            select(Part).where(Part.article_number.like("ART-DEMO-%"))
        )
        existing_demo = result.scalars().all()

        if len(existing_demo) >= 3:
            logger.debug("Demo parts already exist")
            return

        # Generate 8-digit part numbers (ADR-017 v2.0: 10XXXXXX format)
        part_numbers = await NumberGenerator.generate_part_numbers_batch(db, 3)

        # Demo parts data (WITHOUT hardcoded part_numbers!)
        demo_parts_data = [
            {"article_number": "ART-DEMO-001", "name": "Demo hřídel"},
            {"article_number": "ART-DEMO-002", "name": "Demo pouzdro"},
            {"article_number": "ART-DEMO-003", "name": "Demo příruba"},
        ]

        # Step 1: Create Parts first (without material)
        created_parts = []
        for i, data in enumerate(demo_parts_data):
            part = Part(
                part_number=part_numbers[i],  # ADR-017 v2.0 compliant (10XXXXXX)
                article_number=data["article_number"],
                name=data["name"],
                created_by="system_seed"
            )
            db.add(part)
            created_parts.append(part)

        if created_parts:
            await db.commit()
            logger.info(f"✅ Created {len(created_parts)} demo parts with ADR-017 compliant numbers: {part_numbers}")

            # Step 2: Refresh to get IDs, then create MaterialInput for each Part (ADR-024)
            for part in created_parts:
                await db.refresh(part)
                material_input = MaterialInput(
                    part_id=part.id,
                    seq=0,  # First material for this part
                    price_category_id=material.price_category_id,
                    material_item_id=material.id,
                    stock_shape=material.shape,  # Use shape from MaterialItem
                    stock_diameter=material.diameter if material.shape == StockShape.ROUND_BAR else None,
                    stock_length=100.0,
                    quantity=1,
                )
                db.add(material_input)

            await db.commit()
            logger.info(f"✅ Created {len(created_parts)} MaterialInputs for demo parts")
        else:
            logger.debug("Demo parts already exist")

    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding demo parts: {e}", exc_info=True)


# =============================================================================
# EMPLOYEE SEED — reální zaměstnanci z Inforu
# =============================================================================

# Infor EmpNum → user data
# Zdroj: ToExcel_Employees.xlsx (export z Inforu)
# Role: ADMIN = web app + terminál (plný přístup)
#       OPERATOR = terminál + omezený web (PIN login)
#       VIEWER = jen web app (read-only, bez terminálu)
EMPLOYEES = [
    # (emp_num, username,              password,       role,             pin,   first_name,  last_name)
    ("1",   "ladislav.rybka",          "gestima123",   UserRole.ADMIN,    "0001", "Ladislav",  "Rybka"),
    ("2",   "pavel.senkyr",            "gestima123",   UserRole.OPERATOR, "0002", "Pavel",     "Šenkýř"),
    ("3",   "ivana.gratzova",          "gestima123",   UserRole.VIEWER,   None,   "Ivana",     "Grätzová"),
    ("4",   "ivana.senkyrova",         "gestima123",   UserRole.OPERATOR, "0004", "Ivana",     "Šenkýřová"),
    ("5",   "pavel.senkyr.ml",         "gestima123",   UserRole.OPERATOR, "0005", "Pavel",     "Šenkýř ml."),
    ("10",  "petr.drapalik",           "gestima123",   UserRole.OPERATOR, "0010", "Petr",      "Drápalík"),
    ("11",  "adam.pirkl",              "gestima123",   UserRole.OPERATOR, "0011", "Adam",      "Pirkl"),
    ("12",  "karel.novak",             "gestima123",   UserRole.OPERATOR, "0012", "Karel",     "Novák"),
    ("14",  "milan.strnad",            "gestima123",   UserRole.OPERATOR, "0014", "Milan",     "Strnad"),
    ("19",  "milan.kubista",           "gestima123",   UserRole.OPERATOR, "0019", "Milan",     "Kubišta"),
    ("20",  "ladislav.rybka.ml",       "gestima123",   UserRole.ADMIN,    "0020", "Ladislav",  "Rybka ml."),
    ("26",  "helena.stejskalova",      "gestima123",   UserRole.OPERATOR, "0026", "Helena",    "Stejskalová"),
    ("80",  "martin.papacek",          "gestima123",   UserRole.VIEWER,   None,   "Martin",    "Papáček"),
    ("99",  "jan.kolar",               "gestima123",   UserRole.OPERATOR, "0099", "Jan",       "Kolář"),
    ("104", "michaela.senkyrova",      "gestima123",   UserRole.VIEWER,   None,   "Michaela",  "Šenkýřová"),
    ("131", "martin.vagner",           "gestima123",   UserRole.OPERATOR, "0131", "Martin",    "Vágner"),
]


async def seed_employees(db: AsyncSession):
    """Seed zaměstnanců z Inforu — idempotentní (přeskočí existující username).

    Vytvoří uživatele s:
    - username, hashed password
    - role (ADMIN/OPERATOR/VIEWER)
    - infor_emp_num (číslo zaměstnance v Inforu)
    - PIN hash + check (pro terminálové uživatele)
    """
    from app.services.auth_service import get_password_hash, get_pin_hash, get_pin_check

    try:
        # Načti existující usernames pro skip check
        result = await db.execute(select(User.username))
        existing_usernames = {row[0] for row in result.all()}

        created = 0
        for emp_num, username, password, role, pin, first_name, last_name in EMPLOYEES:
            if username in existing_usernames:
                continue

            user = User(
                username=username,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
                infor_emp_num=emp_num,
                created_by="system_seed",
            )

            # PIN pro terminálové uživatele
            if pin:
                user.pin_hash = get_pin_hash(pin)
                user.pin_check = get_pin_check(pin)

            db.add(user)
            created += 1

        if created:
            await db.commit()
            logger.info("Seeded %d employees (Infor EmpNum mapping)", created)
        else:
            logger.debug("All employees already exist — skipping seed")

    except Exception as e:
        await db.rollback()
        logger.error("Error seeding employees: %s", e, exc_info=True)
