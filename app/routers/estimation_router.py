"""GESTIMA - Manual Time Estimation Router (Phase 2-3: ML Training Data Collection)

Provides API endpoints for manual time estimation and ML training data collection.

Router: /api/estimation/
"""

from pathlib import Path
from datetime import datetime
from typing import List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import io
import csv
import numpy as np

from app.database import async_session
from app.models.turning_estimation import TurningEstimation
from app.models.milling_estimation import MillingEstimation
from app.schemas.geometry_features import GeometryFeatures
from app.services.geometry_feature_extractor import GeometryFeatureExtractor
from app.services.pdf_vision_parser import PDFVisionParser
from app.services.machining_time_calculator import MachiningTimeCalculator

router = APIRouter(prefix="/api/estimation", tags=["estimation"])

STEP_UPLOAD_DIR = Path("uploads/drawings/")
DRAWINGS_DIR = Path("uploads/drawings/")
PDF_MAPPING_FILE = Path("uploads/drawings/step_pdf_mapping.json")
ROT_THRESHOLD = 0.6
MATERIAL_CODE_DEFAULT = "20910000"

# Load PDF mapping on startup
_pdf_mapping: dict[str, str] = {}
if PDF_MAPPING_FILE.exists():
    import json
    with open(PDF_MAPPING_FILE, 'r', encoding='utf-8') as f:
        _pdf_mapping = json.load(f)


# ========== PYDANTIC SCHEMAS ==========

class EstimationRecordResponse(BaseModel):
    """Response schema for estimation records"""
    id: int
    filename: str
    part_type: str
    extraction_timestamp: datetime
    part_volume_mm3: float
    removal_ratio: float
    surface_area_mm2: float
    bbox_x_mm: float
    bbox_y_mm: float
    bbox_z_mm: float
    max_dimension_mm: float
    rotational_score: float
    cylindrical_surface_ratio: float
    planar_surface_ratio: float
    material_group_code: str
    material_machinability_index: float
    validation_status: str
    corrected_material_code: Optional[str] = None
    corrected_bbox_x_mm: Optional[float] = None
    corrected_bbox_y_mm: Optional[float] = None
    corrected_bbox_z_mm: Optional[float] = None
    corrected_part_type: Optional[str] = None
    corrected_stock_type: Optional[str] = None
    corrected_stock_diameter: Optional[float] = None
    corrected_stock_length: Optional[float] = None
    correction_notes: Optional[str] = None
    validated_by_user_id: Optional[int] = None
    validation_date: Optional[datetime] = None
    auto_estimated_time_min: Optional[float] = None
    auto_estimate_date: Optional[datetime] = None
    estimated_time_min: Optional[float] = None
    correction_reason: Optional[str] = None
    estimated_by_user_id: Optional[int] = None
    estimation_date: Optional[datetime] = None
    actual_time_min: Optional[float] = None
    actual_time_source: Optional[str] = None
    actual_time_date: Optional[datetime] = None
    data_source: Optional[str] = None
    confidence: Optional[float] = None
    needs_manual_review: Optional[bool] = None
    decision_log: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ManualEstimateRequest(BaseModel):
    """Request body for manual time estimate"""
    estimated_time_min: float = Field(gt=0, description="Estimated machining time in minutes")


class RecalculateTimeRequest(BaseModel):
    """Request body for recalculating times with different parameters"""
    material_code: str = Field(description="Material code (e.g., 1.4305)")
    speed_mode: Literal["low", "mid", "high"] = Field(default="mid", description="Cutting speed mode")


class SimilarPartResponse(BaseModel):
    """Response schema for similar parts"""
    id: int
    filename: str
    part_type: str
    rotational_score: float
    estimated_time_min: Optional[float]
    similarity_score: float = Field(ge=0, le=1)


# ========== HELPER FUNCTIONS ==========

async def get_db() -> AsyncSession:
    """Dependency for database session"""
    async with async_session() as session:
        yield session


def model_to_dict(record) -> dict:
    """Convert SQLAlchemy model instance to dict (all 79 features)"""
    return {c.name: getattr(record, c.name) for c in record.__table__.columns}


def calc_euclidean_distance(dict1: dict, dict2: dict) -> float:
    """Calculate normalized Euclidean distance between two feature vectors"""
    feature_cols = [
        "part_volume_mm3", "removal_ratio", "surface_area_mm2",
        "bbox_x_mm", "bbox_y_mm", "bbox_z_mm", "max_dimension_mm",
        "rotational_score", "cylindrical_surface_ratio", "planar_surface_ratio",
        "material_machinability_index", "feature_density",
        "aspect_ratio_xy", "edge_type_diversity", "surface_type_diversity"
    ]
    vec1 = np.array([dict1[col] for col in feature_cols if col in dict1])
    vec2 = np.array([dict2[col] for col in feature_cols if col in dict2])
    std_dev = np.std(vec1) + 1e-6
    return float(np.linalg.norm((vec1 - vec2) / std_dev))


# ========== API ENDPOINTS ==========

@router.post("/extract-features/{filename}", response_model=EstimationRecordResponse)
async def extract_features_endpoint(
    filename: str,
    material_code: str = Query(default=MATERIAL_CODE_DEFAULT),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract features with AI Vision as PRIMARY source, OCCT for exact dimensions.

    Simplified workflow:
    1. AI Vision parsing (PDF) - part_type, material, stock dimensions (ALWAYS CORRECT)
    2. OCCT extraction (STEP) - exact part dimensions for validation/comparison
    3. Combine: Vision classification + OCCT exact geometry
    4. Save with metadata (data_source, confidence, dimension_match)
    """
    step_path = STEP_UPLOAD_DIR / filename
    if not step_path.exists():
        raise HTTPException(status_code=404, detail=f"STEP file not found: {filename}")

    # Check for PDF drawing (multiple naming patterns)
    base_name = filename.replace('.ipt.step', '').replace('.step', '').replace('.STEP', '')
    pdf_patterns = [
        f"{base_name}.pdf",
        f"{base_name}.idw_Gelso.pdf",
        f"{base_name}.idw.pdf",
    ]
    pdf_path = None
    for pattern in pdf_patterns:
        candidate = DRAWINGS_DIR / pattern
        if candidate.exists():
            pdf_path = candidate
            break

    try:
        # 1. AI VISION PARSING (PRIMARY - always correct!)
        if not pdf_path or not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF drawing not found for {filename}")

        parser = PDFVisionParser()
        vision_data = parser.parse_drawing(pdf_path)

        if "error" in vision_data:
            raise HTTPException(status_code=500, detail=f"Vision parsing failed: {vision_data['error']}")

        # 2. OCCT EXTRACTION (for exact dimensions only)
        extractor = GeometryFeatureExtractor()
        occt_features = extractor.extract_features(step_path, material_code)

        # 3. COMBINE: Vision classification + OCCT geometry
        feature_dict = occt_features.model_dump(exclude={"extraction_timestamp"})
        # Parse timestamp (handle Z suffix)
        timestamp_str = occt_features.extraction_timestamp.replace('Z', '+00:00')
        feature_dict["extraction_timestamp"] = datetime.fromisoformat(timestamp_str)

        # Parse Vision operations (NEW FORMAT - no times, just geometry)
        vision_part_type = vision_data.get("part_type", "ROT")
        vision_material_code = vision_data.get("material_code", "Unknown")
        vision_stock_type = vision_data.get("stock_type", "cylinder")
        vision_stock_dims = vision_data.get("stock_dims", "Unknown")
        vision_operations = vision_data.get("operations", [])
        vision_notes = vision_data.get("notes", "")

        # Calculate times using cutting conditions catalog
        calculator = MachiningTimeCalculator()
        time_results = calculator.calculate_times(
            operations=vision_operations,
            material_code=vision_material_code,
            speed_mode="mid"  # Default to mid speed
        )

        feature_dict["part_type"] = vision_part_type
        # Material mapping (Vision code → internal 8-digit code)
        # TODO: Add proper material mapping table
        feature_dict["material_group_code"] = material_code  # Default for now

        # Store calculated time estimate
        feature_dict["auto_estimated_time_min"] = time_results["total_time_min"]
        feature_dict["auto_estimate_date"] = datetime.utcnow()

        # Store stock dimensions for validation
        feature_dict["corrected_stock_type"] = vision_stock_type
        # Parse stock_dims if format is "Ø20×10.2mm"
        if "Ø" in vision_stock_dims and "×" in vision_stock_dims:
            try:
                parts = vision_stock_dims.replace("mm", "").replace("Ø", "").split("×")
                feature_dict["corrected_stock_diameter"] = float(parts[0])
                feature_dict["corrected_stock_length"] = float(parts[1])
            except:
                pass

        # Metadata
        feature_dict["data_source"] = "vision_catalog_calculated"
        feature_dict["confidence"] = vision_data.get("confidence", 0.0)
        feature_dict["needs_manual_review"] = vision_data.get("confidence", 0) < 0.7

        # Store Vision operations + calculated times in decision_log
        import json
        feature_dict["decision_log"] = json.dumps({
            "vision_raw": vision_data,  # Operations from Vision (geometry only)
            "calculated_times": time_results,  # Times calculated from catalog
            "cutting_speed_mode": "mid",
            "occt_bbox": {
                "x": round(occt_features.bbox_x_mm, 2),
                "y": round(occt_features.bbox_y_mm, 2),
                "z": round(occt_features.bbox_z_mm, 2)
            },
            "summary": (
                f"Machining: {time_results['machining_time_min']:.1f} min | "
                f"Setup: {time_results['setup_time_min']:.1f} min | "
                f"Inspection: {time_results['inspection_time_min']:.1f} min | "
                f"Total: {time_results['total_time_min']:.1f} min | "
                f"Part: {vision_part_type} | Material: {vision_material_code} | "
                f"Operations: {len(vision_operations)} steps"
            )
        }, indent=2)

        # 4. SAVE TO DATABASE (UPSERT: update if exists, insert if not)
        is_turning = (vision_part_type == "ROT")
        Model = TurningEstimation if is_turning else MillingEstimation

        # Check if record already exists
        existing_query = select(Model).where(Model.filename == filename)
        existing_result = await db.execute(existing_query)
        existing_record = existing_result.scalar_one_or_none()

        if existing_record:
            # UPDATE existing record (keep user corrections if present)
            for key, value in feature_dict.items():
                # Don't overwrite user corrections (estimated_time_min, correction_notes, etc.)
                if key in ["estimated_time_min", "estimated_by_user_id", "estimation_date",
                          "correction_notes", "correction_reason", "validated_by_user_id", "validation_date"]:
                    continue
                setattr(existing_record, key, value)

            # Always update extraction timestamp and Vision metadata
            existing_record.extraction_timestamp = datetime.utcnow()
            existing_record.data_source = feature_dict["data_source"]
            existing_record.confidence = feature_dict["confidence"]
            existing_record.needs_manual_review = feature_dict["needs_manual_review"]
            existing_record.decision_log = feature_dict["decision_log"]

            await db.commit()
            await db.refresh(existing_record)
            return EstimationRecordResponse.model_validate(existing_record)
        else:
            # INSERT new record
            record = Model(**feature_dict)
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return EstimationRecordResponse.model_validate(record)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.get("/pending-estimates", response_model=List[EstimationRecordResponse])
async def get_pending_estimates(
    part_type: Optional[Literal["ROT", "PRI"]] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """List parts without manual time estimates (estimated_time_min IS NULL)"""
    try:
        records = []
        if part_type in ["ROT", None]:
            turning_query = select(TurningEstimation).where(TurningEstimation.estimated_time_min.is_(None))
            turning_result = await db.execute(turning_query)
            records.extend(turning_result.scalars().all())
        if part_type in ["PRI", None]:
            milling_query = select(MillingEstimation).where(MillingEstimation.estimated_time_min.is_(None))
            milling_result = await db.execute(milling_query)
            records.extend(milling_result.scalars().all())
        return [EstimationRecordResponse.model_validate(r) for r in records]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.patch("/manual-estimate/{record_id}", response_model=EstimationRecordResponse)
async def submit_manual_estimate(
    record_id: int,
    estimate: ManualEstimateRequest,
    part_type: Literal["ROT", "PRI"] = Query(description="Part type"),
    user_id: int = Query(default=1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Submit manual time estimate for a part"""
    Model = TurningEstimation if part_type == "ROT" else MillingEstimation
    try:
        query = select(Model).where(Model.id == record_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail=f"{part_type} record ID={record_id} not found")
        record.estimated_time_min = estimate.estimated_time_min
        record.estimated_by_user_id = user_id
        record.estimation_date = datetime.utcnow()
        await db.commit()
        await db.refresh(record)
        return EstimationRecordResponse.model_validate(record)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.post("/import-actual-times")
async def import_actual_times(
    file: UploadFile = File(..., description="CSV file: filename, actual_time_min"),
    db: AsyncSession = Depends(get_db)
):
    """Import actual machining times from CSV (ground truth from ERP/machine logs)"""
    try:
        contents = await file.read()
        csv_reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))
        success_count = 0
        fail_count = 0
        errors = []
        for row in csv_reader:
            filename = row.get("filename")
            actual_time_str = row.get("actual_time_min")
            if not filename or not actual_time_str:
                errors.append(f"Missing fields: {row}")
                fail_count += 1
                continue
            try:
                actual_time = float(actual_time_str)
            except ValueError:
                errors.append(f"Invalid time for {filename}: {actual_time_str}")
                fail_count += 1
                continue
            turning_query = select(TurningEstimation).where(TurningEstimation.filename == filename)
            turning_result = await db.execute(turning_query)
            turning_record = turning_result.scalar_one_or_none()
            milling_record = None
            if not turning_record:
                milling_query = select(MillingEstimation).where(MillingEstimation.filename == filename)
                milling_result = await db.execute(milling_query)
                milling_record = milling_result.scalar_one_or_none()
            record = turning_record or milling_record
            if record:
                record.actual_time_min = actual_time
                record.actual_time_source = "CSV import"
                record.actual_time_date = datetime.utcnow()
                success_count += 1
            else:
                errors.append(f"Record not found: {filename}")
                fail_count += 1
        await db.commit()
        return {"success": success_count, "failed": fail_count, "errors": errors[:10]}
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/recalculate-times/{record_id}")
async def recalculate_times(
    record_id: int,
    request: RecalculateTimeRequest,
    part_type: Literal["ROT", "PRI"] = Query(description="Part type"),
    db: AsyncSession = Depends(get_db)
):
    """Recalculate machining times with different material/speed mode"""
    Model = TurningEstimation if part_type == "ROT" else MillingEstimation
    try:
        # Get record with Vision operations
        query = select(Model).where(Model.id == record_id)
        result = await db.execute(query)
        record = result.scalar_one_or_none()

        if not record:
            raise HTTPException(status_code=404, detail=f"{part_type} record ID={record_id} not found")

        # Parse decision_log to get Vision operations
        if not record.decision_log:
            raise HTTPException(status_code=400, detail="No Vision operations found - run AI Vision Extract first")

        import json
        decision_data = json.loads(record.decision_log)
        vision_operations = decision_data.get("vision_raw", {}).get("operations", [])

        if not vision_operations:
            raise HTTPException(status_code=400, detail="No operations found in Vision data")

        # Recalculate times with new parameters
        calculator = MachiningTimeCalculator()
        time_results = calculator.calculate_times(
            operations=vision_operations,
            material_code=request.material_code,
            speed_mode=request.speed_mode
        )

        # Update decision_log with new calculated times
        decision_data["calculated_times"] = time_results
        decision_data["cutting_speed_mode"] = request.speed_mode
        decision_data["summary"] = (
            f"Machining: {time_results['machining_time_min']:.1f} min | "
            f"Setup: {time_results['setup_time_min']:.1f} min | "
            f"Inspection: {time_results['inspection_time_min']:.1f} min | "
            f"Total: {time_results['total_time_min']:.1f} min | "
            f"Material: {request.material_code} | Speed: {request.speed_mode}"
        )

        record.decision_log = json.dumps(decision_data, indent=2)
        record.auto_estimated_time_min = time_results["total_time_min"]

        await db.commit()
        await db.refresh(record)

        return EstimationRecordResponse.model_validate(record)

    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Recalculation failed: {str(e)}")


@router.get("/export-training-data")
async def export_training_data(
    part_type: Optional[Literal["ROT", "PRI"]] = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    """Export training data as CSV (all 79 features + estimated_time_min)"""
    try:
        records = []
        if part_type in ["ROT", None]:
            turning_query = select(TurningEstimation).where(TurningEstimation.estimated_time_min.isnot(None))
            turning_result = await db.execute(turning_query)
            records.extend([model_to_dict(r) for r in turning_result.scalars().all()])
        if part_type in ["PRI", None]:
            milling_query = select(MillingEstimation).where(MillingEstimation.estimated_time_min.isnot(None))
            milling_result = await db.execute(milling_query)
            records.extend([model_to_dict(r) for r in milling_result.scalars().all()])
        if not records:
            raise HTTPException(status_code=404, detail="No training data (no manual estimates yet)")
        output = io.StringIO()
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=training_data_{part_type or 'all'}.csv"}
        )
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/pdf-url/{filename}")
async def get_pdf_url(filename: str):
    """Get PDF URL for STEP filename using mapping"""
    pdf_filename = _pdf_mapping.get(filename)
    if not pdf_filename:
        raise HTTPException(status_code=404, detail=f"No PDF mapping found for {filename}")

    pdf_path = DRAWINGS_DIR / pdf_filename
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_filename}")

    return {"pdf_url": f"/uploads/drawings/{pdf_filename}", "pdf_filename": pdf_filename}


@router.get("/similar-parts/{record_id}", response_model=List[SimilarPartResponse])
async def find_similar_parts(
    record_id: int,
    part_type: Literal["ROT", "PRI"] = Query(description="Part type"),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """Find similar parts using Euclidean distance in feature space"""
    Model = TurningEstimation if part_type == "ROT" else MillingEstimation
    try:
        target_query = select(Model).where(Model.id == record_id)
        target_result = await db.execute(target_query)
        target_record = target_result.scalar_one_or_none()
        if not target_record:
            raise HTTPException(status_code=404, detail=f"{part_type} record ID={record_id} not found")
        target_dict = model_to_dict(target_record)
        candidates_query = select(Model).where(
            Model.id != record_id,
            Model.estimated_time_min.isnot(None)
        )
        candidates_result = await db.execute(candidates_query)
        candidates = candidates_result.scalars().all()
        if not candidates:
            return []
        similarities = []
        for candidate in candidates:
            candidate_dict = model_to_dict(candidate)
            distance = calc_euclidean_distance(target_dict, candidate_dict)
            similarity_score = min(distance / 10.0, 1.0)
            similarities.append({
                "id": candidate.id,
                "filename": candidate.filename,
                "part_type": candidate.part_type,
                "rotational_score": candidate.rotational_score,
                "estimated_time_min": candidate.estimated_time_min,
                "similarity_score": similarity_score
            })
        similarities.sort(key=lambda x: x["similarity_score"])
        return [SimilarPartResponse(**s) for s in similarities[:limit]]
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


# ========== NEW ENDPOINTS (Phase 2-3) ==========


class ValidationRequest(BaseModel):
    """Request body for feature validation"""
    corrected_material_code: Optional[str] = Field(None, min_length=8, max_length=20)
    corrected_bbox_x_mm: Optional[float] = Field(None, gt=0)
    corrected_bbox_y_mm: Optional[float] = Field(None, gt=0)
    corrected_bbox_z_mm: Optional[float] = Field(None, gt=0)
    corrected_part_type: Optional[Literal["ROT", "PRI"]] = None
    correction_notes: Optional[str] = Field(None, max_length=500)


class FinalizeEstimateRequest(BaseModel):
    """Request body for finalizing time estimate with full corrections"""
    # Part classification
    corrected_part_type: Optional[Literal["ROT", "PRI"]] = None
    corrected_stock_type: Optional[Literal["cylinder", "box", "tube"]] = None

    # Stock dimensions
    corrected_stock_diameter: Optional[float] = Field(None, gt=0, description="Stock diameter (mm) for cylinder/tube")
    corrected_stock_length: Optional[float] = Field(None, gt=0, description="Stock length (mm)")
    corrected_bbox_x_mm: Optional[float] = Field(None, gt=0, description="Stock width X (mm) for box")
    corrected_bbox_y_mm: Optional[float] = Field(None, gt=0, description="Stock width Y (mm) for box")
    corrected_bbox_z_mm: Optional[float] = Field(None, gt=0, description="Stock height Z (mm)")

    # Material
    corrected_material_code: Optional[str] = Field(None, min_length=8, max_length=20)

    # Time breakdown
    estimated_roughing_time_min: Optional[float] = Field(None, ge=0, description="Roughing time")
    estimated_finishing_time_min: Optional[float] = Field(None, ge=0, description="Finishing time")
    estimated_setup_time_min: Optional[float] = Field(None, ge=0, description="Setup time")
    estimated_time_min: float = Field(gt=0, description="Total estimated machining time in minutes")

    # Notes
    correction_notes: Optional[str] = Field(None, max_length=500)
    correction_reason: Optional[str] = Field(None, max_length=200)


class AutoEstimateResponse(BaseModel):
    """Response for auto-estimate endpoint"""
    auto_estimated_time_min: float
    roughing_main: float
    roughing_aux: float
    finishing_main: float
    finishing_aux: float


@router.patch("/validate/{record_id}", response_model=EstimationRecordResponse)
async def validate_features(
    record_id: int,
    validation: ValidationRequest,
    part_type: Literal["ROT", "PRI"] = Query(description="Part type"),
    db: AsyncSession = Depends(get_db)
):
    """Validate extracted features with user corrections. Sets validation_status = 'validated'."""
    Model = TurningEstimation if part_type == "ROT" else MillingEstimation
    query = select(Model).where(Model.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"{part_type} record ID={record_id} not found")

    # Apply corrections
    if validation.corrected_material_code is not None:
        record.corrected_material_code = validation.corrected_material_code
    if validation.corrected_bbox_x_mm is not None:
        record.corrected_bbox_x_mm = validation.corrected_bbox_x_mm
    if validation.corrected_bbox_y_mm is not None:
        record.corrected_bbox_y_mm = validation.corrected_bbox_y_mm
    if validation.corrected_bbox_z_mm is not None:
        record.corrected_bbox_z_mm = validation.corrected_bbox_z_mm
    if validation.corrected_part_type is not None:
        record.corrected_part_type = validation.corrected_part_type
    if validation.correction_notes is not None:
        record.correction_notes = validation.correction_notes
    record.validation_status = "validated"
    record.validated_by_user_id = 1
    record.validation_date = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(record)
        return EstimationRecordResponse.model_validate(record)
    except Exception:
        await db.rollback()
        raise


@router.post("/auto-estimate/{record_id}", response_model=AutoEstimateResponse)
async def auto_estimate_time(
    record_id: int,
    part_type: Literal["ROT", "PRI"] = Query(description="Part type"),
    db: AsyncSession = Depends(get_db)
):
    """Calculate auto-estimated time using physics-based MRR model (ADR-040)."""
    Model = TurningEstimation if part_type == "ROT" else MillingEstimation
    query = select(Model).where(Model.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"{part_type} record ID={record_id} not found")

    step_path = STEP_UPLOAD_DIR / record.filename
    if not step_path.exists():
        raise HTTPException(status_code=404, detail=f"STEP file not found: {record.filename}")

    # Import here to avoid circular dependency
    from app.services.machining_time_estimation_service import MachiningTimeEstimationService

    material_code = record.corrected_material_code or record.material_group_code
    stock_type = "cylinder" if part_type == "ROT" else "bbox"
    estimation = MachiningTimeEstimationService.estimate_time(step_path, material_code, stock_type)

    record.auto_estimated_time_min = estimation["total_time_min"]
    record.auto_estimate_date = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(record)
        return AutoEstimateResponse(
            auto_estimated_time_min=estimation["total_time_min"],
            roughing_main=estimation["roughing_time_main"],
            roughing_aux=estimation["roughing_time_aux"],
            finishing_main=estimation["finishing_time_main"],
            finishing_aux=estimation["finishing_time_aux"]
        )
    except Exception:
        await db.rollback()
        raise


@router.patch("/finalize-estimate/{record_id}", response_model=EstimationRecordResponse)
async def finalize_estimate(
    record_id: int,
    finalize: FinalizeEstimateRequest,
    part_type: Literal["ROT", "PRI"] = Query(description="Part type"),
    db: AsyncSession = Depends(get_db)
):
    """Finalize time estimate with user's corrected value and all corrections. Sets validation_status = 'estimated'."""
    Model = TurningEstimation if part_type == "ROT" else MillingEstimation
    query = select(Model).where(Model.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"{part_type} record ID={record_id} not found")

    # Apply all corrections
    if finalize.corrected_part_type is not None:
        record.corrected_part_type = finalize.corrected_part_type
    if finalize.corrected_material_code is not None:
        record.corrected_material_code = finalize.corrected_material_code
    if finalize.corrected_bbox_x_mm is not None:
        record.corrected_bbox_x_mm = finalize.corrected_bbox_x_mm
    if finalize.corrected_bbox_y_mm is not None:
        record.corrected_bbox_y_mm = finalize.corrected_bbox_y_mm
    if finalize.corrected_bbox_z_mm is not None:
        record.corrected_bbox_z_mm = finalize.corrected_bbox_z_mm
    if finalize.corrected_stock_type is not None:
        record.corrected_stock_type = finalize.corrected_stock_type
    if finalize.corrected_stock_diameter is not None:
        record.corrected_stock_diameter = finalize.corrected_stock_diameter
    if finalize.corrected_stock_length is not None:
        record.corrected_stock_length = finalize.corrected_stock_length
    if finalize.correction_notes is not None:
        record.correction_notes = finalize.correction_notes

    # Save time estimate
    record.estimated_time_min = finalize.estimated_time_min
    if finalize.correction_reason:
        record.correction_reason = finalize.correction_reason

    # Update validation workflow state
    record.validation_status = "estimated"
    record.estimated_by_user_id = 1
    record.estimation_date = datetime.utcnow()
    record.validated_by_user_id = 1
    record.validation_date = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(record)
        return EstimationRecordResponse.model_validate(record)
    except Exception:
        await db.rollback()
        raise
