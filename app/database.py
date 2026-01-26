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

    # Seed material hierarchy (ADR-011)
    from app.seed_materials import seed_materials
    async with async_session() as session:
        await seed_materials(session)


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


async def get_db():
    async with async_session() as session:
        yield session


async def close_db():
    """Graceful shutdown - dispose database engine"""
    await engine.dispose()
