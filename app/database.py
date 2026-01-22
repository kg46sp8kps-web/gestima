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
    created_by = Column(String(100), nullable=True)  # TODO: Integrate with auth
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


async def get_db():
    async with async_session() as session:
        yield session
