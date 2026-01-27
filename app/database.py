"""GESTIMA - Database setup"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, event, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


class AuditMixin:
    """Automatic audit fields for all models (ADR-001)"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    # Soft delete (ADR-001)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)
    
    # Optimistic locking
    version = Column(Integer, default=0, nullable=False)


# WAL mode for concurrent reads during writes (ADR)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False}
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Auto-increment version on update (optimistic locking)
@event.listens_for(Base, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    """Auto-increment version for optimistic locking"""
    if hasattr(target, 'version'):
        target.version += 1


async def init_db():
    """Initialize database with WAL mode"""
    # CRITICAL: Import all models BEFORE create_all() to register them with Base.metadata
    from app import models  # noqa: F401 - imports register models with Base

    async with engine.begin() as conn:
        # Enable WAL mode for concurrent access
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA synchronous=NORMAL"))
        await conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache

        # Create tables
        await conn.run_sync(Base.metadata.create_all)

        # Migration: Add stock_* columns to parts table if not exist
        await _migrate_parts_stock_columns(conn)

        # Migration: Update machines hourly rate structure (ADR-016)
        await _migrate_machines_hourly_rate(conn)

        # Migration: Add price_category_id to material_items (ADR-014)
        await _migrate_material_items_price_category(conn)

        # Migration: Create material_norms table (ADR-015)
        await _migrate_material_norms_table(conn)

        # Migration: Add 7-digit random number fields (ADR-017)
        await _migrate_entity_numbers(conn)

    # Seed data (order matters: price_categories → materials → material_norms)
    async with async_session() as session:
        from app.models import MaterialPriceCategory, MaterialGroup, MaterialNorm
        from sqlalchemy import select

        # 1. Seed price categories first (required by materials)
        result = await session.execute(select(MaterialPriceCategory).where(MaterialPriceCategory.deleted_at.is_(None)))
        if not result.scalars().first():
            from scripts.seed_price_categories import seed_price_categories
            await seed_price_categories(session)

        # 2. Then seed materials (depends on price categories)
        result = await session.execute(select(MaterialGroup).where(MaterialGroup.deleted_at.is_(None)))
        if not result.scalars().first():
            from app.seed_materials import seed_materials
            await seed_materials(session)

        # 3. Finally seed material norms (depends on materials)
        result = await session.execute(select(MaterialNorm).where(MaterialNorm.deleted_at.is_(None)))
        if not result.scalars().first():
            from scripts.seed_material_norms import seed_material_norms
            await seed_material_norms(session)


async def _migrate_parts_stock_columns(conn):
    """Add stock_* columns to parts table (v1.2.0 migration)"""
    # Check existing columns
    result = await conn.execute(text("PRAGMA table_info(parts)"))
    existing_columns = {row[1] for row in result.fetchall()}

    # Columns to add
    new_columns = [
        ("stock_diameter", "REAL"),
        ("stock_length", "REAL"),
        ("stock_width", "REAL"),
        ("stock_height", "REAL"),
        ("stock_wall_thickness", "REAL"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            await conn.execute(text(f"ALTER TABLE parts ADD COLUMN {col_name} {col_type}"))

    # Make material_item_id nullable if it isn't
    # SQLite doesn't support ALTER COLUMN, so we skip this check


async def _migrate_machines_hourly_rate(conn):
    """
    Migrate machines table from single hourly_rate to 4-component breakdown (ADR-016)
    - hourly_rate_amortization (odpisy stroje)
    - hourly_rate_labor (mzda operátora)
    - hourly_rate_tools (nástroje)
    - hourly_rate_overhead (provozní režie)
    """
    # Check if machines table exists
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='machines'"))
    if not result.fetchone():
        return  # Table doesn't exist yet, will be created by create_all

    # Check existing columns
    result = await conn.execute(text("PRAGMA table_info(machines)"))
    existing_columns = {row[1] for row in result.fetchall()}

    # New columns to add
    new_columns = [
        ("hourly_rate_amortization", "REAL", 400.0),
        ("hourly_rate_labor", "REAL", 300.0),
        ("hourly_rate_tools", "REAL", 200.0),
        ("hourly_rate_overhead", "REAL", 300.0),
    ]

    for col_name, col_type, default_value in new_columns:
        if col_name not in existing_columns:
            await conn.execute(text(f"ALTER TABLE machines ADD COLUMN {col_name} {col_type} DEFAULT {default_value}"))

    # If old hourly_rate column exists, migrate data
    if "hourly_rate" in existing_columns and "hourly_rate_amortization" in existing_columns:
        # Split old hourly_rate into 4 components (rough estimate: 33% / 25% / 17% / 25%)
        await conn.execute(text("""
            UPDATE machines
            SET
                hourly_rate_amortization = hourly_rate * 0.33,
                hourly_rate_labor = hourly_rate * 0.25,
                hourly_rate_tools = hourly_rate * 0.17,
                hourly_rate_overhead = hourly_rate * 0.25
            WHERE hourly_rate_amortization IS NULL
        """))

        # Note: We can't drop the old column in SQLite without recreating the table
        # So we leave it for backwards compatibility


async def _migrate_material_items_price_category(conn):
    """
    Add price_category_id to material_items table (ADR-014)
    """
    # Check if material_items table exists
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='material_items'"))
    if not result.fetchone():
        return  # Table doesn't exist yet

    # Check existing columns
    result = await conn.execute(text("PRAGMA table_info(material_items)"))
    existing_columns = {row[1] for row in result.fetchall()}

    # Add price_category_id column if missing
    if "price_category_id" not in existing_columns:
        # Add as NULLABLE initially (will be populated by seed script)
        await conn.execute(text("ALTER TABLE material_items ADD COLUMN price_category_id INTEGER"))

        # Check if we have any price categories
        result = await conn.execute(text("SELECT COUNT(*) FROM material_price_categories"))
        count = result.scalar()

        if count > 0:
            # Set default to first category for existing items
            await conn.execute(text("""
                UPDATE material_items
                SET price_category_id = (SELECT id FROM material_price_categories ORDER BY id LIMIT 1)
                WHERE price_category_id IS NULL
            """))


async def _migrate_material_norms_table(conn):
    """
    Create material_norms table (ADR-015: Material Norm Auto-Mapping)
    Note: Usually created by Base.metadata.create_all(), but this ensures indices.
    """
    # Check if material_norms table exists
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='material_norms'"))
    if result.fetchone():
        return  # Table already exists

    # Table will be created by Base.metadata.create_all() above
    # This function is just a placeholder for future manual migrations if needed


async def _migrate_entity_numbers(conn):
    """
    Add 7-digit random number fields (ADR-017: Minimalist Random Numbering)
    - parts.part_number: 1XXXXXX (1000000-1999999)
    - material_items.material_number: 2XXXXXX (2000000-2999999)
    - batches.batch_number: 3XXXXXX (3000000-3999999)

    Migration strategy:
    1. Add column as NULLABLE VARCHAR(7) with UNIQUE constraint
    2. Generate random numbers for existing rows (if any)
    3. Note: SQLite doesn't support ALTER COLUMN to NOT NULL, but Pydantic enforces it

    Version: 1.5.0 (2026-01-27)
    """
    import random

    # === PARTS: part_number ===
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='parts'"))
    if result.fetchone():
        # Check if column exists
        result = await conn.execute(text("PRAGMA table_info(parts)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "part_number" not in existing_columns:
            # Add column
            await conn.execute(text("ALTER TABLE parts ADD COLUMN part_number VARCHAR(7) UNIQUE"))

            # Generate numbers for existing rows
            result = await conn.execute(text("SELECT id FROM parts WHERE part_number IS NULL"))
            existing_rows = result.fetchall()

            if existing_rows:
                used_numbers = set()
                for row in existing_rows:
                    part_id = row[0]
                    # Generate unique random number
                    while True:
                        number = str(random.randint(1000000, 1999999))
                        if number not in used_numbers:
                            used_numbers.add(number)
                            break
                    await conn.execute(
                        text(f"UPDATE parts SET part_number = '{number}' WHERE id = {part_id}")
                    )
        else:
            # Column exists - check if it needs length migration (from VARCHAR(50) to VARCHAR(7))
            # SQLite doesn't support ALTER COLUMN TYPE, so we leave it as is
            # New constraint is enforced by Pydantic (7 chars exactly)
            pass

    # === MATERIAL_ITEMS: material_number ===
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='material_items'"))
    if result.fetchone():
        result = await conn.execute(text("PRAGMA table_info(material_items)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "material_number" not in existing_columns:
            # Add column
            await conn.execute(text("ALTER TABLE material_items ADD COLUMN material_number VARCHAR(7) UNIQUE"))

            # Generate numbers for existing rows
            result = await conn.execute(text("SELECT id FROM material_items WHERE material_number IS NULL OR material_number = ''"))
            existing_rows = result.fetchall()

            if existing_rows:
                used_numbers = set()
                for row in existing_rows:
                    material_id = row[0]
                    while True:
                        number = str(random.randint(2000000, 2999999))
                        if number not in used_numbers:
                            used_numbers.add(number)
                            break
                    await conn.execute(
                        text(f"UPDATE material_items SET material_number = '{number}' WHERE id = {material_id}")
                    )

    # === BATCHES: batch_number ===
    result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='batches'"))
    if result.fetchone():
        result = await conn.execute(text("PRAGMA table_info(batches)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "batch_number" not in existing_columns:
            # Add column
            await conn.execute(text("ALTER TABLE batches ADD COLUMN batch_number VARCHAR(7) UNIQUE"))

            # Generate numbers for existing rows
            result = await conn.execute(text("SELECT id FROM batches WHERE batch_number IS NULL OR batch_number = ''"))
            existing_rows = result.fetchall()

            if existing_rows:
                used_numbers = set()
                for row in existing_rows:
                    batch_id = row[0]
                    while True:
                        number = str(random.randint(3000000, 3999999))
                        if number not in used_numbers:
                            used_numbers.add(number)
                            break
                    await conn.execute(
                        text(f"UPDATE batches SET batch_number = '{number}' WHERE id = {batch_id}")
                    )


async def get_db():
    async with async_session() as session:
        yield session


async def close_db():
    """Graceful shutdown - dispose database engine"""
    await engine.dispose()
