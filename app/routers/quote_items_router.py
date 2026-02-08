"""GESTIMA - Quote Items API router

Quote items are nested under quotes.
Auto-loads pricing from latest frozen batch_set.
Auto-recalculates quote totals after item changes.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user
from app.models import User
from app.models.quote import Quote, QuoteItem, QuoteItemCreate, QuoteItemUpdate, QuoteItemResponse
from app.models.part import Part
from app.services.quote_service import QuoteService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/quotes/{quote_number}/items", response_model=List[QuoteItemResponse])
async def get_quote_items(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all items for a quote"""
    try:
        # Find quote
        result = await db.execute(
            select(Quote).where(
                Quote.quote_number == quote_number,
                Quote.deleted_at.is_(None)
            )
        )
        quote = result.scalar_one_or_none()

        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")

        # Get items
        result = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.deleted_at.is_(None)
            )
        )
        items = result.scalars().all()

        return [QuoteItemResponse.model_validate(item) for item in items]
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching quote items for {quote_number}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při načítání položek nabídky")


@router.post("/quotes/{quote_number}/items", response_model=QuoteItemResponse)
async def create_quote_item(
    quote_number: str,
    data: QuoteItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new quote item.

    Auto-loads pricing from latest frozen batch_set for the part.
    Auto-recalculates quote totals.

    Edit lock: Only allowed if quote is in DRAFT status.
    """
    # Find quote
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Check edit lock
    QuoteService.check_edit_lock(quote)

    # Find part
    part = await db.get(Part, data.part_id)
    if not part or part.deleted_at:
        raise HTTPException(status_code=404, detail="Part not found")

    # Auto-load pricing from frozen batch_set
    unit_price = await QuoteService.get_latest_frozen_batch_price(data.part_id, db)

    # Create item
    item = QuoteItem(
        quote_id=quote.id,
        part_id=data.part_id,
        part_number=part.part_number,
        part_name=part.name,
        quantity=data.quantity,
        unit_price=unit_price,
        notes=data.notes,
    )

    # Calculate line total
    await QuoteService.recalculate_item_total(item)

    set_audit(item, current_user.username)
    db.add(item)
    await db.flush()

    # Recalculate quote totals
    await QuoteService.recalculate_quote_totals(quote, db)
    set_audit(quote, current_user.username, is_update=True)
    quote.version += 1

    await safe_commit(db, item, "vytváření položky nabídky")

    logger.info(
        f"Created quote item for quote {quote_number}, "
        f"part {part.part_number} by {current_user.username}"
    )
    return QuoteItemResponse.model_validate(item)


@router.get("/quote_items/{item_id}", response_model=QuoteItemResponse)
async def get_quote_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single quote item by ID"""
    try:
        result = await db.execute(
            select(QuoteItem).where(
                QuoteItem.id == item_id,
                QuoteItem.deleted_at.is_(None)
            )
        )
        item = result.scalar_one_or_none()

        if not item:
            raise HTTPException(status_code=404, detail="Quote item not found")

        return QuoteItemResponse.model_validate(item)
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching quote item {item_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Chyba databáze při načítání položky nabídky")


@router.put("/quote_items/{item_id}", response_model=QuoteItemResponse)
async def update_quote_item(
    item_id: int,
    data: QuoteItemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quote item.

    Auto-recalculates line_total and quote totals.
    Edit lock: Only allowed if quote is in DRAFT status.
    """
    result = await db.execute(
        select(QuoteItem).where(
            QuoteItem.id == item_id,
            QuoteItem.deleted_at.is_(None)
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Quote item not found")

    # Get quote
    quote = await db.get(Quote, item.quote_id)
    if not quote or quote.deleted_at:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Check edit lock
    QuoteService.check_edit_lock(quote)

    # Optimistic locking
    if item.version != data.version:
        raise HTTPException(status_code=409, detail="Version conflict")

    # Update fields (unit_price is read-only from frozen batch)
    if data.quantity is not None:
        item.quantity = data.quantity
    if data.notes is not None:
        item.notes = data.notes

    # Recalculate line total
    await QuoteService.recalculate_item_total(item)

    set_audit(item, current_user.username, is_update=True)
    item.version += 1

    await db.flush()

    # Recalculate quote totals
    await QuoteService.recalculate_quote_totals(quote, db)
    set_audit(quote, current_user.username, is_update=True)
    quote.version += 1

    await safe_commit(db, item, "aktualizace položky nabídky")

    logger.info(f"Updated quote item {item_id} by {current_user.username}")
    return QuoteItemResponse.model_validate(item)


@router.delete("/quote_items/{item_id}")
async def delete_quote_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete quote item.

    Auto-recalculates quote totals.
    Edit lock: Only allowed if quote is in DRAFT status.
    """
    result = await db.execute(
        select(QuoteItem).where(
            QuoteItem.id == item_id,
            QuoteItem.deleted_at.is_(None)
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Quote item not found")

    # Get quote
    quote = await db.get(Quote, item.quote_id)
    if not quote or quote.deleted_at:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Check edit lock
    QuoteService.check_edit_lock(quote)

    # Soft delete
    from datetime import datetime
    item.deleted_at = datetime.utcnow()
    item.deleted_by = current_user.username

    await db.flush()

    # Recalculate quote totals
    await QuoteService.recalculate_quote_totals(quote, db)
    set_audit(quote, current_user.username, is_update=True)
    quote.version += 1

    await safe_commit(db, action="mazání položky nabídky")

    logger.info(f"Deleted quote item {item_id} by {current_user.username}")
    return {"message": "Quote item deleted"}
