"""GESTIMA - Quote Orchestrator Service (V2)

Creates a complete quote from a parsed request in a single DB transaction:
Partner → Parts → Drawings → MaterialInput → TimeVision → Technology → Batches → Freeze → Quote

This orchestrator reuses existing services (no duplication):
- NumberGenerator for entity numbers
- file_service.store_from_bytes() for drawing storage
- build_technology() for operation generation
- recalculate_batch_costs() for pricing
- create_batch_snapshot() for freeze snapshots
- QuoteService for totals recalculation
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch
from app.models.batch_set import BatchSet
from app.models.enums import StockShape
from app.models.file_record import FileLink
from app.models.material import MaterialItem, MaterialPriceCategory
from app.models.material_input import MaterialInput
from app.models.operation import Operation
from app.models.part import Part
from app.models.partner import Partner
from app.models.quote import Quote, QuoteItem
from app.models.time_vision import TimeVisionEstimation
from app.schemas.quote_request import (
    EstimationData,
    QuoteCreationPartResult,
    QuoteCreationResult,
    QuoteFromRequestCreateV2,
    QuoteFromRequestItemV2,
)
from app.services.article_number_matcher import ArticleNumberMatcher
from app.services.batch_service import recalculate_batch_costs
from app.services.file_service import FileService
from app.services.number_generator import NumberGenerator
from app.services.quote_service import QuoteService
from app.services.snapshot_service import create_batch_snapshot
from app.services.technology_builder import build_technology

logger = logging.getLogger(__name__)

# Default batch quantities for new parts
DEFAULT_BATCH_QUANTITIES = [1, 10, 50, 100, 500]

# Default material input for placeholder (round bar, ø50mm, 100mm length)
DEFAULT_STOCK_SHAPE = StockShape.ROUND_BAR
DEFAULT_STOCK_DIAMETER = 50.0
DEFAULT_STOCK_LENGTH = 100.0


async def _resolve_or_create_partner(
    data: QuoteFromRequestCreateV2,
    db: AsyncSession,
    username: str,
) -> tuple[Optional[int], Optional[str], bool]:
    """Resolve existing partner or create new one.

    Returns:
        (partner_id, partner_number, is_new)
    """
    if data.partner_id:
        partner = await db.get(Partner, data.partner_id)
        if not partner or partner.deleted_at:
            raise ValueError(f"Partner ID {data.partner_id} nenalezen")
        return partner.id, partner.partner_number, False

    if data.partner_data:
        partner_number = await NumberGenerator.generate_partner_number(db)
        new_partner = Partner(
            partner_number=partner_number,
            company_name=data.partner_data.company_name,
            contact_person=data.partner_data.contact_person,
            email=data.partner_data.email,
            phone=data.partner_data.phone,
            ico=data.partner_data.ico,
            dic=data.partner_data.dic,
            is_customer=True,
            is_supplier=data.partner_data.is_supplier,
            created_by=username,
            updated_by=username,
        )
        db.add(new_partner)
        await db.flush()
        logger.info(f"Created partner {partner_number}: {data.partner_data.company_name}")
        return new_partner.id, partner_number, True

    return None, None, False


async def _get_default_price_category(db: AsyncSession) -> Optional[int]:
    """Get a default price category for placeholder MaterialInput.

    Looks for 'Konstrukční ocel' round bar category as sensible default.
    Falls back to any round_bar category, then any category.
    """
    # Try round_bar shape first (most common in CNC machining)
    result = await db.execute(
        select(MaterialPriceCategory)
        .where(
            MaterialPriceCategory.shape == "round_bar",
            MaterialPriceCategory.deleted_at.is_(None),
        )
        .limit(1)
    )
    pc = result.scalar_one_or_none()
    if pc:
        return pc.id

    # Fallback: any active price category
    result = await db.execute(
        select(MaterialPriceCategory)
        .where(MaterialPriceCategory.deleted_at.is_(None))
        .limit(1)
    )
    pc = result.scalar_one_or_none()
    return pc.id if pc else None


async def _create_part_with_full_setup(
    item: QuoteFromRequestItemV2,
    drawing_bytes: Optional[bytes],
    drawing_filename: Optional[str],
    db: AsyncSession,
    username: str,
    file_service: FileService,
) -> QuoteCreationPartResult:
    """Create a new Part with Technology, Batches, BatchSet, and optionally link a drawing.

    Full pipeline per part:
    1. Create Part
    2. Store drawing PDF → FileRecord → FileLink → Part.file_id
    3. Create placeholder MaterialInput
    4. Create TimeVisionEstimation from AI data
    5. Build technology (OP10 + OP20 + OP100)
    6. Create Batches + recalculate costs
    7. Create BatchSet + freeze all
    """
    part_result = QuoteCreationPartResult(
        article_number=item.article_number,
        name=item.name,
        is_new=True,
    )
    warnings: list[str] = []

    # --- 1. Create Part ---
    normalized = ArticleNumberMatcher.normalize(item.article_number)
    clean_article = normalized.base

    part_number = await NumberGenerator.generate_part_number(db)
    new_part = Part(
        part_number=part_number,
        article_number=clean_article,
        drawing_number=item.drawing_number or clean_article,
        customer_revision=normalized.revision,
        name=item.name,
        source="quote_request",
        status="draft",
        created_by=username,
        updated_by=username,
    )
    db.add(new_part)
    await db.flush()
    part_result.part_number = part_number
    logger.info(f"Created part {part_number} (article: {clean_article})")

    # --- 2. Store drawing + link ---
    if drawing_bytes and drawing_filename:
        try:
            file_record = await file_service.store_from_bytes(
                content=drawing_bytes,
                filename=drawing_filename,
                directory=f"parts/{part_number}",
                db=db,
                allowed_types=["pdf"],
                created_by=username,
            )
            await db.flush()

            # Create FileLink
            file_link = FileLink(
                file_id=file_record.id,
                entity_type="part",
                entity_id=new_part.id,
                is_primary=True,
                link_type="drawing",
                created_by=username,
                updated_by=username,
            )
            db.add(file_link)

            # Set Part.file_id FK
            new_part.file_id = file_record.id

            part_result.drawing_linked = True
            logger.info(f"Linked drawing {drawing_filename} → part {part_number}")
        except Exception as e:
            warnings.append(f"Nepodařilo se uložit výkres: {e}")
            logger.warning(f"Drawing storage failed for {part_number}: {e}")

    # --- 3. Create placeholder MaterialInput ---
    default_pc_id = await _get_default_price_category(db)
    if default_pc_id:
        material_input = MaterialInput(
            part_id=new_part.id,
            seq=0,
            price_category_id=default_pc_id,
            stock_shape=DEFAULT_STOCK_SHAPE,
            stock_diameter=DEFAULT_STOCK_DIAMETER,
            stock_length=DEFAULT_STOCK_LENGTH,
            quantity=1,
            notes="Placeholder z poptávky — upřesněte materiál a rozměry",
            created_by=username,
            updated_by=username,
        )
        db.add(material_input)
        await db.flush()
    else:
        material_input = None
        warnings.append("Žádná cenová kategorie v DB — materiál nepřiřazen")

    # --- 4. Create TimeVisionEstimation ---
    estimation_data = item.estimation or EstimationData()
    estimation = TimeVisionEstimation(
        pdf_filename=drawing_filename or f"{clean_article}.pdf",
        pdf_path=f"parts/{part_number}",
        part_id=new_part.id,
        file_id=new_part.file_id,
        ai_provider="quote_estimate",
        ai_model="quote_estimate",
        part_type=estimation_data.part_type,
        complexity=estimation_data.complexity,
        estimated_time_min=estimation_data.estimated_time_min,
        max_diameter_mm=estimation_data.max_diameter_mm,
        max_length_mm=estimation_data.max_length_mm,
        status="estimated",
        estimation_type="time_v1",
        created_by=username,
        updated_by=username,
    )
    db.add(estimation)
    await db.flush()

    # --- 5. Build technology (OP10 + OP20 + OP100) ---
    try:
        plan = await build_technology(
            estimation=estimation,
            material_input=material_input,
            part_id=new_part.id,
            db=db,
            cutting_mode="mid",
        )

        for op_create in plan.operations:
            operation = Operation(**op_create.model_dump())
            operation.created_by = username
            operation.updated_by = username
            db.add(operation)

        if plan.warnings:
            warnings.extend(plan.warnings)

        part_result.technology_generated = True
        await db.flush()
        logger.info(f"Generated technology for part {part_number}: {len(plan.operations)} operations")
    except Exception as e:
        warnings.append(f"Technologie: {e}")
        logger.warning(f"Technology generation failed for {part_number}: {e}")

    # --- 6. Create Batches + recalculate costs ---
    batch_numbers = await NumberGenerator.generate_batch_numbers_batch(
        db, count=len(DEFAULT_BATCH_QUANTITIES)
    )

    batches: list[Batch] = []
    for i, qty in enumerate(DEFAULT_BATCH_QUANTITIES):
        batch = Batch(
            batch_number=batch_numbers[i],
            part_id=new_part.id,
            quantity=qty,
            is_default=(qty == 1),
            created_by=username,
            updated_by=username,
        )
        db.add(batch)
        batches.append(batch)

    await db.flush()

    # Recalculate costs for each batch
    for batch in batches:
        try:
            await recalculate_batch_costs(batch, db)
        except Exception as e:
            warnings.append(f"Kalkulace dávky {batch.quantity}ks: {e}")
            logger.warning(f"Batch cost calc failed for {part_number} qty={batch.quantity}: {e}")

    await db.flush()

    # --- 7. Create BatchSet + freeze all ---
    try:
        set_number = await NumberGenerator.generate_batch_set_number(db)
        batch_set = BatchSet(
            set_number=set_number,
            part_id=new_part.id,
            name=datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            status="frozen",
            frozen_at=datetime.utcnow(),
            created_by=username,
            updated_by=username,
        )
        db.add(batch_set)
        await db.flush()

        now = datetime.utcnow()
        for batch in batches:
            batch.batch_set_id = batch_set.id
            batch.is_frozen = True
            batch.frozen_at = now
            batch.unit_price_frozen = batch.unit_cost
            batch.total_price_frozen = batch.total_cost

            try:
                snapshot = await create_batch_snapshot(batch, username, db)
                batch.snapshot_data = snapshot
            except Exception as e:
                logger.warning(f"Snapshot creation failed for batch {batch.batch_number}: {e}")

        part_result.batch_set_frozen = True
        logger.info(f"Frozen BatchSet {set_number} with {len(batches)} batches for part {part_number}")
    except Exception as e:
        warnings.append(f"Zmrazení dávek: {e}")
        logger.warning(f"BatchSet freeze failed for {part_number}: {e}")

    part_result.warnings = warnings
    return part_result


async def create_quote_from_request(
    data: QuoteFromRequestCreateV2,
    drawing_files: dict[str, bytes],
    db: AsyncSession,
    username: str,
) -> QuoteCreationResult:
    """Create a complete quote from a parsed request.

    Orchestrates the entire flow in a single DB transaction:
    1. Partner — find or create
    2. For each new part: create Part + Drawing + Material + Technology + Batches + Freeze
    3. For existing parts: use existing frozen batches
    4. Create Quote + QuoteItems with real prices
    5. Recalculate totals

    Args:
        data: Validated request data (V2 schema)
        drawing_files: Map of drawing_index (as str) → PDF bytes
        db: AsyncSession (caller manages transaction)
        username: Current user for audit trail

    Returns:
        QuoteCreationResult with full summary

    Raises:
        ValueError: Invalid data
        Exception: DB errors (caller should rollback)
    """
    result_warnings: list[str] = []
    part_results: list[QuoteCreationPartResult] = []
    parts_created = 0
    parts_existing = 0
    drawings_linked = 0

    file_service = FileService()

    # --- 1. Partner ---
    partner_id, partner_number, partner_is_new = await _resolve_or_create_partner(
        data, db, username
    )
    if partner_is_new:
        logger.info(f"Created new partner {partner_number}")

    # --- 2. Process items (create parts or resolve existing) ---
    # Track article_number → part_id to deduplicate
    article_to_part: dict[str, tuple[int, str]] = {}  # clean_article → (part_id, part_number)

    for idx, item in enumerate(data.items):
        normalized = ArticleNumberMatcher.normalize(item.article_number)
        clean_article = normalized.base

        if item.part_id:
            # Existing part — verify it exists
            part = await db.get(Part, item.part_id)
            if not part or part.deleted_at:
                result_warnings.append(f"Díl ID {item.part_id} nenalezen, přeskočen")
                continue

            article_to_part[clean_article] = (part.id, part.part_number)
            parts_existing += 1

            # Get price from existing frozen batch
            batch, status, batch_warnings = await QuoteService.find_best_batch(
                part, item.quantity, db
            )
            unit_price = 0.0
            if batch:
                unit_price = float(batch.unit_price_frozen or batch.unit_cost)

            part_results.append(QuoteCreationPartResult(
                article_number=item.article_number,
                part_number=part.part_number,
                name=item.name,
                is_new=False,
                unit_price=unit_price,
                warnings=batch_warnings,
            ))

        elif clean_article in article_to_part:
            # Same article already processed (deduplication)
            existing_part_id, existing_part_number = article_to_part[clean_article]
            parts_existing += 1
            part_results.append(QuoteCreationPartResult(
                article_number=item.article_number,
                part_number=existing_part_number,
                name=item.name,
                is_new=False,
            ))

        else:
            # New part — full creation pipeline
            drawing_bytes = None
            drawing_filename = None
            if item.drawing_index is not None:
                key = str(item.drawing_index)
                if key in drawing_files:
                    drawing_bytes = drawing_files[key]
                    drawing_filename = f"{clean_article}.pdf"

            part_result = await _create_part_with_full_setup(
                item=item,
                drawing_bytes=drawing_bytes,
                drawing_filename=drawing_filename,
                db=db,
                username=username,
                file_service=file_service,
            )
            article_to_part[clean_article] = (
                (await db.execute(
                    select(Part.id).where(Part.part_number == part_result.part_number)
                )).scalar_one(),
                part_result.part_number,
            )
            part_results.append(part_result)
            parts_created += 1
            if part_result.drawing_linked:
                drawings_linked += 1

    # --- 3. Create Quote ---
    quote_number = await NumberGenerator.generate_quote_number(db)
    new_quote = Quote(
        quote_number=quote_number,
        partner_id=partner_id,
        title=data.title,
        description=data.notes,
        customer_request_number=data.customer_request_number,
        request_date=data.request_date,
        offer_deadline=data.offer_deadline,
        valid_until=data.valid_until,
        status="draft",
        discount_percent=data.discount_percent,
        tax_percent=data.tax_percent,
        notes=data.notes,
        created_by=username,
        updated_by=username,
    )
    db.add(new_quote)
    await db.flush()

    # --- 4. Create QuoteItems ---
    seen_items: set[tuple[str, int]] = set()

    for idx, item in enumerate(data.items):
        normalized = ArticleNumberMatcher.normalize(item.article_number)
        clean_article = normalized.base

        # Deduplicate by (article_number, quantity)
        dedup_key = (clean_article.lower(), item.quantity)
        if dedup_key in seen_items:
            continue
        seen_items.add(dedup_key)

        if clean_article not in article_to_part:
            continue

        part_id, part_number = article_to_part[clean_article]

        # Load part for denormalized fields
        part = await db.get(Part, part_id)
        if not part:
            continue

        # Find best batch for pricing
        batch, status, batch_warnings = await QuoteService.find_best_batch(
            part, item.quantity, db
        )
        unit_price = 0.0
        if batch:
            unit_price = float(batch.unit_price_frozen or batch.unit_cost)

        # Update part_result with price
        for pr in part_results:
            if pr.part_number == part_number and pr.unit_price == 0.0:
                pr.unit_price = unit_price
                break

        quote_item = QuoteItem(
            quote_id=new_quote.id,
            part_id=part_id,
            part_number=part.part_number,
            part_name=part.name,
            drawing_number=part.drawing_number,
            quantity=item.quantity,
            unit_price=unit_price,
            line_total=item.quantity * unit_price,
            notes=item.notes,
            created_by=username,
            updated_by=username,
        )
        db.add(quote_item)

    await db.flush()

    # --- 5. Recalculate totals ---
    await QuoteService.recalculate_quote_totals(new_quote, db)

    logger.info(
        f"Created quote {quote_number}: "
        f"{parts_created} new parts, {parts_existing} existing, "
        f"{drawings_linked} drawings linked, total={new_quote.total}"
    )

    return QuoteCreationResult(
        quote_number=quote_number,
        quote_id=new_quote.id,
        partner_number=partner_number,
        partner_is_new=partner_is_new,
        parts=part_results,
        parts_created=parts_created,
        parts_existing=parts_existing,
        drawings_linked=drawings_linked,
        total_amount=new_quote.total,
        warnings=result_warnings,
    )
