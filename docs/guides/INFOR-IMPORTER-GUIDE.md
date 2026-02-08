# Infor Generic Importer System - Developer Guide

**Version:** 1.0
**Date:** 2026-02-03
**Author:** Claude + Lofas

---

## Overview

Generic system for importing data from Infor CloudSuite Industrial to Gestima entities.

**Architecture:**
- `InforImporterBase<T>` - Abstract base class (generic)
- Config-driven field mappings
- Automatic validation & duplicate detection
- Support for M:N relationships and multi-source imports

---

## Quick Start - Add New Importer

### Example: Import Parts from Infor

**Goal:** Import manufactured parts from 2 Infor IDOs:
- `SLItems` → Item data (code, description)
- `SLOperations` → Operations data

**Target Entity:** `Part` (Gestima)

### Step 1: Create Importer Class

**File:** `app/services/infor_part_importer.py` (NEW)

```python
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.infor_importer_base import (
    InforImporterBase,
    InforImporterConfig,
    FieldMapping,
    ValidationResult
)
from app.models.part import Part
from app.services.number_generator import NumberGenerator


class PartImporter(InforImporterBase[Part]):
    """Importer for Part from Infor SLItems + SLOperations"""

    def get_config(self) -> InforImporterConfig:
        """Configure field mappings"""
        return InforImporterConfig(
            entity_name="Part",
            ido_name="SLItems",  # Primary IDO
            field_mappings=[
                # Required fields
                FieldMapping("Item", "code", required=True),
                FieldMapping("Description", "name", required=True),
                # Optional fields
                FieldMapping("DrawingNo", "drawing_number"),
                FieldMapping("Revision", "revision"),
                FieldMapping("Weight", "weight"),
                # Fallback example: try "UM" first, then "UnitMeasure"
                FieldMapping("UM", "unit", fallback_fields=["UnitMeasure"]),
            ],
            duplicate_check_field="code",
            additional_idos={
                "operations": "SLOperations"  # For M:N relationship
            }
        )

    async def map_row_custom(
        self,
        row: Dict[str, Any],
        basic_mapped: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Custom mapping logic for Part"""
        custom = {}

        # Example: Parse part type from description
        description = row.get("Description", "")
        if "ASSEMBLY" in description.upper():
            custom["part_type"] = "assembly"
        elif "COMPONENT" in description.upper():
            custom["part_type"] = "component"
        else:
            custom["part_type"] = "raw"

        # Example: Detect category from Item code
        item_code = row.get("Item", "")
        if item_code.startswith("P-"):
            custom["category_id"] = 1  # Manufactured parts
        elif item_code.startswith("C-"):
            custom["category_id"] = 2  # Purchased components

        # part_number will be generated in create_entity
        custom["part_number"] = None

        return custom

    async def create_entity(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Part:
        """Create Part instance"""
        # Generate part_number
        part_numbers = await NumberGenerator.generate_part_numbers_batch(db, 1)
        part_number = part_numbers[0]

        return Part(
            part_number=part_number,
            code=mapped_data["code"],
            name=mapped_data["name"],
            drawing_number=mapped_data.get("drawing_number"),
            revision=mapped_data.get("revision"),
            weight=mapped_data.get("weight"),
            unit=mapped_data.get("unit", "ks"),
            part_type=mapped_data.get("part_type"),
            category_id=mapped_data.get("category_id")
        )

    async def check_duplicate(
        self,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> Optional[Part]:
        """Check if Part with same code exists"""
        code = mapped_data.get("code")
        if not code:
            return None

        result = await db.execute(
            select(Part).where(Part.code == code)
        )
        return result.scalar_one_or_none()

    async def update_entity(
        self,
        existing: Part,
        mapped_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """Update existing Part (only safe fields)"""
        existing.revision = mapped_data.get("revision")
        existing.weight = mapped_data.get("weight")
```

### Step 2: Add Router Endpoints

**File:** `app/routers/infor_router.py` (MODIFY - add ~50 lines)

```python
from app.services.infor_part_importer import PartImporter

# === PYDANTIC SCHEMAS FOR PART IMPORT ===

class PartImportPreviewRequest(BaseModel):
    ido_name: str
    rows: List[Dict[str, Any]]

class PartImportPreviewResponse(BaseModel):
    valid_count: int
    error_count: int
    duplicate_count: int
    rows: List[StagedMaterialRowSchema]  # Reuse generic schema

class PartItemImportData(BaseModel):
    code: str
    name: str
    drawing_number: Optional[str] = None
    revision: Optional[str] = None
    weight: Optional[float] = None
    unit: str = "ks"
    part_type: Optional[str] = None
    category_id: Optional[int] = None
    duplicate_action: Optional[str] = "skip"

class PartImportExecuteRequest(BaseModel):
    rows: List[PartItemImportData]

class PartImportExecuteResponse(BaseModel):
    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]


@router.post("/import/parts/preview", response_model=PartImportPreviewResponse)
async def preview_part_import(
    data: PartImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Preview part import from Infor data"""
    try:
        importer = PartImporter()
        preview_result = await importer.preview_import(data.rows, db)

        return PartImportPreviewResponse(
            valid_count=preview_result["valid_count"],
            error_count=preview_result["error_count"],
            duplicate_count=preview_result["duplicate_count"],
            rows=preview_result["rows"]
        )
    except Exception as e:
        logger.error(f"Part preview failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/parts/execute", response_model=PartImportExecuteResponse)
async def execute_part_import(
    data: PartImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Execute part import - create Parts in database"""
    try:
        importer = PartImporter()
        rows_as_dicts = [row.dict() for row in data.rows]
        import_result = await importer.execute_import(rows_as_dicts, db)

        return PartImportExecuteResponse(
            success=import_result["success"],
            created_count=import_result["created_count"],
            updated_count=import_result["updated_count"],
            skipped_count=import_result["skipped_count"],
            errors=import_result["errors"]
        )
    except Exception as e:
        logger.error(f"Part import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**That's it!** Only **~150 lines** of code for a complete importer!

---

## InforImporterBase API Reference

### Abstract Methods (MUST implement)

#### `get_config() -> InforImporterConfig`
Return configuration for field mappings and duplicate checking.

**Example:**
```python
def get_config(self) -> InforImporterConfig:
    return InforImporterConfig(
        entity_name="MaterialItem",
        ido_name="SLItems",
        field_mappings=[
            FieldMapping("Item", "code", required=True),
            FieldMapping("Description", "name", required=True),
            FieldMapping("UnitCost", "cost", transform=lambda x: float(x) if x else 0.0),
        ],
        duplicate_check_field="code"
    )
```

#### `map_row_custom(row, basic_mapped, db) -> Dict`
Custom mapping logic beyond simple field mapping.

**Use Cases:**
- Parse complex fields (e.g., shape from description text)
- Lookup foreign keys (e.g., MaterialGroup from material code)
- Transform data (e.g., unit conversion)
- Detect relationships (e.g., M:N)

**Example:**
```python
async def map_row_custom(self, row, basic_mapped, db):
    custom = {}

    # Parse shape from description
    description = row.get("Description", "")
    if "kulatina" in description.lower():
        custom["shape"] = "round_bar"

    # Lookup MaterialGroup
    material_code = self.extract_material_code(description)
    if material_code:
        group = await db.execute(
            select(MaterialGroup).where(MaterialGroup.code == material_code)
        )
        custom["material_group_id"] = group.scalar_one_or_none()?.id

    return custom
```

#### `create_entity(mapped_data, db) -> T`
Create entity instance from mapped data.

**Example:**
```python
async def create_entity(self, mapped_data, db):
    material_numbers = await NumberGenerator.generate_material_numbers_batch(db, 1)

    return MaterialItem(
        material_number=material_numbers[0],
        code=mapped_data["code"],
        name=mapped_data["name"],
        shape=mapped_data.get("shape"),
        material_group_id=mapped_data.get("material_group_id")
    )
```

#### `check_duplicate(mapped_data, db) -> Optional[T]`
Check if entity already exists.

**Example:**
```python
async def check_duplicate(self, mapped_data, db):
    code = mapped_data.get("code")
    if not code:
        return None

    result = await db.execute(
        select(MaterialItem).where(MaterialItem.code == code)
    )
    return result.scalar_one_or_none()
```

### Optional Methods

#### `update_entity(existing, mapped_data, db) -> None`
Update existing entity (for `duplicate_action='update'`).

**Default:** No-op (logs warning)

**Example:**
```python
async def update_entity(self, existing, mapped_data, db):
    # Only update safe fields (not core identifiers)
    existing.supplier_code = mapped_data.get("supplier_code")
    existing.supplier = mapped_data.get("supplier")
    existing.stock_available = mapped_data.get("stock_available", 0.0)
```

#### `validate_mapped_row(mapped_data, db) -> ValidationResult`
Custom validation beyond required fields.

**Default:** Checks required fields + duplicates

**Example:**
```python
async def validate_mapped_row(self, mapped_data, db):
    # Call base validation first
    result = await super().validate_mapped_row(mapped_data, db)

    # Custom validation
    if not mapped_data.get("shape"):
        result.errors.append("Shape not detected - manual selection required")
        result.is_valid = False
        result.needs_manual_input["shape"] = True

    diameter = mapped_data.get("diameter")
    if diameter is not None and diameter < 0:
        result.errors.append("Diameter must be >= 0")
        result.is_valid = False

    return result
```

---

## FieldMapping Configuration

### Basic Mapping
```python
FieldMapping("Item", "code")  # Infor "Item" → Gestima "code"
```

### Required Fields
```python
FieldMapping("Item", "code", required=True)  # Validation error if missing
```

### Fallback Fields
```python
FieldMapping("UnitMeasure", "unit", fallback_fields=["UM", "Unit"])
# Try "UnitMeasure" first, then "UM", then "Unit"
```

### Transform Function
```python
def parse_bool(value):
    return value in ["Y", "1", "True", "true"]

FieldMapping("IsActive", "is_active", transform=parse_bool)
```

### Complex Example
```python
FieldMapping(
    source_field="WallThickness",
    target_field="wall_thickness",
    required=False,
    transform=lambda x: float(x) if x else None,
    fallback_fields=["WallThick", "Thickness"]
)
```

---

## Multi-Source Imports (M:N)

### Example: Part + Operations

**Config:**
```python
def get_config(self):
    return InforImporterConfig(
        entity_name="Part",
        ido_name="SLItems",  # Primary IDO
        field_mappings=[...],
        additional_idos={
            "operations": "SLOperations"  # Secondary IDO
        }
    )
```

**Custom Mapping:**
```python
async def map_row_custom(self, row, basic_mapped, db):
    custom = {}

    # Get operations data from additional IDO
    item_code = row.get("Item")
    operations_result = await self.client.load_collection(
        ido_name="SLOperations",
        properties=["Operation", "OpDesc", "SetupHours", "RunHours"],
        filter=f"Item = '{item_code}'"
    )

    # Store for later processing in create_entity
    custom["operations_data"] = operations_result["data"]

    return custom
```

**Create Entity:**
```python
async def create_entity(self, mapped_data, db):
    # Create Part
    part = Part(
        part_number=...,
        code=mapped_data["code"],
        name=mapped_data["name"]
    )
    db.add(part)
    await db.flush()  # Get part.id

    # Create Operations (M:N relationship)
    operations_data = mapped_data.get("operations_data", [])
    for op_row in operations_data:
        operation = PartOperation(
            part_id=part.id,
            operation_code=op_row["Operation"],
            description=op_row["OpDesc"],
            setup_hours=op_row["SetupHours"],
            run_hours=op_row["RunHours"]
        )
        db.add(operation)

    return part
```

---

## Testing

### Unit Tests

**File:** `tests/test_infor_part_importer.py`

```python
import pytest
from app.services.infor_part_importer import PartImporter

@pytest.mark.asyncio
async def test_map_row_custom(db_session):
    importer = PartImporter()

    row = {
        "Item": "P-12345",
        "Description": "ASSEMBLY - Main Frame"
    }
    basic_mapped = {"code": "P-12345", "name": "ASSEMBLY - Main Frame"}

    result = await importer.map_row_custom(row, basic_mapped, db_session)

    assert result["part_type"] == "assembly"
    assert result["category_id"] == 1

@pytest.mark.asyncio
async def test_preview_import(db_session):
    importer = PartImporter()

    rows = [
        {"Item": "P-001", "Description": "Part 1"},
        {"Item": "P-002", "Description": "Part 2"},
    ]

    result = await importer.preview_import(rows, db_session)

    assert result["valid_count"] == 2
    assert result["error_count"] == 0
    assert len(result["rows"]) == 2
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_execute_import(db_session, admin_user):
    importer = PartImporter()

    rows = [
        {
            "code": "P-TEST-001",
            "name": "Test Part",
            "drawing_number": "DWG-001",
            "unit": "ks",
            "part_type": "component"
        }
    ]

    result = await importer.execute_import(rows, db_session)

    assert result["success"] is True
    assert result["created_count"] == 1

    # Verify in DB
    part = await db_session.execute(
        select(Part).where(Part.code == "P-TEST-001")
    )
    assert part.scalar_one_or_none() is not None
```

---

## Frontend Component (Optional)

If you want a dedicated UI for Part import (like MaterialImport), create:

**File:** `frontend/src/components/modules/infor/InforPartImportPanel.vue`

Copy structure from `InforMaterialImportPanel.vue` and adjust:
- API endpoints: `/api/infor/import/parts/preview`, `/api/infor/import/parts/execute`
- Field mappings
- Validation display

---

## Performance Tips

1. **Batch NumberGenerator calls**:
   ```python
   # GOOD: Generate all IDs upfront
   numbers = await NumberGenerator.generate_part_numbers_batch(db, len(rows))

   # BAD: Generate one by one in loop
   for row in rows:
       number = await NumberGenerator.generate_part_number(db)
   ```

2. **Preload reference data**:
   ```python
   # Load all MaterialGroups once
   groups = await db.execute(select(MaterialGroup))
   groups_dict = {g.code: g for g in groups.scalars().all()}

   # Then lookup in memory
   group = groups_dict.get(material_code)
   ```

3. **Use transactions**:
   ```python
   async with db.begin():
       # All operations in single transaction
       # Auto-rollback on error
   ```

---

## Troubleshooting

### Import fails with "Transaction already begun"
**Fix:** Don't call `db.begin()` manually - base class handles it.

### Duplicate check not working
**Fix:** Ensure `duplicate_check_field` matches the field name in `mapped_data`, not Infor field name.

### Validation errors not showing
**Fix:** Override `validate_mapped_row()` and call `await super().validate_mapped_row(...)` first.

### Foreign key constraint error
**Fix:** Ensure related entities (MaterialGroup, PriceCategory) exist before import.

---

## Changelog

- **v1.0** (2026-02-03): Initial generic system with MaterialImporter
- **Future**: Add PartImporter, QuoteImporter, OrderImporter examples

---

**Questions?** Check [ADR-031](../ADR/ADR-031-infor-generic-importer.md) for architecture decisions.
