"""GESTIMA - Tests for seed data compliance with ADR-017

CRITICAL: Seed data MUST comply with ADR-017 (7-digit random numbering).
This test prevents L-015 anti-pattern (changing validation to fit bad data).

Real-world incident (2026-01-27):
- seed_data.py created "DEMO-001", "DEMO-002", "DEMO-003" (8 chars)
- ValidationError: String should have at most 7 characters
- Almost changed validation to fit bad data (walkaround)
- Caught by user: "tohle je kritické selhání!!!"

Prevention: This test ensures seed data never violates architecture again.
"""

import pytest
import re
from sqlalchemy import select

from app.seed_data import seed_demo_parts
from app.models.part import Part


@pytest.mark.asyncio
async def test_seed_demo_parts_adr017_compliance(db_session):
    """
    CRITICAL: Demo parts MUST comply with ADR-017 (7-digit format: 1XXXXXX)

    Test prevents L-015 anti-pattern (changing validation to fit bad data).
    If this test fails, FIX seed_data.py - DO NOT relax validation!
    """
    # Run seed function
    await seed_demo_parts(db_session)

    # Get all demo parts
    result = await db_session.execute(
        select(Part).where(Part.notes.like("%DEMO%"))
    )
    demo_parts = result.scalars().all()

    # Assert: At least 3 demo parts created
    assert len(demo_parts) >= 3, "Expected at least 3 demo parts"

    # ADR-017: Format MUST be 1XXXXXX (7 digits, starts with 1)
    adr017_pattern = re.compile(r"^1\d{6}$")

    for part in demo_parts:
        # FAIL if part_number doesn't match ADR-017
        assert adr017_pattern.match(part.part_number), (
            f"❌ SEED DATA VIOLATES ADR-017!\n"
            f"   Part: {part.name}\n"
            f"   part_number: {part.part_number}\n"
            f"   Expected: 1XXXXXX (7 digits, starts with 1)\n"
            f"   Found: {len(part.part_number)} characters\n"
            f"\n"
            f"   🚨 FIX: app/seed_data.py - use NumberGenerator!\n"
            f"   ❌ DO NOT: Change validation to fit bad data (L-015)!\n"
            f"   📖 READ: docs/ADR/017-7digit-random-numbering.md\n"
        )

        # Additional checks
        assert len(part.part_number) == 7, (
            f"part_number '{part.part_number}' must be exactly 7 characters"
        )
        assert part.part_number[0] == "1", (
            f"part_number '{part.part_number}' must start with '1' (ADR-017 prefix)"
        )
        assert part.part_number.isdigit(), (
            f"part_number '{part.part_number}' must contain only digits (no letters/symbols)"
        )


@pytest.mark.asyncio
async def test_seed_demo_parts_no_hardcoded_numbers(db_session):
    """
    Demo parts MUST NOT use hardcoded part_numbers like DEMO-001, DEMO-002, etc.

    This test catches hardcoded values that violate ADR-017.
    """
    await seed_demo_parts(db_session)

    result = await db_session.execute(
        select(Part).where(Part.notes.like("%DEMO%"))
    )
    demo_parts = result.scalars().all()

    # Forbidden patterns (8+ chars, contains letters, hyphens, etc.)
    forbidden_patterns = [
        r"DEMO-\d+",     # DEMO-001, DEMO-002
        r"[A-Za-z]+",    # Contains letters
        r".*-.*",        # Contains hyphens
        r".*\..*",       # Contains dots
    ]

    for part in demo_parts:
        for pattern in forbidden_patterns:
            assert not re.match(pattern, part.part_number), (
                f"❌ HARDCODED part_number detected!\n"
                f"   Part: {part.name}\n"
                f"   part_number: {part.part_number}\n"
                f"   Forbidden pattern: {pattern}\n"
                f"\n"
                f"   🚨 FIX: Use NumberGenerator.generate_part_numbers_batch()\n"
                f"   ❌ DO NOT: Hardcode DEMO-XXX or similar patterns!\n"
            )


@pytest.mark.asyncio
async def test_seed_demo_parts_unique(db_session):
    """
    Demo parts MUST have unique part_numbers (no duplicates).
    """
    await seed_demo_parts(db_session)

    result = await db_session.execute(
        select(Part.part_number).where(Part.notes.like("%DEMO%"))
    )
    part_numbers = [row[0] for row in result.all()]

    # Check for duplicates
    assert len(part_numbers) == len(set(part_numbers)), (
        f"❌ DUPLICATE part_numbers detected in demo data!\n"
        f"   part_numbers: {part_numbers}\n"
        f"   Duplicates: {[x for x in part_numbers if part_numbers.count(x) > 1]}\n"
    )


@pytest.mark.asyncio
async def test_seed_demo_parts_idempotent(db_session):
    """
    Running seed_demo_parts multiple times MUST be idempotent (no duplicates).
    """
    # Run seed twice
    await seed_demo_parts(db_session)
    await seed_demo_parts(db_session)

    result = await db_session.execute(
        select(Part).where(Part.notes.like("%DEMO%"))
    )
    demo_parts = result.scalars().all()

    # Should still have only 3 demo parts (not 6)
    assert len(demo_parts) == 3, (
        f"seed_demo_parts is not idempotent! "
        f"Expected 3 demo parts, found {len(demo_parts)}"
    )


@pytest.mark.asyncio
async def test_seed_demo_parts_pydantic_validation(db_session):
    """
    CRITICAL: Demo parts MUST pass Pydantic validation (PartResponse model).

    This is the actual validation that failed in production (2026-01-27).
    If this test fails, seed data are invalid!
    """
    from app.models.part import PartResponse

    await seed_demo_parts(db_session)

    result = await db_session.execute(
        select(Part).where(Part.notes.like("%DEMO%"))
    )
    demo_parts = result.scalars().all()

    for part in demo_parts:
        try:
            # This is what failed in production with DEMO-003
            PartResponse.model_validate(part)
        except Exception as e:
            pytest.fail(
                f"❌ PYDANTIC VALIDATION FAILED!\n"
                f"   Part: {part.name}\n"
                f"   part_number: {part.part_number}\n"
                f"   Error: {e}\n"
                f"\n"
                f"   This is the EXACT error that triggered L-015 incident!\n"
                f"   🚨 FIX: app/seed_data.py to generate valid data\n"
                f"   ❌ DO NOT: Change Pydantic validation to fit bad data!\n"
            )
