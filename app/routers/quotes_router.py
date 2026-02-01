"""GESTIMA - Quotes API router

Quote workflow:
- DRAFT: Editable
- SENT: Read-only (snapshot created)
- APPROVED/REJECTED: Final states

Edit lock: After SENT, must clone to edit
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db_helpers import set_audit, safe_commit
from app.dependencies import get_current_user, require_role
from app.models import User, UserRole
from app.rate_limiter import limiter
from app.config import settings
from app.models.quote import (
    Quote, QuoteCreate, QuoteUpdate, QuoteResponse,
    QuoteWithItemsResponse, QuoteListResponse
)
from app.models.partner import Partner
from app.models.enums import QuoteStatus
from app.services.number_generator import NumberGenerator
from app.services.quote_service import QuoteService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[QuoteListResponse])
async def get_quotes(
    skip: int = Query(0, ge=0, description="Počet záznamů k přeskočení"),
    limit: int = Query(100, ge=1, le=500, description="Max počet záznamů"),
    status: Optional[str] = Query(None, description="Filter podle statusu"),
    partner_id: Optional[int] = Query(None, description="Filter podle partnera"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List všech nabídek s pagination a filtry"""
    query = select(Quote).where(Quote.deleted_at.is_(None))

    # Filter by status
    if status:
        query = query.where(Quote.status == status)

    # Filter by partner
    if partner_id:
        query = query.where(Quote.partner_id == partner_id)

    result = await db.execute(
        query
        .order_by(Quote.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/search")
async def search_quotes(
    search: str = Query("", description="Hledat v čísle nabídky, názvu"),
    status: Optional[str] = Query(None, description="Filter podle statusu"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Filtrování nabídek s multi-field search"""
    query = select(Quote).where(Quote.deleted_at.is_(None))

    # Status filter
    if status:
        query = query.where(Quote.status == status)

    # Search filter
    if search.strip():
        search_term = f"%{search.strip()}%"
        filters = [
            Quote.quote_number.ilike(search_term),
            Quote.title.ilike(search_term),
        ]

        # Pokud je search digit, přidat ID search
        if search.strip().isdigit():
            filters.append(Quote.id == int(search.strip()))

        query = query.where(or_(*filters))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Quote.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    quotes = result.scalars().all()

    # Convert to Pydantic models
    quotes_response = [QuoteListResponse.model_validate(quote) for quote in quotes]

    return {
        "quotes": quotes_response,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{quote_number}", response_model=QuoteWithItemsResponse)
async def get_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get single quote by quote_number (with items)"""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Quote)
        .options(selectinload(Quote.items))  # Eager load items
        .where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    return QuoteWithItemsResponse.model_validate(quote)


@router.post("/", response_model=QuoteResponse)
async def create_quote(
    data: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create new quote in DRAFT status.

    Auto-generates quote_number (50XXXXXX) - ADR-017
    """
    # Verify partner exists
    partner = await db.get(Partner, data.partner_id)
    if not partner or partner.deleted_at:
        raise HTTPException(status_code=404, detail="Partner not found")

    if not partner.is_customer:
        raise HTTPException(status_code=400, detail="Partner must be a customer")

    # Generate quote number
    quote_number = await NumberGenerator.generate_quote_number(db)

    # Create quote
    quote = Quote(
        quote_number=quote_number,
        partner_id=data.partner_id,
        title=data.title,
        description=data.description,
        valid_until=data.valid_until,
        status=QuoteStatus.DRAFT.value,
        discount_percent=data.discount_percent,
        tax_percent=data.tax_percent,
        notes=data.notes,
    )

    set_audit(quote, current_user.username)
    db.add(quote)
    await safe_commit(db, quote, "vytváření nabídky")

    logger.info(f"Created quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.put("/{quote_number}", response_model=QuoteResponse)
async def update_quote(
    quote_number: str,
    data: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quote - ONLY if status == DRAFT.

    Edit lock: Returns HTTP 409 if quote is not in DRAFT status
    """
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

    # Optimistic locking
    if quote.version != data.version:
        raise HTTPException(status_code=409, detail="Version conflict")

    # Update fields
    if data.title is not None:
        quote.title = data.title
    if data.description is not None:
        quote.description = data.description
    if data.valid_until is not None:
        quote.valid_until = data.valid_until
    if data.discount_percent is not None:
        quote.discount_percent = data.discount_percent
    if data.tax_percent is not None:
        quote.tax_percent = data.tax_percent
    if data.notes is not None:
        quote.notes = data.notes

    # Recalculate totals
    await QuoteService.recalculate_quote_totals(quote, db)

    set_audit(quote, current_user.username, is_update=True)
    quote.version += 1

    await safe_commit(db, quote, "aktualizace nabídky")

    logger.info(f"Updated quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.delete("/{quote_number}")
async def delete_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete quote.

    Protection: SENT and APPROVED quotes cannot be deleted (contain legal snapshot).
    Only DRAFT and REJECTED quotes can be deleted.
    """
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Protect SENT and APPROVED quotes from deletion
    if quote.status in [QuoteStatus.SENT.value, QuoteStatus.APPROVED.value]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Nelze smazat nabídku ve stavu '{quote.status}'. "
                "Odeslané a schválené nabídky obsahují právně závazný snapshot a nesmí být smazány."
            )
        )

    # Soft delete (only DRAFT and REJECTED)
    from datetime import datetime
    quote.deleted_at = datetime.utcnow()
    quote.deleted_by = current_user.username

    await safe_commit(db, action="mazání nabídky")

    logger.info(f"Deleted quote {quote_number} (status={quote.status}) by {current_user.username}")
    return {"message": "Quote deleted"}


@router.post("/{quote_number}/send", response_model=QuoteResponse)
async def send_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transition DRAFT → SENT (creates snapshot).

    After this, quote is READ-ONLY.
    """
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Transition to SENT
    await QuoteService.transition_to_sent(quote, db, current_user.username)
    quote.version += 1

    await safe_commit(db, quote, "odeslání nabídky")

    logger.info(f"Sent quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.post("/{quote_number}/approve", response_model=QuoteResponse)
async def approve_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transition SENT → APPROVED"""
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Transition to APPROVED
    await QuoteService.transition_to_approved(quote, current_user.username)
    quote.version += 1

    await safe_commit(db, quote, "schválení nabídky")

    logger.info(f"Approved quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.post("/{quote_number}/reject", response_model=QuoteResponse)
async def reject_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transition SENT → REJECTED"""
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Transition to REJECTED
    await QuoteService.transition_to_rejected(quote, current_user.username)
    quote.version += 1

    await safe_commit(db, quote, "zamítnutí nabídky")

    logger.info(f"Rejected quote {quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(quote)


@router.post("/{quote_number}/clone", response_model=QuoteResponse)
async def clone_quote(
    quote_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clone quote (creates new DRAFT copy).

    Use this to edit after quote has been sent.
    """
    result = await db.execute(
        select(Quote).where(
            Quote.quote_number == quote_number,
            Quote.deleted_at.is_(None)
        )
    )
    quote = result.scalar_one_or_none()

    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Generate new quote number
    new_quote_number = await NumberGenerator.generate_quote_number(db)

    # Clone quote
    new_quote = await QuoteService.clone_quote(
        quote, db, current_user.username, new_quote_number
    )

    await safe_commit(db, new_quote, "klonování nabídky")

    logger.info(f"Cloned quote {quote_number} → {new_quote_number} by {current_user.username}")
    return QuoteResponse.model_validate(new_quote)


# =============================================================================
# AI Quote Request Parsing
# =============================================================================

@router.post("/parse-request", response_model=dict)
@limiter.limit(settings.AI_RATE_LIMIT)  # Cost control: 10/hour
async def parse_quote_request_pdf(
    request: Request,  # Required for rate limiter
    file: UploadFile = File(..., description="PDF poptávky"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parse quote request PDF using Claude AI.

    Workflow:
    1. Upload PDF → temp storage
    2. Claude Vision extracts customer + items
    3. Match parts (by article_number)
    4. Match batches (exact or nearest lower)
    5. Return QuoteRequestReview for user verification

    Rate limit: 10 requests/hour per user (cost control)
    Max file size: 10 MB

    Returns:
        QuoteRequestReview with customer + items + batch matches
    """
    from pathlib import Path
    import uuid
    from app.services.quote_request_parser import get_quote_parser
    from app.schemas.quote_request import QuoteRequestReview

    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )

    # Validate file size (10 MB max)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to start

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({file_size / 1024 / 1024:.1f} MB). Maximum: 10 MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file not allowed"
        )

    # Save to temp storage
    temp_dir = Path("uploads/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_id = str(uuid.uuid4())
    temp_path = temp_dir / f"{temp_id}.pdf"

    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"Saved temp PDF: {temp_id} ({len(content)} bytes) by {current_user.username}")

        # Parse with Claude
        parser = get_quote_parser()
        extraction = await parser.parse_pdf(temp_path)

        logger.info(
            f"AI extracted: customer={extraction.customer.company_name}, "
            f"items={len(extraction.items)}"
        )

        # Match customer (Partner)
        customer_match = await _match_customer(extraction.customer, db)

        # Match parts + batches
        item_matches = []
        for item in extraction.items:
            part_match = await QuoteService.match_item(
                article_number=item.article_number,
                name=item.name,
                quantity=item.quantity,
                notes=item.notes,
                db=db
            )
            item_matches.append(part_match)

        # Build review data
        unique_parts = len(set(m.article_number for m in item_matches))
        matched_parts = sum(1 for m in item_matches if m.part_exists)
        new_parts = unique_parts - len(set(
            m.article_number for m in item_matches if m.part_exists
        ))
        missing_batches = sum(
            1 for m in item_matches
            if m.batch_match and m.batch_match.status == "missing"
        )

        review = QuoteRequestReview(
            customer=customer_match,
            items=item_matches,
            valid_until=extraction.valid_until,
            notes=extraction.notes,
            total_items=len(item_matches),
            unique_parts=unique_parts,
            matched_parts=matched_parts,
            new_parts=new_parts,
            missing_batches=missing_batches
        )

        logger.info(
            f"Review generated: {unique_parts} unique parts, "
            f"{matched_parts} matched, {new_parts} new, {missing_batches} missing batches"
        )

        return review.model_dump()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse quote request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse quote request: {str(e)}"
        )
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
            logger.debug(f"Deleted temp file: {temp_id}")


async def _match_customer(
    customer_extraction: "CustomerExtraction",
    db: AsyncSession
) -> "CustomerMatch":
    """
    Match customer (Partner) by company name + ICO/email.

    Matching strategy:
    1. Try exact company_name + ICO match (most reliable)
    2. Try exact company_name + email match
    3. Try exact company_name only (may have duplicates like "Gelso AG" vs "Gelso DE")

    Note: User typically has unique customers, but edge cases exist
    (e.g., Gelso AG Germany vs Gelso DE - different addresses).

    Returns:
        CustomerMatch with partner info if found
    """
    from app.schemas.quote_request import CustomerMatch

    # Strategy 1: company_name + ICO (best match)
    if customer_extraction.ico:
        result = await db.execute(
            select(Partner).where(
                Partner.company_name == customer_extraction.company_name,
                Partner.ico == customer_extraction.ico,
                Partner.deleted_at.is_(None)
            )
        )
        partner = result.scalar_one_or_none()

        if partner:
            logger.debug(f"Matched customer by name+ICO: {partner.partner_number}")
            return CustomerMatch(
                company_name=customer_extraction.company_name,
                contact_person=customer_extraction.contact_person,
                email=customer_extraction.email,
                phone=customer_extraction.phone,
                ico=customer_extraction.ico,
                partner_id=partner.id,
                partner_number=partner.partner_number,
                partner_exists=True,
                match_confidence=1.0  # Exact match
            )

    # Strategy 2: company_name + email
    if customer_extraction.email:
        result = await db.execute(
            select(Partner).where(
                Partner.company_name == customer_extraction.company_name,
                Partner.email == customer_extraction.email,
                Partner.deleted_at.is_(None)
            )
        )
        partner = result.scalar_one_or_none()

        if partner:
            logger.debug(f"Matched customer by name+email: {partner.partner_number}")
            return CustomerMatch(
                company_name=customer_extraction.company_name,
                contact_person=customer_extraction.contact_person,
                email=customer_extraction.email,
                phone=customer_extraction.phone,
                ico=customer_extraction.ico,
                partner_id=partner.id,
                partner_number=partner.partner_number,
                partner_exists=True,
                match_confidence=0.95  # High confidence
            )

    # Strategy 3: company_name only (fallback - may be ambiguous)
    result = await db.execute(
        select(Partner).where(
            Partner.company_name == customer_extraction.company_name,
            Partner.deleted_at.is_(None)
        )
        .limit(1)
    )
    partner = result.scalar_one_or_none()

    if partner:
        logger.debug(f"Matched customer by name only: {partner.partner_number}")
        return CustomerMatch(
            company_name=customer_extraction.company_name,
            contact_person=customer_extraction.contact_person,
            email=customer_extraction.email,
            phone=customer_extraction.phone,
            ico=customer_extraction.ico,
            partner_id=partner.id,
            partner_number=partner.partner_number,
            partner_exists=True,
            match_confidence=0.8  # Lower confidence (name only)
        )

    # No match - will create new
    logger.debug(f"No customer match for: {customer_extraction.company_name}")
    return CustomerMatch(
        company_name=customer_extraction.company_name,
        contact_person=customer_extraction.contact_person,
        email=customer_extraction.email,
        phone=customer_extraction.phone,
        ico=customer_extraction.ico,
        partner_exists=False,
        match_confidence=customer_extraction.confidence
    )


@router.post("/from-request", response_model=QuoteResponse)
async def create_quote_from_request(
    data: "QuoteFromRequestCreate",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create Quote + Parts + Items from AI-parsed request.

    Workflow:
    1. Create/match Partner (if partner_id null)
    2. Create missing Parts (if part_id null)
    3. Create Quote
    4. Create QuoteItems with pricing from matched batches
    5. Recalculate totals

    Returns:
        Created Quote
    """
    from app.schemas.quote_request import QuoteFromRequestCreate
    from app.services.number_generator import NumberGenerator
    from app.models.part import Part, PartCreate
    from app.models.partner import Partner, PartnerCreate

    # 1. Create/match Partner
    partner_id = data.partner_id

    if not partner_id and data.partner_data:
        # Create new partner
        partner_number = await NumberGenerator.generate_partner_number(db)

        new_partner = Partner(
            partner_number=partner_number,
            company_name=data.partner_data.company_name,
            contact_person=data.partner_data.contact_person,
            email=data.partner_data.email,
            phone=data.partner_data.phone,
            ico=data.partner_data.ico,
            is_customer=True,
            created_by=current_user.username,
            updated_by=current_user.username
        )
        db.add(new_partner)
        await db.flush()

        partner_id = new_partner.id
        logger.info(f"Created new partner: {partner_number} - {data.partner_data.company_name}")

    if not partner_id:
        raise HTTPException(
            status_code=400,
            detail="partner_id or partner_data required"
        )

    # 2. Create missing Parts
    for item in data.items:
        if not item.part_id:
            # Create new part
            part_number = await NumberGenerator.generate_part_number(db)

            new_part = Part(
                part_number=part_number,
                article_number=item.article_number,
                name=item.name,
                revision="A",
                status="draft",
                created_by=current_user.username,
                updated_by=current_user.username
            )
            db.add(new_part)
            await db.flush()

            # Update item with new part_id
            item.part_id = new_part.id
            logger.info(f"Created new part: {part_number} - {item.article_number}")

    # 3. Create Quote
    quote_number = await NumberGenerator.generate_quote_number(db)

    new_quote = Quote(
        quote_number=quote_number,
        partner_id=partner_id,
        title=data.title,
        valid_until=data.valid_until,
        notes=data.notes,
        status=QuoteStatus.DRAFT.value,
        discount_percent=data.discount_percent,
        tax_percent=data.tax_percent,
        created_by=current_user.username,
        updated_by=current_user.username
    )
    db.add(new_quote)
    await db.flush()

    logger.info(f"Created quote: {quote_number} for partner_id={partner_id}")

    # 4. Create QuoteItems
    for item in data.items:
        # Get unit price from matched batch
        unit_price = 0.0
        if item.part_id:
            # Try to get price from frozen batch
            try:
                part = await db.get(Part, item.part_id)
                if part:
                    batch, status, warnings = await QuoteService.find_best_batch(
                        part, item.quantity, db
                    )
                    if batch:
                        unit_price = float(
                            batch.unit_price_frozen if batch.unit_price_frozen else batch.unit_cost
                        )
            except Exception as e:
                logger.warning(f"Failed to get price for part {item.part_id}: {e}")

        # Denormalize part fields
        part = await db.get(Part, item.part_id) if item.part_id else None
        part_number = part.part_number if part else None
        part_name = part.name if part else item.name

        new_item = QuoteItem(
            quote_id=new_quote.id,
            part_id=item.part_id,
            part_number=part_number,
            part_name=part_name,
            quantity=item.quantity,
            unit_price=unit_price,
            line_total=item.quantity * unit_price,
            notes=item.notes,
            created_by=current_user.username,
            updated_by=current_user.username
        )
        db.add(new_item)

    await db.flush()

    # 5. Recalculate quote totals
    await QuoteService.recalculate_quote_totals(new_quote, db)

    # Commit
    await safe_commit(db, new_quote, "vytvoření nabídky z poptávky")

    logger.info(
        f"Created quote from request: {quote_number}, "
        f"{len(data.items)} items, total={new_quote.total}"
    )

    return QuoteResponse.model_validate(new_quote)
