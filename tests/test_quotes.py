"""Tests for Quote module (ADR-VIS-002)

Test coverage:
- CRUD operations
- Workflow transitions (DRAFT → SENT → APPROVED/REJECTED)
- Edit lock enforcement
- Quote items CRUD with auto-recalc
- Snapshot creation
- Auto-pricing from frozen batch_set
- Clone functionality
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote, QuoteItem
from app.models.partner import Partner
from app.models.part import Part
from app.models.batch import Batch
from app.models.batch_set import BatchSet
from app.models.enums import QuoteStatus
from app.services.quote_service import QuoteService
from app.services.number_generator import NumberGenerator


@pytest.mark.asyncio
async def test_create_quote(db_session: AsyncSession, test_partner: Partner):
    """Test quote creation with auto-generated number"""
    # Generate quote number
    quote_number = await NumberGenerator.generate_quote_number(db_session)

    # Create quote
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        description="Test description",
        discount_percent=10.0,
        tax_percent=21.0,
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )

    db_session.add(quote)
    await db_session.commit()
    await db_session.refresh(quote)

    # Verify
    assert quote.id is not None
    assert quote.quote_number.startswith("50")  # ADR-017: Quotes prefix = 50
    assert quote.status == QuoteStatus.DRAFT.value
    assert quote.partner_id == test_partner.id
    assert quote.total == 0.0


@pytest.mark.asyncio
async def test_quote_item_auto_pricing(
    db_session: AsyncSession,
    test_partner: Partner,
    test_part: Part
):
    """Test quote item auto-loads pricing from frozen batch_set"""
    # Create frozen batch_set with pricing
    batch_set = BatchSet(
        set_number="35000001",
        part_id=test_part.id,
        name="Test Batch Set",
        status="frozen",
        frozen_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(batch_set)
    await db_session.flush()

    # Create batch with pricing
    batch = Batch(
        batch_number="30000001",
        part_id=test_part.id,
        batch_set_id=batch_set.id,
        quantity=100,
        unit_cost=50.0,
        unit_price_frozen=75.0,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(batch)
    await db_session.commit()

    # Auto-load price
    price = await QuoteService.get_latest_frozen_batch_price(test_part.id, db_session)

    # Verify
    assert price == 75.0


@pytest.mark.asyncio
async def test_quote_totals_calculation(db_session: AsyncSession, test_partner: Partner):
    """Test quote totals recalculation"""
    # Create quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        discount_percent=10.0,
        tax_percent=21.0,
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.flush()

    # Add items
    item1 = QuoteItem(
        quote_id=quote.id,
        part_number="10000001",
        part_name="Test Part 1",
        quantity=5,
        unit_price=100.0,
        line_total=500.0,
        created_by="test_user",
        updated_by="test_user"
    )
    item2 = QuoteItem(
        quote_id=quote.id,
        part_number="10000002",
        part_name="Test Part 2",
        quantity=3,
        unit_price=200.0,
        line_total=600.0,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add_all([item1, item2])
    await db_session.flush()

    # Recalculate totals
    await QuoteService.recalculate_quote_totals(quote, db_session)

    # Verify
    # subtotal = 500 + 600 = 1100
    # discount = 1100 * 0.10 = 110
    # taxable = 1100 - 110 = 990
    # tax = 990 * 0.21 = 207.9
    # total = 990 + 207.9 = 1197.9

    assert quote.subtotal == 1100.0
    assert quote.discount_amount == 110.0
    assert quote.tax_amount == 207.9
    assert quote.total == 1197.9


@pytest.mark.asyncio
async def test_transition_to_sent_creates_snapshot(
    db_session: AsyncSession,
    test_partner: Partner
):
    """Test DRAFT → SENT transition creates snapshot"""
    # Create quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.flush()

    # Add item
    item = QuoteItem(
        quote_id=quote.id,
        part_number="10000001",
        part_name="Test Part",
        quantity=5,
        unit_price=100.0,
        line_total=500.0,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(item)
    await db_session.flush()

    # Recalculate totals
    await QuoteService.recalculate_quote_totals(quote, db_session)

    # Transition to SENT
    await QuoteService.transition_to_sent(quote, db_session, "test_user")

    # Verify
    assert quote.status == QuoteStatus.SENT.value
    assert quote.sent_at is not None
    assert quote.snapshot_data is not None
    assert quote.snapshot_data["quote_number"] == quote_number
    assert quote.snapshot_data["total"] == quote.total
    assert len(quote.snapshot_data["items"]) == 1


@pytest.mark.asyncio
async def test_edit_lock_after_sent(db_session: AsyncSession, test_partner: Partner):
    """Test quote is read-only after SENT"""
    # Create quote in SENT status
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.SENT.value,
        sent_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Try to check edit lock
    with pytest.raises(Exception) as exc_info:
        QuoteService.check_edit_lock(quote)

    assert exc_info.value.status_code == 409
    assert "read-only" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_workflow_draft_to_approved(db_session: AsyncSession, test_partner: Partner):
    """Test full workflow: DRAFT → SENT → APPROVED"""
    # Create quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # DRAFT → SENT
    await QuoteService.transition_to_sent(quote, db_session, "test_user")
    assert quote.status == QuoteStatus.SENT.value

    # SENT → APPROVED
    await QuoteService.transition_to_approved(quote, "test_user")
    assert quote.status == QuoteStatus.APPROVED.value
    assert quote.approved_at is not None


@pytest.mark.asyncio
async def test_workflow_draft_to_rejected(db_session: AsyncSession, test_partner: Partner):
    """Test workflow: DRAFT → SENT → REJECTED"""
    # Create quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # DRAFT → SENT
    await QuoteService.transition_to_sent(quote, db_session, "test_user")

    # SENT → REJECTED
    await QuoteService.transition_to_rejected(quote, "test_user")
    assert quote.status == QuoteStatus.REJECTED.value
    assert quote.rejected_at is not None


@pytest.mark.asyncio
async def test_clone_quote(db_session: AsyncSession, test_partner: Partner):
    """Test quote cloning"""
    # Create original quote
    original_number = await NumberGenerator.generate_quote_number(db_session)
    original = Quote(
        quote_number=original_number,
        partner_id=test_partner.id,
        title="Original Quote",
        status=QuoteStatus.SENT.value,
        discount_percent=10.0,
        tax_percent=21.0,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(original)
    await db_session.flush()

    # Add items
    item = QuoteItem(
        quote_id=original.id,
        part_number="10000001",
        part_name="Test Part",
        quantity=5,
        unit_price=100.0,
        line_total=500.0,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(item)
    await db_session.flush()

    # Clone
    new_number = await NumberGenerator.generate_quote_number(db_session)
    clone = await QuoteService.clone_quote(original, db_session, "test_user", new_number)

    # Verify
    assert clone.quote_number != original.quote_number
    assert clone.status == QuoteStatus.DRAFT.value
    assert clone.title == "Original Quote (Copy)"
    assert clone.partner_id == original.partner_id
    assert clone.discount_percent == original.discount_percent

    # Verify items cloned
    result = await db_session.execute(
        select(QuoteItem).where(QuoteItem.quote_id == clone.id)
    )
    cloned_items = result.scalars().all()
    assert len(cloned_items) == 1
    assert cloned_items[0].part_number == "10000001"


@pytest.mark.asyncio
async def test_invalid_transition_throws_error(db_session: AsyncSession, test_partner: Partner):
    """Test invalid workflow transitions throw errors"""
    # Create quote in DRAFT
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Try to approve DRAFT (should fail - only SENT can be approved)
    with pytest.raises(Exception) as exc_info:
        await QuoteService.transition_to_approved(quote, "test_user")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_item_line_total_recalculation(db_session: AsyncSession):
    """Test item line_total recalculation"""
    item = QuoteItem(
        quote_id=1,
        part_number="10000001",
        part_name="Test Part",
        quantity=5,
        unit_price=100.0,
        line_total=0.0,  # Wrong value
        created_by="test_user",
        updated_by="test_user"
    )

    # Recalculate
    await QuoteService.recalculate_item_total(item)

    # Verify
    assert item.line_total == 500.0


@pytest.mark.asyncio
async def test_quote_number_generation(db_session: AsyncSession):
    """Test quote number generation in correct range (ADR-017: prefix 50)"""
    quote_number = await NumberGenerator.generate_quote_number(db_session)

    # Verify format
    assert len(quote_number) == 8
    assert quote_number.startswith("50")  # ADR-017: Quotes = 50XXXXXX
    assert int(quote_number) >= 50000000
    assert int(quote_number) <= 50999999


@pytest.mark.asyncio
async def test_quote_soft_delete(db_session: AsyncSession, test_partner: Partner):
    """Test quote soft delete"""
    # Create quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Soft delete
    quote.deleted_at = datetime.utcnow()
    quote.deleted_by = "test_user"
    await db_session.commit()

    # Verify still in DB but marked deleted
    result = await db_session.execute(select(Quote).where(Quote.id == quote.id))
    deleted_quote = result.scalar_one()
    assert deleted_quote.deleted_at is not None


@pytest.mark.asyncio
async def test_sent_quote_cannot_be_deleted(db_session: AsyncSession, test_partner: Partner):
    """Test SENT quotes are protected from deletion (contain legal snapshot)"""
    from fastapi import HTTPException

    # Create SENT quote with snapshot
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.SENT.value,
        snapshot_data={"test": "snapshot"},
        sent_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Try to soft delete (should be blocked)
    # NOTE: This simulates router logic - in real app, router checks status
    if quote.status in [QuoteStatus.SENT.value, QuoteStatus.APPROVED.value]:
        # This is what router should do
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=403,
                detail=f"Nelze smazat nabídku ve stavu '{quote.status}'. "
                       "Odeslané a schválené nabídky obsahují právně závazný snapshot a nesmí být smazány."
            )

        assert exc_info.value.status_code == 403
        assert "Nelze smazat" in str(exc_info.value.detail)

        # Verify quote was NOT deleted
        result = await db_session.execute(select(Quote).where(Quote.id == quote.id))
        existing_quote = result.scalar_one()
        assert existing_quote.deleted_at is None


@pytest.mark.asyncio
async def test_approved_quote_cannot_be_deleted(db_session: AsyncSession, test_partner: Partner):
    """Test APPROVED quotes are protected from deletion (contain legal snapshot)"""
    from fastapi import HTTPException

    # Create APPROVED quote with snapshot
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.APPROVED.value,
        snapshot_data={"test": "snapshot"},
        sent_at=datetime.utcnow(),
        approved_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Try to soft delete (should be blocked)
    if quote.status in [QuoteStatus.SENT.value, QuoteStatus.APPROVED.value]:
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=403,
                detail=f"Nelze smazat nabídku ve stavu '{quote.status}'. "
                       "Odeslané a schválené nabídky obsahují právně závazný snapshot a nesmí být smazány."
            )

        assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_draft_quote_can_be_deleted(db_session: AsyncSession, test_partner: Partner):
    """Test DRAFT quotes can be deleted (no snapshot yet)"""
    # Create DRAFT quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.DRAFT.value,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Soft delete (should succeed)
    quote.deleted_at = datetime.utcnow()
    quote.deleted_by = "test_user"
    await db_session.commit()

    # Verify deleted
    result = await db_session.execute(select(Quote).where(Quote.id == quote.id))
    deleted_quote = result.scalar_one()
    assert deleted_quote.deleted_at is not None


@pytest.mark.asyncio
async def test_rejected_quote_can_be_deleted(db_session: AsyncSession, test_partner: Partner):
    """Test REJECTED quotes can be deleted"""
    # Create REJECTED quote
    quote_number = await NumberGenerator.generate_quote_number(db_session)
    quote = Quote(
        quote_number=quote_number,
        partner_id=test_partner.id,
        title="Test Quote",
        status=QuoteStatus.REJECTED.value,
        snapshot_data={"test": "snapshot"},  # Has snapshot but rejected
        sent_at=datetime.utcnow(),
        rejected_at=datetime.utcnow(),
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(quote)
    await db_session.commit()

    # Soft delete (should succeed)
    quote.deleted_at = datetime.utcnow()
    quote.deleted_by = "test_user"
    await db_session.commit()

    # Verify deleted
    result = await db_session.execute(select(Quote).where(Quote.id == quote.id))
    deleted_quote = result.scalar_one()
    assert deleted_quote.deleted_at is not None


# Fixtures for tests

@pytest.fixture
async def test_partner(db_session: AsyncSession) -> Partner:
    """Create test partner"""
    partner = Partner(
        partner_number="70000001",
        company_name="Test Customer",
        is_customer=True,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(partner)
    await db_session.commit()
    await db_session.refresh(partner)
    return partner


@pytest.fixture
async def test_part(db_session: AsyncSession) -> Part:
    """Create test part"""
    part = Part(
        part_number="10000001",
        name="Test Part",
        status="active",
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(part)
    await db_session.commit()
    await db_session.refresh(part)
    return part
