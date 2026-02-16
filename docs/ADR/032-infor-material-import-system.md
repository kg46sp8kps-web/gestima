# ADR-032: Infor Material Import System with Generic Base

**Status:** Accepted
**Date:** 2026-02-03
**Author:** Claude + Lofas

## Context

GESTIMA needs to import material catalog data from Infor CloudSuite Industrial (SyteLine) ERP system. The integration must:

1. **Load source data** from Infor IDOs (Intelligent Data Objects)
2. **Parse and map** fields from Infor format → Gestima MaterialItem schema
3. **Auto-detect** MaterialGroup (from material codes like 1.4301, S235, C45)
4. **Auto-detect** StockShape (from descriptions: "tyč kruhová D20", "plech t5")
5. **Validate** required fields and business rules
6. **Handle duplicates** (skip or update catalog fields only)
7. **Provide UI** for preview, manual corrections, and batch import

### Existing Approaches Considered

1. **Direct API mapping** - Tightly coupled, hard to maintain
2. **Entity-specific importers** - Code duplication across entities
3. **Generic base system** ✅ - Reusable, config-driven, extensible

## Decision

Implement a **generic import system** with `InforImporterBase<T>` base class that provides:

### 1. Generic Base Class (`InforImporterBase<T>`)

```python
class InforImporterBase(ABC, Generic[T]):
    """Reusable base for ALL Infor imports (materials, customers, orders, etc.)"""

    @abstractmethod
    def get_config(self) -> InforImporterConfig
        """Field mappings, IDO names, duplicate check field"""

    @abstractmethod
    async def map_row_custom(self, row, basic_mapped, db) -> Dict
        """Entity-specific mapping logic (shape parsing, group detection)"""

    @abstractmethod
    async def create_entity(self, mapped_data, db) -> T
        """Create entity instance with generated IDs"""

    @abstractmethod
    async def check_duplicate(self, mapped_data, db) -> Optional[T]
        """Check if entity already exists"""

    # Provided by base:
    async def preview_import(rows, db) -> ValidationResults
    async def execute_import(rows, db) -> ImportStats
    async def validate_mapped_row(mapped, db) -> ValidationResult
```

### 2. Material-Specific Importer (`MaterialImporter`)

```python
class MaterialImporter(InforImporterBase[MaterialItem]):
    """Concrete importer for MaterialItem from Infor SLItems"""

    def get_config(self) -> InforImporterConfig:
        return InforImporterConfig(
            entity_name="MaterialItem",
            ido_name="SLItems",
            field_mappings=[
                FieldMapping("Item", "code", required=True),
                FieldMapping("Description", "name", required=True),
                FieldMapping("Diameter", "diameter"),
                # ... 12 more fields
            ],
            duplicate_check_field="code"
        )

    async def map_row_custom(self, row, basic_mapped, db):
        """Parse shape, detect MaterialGroup, detect PriceCategory"""
        description = row.get("Description", "")

        # 1. Parse shape from description
        shape = self.parse_shape_from_text(description)

        # 2. Extract material code (1.4301, S235, C45)
        material_code = self.extract_material_code(description)

        # 3. Auto-detect MaterialGroup from material_code
        material_group_id = await self.detect_material_group(material_code, db)

        # 4. Auto-detect PriceCategory from group + shape
        price_category_id = await self.detect_price_category(
            material_group_id, shape, db
        )

        # 5. Parse dimensions (D20 → diameter=20.0)
        dims = self.parse_dimensions(description, shape)

        return {
            "shape": shape,
            "material_group_id": material_group_id,
            "price_category_id": price_category_id,
            **dims
        }
```

### 3. Shape Detection Patterns

```python
SHAPE_PATTERNS = {
    StockShape.ROUND_BAR: [
        r"tyč\s+kruhov[áý]",  # tyč kruhová
        r"kulatina",           # kulatina
        r"Ø\s*\d+",           # Ø20
        r"D\s*\d+",           # D20
    ],
    StockShape.PLATE: [
        r"plech",
        r"plate",
        r"t\s*\d+",           # t5
        r"tl\.?\s*\d+",       # tl.5
    ],
    StockShape.TUBE: [
        r"trubka",
        r"tube",
        r"rour?a",
    ],
    # ... 5 more shapes
}
```

### 4. Material Code Extraction

```python
MATERIAL_CODE_PATTERNS = [
    r"1\.\d{4}",    # W.Nr (1.4301, 1.4571)
    r"S\d{3}",      # EN standards (S235, S355)
    r"C\d{2,3}",    # Carbon steel (C45, C20)
    r"\d{5}",       # ČSN (11375)
    r"[67]\d{3}",   # Aluminum (6061, 7075)
]
```

### 5. MaterialGroup Detection

```python
async def detect_material_group(self, material_code: str, db) -> Optional[int]:
    """Match material code → MaterialNorm → MaterialGroup"""
    norm = await db.execute(
        select(MaterialNorm).where(
            (MaterialNorm.w_nr == material_code) |
            (MaterialNorm.en_iso == material_code) |
            (MaterialNorm.csn == material_code) |
            (MaterialNorm.aisi == material_code)
        ).limit(1)
    )
    return norm.material_group_id if norm else None
```

### 6. PriceCategory Detection

```python
async def detect_price_category(
    self, material_group_id: int, shape: StockShape, db
) -> Optional[int]:
    """Match MaterialGroup + shape → PriceCategory"""
    categories = await db.execute(
        select(MaterialPriceCategory)
        .where(MaterialPriceCategory.material_group_id == material_group_id)
    )

    # Match shape from category name/code
    shape_keywords = {
        StockShape.ROUND_BAR: ["kruhov", "round", "kulatina"],
        StockShape.PLATE: ["plech", "plate"],
        # ... other shapes
    }

    for category in categories:
        if any(kw in category.name.lower() for kw in shape_keywords[shape]):
            return category.id

    return categories[0].id  # Fallback to first
```

### 7. API Endpoints

```python
@router.post("/api/infor/import/materials/preview")
async def preview_material_import(data: MaterialImportPreviewRequest):
    """
    Validate rows without creating entities.

    Request: {ido_name, rows: [...]}
    Response: {valid_count, error_count, duplicate_count, rows: [...]}
    """
    importer = MaterialImporter()
    return await importer.preview_import(data.rows, db)

@router.post("/api/infor/import/materials/execute")
async def execute_material_import(data: MaterialImportExecuteRequest):
    """
    Create MaterialItems from validated staging data.

    Request: {rows: [{...mapped_data, duplicate_action: 'skip'|'update'}]}
    Response: {success, created_count, updated_count, skipped_count, errors}
    """
    importer = MaterialImporter()
    return await importer.execute_import(data.rows, db)

@router.post("/api/infor/import/materials/test-pattern")
async def test_material_pattern(data: dict):
    """
    Debug endpoint - test parsing patterns on single row.

    Returns: {description, parsed: {...}, detected: {...}, not_found: [...]}
    """
    importer = MaterialImporter()
    # ... detailed breakdown for debugging
```

### 8. Frontend UI (`InforMaterialImportPanel.vue`)

**Split-pane layout:**
- **LEFT panel**: Load Infor source data
  - IDO Name input + Fetch Fields button
  - Field chooser (collapsible dropdown with search)
  - Filter (WHERE clause) + Limit
  - Load Data button
  - Data table with checkboxes + toolbar:
    - Stage Selected (purple accent, first button)
    - Select All / Unselect All
    - Clear Data
- **RIGHT panel**: Staging & validation
  - Validation summary badges (valid/errors/duplicates)
  - Staging table with:
    - Status icons (CheckCircle / AlertTriangle / XCircle)
    - All mapped fields (code, name, shape, dimensions, group, category, supplier)
    - Errors column
  - Toolbar:
    - Select All / Unselect All
    - Test Pattern (opens debug modal)
    - Clear Staging
  - Import button (disabled if errors)

**Pattern Testing Modal:**
- Original Description field
- Parsed results (shape, material_code, dimensions)
- Auto-detected (material_group, price_category)
- Not found fields
- Errors/Warnings

**UI Features:**
- All Lucide icons (no emojis)
- Icon-only buttons with tooltips
- Transparent button backgrounds (hover shows bg)
- Design System v4.0 tokens
- Resizable split panels

### 9. Validation Rules

```python
async def validate_mapped_row(self, mapped_data: Dict, db) -> ValidationResult:
    result = ValidationResult()

    # Required fields
    if not mapped_data.get("shape"):
        result.errors.append("Shape not detected - manual selection required")
        result.is_valid = False
        result.needs_manual_input["shape"] = True

    if not mapped_data.get("material_group_id"):
        result.errors.append("MaterialGroup not detected - manual selection required")
        result.is_valid = False
        result.needs_manual_input["material_group_id"] = True

    # Optional warning
    if not mapped_data.get("price_category_id"):
        result.warnings.append("PriceCategory not detected")
        result.needs_manual_input["price_category_id"] = True

    # Dimension validation
    for dim in ["diameter", "width", "thickness"]:
        if mapped_data.get(dim) is not None and float(mapped_data[dim]) < 0:
            result.errors.append(f"Invalid {dim}: must be >= 0")
            result.is_valid = False

    # Check duplicates
    existing = await self.check_duplicate(mapped_data, db)
    if existing:
        result.is_duplicate = True
        result.warnings.append(f"Material with code '{mapped_data['code']}' already exists")

    return result
```

### 10. Import Execution

```python
async def execute_import(self, rows: List[Dict], db: AsyncSession) -> Dict:
    created = []
    updated = []
    skipped = []
    errors = []

    try:
        async with db.begin():
            # Generate material_numbers in batch (efficient)
            material_numbers = await NumberGenerator.generate_material_numbers_batch(
                db, len([r for r in rows if r.get('duplicate_action') != 'skip'])
            )

            for i, row_data in enumerate(rows):
                existing = await self.check_duplicate(row_data, db)

                if existing:
                    if row_data.get('duplicate_action') == 'skip':
                        skipped.append(row_data['code'])
                        continue
                    elif row_data.get('duplicate_action') == 'update':
                        # Update ONLY catalog fields
                        existing.supplier_code = row_data.get('supplier_code')
                        existing.supplier = row_data.get('supplier')
                        existing.stock_available = row_data.get('stock_available', 0.0)
                        updated.append(row_data['code'])
                        continue

                # Create new entity
                new_item = await self.create_entity(row_data, db)
                db.add(new_item)
                created.append(new_item)

            await db.commit()

        return {
            "success": True,
            "created_count": len(created),
            "updated_count": len(updated),
            "skipped_count": len(skipped),
            "errors": errors
        }
    except Exception as e:
        await db.rollback()
        raise
```

## Consequences

### Positive

1. **Reusability** - Base class can be reused for ANY Infor entity (customers, orders, operations)
2. **Config-driven** - Field mappings in simple config, no code duplication
3. **Smart auto-detection** - MaterialGroup and PriceCategory detected from Description
4. **Shape parsing** - Intelligent regex patterns for Czech/English material descriptions
5. **Validation-first** - Preview before import, no surprises
6. **Batch efficiency** - Material numbers generated in batch (not one-by-one)
7. **Safe updates** - Duplicates only update catalog fields (supplier, stock), never core fields
8. **Debugging** - Pattern Test modal for troubleshooting parsing logic
9. **Extensible** - Easy to add new importers (CustomerImporter, OrderImporter, etc.)
10. **Clean UI** - Lucide icons, Design System v4.0 tokens, responsive split-pane

### Negative

1. **Regex maintenance** - Shape patterns need updates as new formats appear
2. **MaterialNorm dependency** - Requires MaterialNorm table to be populated
3. **Generic base learning curve** - Developers need to understand base/subclass pattern
4. **Pattern false positives** - "D20" in "MODEL D2000" might be misdetected as diameter

### Neutral

1. **Manual fallback** - If auto-detection fails, user MUST manually select (via future dropdown)
2. **Transaction size** - Large imports (1000+ rows) use single transaction (all-or-nothing)
3. **Duplicate handling** - Currently: skip or update - no "replace" option

## Implementation Files

**Backend:**
- `app/services/infor_importer_base.py` (250 lines) - Generic base
- `app/services/infor_material_importer_v2.py` (358 lines) - Material-specific
- `app/routers/infor_router.py` (+180 lines) - API endpoints

**Frontend:**
- `frontend/src/components/modules/InforAdminModule.vue` (+20 lines) - Import tab
- `frontend/src/components/modules/infor/InforMaterialImportPanel.vue` (1398 lines) - Main UI
- `frontend/src/types/infor.ts` (80 lines) - TypeScript types

**Total:** ~2286 lines (including tests and docs)

## Developer Guide

To add a new importer (e.g., CustomerImporter):

1. **Subclass `InforImporterBase<Customer>`**
2. **Implement 5 abstract methods:**
   - `get_config()` - Field mappings
   - `map_row_custom()` - Custom logic
   - `create_entity()` - Entity instantiation
   - `check_duplicate()` - Duplicate check
   - `update_entity()` (optional) - Update logic
3. **Add API endpoints** in `infor_router.py`
4. **Create UI component** (copy InforMaterialImportPanel template)
5. **Write tests** for parsing and validation

Full guide: [docs/guides/INFOR-IMPORTER-GUIDE.md](../guides/INFOR-IMPORTER-GUIDE.md)

## Testing

End-to-end test:
1. Load 10 rows from Infor SLItems
2. Verify shape detection (8/10 success)
3. Verify MaterialGroup detection (7/10 success)
4. Manually fix 3 rows (missing shape/group)
5. Handle 1 duplicate (skip)
6. Execute import
7. Verify: 8 created, 0 updated, 1 skipped, 1 error

## Future Enhancements

1. **Manual dropdowns** - Select shape/group/category when auto-detection fails
2. **Saved templates** - Store field mapping configs per IDO
3. **Batch actions** - "Apply to all" for shape/group assignment
4. **Import history** - Audit log with rollback capability
5. **Incremental sync** - Periodic updates from Infor (delta changes only)
6. **PriceCategory manual selection** - Currently auto-only
7. **CSV export** - Export validation errors for review

## Related ADRs

- [ADR-017: 8-Digit Entity Numbering](./017-8digit-entity-numbering.md) - Material number generation
- [ADR-019: Material Catalog Smart Lookup](./019-material-catalog-smart-lookup.md) - Material selection
- [ADR-031: Module Defaults Persistence](./031-module-defaults-persistence.md) - UI state

## References

- Infor API Client: `app/services/infor_api_client.py`
- Material Models: `app/models/material.py`
- NumberGenerator: `app/services/number_generator.py`
- Design System: [docs/reference/DESIGN-SYSTEM.md](../reference/DESIGN-SYSTEM.md)
