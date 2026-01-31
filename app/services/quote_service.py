"""GESTIMA - Quote Service (Business Logic)

Core responsibilities:
- Pricing calculation (auto-load from frozen batch_sets)
- Quote totals recalculation
- Workflow transitions (DRAFT → SENT → APPROVED/REJECTED)
- Snapshot creation (ADR-VIS-002)
- Edit lock enforcement
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.quote import Quote, QuoteItem
from app.models.batch_set import BatchSet
from app.models.batch import Batch
from app.models.part import Part
from app.models.partner import Partner
from app.models.enums import QuoteStatus

logger = logging.getLogger(__name__)


class QuoteService:
    """Business logic for quotes"""

    @staticmethod
    async def get_latest_frozen_batch_price(part_id: int, db: AsyncSession) -> float:
        """
        Get unit price from latest frozen batch_set for a part.

        Logic:
        1. Find frozen batch_set for part (status='frozen')
        2. Order by updated_at DESC
        3. Return unit_price_frozen from first batch in set

        Returns:
            Unit price (float), defaults to 0.0 if no frozen batch found
        """
        # Find latest frozen batch_set
        result = await db.execute(
            select(BatchSet)
            .where(
                BatchSet.part_id == part_id,
                BatchSet.status == "frozen",
                BatchSet.deleted_at.is_(None)
            )
            .order_by(desc(BatchSet.updated_at))
            .limit(1)
        )
        batch_set = result.scalar_one_or_none()

        if not batch_set:
            logger.warning(f"No frozen batch_set found for part_id={part_id}")
            return 0.0

        # Get first batch from the set
        result = await db.execute(
            select(Batch)
            .where(
                Batch.batch_set_id == batch_set.id,
                Batch.deleted_at.is_(None)
            )
            .limit(1)
        )
        batch = result.scalar_one_or_none()

        if not batch:
            logger.warning(f"No batches found in batch_set {batch_set.set_number}")
            return 0.0

        # Return frozen price or fallback to unit_cost
        price = batch.unit_price_frozen if batch.unit_price_frozen else batch.unit_cost
        logger.debug(f"Auto-loaded price for part_id={part_id}: {price}")
        return float(price)

    @staticmethod
    async def recalculate_item_total(item: QuoteItem) -> QuoteItem:
        """
        Recalculate line_total for a quote item.

        Formula: line_total = quantity * unit_price
        """
        item.line_total = item.quantity * item.unit_price
        return item

    @staticmethod
    async def recalculate_quote_totals(quote: Quote, db: AsyncSession) -> Quote:
        """
        Recalculate all quote totals from items.

        Formula:
        1. subtotal = sum(item.line_total)
        2. discount_amount = subtotal * (discount_percent / 100)
        3. taxable = subtotal - discount_amount
        4. tax_amount = taxable * (tax_percent / 100)
        5. total = taxable + tax_amount
        """
        # Reload items
        result = await db.execute(
            select(QuoteItem)
            .where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.deleted_at.is_(None)
            )
        )
        items = result.scalars().all()

        # Calculate subtotal
        quote.subtotal = sum(item.line_total for item in items)

        # Calculate discount
        quote.discount_amount = quote.subtotal * (quote.discount_percent / 100)

        # Calculate tax
        taxable = quote.subtotal - quote.discount_amount
        quote.tax_amount = taxable * (quote.tax_percent / 100)

        # Calculate total
        quote.total = taxable + quote.tax_amount

        logger.debug(
            f"Recalculated quote {quote.quote_number}: "
            f"subtotal={quote.subtotal}, discount={quote.discount_amount}, "
            f"tax={quote.tax_amount}, total={quote.total}"
        )

        return quote

    @staticmethod
    async def create_quote_snapshot(quote: Quote, db: AsyncSession) -> Dict[str, Any]:
        """
        Create snapshot when sending quote (ADR-VIS-002).

        Snapshot includes:
        - Quote metadata (title, description, dates)
        - Partner data (company_name, address, contact)
        - Items with denormalized fields
        - Totals

        Returns:
            Snapshot dictionary (stored in quote.snapshot_data JSON field)
        """
        # Load partner
        partner_data = None
        if quote.partner_id:
            partner = await db.get(Partner, quote.partner_id)
            if partner:
                partner_data = {
                    "partner_number": partner.partner_number,
                    "company_name": partner.company_name,
                    "ico": partner.ico,
                    "dic": partner.dic,
                    "email": partner.email,
                    "phone": partner.phone,
                    "contact_person": partner.contact_person,
                    "street": partner.street,
                    "city": partner.city,
                    "postal_code": partner.postal_code,
                    "country": partner.country,
                }

        # Load items
        result = await db.execute(
            select(QuoteItem)
            .where(
                QuoteItem.quote_id == quote.id,
                QuoteItem.deleted_at.is_(None)
            )
        )
        items = result.scalars().all()

        items_data = [
            {
                "part_number": item.part_number,
                "part_name": item.part_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
                "notes": item.notes,
            }
            for item in items
        ]

        snapshot = {
            "quote_number": quote.quote_number,
            "title": quote.title,
            "description": quote.description,
            "valid_until": quote.valid_until.isoformat() if quote.valid_until else None,
            "partner": partner_data,
            "items": items_data,
            "subtotal": quote.subtotal,
            "discount_percent": quote.discount_percent,
            "discount_amount": quote.discount_amount,
            "tax_percent": quote.tax_percent,
            "tax_amount": quote.tax_amount,
            "total": quote.total,
            "notes": quote.notes,
            "created_at": quote.created_at.isoformat(),
            "sent_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Created snapshot for quote {quote.quote_number}")
        return snapshot

    @staticmethod
    async def transition_to_sent(quote: Quote, db: AsyncSession, username: str) -> Quote:
        """
        Transition DRAFT → SENT (with snapshot).

        Rules:
        - Only DRAFT quotes can be sent
        - Creates snapshot
        - Sets sent_at timestamp
        - Quote becomes READ-ONLY

        Raises:
            HTTPException 400: If quote is not in DRAFT status
        """
        if quote.status != QuoteStatus.DRAFT.value:
            raise HTTPException(
                status_code=400,
                detail=f"Only DRAFT quotes can be sent (current status: {quote.status})"
            )

        # Create snapshot
        snapshot = await QuoteService.create_quote_snapshot(quote, db)

        # Update quote
        quote.status = QuoteStatus.SENT.value
        quote.sent_at = datetime.utcnow()
        quote.snapshot_data = snapshot
        quote.updated_by = username

        logger.info(f"Quote {quote.quote_number} transitioned to SENT by {username}")
        return quote

    @staticmethod
    async def transition_to_approved(quote: Quote, username: str) -> Quote:
        """
        Transition SENT → APPROVED.

        Raises:
            HTTPException 400: If quote is not in SENT status
        """
        if quote.status != QuoteStatus.SENT.value:
            raise HTTPException(
                status_code=400,
                detail=f"Only SENT quotes can be approved (current status: {quote.status})"
            )

        quote.status = QuoteStatus.APPROVED.value
        quote.approved_at = datetime.utcnow()
        quote.updated_by = username

        logger.info(f"Quote {quote.quote_number} approved by {username}")
        return quote

    @staticmethod
    async def transition_to_rejected(quote: Quote, username: str) -> Quote:
        """
        Transition SENT → REJECTED.

        Raises:
            HTTPException 400: If quote is not in SENT status
        """
        if quote.status != QuoteStatus.SENT.value:
            raise HTTPException(
                status_code=400,
                detail=f"Only SENT quotes can be rejected (current status: {quote.status})"
            )

        quote.status = QuoteStatus.REJECTED.value
        quote.rejected_at = datetime.utcnow()
        quote.updated_by = username

        logger.info(f"Quote {quote.quote_number} rejected by {username}")
        return quote

    @staticmethod
    def check_edit_lock(quote: Quote) -> None:
        """
        Check if quote is editable (only DRAFT status).

        Raises:
            HTTPException 409: If quote is not editable (status != DRAFT)
        """
        if quote.status != QuoteStatus.DRAFT.value:
            raise HTTPException(
                status_code=409,
                detail=f"Quote is read-only (status: {quote.status}). Clone to edit."
            )

    @staticmethod
    async def clone_quote(
        original_quote: Quote,
        db: AsyncSession,
        username: str,
        new_quote_number: str
    ) -> Quote:
        """
        Clone quote (used when editing after SENT).

        Creates new quote in DRAFT status with:
        - Same partner, title, description
        - Same discount/tax settings
        - Same items (without IDs)

        Args:
            original_quote: Quote to clone
            db: Database session
            username: Current user
            new_quote_number: New quote number (pre-generated)

        Returns:
            New quote in DRAFT status
        """
        # Load items
        result = await db.execute(
            select(QuoteItem)
            .where(
                QuoteItem.quote_id == original_quote.id,
                QuoteItem.deleted_at.is_(None)
            )
        )
        items = result.scalars().all()

        # Create new quote
        new_quote = Quote(
            quote_number=new_quote_number,
            partner_id=original_quote.partner_id,
            title=f"{original_quote.title} (Copy)",
            description=original_quote.description,
            valid_until=original_quote.valid_until,
            status=QuoteStatus.DRAFT.value,
            discount_percent=original_quote.discount_percent,
            tax_percent=original_quote.tax_percent,
            notes=original_quote.notes,
            created_by=username,
            updated_by=username,
        )

        db.add(new_quote)
        await db.flush()  # Get new_quote.id

        # Clone items
        for item in items:
            new_item = QuoteItem(
                quote_id=new_quote.id,
                part_id=item.part_id,
                part_number=item.part_number,
                part_name=item.part_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
                notes=item.notes,
                created_by=username,
                updated_by=username,
            )
            db.add(new_item)

        # Recalculate totals
        await QuoteService.recalculate_quote_totals(new_quote, db)

        logger.info(f"Cloned quote {original_quote.quote_number} → {new_quote_number}")
        return new_quote
