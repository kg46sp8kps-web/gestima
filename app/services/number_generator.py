"""
Number Generator Service

Generates unique 8-digit random numbers for entities (v2.0):
- Parts: 10XXXXXX (10000000-10999999)
- Materials: 20XXXXXX (20000000-20999999)
- Batches: 30XXXXXX (30000000-30999999)

Performance:
- Single number: ~50ms
- Batch (30 numbers): ~50ms (not 3000ms!)
- Import (3000 numbers): ~3s with batching

Collision handling:
- 2× buffer strategy (adaptive for high utilization)
- Recursive retry on insufficient buffer
- MAX_RETRIES safety limit

See ADR-017 for numbering system rationale.
"""

import random
import logging
from typing import List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.part import Part
from app.models.material import MaterialItem
from app.models.batch import Batch
from app.models.batch_set import BatchSet
from app.models.work_center import WorkCenter
from app.models.partner import Partner
from app.models.quote import Quote

logger = logging.getLogger(__name__)


class NumberGenerationError(Exception):
    """Raised when unable to generate unique number after MAX_RETRIES"""
    pass


class NumberGenerator:
    """Service for generating unique random entity numbers"""

    # Range definitions (v2.0: 8-digit with 2-digit prefix)
    PART_MIN = 10000000
    PART_MAX = 10999999
    MATERIAL_MIN = 20000000
    MATERIAL_MAX = 20999999
    BATCH_MIN = 30000000
    BATCH_MAX = 30999999
    BATCH_SET_MIN = 35000000  # ADR-022: BatchSets (pricing domain)
    BATCH_SET_MAX = 35999999
    PARTNER_MIN = 70000000  # Partners (customers & suppliers)
    PARTNER_MAX = 70999999
    WORK_CENTER_MIN = 80000001  # Sequential, not random (ADR-021)
    WORK_CENTER_MAX = 80999999
    QUOTE_MIN = 85000000  # Quotes (customer quotations)
    QUOTE_MAX = 85999999

    # Safety limits
    MAX_RETRIES = 10
    MAX_BATCH_SIZE = 1000

    # Capacity per type
    CAPACITY = 1000000

    @staticmethod
    async def _calculate_buffer_multiplier(
        db: AsyncSession,
        model,
        capacity: int
    ) -> float:
        """
        Calculate buffer multiplier based on DB utilization.

        Higher utilization = more collisions expected = larger buffer needed.
        """
        result = await db.execute(select(func.count(model.id)))
        count = result.scalar() or 0

        utilization = count / capacity

        if utilization < 0.5:
            return 2.0  # <50% full → 2× buffer
        elif utilization < 0.8:
            return 3.0  # <80% full → 3× buffer
        else:
            return 5.0  # ≥80% full → 5× buffer (high collision rate)

    @staticmethod
    async def generate_part_numbers_batch(
        db: AsyncSession,
        count: int
    ) -> List[str]:
        """
        Generate multiple unique 8-digit part numbers at once.

        Format: 10XXXXXX (10000000-10999999)
        Performance: O(1) DB query regardless of count

        Args:
            db: Database session
            count: Number of unique part numbers to generate

        Returns:
            List of unique part numbers

        Raises:
            ValueError: If count <= 0 or count > MAX_BATCH_SIZE
            NumberGenerationError: If unable to generate after MAX_RETRIES
        """
        if count <= 0:
            return []

        if count > NumberGenerator.MAX_BATCH_SIZE:
            raise ValueError(
                f"Cannot generate more than {NumberGenerator.MAX_BATCH_SIZE} "
                f"numbers per batch"
            )

        for attempt in range(NumberGenerator.MAX_RETRIES):
            # Calculate adaptive buffer
            multiplier = await NumberGenerator._calculate_buffer_multiplier(
                db, Part, NumberGenerator.CAPACITY
            )
            buffer_size = int(count * multiplier)

            # Generate random candidates
            # AUDIT-FIX: Added iteration limit to prevent infinite loop at high DB utilization
            candidates = set()
            max_iterations = buffer_size * 10  # Safety limit
            iterations = 0
            while len(candidates) < buffer_size and iterations < max_iterations:
                number = str(random.randint(
                    NumberGenerator.PART_MIN,
                    NumberGenerator.PART_MAX
                ))
                candidates.add(number)
                iterations += 1

            if iterations >= max_iterations:
                logger.warning(
                    f"Hit iteration limit ({max_iterations}) generating part numbers. "
                    f"Generated {len(candidates)}/{buffer_size} candidates."
                )

            # Single DB query to check all candidates
            result = await db.execute(
                select(Part.part_number).where(
                    Part.part_number.in_(candidates)
                )
            )
            existing = {row[0] for row in result}

            # Filter out existing numbers
            available = list(candidates - existing)

            # Check if we have enough unique numbers
            if len(available) >= count:
                logger.debug(
                    f"Generated {count} part numbers on attempt {attempt + 1}"
                )
                return available[:count]

            # Not enough numbers, will retry with larger buffer
            logger.warning(
                f"Attempt {attempt + 1}: Only {len(available)}/{count} unique "
                f"numbers generated (collision rate high)"
            )

        # Failed after MAX_RETRIES
        raise NumberGenerationError(
            f"Failed to generate {count} unique part numbers after "
            f"{NumberGenerator.MAX_RETRIES} attempts. Database may be near capacity."
        )

    @staticmethod
    async def generate_material_numbers_batch(
        db: AsyncSession,
        count: int
    ) -> List[str]:
        """
        Generate multiple unique 8-digit material numbers at once.

        Format: 20XXXXXX (20000000-20999999)
        """
        if count <= 0:
            return []

        if count > NumberGenerator.MAX_BATCH_SIZE:
            raise ValueError(
                f"Cannot generate more than {NumberGenerator.MAX_BATCH_SIZE} "
                f"numbers per batch"
            )

        for attempt in range(NumberGenerator.MAX_RETRIES):
            multiplier = await NumberGenerator._calculate_buffer_multiplier(
                db, MaterialItem, NumberGenerator.CAPACITY
            )
            buffer_size = int(count * multiplier)

            # AUDIT-FIX: Added iteration limit to prevent infinite loop
            candidates = set()
            max_iterations = buffer_size * 10
            iterations = 0
            while len(candidates) < buffer_size and iterations < max_iterations:
                number = str(random.randint(
                    NumberGenerator.MATERIAL_MIN,
                    NumberGenerator.MATERIAL_MAX
                ))
                candidates.add(number)
                iterations += 1

            result = await db.execute(
                select(MaterialItem.material_number).where(
                    MaterialItem.material_number.in_(candidates)
                )
            )
            existing = {row[0] for row in result}
            available = list(candidates - existing)

            if len(available) >= count:
                logger.debug(
                    f"Generated {count} material numbers on attempt {attempt + 1}"
                )
                return available[:count]

            logger.warning(
                f"Attempt {attempt + 1}: Only {len(available)}/{count} unique "
                f"material numbers generated"
            )

        raise NumberGenerationError(
            f"Failed to generate {count} unique material numbers after "
            f"{NumberGenerator.MAX_RETRIES} attempts"
        )

    @staticmethod
    async def generate_batch_numbers_batch(
        db: AsyncSession,
        count: int
    ) -> List[str]:
        """
        Generate multiple unique 8-digit batch numbers at once.

        Format: 30XXXXXX (30000000-30999999)
        """
        if count <= 0:
            return []

        if count > NumberGenerator.MAX_BATCH_SIZE:
            raise ValueError(
                f"Cannot generate more than {NumberGenerator.MAX_BATCH_SIZE} "
                f"numbers per batch"
            )

        for attempt in range(NumberGenerator.MAX_RETRIES):
            multiplier = await NumberGenerator._calculate_buffer_multiplier(
                db, Batch, NumberGenerator.CAPACITY
            )
            buffer_size = int(count * multiplier)

            # AUDIT-FIX: Added iteration limit to prevent infinite loop
            candidates = set()
            max_iterations = buffer_size * 10
            iterations = 0
            while len(candidates) < buffer_size and iterations < max_iterations:
                number = str(random.randint(
                    NumberGenerator.BATCH_MIN,
                    NumberGenerator.BATCH_MAX
                ))
                candidates.add(number)
                iterations += 1

            result = await db.execute(
                select(Batch.batch_number).where(
                    Batch.batch_number.in_(candidates)
                )
            )
            existing = {row[0] for row in result}
            available = list(candidates - existing)

            if len(available) >= count:
                logger.debug(
                    f"Generated {count} batch numbers on attempt {attempt + 1}"
                )
                return available[:count]

            logger.warning(
                f"Attempt {attempt + 1}: Only {len(available)}/{count} unique "
                f"batch numbers generated"
            )

        raise NumberGenerationError(
            f"Failed to generate {count} unique batch numbers after "
            f"{NumberGenerator.MAX_RETRIES} attempts"
        )

    @staticmethod
    async def generate_batch_set_numbers_batch(
        db: AsyncSession,
        count: int
    ) -> List[str]:
        """
        Generate multiple unique 8-digit batch set numbers at once.

        Format: 35XXXXXX (35000000-35999999)
        ADR-022: BatchSets (pricing domain, near Batches 30XXXXXX)
        """
        if count <= 0:
            return []

        if count > NumberGenerator.MAX_BATCH_SIZE:
            raise ValueError(
                f"Cannot generate more than {NumberGenerator.MAX_BATCH_SIZE} "
                f"numbers per batch"
            )

        for attempt in range(NumberGenerator.MAX_RETRIES):
            multiplier = await NumberGenerator._calculate_buffer_multiplier(
                db, BatchSet, NumberGenerator.CAPACITY
            )
            buffer_size = int(count * multiplier)

            candidates = set()
            max_iterations = buffer_size * 10
            iterations = 0
            while len(candidates) < buffer_size and iterations < max_iterations:
                number = str(random.randint(
                    NumberGenerator.BATCH_SET_MIN,
                    NumberGenerator.BATCH_SET_MAX
                ))
                candidates.add(number)
                iterations += 1

            result = await db.execute(
                select(BatchSet.set_number).where(
                    BatchSet.set_number.in_(candidates)
                )
            )
            existing = {row[0] for row in result}
            available = list(candidates - existing)

            if len(available) >= count:
                logger.debug(
                    f"Generated {count} batch set numbers on attempt {attempt + 1}"
                )
                return available[:count]

            logger.warning(
                f"Attempt {attempt + 1}: Only {len(available)}/{count} unique "
                f"batch set numbers generated"
            )

        raise NumberGenerationError(
            f"Failed to generate {count} unique batch set numbers after "
            f"{NumberGenerator.MAX_RETRIES} attempts"
        )

    @staticmethod
    async def generate_partner_numbers_batch(
        db: AsyncSession,
        count: int
    ) -> List[str]:
        """
        Generate multiple unique 8-digit partner numbers at once.

        Format: 70XXXXXX (70000000-70999999)
        """
        if count <= 0:
            return []

        if count > NumberGenerator.MAX_BATCH_SIZE:
            raise ValueError(
                f"Cannot generate more than {NumberGenerator.MAX_BATCH_SIZE} "
                f"numbers per batch"
            )

        for attempt in range(NumberGenerator.MAX_RETRIES):
            multiplier = await NumberGenerator._calculate_buffer_multiplier(
                db, Partner, NumberGenerator.CAPACITY
            )
            buffer_size = int(count * multiplier)

            candidates = set()
            max_iterations = buffer_size * 10
            iterations = 0
            while len(candidates) < buffer_size and iterations < max_iterations:
                number = str(random.randint(
                    NumberGenerator.PARTNER_MIN,
                    NumberGenerator.PARTNER_MAX
                ))
                candidates.add(number)
                iterations += 1

            result = await db.execute(
                select(Partner.partner_number).where(
                    Partner.partner_number.in_(candidates)
                )
            )
            existing = {row[0] for row in result}
            available = list(candidates - existing)

            if len(available) >= count:
                logger.debug(
                    f"Generated {count} partner numbers on attempt {attempt + 1}"
                )
                return available[:count]

            logger.warning(
                f"Attempt {attempt + 1}: Only {len(available)}/{count} unique "
                f"partner numbers generated"
            )

        raise NumberGenerationError(
            f"Failed to generate {count} unique partner numbers after "
            f"{NumberGenerator.MAX_RETRIES} attempts"
        )

    # Convenience methods for single number generation

    @staticmethod
    async def generate_part_number(db: AsyncSession) -> str:
        """Generate a single unique part number (delegates to batch)"""
        numbers = await NumberGenerator.generate_part_numbers_batch(db, 1)
        return numbers[0]

    @staticmethod
    async def generate_material_number(db: AsyncSession) -> str:
        """Generate a single unique material number (delegates to batch)"""
        numbers = await NumberGenerator.generate_material_numbers_batch(db, 1)
        return numbers[0]

    @staticmethod
    async def generate_batch_number(db: AsyncSession) -> str:
        """Generate a single unique batch number (delegates to batch)"""
        numbers = await NumberGenerator.generate_batch_numbers_batch(db, 1)
        return numbers[0]

    @staticmethod
    async def generate_batch_set_number(db: AsyncSession) -> str:
        """Generate a single unique batch set number (delegates to batch)"""
        numbers = await NumberGenerator.generate_batch_set_numbers_batch(db, 1)
        return numbers[0]

    @staticmethod
    async def generate_partner_number(db: AsyncSession) -> str:
        """Generate a single unique partner number (delegates to batch)"""
        numbers = await NumberGenerator.generate_partner_numbers_batch(db, 1)
        return numbers[0]

    # =========================================================================
    # WORK CENTER - SEQUENTIAL (not random) - ADR-021
    # =========================================================================

    @staticmethod
    async def generate_work_center_number(db: AsyncSession) -> str:
        """
        Generate next sequential work center number.

        Format: 80XXXXXX (80000001-80999999)
        Sequential (not random) - easier for operators, no collision handling needed.

        Args:
            db: Database session

        Returns:
            Next sequential work center number as string

        Raises:
            NumberGenerationError: If number space is exhausted
        """
        result = await db.execute(
            select(func.max(WorkCenter.work_center_number))
        )
        max_number = result.scalar()

        if max_number is None:
            # First work center
            return str(NumberGenerator.WORK_CENTER_MIN)

        next_num = int(max_number) + 1

        if next_num > NumberGenerator.WORK_CENTER_MAX:
            raise NumberGenerationError(
                f"Work center number space exhausted (max: {NumberGenerator.WORK_CENTER_MAX})"
            )

        logger.debug(f"Generated work center number: {next_num}")
        return str(next_num)

    @staticmethod
    async def generate_quote_numbers_batch(
        db: AsyncSession,
        count: int
    ) -> List[str]:
        """
        Generate multiple unique 8-digit quote numbers at once.

        Format: 85XXXXXX (85000000-85999999)
        """
        if count <= 0:
            return []

        if count > NumberGenerator.MAX_BATCH_SIZE:
            raise ValueError(
                f"Cannot generate more than {NumberGenerator.MAX_BATCH_SIZE} "
                f"numbers per batch"
            )

        for attempt in range(NumberGenerator.MAX_RETRIES):
            multiplier = await NumberGenerator._calculate_buffer_multiplier(
                db, Quote, NumberGenerator.CAPACITY
            )
            buffer_size = int(count * multiplier)

            candidates = set()
            max_iterations = buffer_size * 10
            iterations = 0
            while len(candidates) < buffer_size and iterations < max_iterations:
                number = str(random.randint(
                    NumberGenerator.QUOTE_MIN,
                    NumberGenerator.QUOTE_MAX
                ))
                candidates.add(number)
                iterations += 1

            result = await db.execute(
                select(Quote.quote_number).where(
                    Quote.quote_number.in_(candidates)
                )
            )
            existing = {row[0] for row in result}
            available = list(candidates - existing)

            if len(available) >= count:
                logger.debug(
                    f"Generated {count} quote numbers on attempt {attempt + 1}"
                )
                return available[:count]

            logger.warning(
                f"Attempt {attempt + 1}: Only {len(available)}/{count} unique "
                f"quote numbers generated"
            )

        raise NumberGenerationError(
            f"Failed to generate {count} unique quote numbers after "
            f"{NumberGenerator.MAX_RETRIES} attempts"
        )

    @staticmethod
    async def generate_quote_number(db: AsyncSession) -> str:
        """Generate a single unique quote number (delegates to batch)"""
        numbers = await NumberGenerator.generate_quote_numbers_batch(db, 1)
        return numbers[0]
