"""GESTIMA - Quote Service (Business Logic)

Core responsibilities:
- Pricing calculation (auto-load from frozen batch_sets)
- Quote totals recalculation
- Workflow transitions (DRAFT → SENT → APPROVED/REJECTED)
- Snapshot creation (ADR-VIS-002)
- Edit lock enforcement
- AI quote request: Part & Batch matching
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.quote import Quote, QuoteItem
from app.models.batch_set import BatchSet
from app.models.batch import Batch
from app.models.part import Part
from app.models.partner import Partner
from app.models.enums import QuoteStatus
from app.schemas.quote_request import PartMatch, BatchMatch

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
            Unit price (float)

        Raises:
            HTTPException 400: If no frozen batch_set found (must freeze batch first)
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
            raise HTTPException(
                status_code=400,
                detail=f"Část nemá zmrazenou kalkulaci. Nejdříve zmrazte batch pro přidání do nabídky."
            )

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
            raise HTTPException(
                status_code=400,
                detail=f"Sada kalkulací {batch_set.set_number} neobsahuje žádné batche."
            )

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

        # INVARIANT CHECK: Verify calculation integrity
        expected = item.quantity * item.unit_price
        if abs(item.line_total - expected) > 0.01:
            logger.error(
                f"INVARIANT VIOLATION: QuoteItem {item.id} line_total mismatch! "
                f"Stored: {item.line_total}, Expected: {expected}"
            )
            raise ValueError(
                f"Data integrity error: QuoteItem line_total mismatch"
            )

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

        # INVARIANT CHECK: Verify calculation integrity
        expected_subtotal = sum(item.line_total for item in items)
        if abs(quote.subtotal - expected_subtotal) > 0.01:
            logger.error(
                f"INVARIANT VIOLATION: Quote {quote.quote_number} subtotal mismatch! "
                f"Stored: {quote.subtotal}, Expected: {expected_subtotal}"
            )
            raise ValueError(
                f"Data integrity error: Quote subtotal mismatch "
                f"({quote.subtotal} != {expected_subtotal})"
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

    # =========================================================================
    # AI Quote Request: Part & Batch Matching
    # =========================================================================

    @staticmethod
    async def find_best_batch(
        part: Part,
        requested_quantity: int,
        db: AsyncSession
    ) -> Tuple[Optional[Batch], str, List[str]]:
        """
        Find best frozen batch for requested quantity.

        Matching rules:
        1. EXACT MATCH preferred (batch.quantity == requested_quantity)
        2. NEAREST LOWER batch (batch.quantity < requested_quantity, maximize batch.quantity)
        3. If no lower batch found, return None

        Args:
            part: Part instance
            requested_quantity: Requested quantity from quote request
            db: Database session

        Returns:
            Tuple of (batch, status, warnings):
            - batch: Best matching Batch or None
            - status: "exact" | "lower" | "missing"
            - warnings: List of warning messages
        """
        # Get all frozen batches for part
        result = await db.execute(
            select(Batch)
            .join(BatchSet, Batch.batch_set_id == BatchSet.id)
            .where(
                Batch.part_id == part.id,
                BatchSet.status == "frozen",
                Batch.deleted_at.is_(None),
                BatchSet.deleted_at.is_(None)
            )
            .order_by(Batch.quantity.asc())
        )
        frozen_batches = result.scalars().all()

        if not frozen_batches:
            logger.warning(f"No frozen batches for part {part.part_number}")
            return None, "missing", [
                f"🔴 Díl {part.part_number} nemá žádnou zmrazenou kalkulaci"
            ]

        # 1. Try exact match
        exact_batch = next(
            (b for b in frozen_batches if b.quantity == requested_quantity),
            None
        )
        if exact_batch:
            logger.debug(
                f"Exact batch match: part={part.part_number}, "
                f"qty={requested_quantity}, batch_id={exact_batch.id}"
            )
            return exact_batch, "exact", []

        # 2. Try nearest LOWER batch
        lower_batches = [b for b in frozen_batches if b.quantity < requested_quantity]
        if lower_batches:
            # Get highest lower batch
            nearest_lower = max(lower_batches, key=lambda b: b.quantity)
            warning = (
                f"⚠️ Neexistuje dávka {requested_quantity} ks - "
                f"použita dávka {nearest_lower.quantity} ks. "
                f"Doporučujeme vytvořit přesnou dávku."
            )
            logger.debug(
                f"Lower batch match: part={part.part_number}, "
                f"requested={requested_quantity}, used={nearest_lower.quantity}"
            )
            return nearest_lower, "lower", [warning]

        # 3. No suitable batch found
        available = ", ".join([f"{b.quantity}ks" for b in frozen_batches])
        warning = (
            f"🔴 Nejnižší dostupná dávka je {frozen_batches[0].quantity} ks "
            f"(požadováno {requested_quantity} ks). "
            f"Dostupné dávky: {available}"
        )
        logger.warning(
            f"No suitable batch: part={part.part_number}, "
            f"requested={requested_quantity}, available={available}"
        )
        return None, "missing", [warning]

    @staticmethod
    async def match_part_by_article_number(
        article_number: str,
        db: AsyncSession
    ) -> Optional[Part]:
        """
        Find existing part by article_number (exact match).

        Args:
            article_number: Article number from quote request
            db: Database session

        Returns:
            Part or None if not found
        """
        from app.services.article_number_matcher import ArticleNumberMatcher

        # Generate search variants (exact, without prefix, without revision)
        variants = ArticleNumberMatcher.generate_variants(article_number)
        logger.debug(f"Searching for article_number variants: {variants}")

        for variant in variants:
            result = await db.execute(
                select(Part)
                .where(
                    Part.article_number == variant,
                    Part.deleted_at.is_(None)
                )
                .limit(1)
            )
            part = result.scalar_one_or_none()

            if part:
                # Determine match type
                match_type, warning = ArticleNumberMatcher.match_type(
                    article_number,
                    part.article_number
                )
                logger.info(
                    f"Found part: '{article_number}' → {part.part_number} "
                    f"(match={match_type})"
                )
                if warning:
                    logger.warning(warning)

                # Return tuple: (part, match_type, warning)
                # Store as tuple for backward compat
                part._fuzzy_match_type = match_type
                part._fuzzy_warning = warning
                return part

        # No match found
        logger.debug(f"Part not found: {article_number}")
        return None

    @staticmethod
    async def match_item(
        article_number: str,
        drawing_number: Optional[str],
        name: str,
        quantity: int,
        notes: Optional[str],
        db: AsyncSession
    ) -> PartMatch:
        """
        Match single item (part + batch).

        Process:
        1. Match part by article_number
        2. If part exists, find best batch for quantity
        3. Return PartMatch with all info

        Args:
            article_number: Article number from PDF
            name: Part name from PDF
            quantity: Requested quantity
            notes: Notes from PDF
            db: Database session

        Returns:
            PartMatch with part + batch matching results
        """
        from app.services.article_number_matcher import ArticleNumberMatcher

        # Normalize article_number (strip prefixes like byn-, trgcz-, etc.)
        normalized = ArticleNumberMatcher.normalize(article_number)
        clean_article_number = normalized.base  # Without prefix AND revision

        logger.debug(
            f"Normalizing article_number: '{article_number}' → '{clean_article_number}' "
            f"(prefix={normalized.prefix}, revision={normalized.revision})"
        )

        # Try to match part
        part = await QuoteService.match_part_by_article_number(article_number, db)

        if not part:
            # Part doesn't exist - will be created
            return PartMatch(
                part_exists=False,
                article_number=clean_article_number,  # Return normalized
                drawing_number=drawing_number,
                name=name,
                quantity=quantity,
                notes=notes,
                batch_match=BatchMatch(
                    status="missing",
                    unit_price=0.0,
                    line_total=0.0,
                    warnings=["🔴 Nový díl - bude vytvořen bez ceny"]
                )
            )

        # Part exists - check for fuzzy match warning
        fuzzy_warning = getattr(part, '_fuzzy_warning', '')
        if fuzzy_warning:
            # Append fuzzy warning to notes
            notes = f"{fuzzy_warning}\n{notes}" if notes else fuzzy_warning

        # Find best batch
        batch, status, batch_warnings = await QuoteService.find_best_batch(
            part, quantity, db
        )

        # Calculate pricing
        unit_price = 0.0
        if batch:
            # Use frozen price or fallback to unit_cost
            unit_price = float(
                batch.unit_price_frozen if batch.unit_price_frozen else batch.unit_cost
            )

        line_total = quantity * unit_price

        batch_match = BatchMatch(
            batch_id=batch.id if batch else None,
            batch_quantity=batch.quantity if batch else None,
            status=status,
            unit_price=unit_price,
            line_total=line_total,
            warnings=batch_warnings
        )

        return PartMatch(
            part_id=part.id,
            part_number=part.part_number,
            part_exists=True,
            article_number=clean_article_number,  # Return normalized
            drawing_number=drawing_number,
            name=name,
            quantity=quantity,
            notes=notes,
            batch_match=batch_match
        )
