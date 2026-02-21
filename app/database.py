"""GESTIMA - Database setup"""

import os
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
    
    # Soft delete (ADR-001) - index=True for query performance (C-3 audit fix)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by = Column(String(100), nullable=True)
    
    # Optimistic locking
    version = Column(Integer, default=0, nullable=False)


# WAL mode for concurrent reads during writes (ADR)
# Note: check_same_thread is for sync SQLite only, NOT for aiosqlite
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Auto-increment version on update (optimistic locking)
@event.listens_for(Base, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    """Auto-increment version for optimistic locking"""
    if hasattr(target, 'version'):
        target.version += 1


async def init_db():
    """
    Initialize database with WAL mode and migrations.

    Strategy (C-5, C-6 audit fix):
    - CRITICAL failures (WAL, create_all) → FAIL FAST
    - Optional migrations → WARN and CONTINUE (idempotent)
    - Seed data → WARN and CONTINUE (non-critical)

    Migration strategy:
    - If Alembic available → use `alembic upgrade head`
    - Else → use legacy ad-hoc migrations (backwards compat)
    """
    from app.logging_config import get_logger
    logger = get_logger(__name__)

    # CRITICAL: Import all models BEFORE create_all() to register them with Base.metadata
    from app import models  # noqa: F401 - imports register models with Base

    try:
        async with engine.begin() as conn:
            # === CRITICAL: WAL mode (FAIL FAST if fails) ===
            try:
                await conn.execute(text("PRAGMA journal_mode=WAL"))
                await conn.execute(text("PRAGMA synchronous=NORMAL"))
                await conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache
                logger.info("✅ WAL mode enabled")
            except Exception as e:
                logger.critical(f"❌ CRITICAL: WAL mode failed: {e}")
                raise  # FAIL FAST - WAL mode is critical for concurrency

            # === CRITICAL: Create tables (FAIL FAST if fails) ===
            try:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("✅ Database tables created/verified")
            except Exception as e:
                logger.critical(f"❌ CRITICAL: create_all() failed: {e}")
                raise  # FAIL FAST - can't run without tables

            # === MIGRATIONS: Alembic vs Legacy ===
            # Check if Alembic version table exists
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
            )
            uses_alembic = result.fetchone() is not None

            if uses_alembic:
                # Use Alembic for migrations
                logger.info("🔄 Using Alembic migrations")
                try:
                    # Auto-backup before migration (safety net)
                    import shutil
                    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
                    if db_path and os.path.exists(db_path) and os.path.getsize(db_path) > 0:
                        backup_path = f"{db_path}.pre-migration.bak"
                        shutil.copy2(db_path, backup_path)
                        logger.info(f"💾 Pre-migration backup: {backup_path}")

                    import subprocess
                    result = subprocess.run(
                        ["alembic", "upgrade", "head"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info("✅ Alembic migrations applied")
                except Exception as e:
                    logger.warning(f"⚠️ Alembic migration failed (non-critical): {e}")
            else:
                # Fallback to legacy ad-hoc migrations (backwards compat)
                logger.info("🔄 Using legacy ad-hoc migrations (backwards compat)")
                await _safe_migrate("parts stock columns", _migrate_parts_stock_columns, conn, logger)
                await _safe_migrate("machines hourly rate", _migrate_machines_hourly_rate, conn, logger)
                await _safe_migrate("material_items price_category", _migrate_material_items_price_category, conn, logger)
                await _safe_migrate("material_norms table", _migrate_material_norms_table, conn, logger)
                await _safe_migrate("entity numbers", _migrate_entity_numbers, conn, logger)
                await _safe_migrate("deleted_at indexes", _migrate_deleted_at_indexes, conn, logger)

    except Exception as e:
        logger.critical(f"❌ Database initialization FAILED: {e}", exc_info=True)
        raise  # FAIL FAST - app must not start with broken DB

    # === SEED DATA (NON-CRITICAL) ===
    async with async_session() as session:
        from app.models import MaterialPriceCategory, MaterialGroup, MaterialNorm
        from sqlalchemy import select

        await _safe_seed("price categories", _seed_price_categories_wrapper, session, logger)
        await _safe_seed("material groups", _seed_material_groups_wrapper, session, logger)
        await _safe_seed("material norms", _seed_material_norms_wrapper, session, logger)


async def _safe_migrate(name: str, migration_func, conn, logger):
    """Wrapper for safe migrations with structured logging (C-5)"""
    try:
        await migration_func(conn)
        logger.info(f"✅ Migration '{name}' successful")
    except Exception as e:
        logger.warning(f"⚠️ Migration '{name}' failed (non-critical): {e}")
        # CONTINUE - migrations are idempotent, skip if already applied


async def _safe_seed(name: str, seed_func, session, logger):
    """Wrapper for safe seeding with structured logging (C-6)"""
    try:
        await seed_func(session)
        logger.info(f"✅ Seed '{name}' successful")
    except Exception as e:
        logger.warning(f"⚠️ Seed '{name}' failed (non-critical): {e}")
        # CONTINUE - seed data is not critical for app startup


# === SEED WRAPPERS ===
async def _seed_price_categories_wrapper(session):
    """Wrapper to check & seed price categories (2026-02-08: skip - handled by gestima.py seed-demo)"""
    # NOTE: PriceCategories seed is now handled by scripts/seed_price_categories.py
    # Called explicitly in gestima.py seed-demo command
    # This wrapper left empty to avoid import errors
    pass


async def _seed_material_groups_wrapper(session):
    """Wrapper to check & seed material groups (2026-02-08: inline 8-digit seed)"""
    from app.models import MaterialGroup
    from sqlalchemy import select

    result = await session.execute(select(MaterialGroup).where(MaterialGroup.deleted_at.is_(None)))
    if not result.scalars().first():
        # Inline seed data (9 groups with 8-digit codes)
        groups = [
            {'code': '20910000', 'name': 'Hliník', 'density': 2.7},
            {'code': '20910001', 'name': 'Měď', 'density': 8.9},
            {'code': '20910002', 'name': 'Mosaz', 'density': 8.5},
            {'code': '20910003', 'name': 'Ocel automatová', 'density': 7.85},
            {'code': '20910004', 'name': 'Ocel konstrukční', 'density': 7.85},
            {'code': '20910005', 'name': 'Ocel legovaná', 'density': 7.85},
            {'code': '20910006', 'name': 'Ocel nástrojová', 'density': 7.85},
            {'code': '20910007', 'name': 'Nerez', 'density': 7.9},
            {'code': '20910008', 'name': 'Plasty', 'density': 1.2},
        ]
        for g in groups:
            session.add(MaterialGroup(**g, created_by='system_seed'))
        await session.commit()


async def _seed_material_norms_wrapper(session):
    """Wrapper to check & seed material norms (2026-02-08: skip - handled by gestima.py seed-demo)"""
    # NOTE: MaterialNorms seed is now handled by scripts/seed_material_norms_complete.py
    # Called explicitly in gestima.py seed-demo command
    # This wrapper left empty to avoid import errors
    pass


def _validate_identifier(name: str) -> str:
    """Validate SQL identifier against injection (only alphanumeric + underscore)."""
    import re
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


async def _migrate_parts_stock_columns(conn):
    """Add stock_* columns to parts table (v1.2.0 migration)"""
    # Check existing columns
    result = await conn.execute(text("PRAGMA table_info(parts)"))
    existing_columns = {row[1] for row in result.fetchall()}

    # Columns to add (hardcoded safe identifiers, validated for defense-in-depth)
    new_columns = [
        ("stock_diameter", "REAL"),
        ("stock_length", "REAL"),
        ("stock_width", "REAL"),
        ("stock_height", "REAL"),
        ("stock_wall_thickness", "REAL"),
    ]

    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            _validate_identifier(col_name)
            _validate_identifier(col_type)
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
            _validate_identifier(col_name)
            _validate_identifier(col_type)
            await conn.execute(
                text(f"ALTER TABLE machines ADD COLUMN {col_name} {col_type} DEFAULT :default_val"),
                {"default_val": default_value}
            )

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
                        text("UPDATE parts SET part_number = :num WHERE id = :pid"),
                        {"num": number, "pid": part_id}
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
                        text("UPDATE material_items SET material_number = :num WHERE id = :mid"),
                        {"num": number, "mid": material_id}
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
                        text("UPDATE batches SET batch_number = :num WHERE id = :bid"),
                        {"num": number, "bid": batch_id}
                    )


async def _migrate_deleted_at_indexes(conn):
    """
    Add indexes on deleted_at columns for performance (C-3 audit fix).
    All list queries filter by deleted_at.is_(None), index makes these O(log n).
    """
    # Tables with AuditMixin (soft delete support)
    tables_with_deleted_at = [
        'parts',
        'batches',
        'operations',
        'features',
        'users',
        'machines',
        'system_config',
        'material_groups',
        'material_price_categories',
        'material_price_tiers',
        'material_items',
        'material_norms',
    ]

    for table in tables_with_deleted_at:
        _validate_identifier(table)
        index_name = f'ix_{table}_deleted_at'
        _validate_identifier(index_name)

        # Check if table exists
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:tbl"),
            {"tbl": table}
        )
        if not result.fetchone():
            continue

        # Check if index exists
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND name=:idx"),
            {"idx": index_name}
        )
        if result.fetchone():
            continue  # Index already exists

        # Create index (DDL — identifiers validated above, cannot use bind params)
        await conn.execute(text(f"CREATE INDEX {index_name} ON {table}(deleted_at)"))


async def get_db():
    async with async_session() as session:
        yield session


async def close_db():
    """Graceful shutdown - dispose database engine"""
    await engine.dispose()
