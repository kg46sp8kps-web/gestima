"""GESTIMA - Infor CloudSuite Industrial Integration Router"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.services.infor_api_client import InforAPIClient
from app.services.infor_material_importer import MaterialImporter
from app.services.number_generator import NumberGenerator
from app.database import get_db
from app.models.user import User, UserRole
from app.models.material import MaterialItem
from app.dependencies import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/infor", tags=["infor"])


# === PYDANTIC SCHEMAS FOR MATERIAL IMPORT ===

class ValidationResultSchema(BaseModel):
    is_valid: bool
    is_duplicate: bool
    errors: List[str]
    warnings: List[str]
    needs_manual_group: bool
    needs_manual_shape: bool


class StagedMaterialRowSchema(BaseModel):
    row_index: int
    infor_data: Dict[str, Any]
    mapped_data: Dict[str, Any]
    validation: ValidationResultSchema


class MaterialImportPreviewRequest(BaseModel):
    ido_name: str
    rows: List[Dict[str, Any]]


class MaterialImportPreviewResponse(BaseModel):
    valid_count: int
    error_count: int
    duplicate_count: int
    rows: List[StagedMaterialRowSchema]


class MaterialItemImportData(BaseModel):
    code: str
    name: str
    shape: str
    diameter: Optional[float] = None
    width: Optional[float] = None
    thickness: Optional[float] = None
    wall_thickness: Optional[float] = None
    weight_per_meter: Optional[float] = None
    standard_length: Optional[float] = None
    norms: Optional[str] = None
    supplier_code: Optional[str] = None
    supplier: Optional[str] = None
    stock_available: Optional[float] = 0.0
    material_group_id: int
    price_category_id: int
    duplicate_action: Optional[str] = "skip"  # skip | update


class MaterialImportExecuteRequest(BaseModel):
    rows: List[MaterialItemImportData]


class MaterialImportExecuteResponse(BaseModel):
    success: bool
    created_count: int
    updated_count: int
    skipped_count: int
    errors: List[str]


def get_infor_client() -> InforAPIClient:
    """Dependency pro InforAPIClient s konfigurací ze settings"""

    if not settings.INFOR_API_URL:
        raise HTTPException(
            status_code=501,
            detail="Infor API integration not configured. Set INFOR_API_URL in .env"
        )

    return InforAPIClient(
        base_url=settings.INFOR_API_URL,
        config=settings.INFOR_CONFIG,
        username=settings.INFOR_USERNAME,
        password=settings.INFOR_PASSWORD,
        verify_ssl=False  # Self-signed certs
    )


@router.get("/test-connection")
async def test_connection(
    client: InforAPIClient = Depends(get_infor_client),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Test připojení k Infor API.

    Zkusí:
    1. Získat token
    2. Načíst dostupné konfigurace

    Vrátí status + diagnostické info.
    """
    try:
        # 1. Test tokenu
        token = await client.get_token()

        # 2. Test get configurations
        configs = await client.get_configurations()

        return {
            "status": "ok",
            "connected": True,
            "token_acquired": bool(token),
            "token_preview": f"{token[:20]}..." if token else None,
            "configurations": configs,
            "base_url": settings.INFOR_API_URL,
            "config": settings.INFOR_CONFIG
        }

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {
            "status": "error",
            "connected": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "base_url": settings.INFOR_API_URL,
            "config": settings.INFOR_CONFIG
        }


@router.get("/discover-idos")
async def discover_idos(
    custom_names: Optional[str] = None,
    client: InforAPIClient = Depends(get_infor_client),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Discovery tool - zjistit, které IDO názvy existují.

    Query params:
        custom_names: Čárkou oddělený seznam názvů k vyzkoušení (opcional)

    Příklad:
        GET /api/infor/discover-idos
        GET /api/infor/discover-idos?custom_names=SLItems,Items,ItemMaster
    """
    try:
        # Parse custom names
        names_to_try = None
        if custom_names:
            names_to_try = [n.strip() for n in custom_names.split(",")]

        # Discovery
        results = await client.discover_ido_names(common_names=names_to_try)

        # Rozdělení na existující a neexistující
        found = [name for name, exists in results.items() if exists]
        not_found = [name for name, exists in results.items() if not exists]

        return {
            "status": "ok",
            "found": found,
            "not_found": not_found,
            "total_checked": len(results),
            "found_count": len(found)
        }

    except Exception as e:
        logger.error(f"IDO discovery failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ido/{ido_name}/info")
async def get_ido_info(
    ido_name: str,
    client: InforAPIClient = Depends(get_infor_client),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Získat metadata o IDO - jaké fields má, jejich typy, atd.

    Path params:
        ido_name: Název IDO (např. "SLItems")

    Příklad:
        GET /api/infor/ido/SLItems/info
    """
    try:
        info = await client.get_ido_info(ido_name)
        return {
            "status": "ok",
            "ido_name": ido_name,
            "info": info
        }

    except Exception as e:
        logger.error(f"Failed to get IDO info for {ido_name}: {e}")
        raise HTTPException(status_code=404, detail=f"IDO '{ido_name}' not found or error: {str(e)}")


@router.get("/ido/{ido_name}/data")
async def get_ido_data(
    ido_name: str,
    properties: str,
    filter: Optional[str] = None,
    order_by: Optional[str] = None,
    limit: int = 100,
    load_type: Optional[str] = None,
    bookmark: Optional[str] = None,
    distinct: bool = False,
    client: InforAPIClient = Depends(get_infor_client),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Načíst data z IDO.

    Path params:
        ido_name: Název IDO (např. "SLItems")

    Query params:
        properties: Čárkou oddělený seznam polí (např. "Item,Description,UnitCost")
        filter: WHERE podmínka (např. "Item LIKE 'A%'")
        order_by: Řazení (např. "Item ASC")
        limit: Max počet záznamů (default 100, 0 = unlimited)
        load_type: Type of load - FIRST | NEXT | PREVIOUS | LAST
        bookmark: Bookmark ID from previous response for pagination
        distinct: Use SQL DISTINCT (default false)

    Příklad:
        GET /api/infor/ido/SLItems/data?properties=Item,Description,UnitCost&limit=10
        GET /api/infor/ido/SLItems/data?properties=Item,Description&filter=Item LIKE 'A%'
        GET /api/infor/ido/SLItems/data?properties=Item&limit=100&load_type=NEXT&bookmark=xyz
    """
    try:
        # Parse properties
        props_list = [p.strip() for p in properties.split(",")]

        logger.info(f"GET /ido/{ido_name}/data - properties: {props_list}, filter: {filter}, limit: {limit}, load_type: {load_type}, bookmark: {bookmark}")

        # Load data
        result = await client.load_collection(
            ido_name=ido_name,
            properties=props_list,
            filter=filter,
            order_by=order_by,
            record_cap=limit,
            load_type=load_type,
            bookmark=bookmark,
            distinct=distinct
        )

        data = result["data"]
        response_bookmark = result.get("bookmark")
        has_more = result.get("has_more", False)

        logger.info(f"Loaded {len(data)} records from {ido_name}, bookmark: {response_bookmark}, has_more: {has_more}")

        response = {
            "status": "ok",
            "ido_name": ido_name,
            "properties": props_list,
            "filter": filter,
            "order_by": order_by,
            "count": len(data),
            "data": data,
            "bookmark": response_bookmark,
            "has_more": has_more
        }

        logger.info(f"Returning response with {len(data)} records")
        return response

    except Exception as e:
        logger.error(f"Failed to load data from {ido_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items")
async def get_items(
    item: Optional[str] = None,
    limit: int = 100,
    client: InforAPIClient = Depends(get_infor_client),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Zkratka pro načtení položek/materiálů.

    Automaticky zkusí různé běžné názvy IDO pro položky.

    Query params:
        item: Filtr podle kódu položky (optional)
        limit: Max počet záznamů (default 100)

    Příklad:
        GET /api/infor/items
        GET /api/infor/items?item=ABC123
        GET /api/infor/items?limit=10
    """
    # Běžné názvy IDO pro položky
    possible_ido_names = ["SLItems", "Items", "ItemMaster", "Item"]

    # Zkusit najít fungující IDO
    working_ido = None
    for ido_name in possible_ido_names:
        try:
            await client.get_ido_info(ido_name)
            working_ido = ido_name
            logger.info(f"Found working IDO for items: {ido_name}")
            break
        except Exception:
            continue

    if not working_ido:
        raise HTTPException(
            status_code=404,
            detail=f"Items IDO not found. Tried: {possible_ido_names}. Use /discover-idos to find available IDOs."
        )

    # Načíst data
    try:
        filter_expr = f"Item = '{item}'" if item else None

        result = await client.load_collection(
            ido_name=working_ido,
            properties=["Item", "Description", "UnitCost", "UnitPrice", "UM"],
            filter=filter_expr,
            record_cap=limit
        )

        data = result["data"]

        return {
            "status": "ok",
            "ido_name": working_ido,
            "count": len(data),
            "items": data,
            "bookmark": result.get("bookmark"),
            "has_more": result.get("has_more", False)
        }

    except Exception as e:
        logger.error(f"Failed to load items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/materials/preview", response_model=MaterialImportPreviewResponse)
async def preview_material_import(
    data: MaterialImportPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Preview material import from Infor data.

    Validates rows, detects duplicates, maps fields.
    Returns validation results without creating any records.

    Request:
    {
      "ido_name": "SLItems",
      "rows": [{"Item": "ABC", "Description": "Kulatina D20 1.4301", ...}, ...]
    }

    Response:
    {
      "valid_count": 45,
      "error_count": 5,
      "duplicate_count": 3,
      "rows": [
        {
          "row_index": 0,
          "infor_data": {...},
          "mapped_data": {...},
          "validation": {
            "is_valid": true,
            "is_duplicate": false,
            "errors": [],
            "warnings": [],
            "needs_manual_group": false,
            "needs_manual_shape": false
          }
        }
      ]
    }
    """
    try:
        logger.info(f"📥 Preview request: ido_name={data.ido_name}, rows_count={len(data.rows)}")
        if data.rows:
            logger.info(f"📝 First row sample: {data.rows[0]}")

        # Use generic MaterialImporter
        importer = MaterialImporter()

        # Call generic preview_import method
        preview_result = await importer.preview_import(data.rows, db)

        logger.info(f"✅ Preview result: valid={preview_result['valid_count']}, errors={preview_result['error_count']}, duplicates={preview_result['duplicate_count']}")

        return MaterialImportPreviewResponse(
            valid_count=preview_result["valid_count"],
            error_count=preview_result["error_count"],
            duplicate_count=preview_result["duplicate_count"],
            rows=preview_result["rows"]
        )

    except Exception as e:
        logger.error(f"❌ Preview failed: {e}", exc_info=True)
        logger.error(f"Request data: ido_name={data.ido_name}, rows_count={len(data.rows) if data.rows else 0}")
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/import/materials/test-pattern")
async def test_material_pattern(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Test parsing patterns on single material row (debugging tool).

    Shows detailed breakdown of what was parsed from Description field.

    Request:
    {
      "row": {"Item": "ABC", "Description": "Kulatina D20 1.4301 L6000", ...}
    }

    Response:
    {
      "description": "Kulatina D20 1.4301 L6000",
      "parsed": {
        "shape": "round_bar",
        "shape_matched_pattern": "kulatina",
        "material_code": "1.4301",
        "material_code_matched_pattern": "1\\.\\\\d{4}",
        "diameter": 20.0,
        "diameter_matched_pattern": "D\\\\s*(\\\\d+(?:\\\\.\\\\d+)?)",
        "standard_length": 6000.0,
        "length_matched_pattern": "L(\\\\d+(?:\\\\.\\\\d+)?)"
      },
      "detected": {
        "material_group_id": 5,
        "material_group_name": "Nerezová ocel",
        "price_category_id": 12,
        "price_category_name": "Nerez tyč kruhová"
      },
      "not_found": [
        "width",
        "thickness",
        "wall_thickness"
      ],
      "errors": [],
      "warnings": []
    }
    """
    try:
        row_data = data.get("row", {})
        logger.info(f"🔧 Test pattern for row: {row_data}")

        importer = MaterialImporter()

        item_code = row_data.get("Item", "")
        description = row_data.get("Description", "")

        # Parse dimensions (prioritize Item code as MASTER)
        dimensions = importer.parse_dimensions_from_item_code(item_code)

        # Parse shape (prioritize Item code as MASTER)
        shape = importer.parse_shape_from_item_code(item_code, dimensions)
        shape_source = "Item code (MASTER)" if shape else None

        # Fallback: Try from Description if not found in Item code
        if not shape:
            shape = importer.parse_shape_from_text(description)
            shape_source = "Description (fallback)" if shape else None

        # Fallback dimensions from Description if not found in Item code
        if all(v is None for v in dimensions.values()):
            dimensions = importer.parse_dimensions(description, shape)
            logger.info(f"Using fallback dimensions from Description")

        # Extract material code (prioritize Item code as MASTER)
        # 1. Try W.Nr from Item code (MASTER)
        material_code = importer.extract_w_nr_from_item_code(item_code)
        material_code_source = "Item code (MASTER)" if material_code else None

        # 2. Fallback: Try from Description
        if not material_code:
            material_code = importer.extract_material_code(description)
            material_code_source = "Description (fallback)" if material_code else None

        # Extract surface treatment from Item code
        surface_treatment = importer.extract_surface_treatment(item_code)

        # Detect material group
        material_group_id = await importer.detect_material_group(material_code, db)

        # Get material group name
        material_group_name = None
        if material_group_id:
            from app.models.material import MaterialGroup
            result = await db.execute(
                select(MaterialGroup).where(MaterialGroup.id == material_group_id)
            )
            group = result.scalar_one_or_none()
            if group:
                material_group_name = group.name

        # Detect price category
        price_category_id = await importer.detect_price_category(material_group_id, shape, db)

        # Get price category name
        price_category_name = None
        if price_category_id:
            from app.models.material import MaterialPriceCategory
            result = await db.execute(
                select(MaterialPriceCategory).where(MaterialPriceCategory.id == price_category_id)
            )
            category = result.scalar_one_or_none()
            if category:
                price_category_name = category.name

        # Build response
        parsed = {
            "shape": shape.value if shape else None,
            "material_code": material_code,
            "material_code_source": material_code_source,
            "surface_treatment": surface_treatment,
            **dimensions
        }

        detected = {
            "material_group_id": material_group_id,
            "material_group_name": material_group_name,
            "price_category_id": price_category_id,
            "price_category_name": price_category_name
        }

        not_found = []
        if not shape:
            not_found.append("shape")
        if not material_code:
            not_found.append("material_code")
        if not material_group_id:
            not_found.append("material_group")
        if not price_category_id:
            not_found.append("price_category")
        if not surface_treatment:
            not_found.append("surface_treatment")

        for dim_key, dim_value in dimensions.items():
            if dim_value is None:
                not_found.append(dim_key)

        errors = []
        warnings = []

        if not shape:
            errors.append("Shape not detected - no pattern matched in Description")
        if not material_group_id:
            errors.append(f"MaterialGroup not found for code '{material_code}'" if material_code else "No material code detected")
        if not price_category_id:
            warnings.append("PriceCategory not detected")

        logger.info(f"✅ Test pattern result: shape={shape}, material_code={material_code}, group={material_group_id}, category={price_category_id}")

        return {
            "description": description,
            "parsed": parsed,
            "detected": detected,
            "not_found": not_found,
            "errors": errors,
            "warnings": warnings
        }

    except Exception as e:
        logger.error(f"❌ Test pattern failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Test pattern failed: {str(e)}")


@router.post("/import/materials/execute", response_model=MaterialImportExecuteResponse)
async def execute_material_import(
    data: MaterialImportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """
    Execute material import - create MaterialItems in database.

    Request:
    {
      "rows": [
        {
          "code": "ABC",
          "name": "Kulatina D20 1.4301",
          "shape": "round_bar",
          "diameter": 20.0,
          "material_group_id": 1,
          "price_category_id": 5,
          "duplicate_action": "skip"  # or "update"
        }
      ]
    }

    Response:
    {
      "success": true,
      "created_count": 45,
      "updated_count": 3,
      "skipped_count": 5,
      "errors": []
    }
    """
    try:
        logger.info(f"🚀 Execute request: rows_count={len(data.rows)}")
        if data.rows:
            logger.info(f"📝 First row sample: {data.rows[0].dict()}")

        # Use generic MaterialImporter
        importer = MaterialImporter()

        # Convert Pydantic models to dicts for generic system
        rows_as_dicts = [row.dict() for row in data.rows]

        # Call generic execute_import method
        import_result = await importer.execute_import(rows_as_dicts, db)

        logger.info(
            f"✅ Execute result: created={import_result['created_count']}, "
            f"updated={import_result['updated_count']}, skipped={import_result['skipped_count']}, "
            f"errors={len(import_result['errors'])}"
        )

        if import_result["errors"]:
            logger.error(f"Import errors: {import_result['errors']}")

        return MaterialImportExecuteResponse(
            success=import_result["success"],
            created_count=import_result["created_count"],
            updated_count=import_result["updated_count"],
            skipped_count=import_result["skipped_count"],
            errors=import_result["errors"]
        )

    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
