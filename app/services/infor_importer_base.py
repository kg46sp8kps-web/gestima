"""GESTIMA - Generic Infor Import System

Base classes and utilities for importing data from Infor CloudSuite Industrial
into Gestima entities.

Architecture:
- InforImporterBase<T>: Generic base class for all importers
- Subclasses implement entity-specific mapping logic
- Config-driven field mappings
- Support for M:N relationships and multi-source imports
"""

import logging
from typing import Dict, Any, Optional, List, TypeVar, Generic, Type
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Type variable for target entity
T = TypeVar('T')


class ValidationResult:
    """Validation result for a single import row"""

    def __init__(self):
        self.is_valid = True
        self.is_duplicate = False
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.needs_manual_input: Dict[str, bool] = {}  # field_name -> needs_manual

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "is_duplicate": self.is_duplicate,
            "errors": self.errors,
            "warnings": self.warnings,
            "needs_manual_input": self.needs_manual_input,
            # Extract specific fields for Pydantic schema compatibility
            "needs_manual_group": self.needs_manual_input.get("material_group_id", False),
            "needs_manual_shape": self.needs_manual_input.get("shape", False),
        }


class FieldMapping:
    """Configuration for field mapping from Infor to Gestima"""

    def __init__(
        self,
        source_field: str,
        target_field: str,
        required: bool = False,
        transform: Optional[callable] = None,
        fallback_fields: Optional[List[str]] = None
    ):
        """
        Args:
            source_field: Field name in Infor IDO
            target_field: Field name in Gestima entity
            required: Whether this field is required
            transform: Optional function to transform value (e.g., str → enum)
            fallback_fields: Alternative source fields to try if primary is empty
        """
        self.source_field = source_field
        self.target_field = target_field
        self.required = required
        self.transform = transform
        self.fallback_fields = fallback_fields or []


class InforImporterConfig:
    """Configuration for a specific importer"""

    def __init__(
        self,
        entity_name: str,
        ido_name: str,
        field_mappings: List[FieldMapping],
        duplicate_check_field: str = "code",
        additional_idos: Optional[Dict[str, str]] = None
    ):
        """
        Args:
            entity_name: Name of target entity (e.g., "MaterialItem")
            ido_name: Primary Infor IDO name (e.g., "SLItems")
            field_mappings: List of field mappings
            duplicate_check_field: Field to check for duplicates
            additional_idos: Optional dict of {role: ido_name} for multi-source imports
                            Example: {"operations": "SLOperations"}
        """
        self.entity_name = entity_name
        self.ido_name = ido_name
        self.field_mappings = field_mappings
        self.duplicate_check_field = duplicate_check_field
        self.additional_idos = additional_idos or {}


class InforImporterBase(ABC, Generic[T]):
    """
    Generic base class for Infor importers.

    Subclasses must implement:
    - get_config(): Return InforImporterConfig
    - map_row_custom(): Custom mapping logic beyond simple field mapping
    - create_entity(): Create the target entity from mapped data
    - check_duplicate(): Check if entity already exists
    """

    def __init__(self):
        self.config = self.get_config()

    @abstractmethod
    def get_config(self) -> InforImporterConfig:
        """Return importer configuration"""
        pass

    @abstractmethod
    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Custom mapping logic beyond simple field mapping.

        Args:
            row: Raw Infor IDO row
            basic_mapped: Result of basic field mapping
            db: Database session

        Returns:
            Dict with additional/modified mapped fields
        """
        pass

    @abstractmethod
    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> T:
        """
        Create entity instance from mapped data.

        Args:
            mapped_data: Fully mapped and validated data
            db: Database session

        Returns:
            Entity instance (not yet committed)
        """
        pass

    @abstractmethod
    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[T]:
        """
        Check if entity with same identifier already exists.

        Args:
            mapped_data: Mapped data
            db: Database session

        Returns:
            Existing entity or None
        """
        pass

    async def update_entity(
        self,
        existing: T,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """
        Update existing entity (for duplicate_action='update').

        Default: no-op (subclasses can override)

        Args:
            existing: Existing entity instance
            mapped_data: New mapped data
            db: Database session
        """
        logger.warning(f"Update not implemented for {self.config.entity_name}")

    # === GENERIC LOGIC (reusable across all importers) ===

    def apply_basic_mapping(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply basic field mappings from config.

        Args:
            row: Infor IDO row

        Returns:
            Dict with mapped fields
        """
        mapped = {}

        for field_map in self.config.field_mappings:
            # Try primary field
            value = row.get(field_map.source_field)

            # Try fallback fields if primary is empty
            if not value and field_map.fallback_fields:
                for fallback in field_map.fallback_fields:
                    value = row.get(fallback)
                    if value:
                        logger.debug(f"Used fallback field {fallback} for {field_map.target_field}")
                        break

            # Apply transformation if provided
            if value and field_map.transform:
                try:
                    value = field_map.transform(value)
                except Exception as e:
                    logger.error(f"Transform failed for {field_map.target_field}: {e}")
                    value = None

            mapped[field_map.target_field] = value

        return mapped

    async def map_row(
        self,
        row: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Map Infor row to entity fields.

        Combines basic field mapping with custom logic.

        Args:
            row: Infor IDO row
            db: Database session

        Returns:
            Fully mapped dict
        """
        # 1. Basic field mapping
        basic_mapped = self.apply_basic_mapping(row)

        # 2. Custom mapping logic (entity-specific)
        custom_mapped = await self.map_row_custom(row, basic_mapped, db)

        # 3. Merge results
        final_mapped = {**basic_mapped, **custom_mapped}

        return final_mapped

    async def validate_mapped_row(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> ValidationResult:
        """
        Validate mapped data.

        Args:
            mapped_data: Mapped fields
            db: Database session

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check required fields from config
        for field_map in self.config.field_mappings:
            if field_map.required and not mapped_data.get(field_map.target_field):
                result.errors.append(f"Missing required field: {field_map.target_field}")
                result.is_valid = False
                result.needs_manual_input[field_map.target_field] = True

        # Check for duplicates
        existing = await self.check_duplicate(mapped_data, db)
        if existing:
            result.is_duplicate = True
            result.warnings.append(
                f"{self.config.entity_name} with {self.config.duplicate_check_field}='{mapped_data.get(self.config.duplicate_check_field)}' already exists"
            )

        return result

    async def preview_import(
        self,
        rows: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Preview import without creating entities.

        Args:
            rows: List of Infor IDO rows
            db: Database session

        Returns:
            Dict with validation results and statistics
        """
        results = []
        valid_count = 0
        error_count = 0
        duplicate_count = 0

        for i, row in enumerate(rows):
            # Map row
            mapped = await self.map_row(row, db)

            # Validate
            validation = await self.validate_mapped_row(mapped, db)

            # Count statistics
            if validation.is_valid:
                valid_count += 1
            else:
                error_count += 1

            if validation.is_duplicate:
                duplicate_count += 1

            results.append({
                "row_index": i,
                "infor_data": row,
                "mapped_data": mapped,
                "validation": validation.to_dict()
            })

        logger.info(
            f"Preview complete for {self.config.entity_name}: "
            f"{len(rows)} rows, {valid_count} valid, {error_count} errors, {duplicate_count} duplicates"
        )

        return {
            "entity_name": self.config.entity_name,
            "valid_count": valid_count,
            "error_count": error_count,
            "duplicate_count": duplicate_count,
            "rows": results
        }

    async def execute_import(
        self,
        rows: List[Dict[str, Any]],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Execute import - create entities.

        Args:
            rows: List of validated mapped data dicts (with duplicate_action)
            db: Database session (already has active transaction from FastAPI get_db)

        Returns:
            Dict with import statistics
        """
        created = []
        updated = []
        skipped = []
        errors = []

        try:
            for row_data in rows:
                try:
                    duplicate_action = row_data.get("duplicate_action", "skip")

                    # Check if exists
                    existing = await self.check_duplicate(row_data, db)

                    if existing:
                        if duplicate_action == 'skip':
                            skipped.append(row_data.get(self.config.duplicate_check_field))
                            continue
                        elif duplicate_action == 'update':
                            await self.update_entity(existing, row_data, db)
                            updated.append(row_data.get(self.config.duplicate_check_field))
                            continue

                    # Create new entity
                    new_entity = await self.create_entity(row_data, db)
                    db.add(new_entity)
                    created.append(row_data.get(self.config.duplicate_check_field))

                except Exception as row_error:
                    error_msg = f"Failed to process row: {str(row_error)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)

            # Commit all changes
            await db.commit()

            logger.info(
                f"Import complete for {self.config.entity_name}: "
                f"{len(created)} created, {len(updated)} updated, {len(skipped)} skipped, {len(errors)} errors"
            )

            return {
                "success": len(errors) == 0,
                "created_count": len(created),
                "updated_count": len(updated),
                "skipped_count": len(skipped),
                "errors": errors
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Import failed for {self.config.entity_name}: {e}", exc_info=True)
            raise
