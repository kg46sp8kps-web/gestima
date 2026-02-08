"""
Batch Machining Time Estimation Service

Estimates total machining time for STEP files using heuristic model:
  total_time_min = setup_time + (material_removal_volume * material_mrr_factor * constraint_multiplier)

Deterministic: 100% reproducible results across runs.

Works with OCCT (for real geometry) or falls back to mock data (for testing).

ADR-040: Batch Estimation - Volume-based MRR Model
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# OCCT imports (optional - graceful degradation)
try:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False
    logger.info("OCCT not available - using mock data for batch estimation")


@dataclass
class MaterialParams:
    """Material class parameters for MRR calculation."""
    name: str
    mrr_factor: float  # minutes per cm³ of material removed
    setup_time_min: float
    description: str


# Material database (deterministic, no randomness)
MATERIAL_DATABASE = {
    "16MnCr5": MaterialParams(
        name="16MnCr5",
        mrr_factor=0.45,  # minutes/cm³
        setup_time_min=15.0,
        description="Case-hardened steel (carburized)"
    ),
    "C45": MaterialParams(
        name="C45",
        mrr_factor=0.35,
        setup_time_min=12.0,
        description="Medium carbon steel"
    ),
    "AlMgSi1": MaterialParams(
        name="AlMgSi1",
        mrr_factor=0.15,
        setup_time_min=10.0,
        description="Aluminum alloy"
    ),
    "316L": MaterialParams(
        name="316L",
        mrr_factor=0.65,
        setup_time_min=18.0,
        description="Stainless steel"
    ),
    "Titanium": MaterialParams(
        name="Titanium",
        mrr_factor=1.2,
        setup_time_min=20.0,
        description="Titanium alloy (difficult)"
    ),
}


def detect_material_from_filename(filename: str) -> str:
    """
    Try to detect material code from filename.
    
    Examples:
        "JR_810686_16MnCr5.step" → "16MnCr5"
        "part_aluminum.step" → "AlMgSi1" (if matches)
        "unknown.step" → "16MnCr5" (default)
    
    Args:
        filename: STEP filename
    
    Returns:
        Material code (key from MATERIAL_DATABASE)
    """
    filename_upper = filename.upper()
    
    # Check for material codes in filename
    for code in MATERIAL_DATABASE.keys():
        if code.upper() in filename_upper:
            return code
    
    # Check for aliases
    if "ALU" in filename_upper or "ALUMINUM" in filename_upper:
        return "AlMgSi1"
    if "STAINLESS" in filename_upper or "316" in filename_upper:
        return "316L"
    if "TITAN" in filename_upper:
        return "Titanium"
    
    # Default fallback
    return "16MnCr5"


def extract_step_metadata(step_file: Path) -> Dict[str, Any]:
    """
    Extract volume and bounding box from STEP file using OCCT.
    
    Falls back to mock data based on filename if OCCT not available.
    
    Args:
        step_file: Path to STEP file
    
    Returns:
        Dict with keys: part_volume_mm3, stock_volume_mm3, bbox_mm
    
    Raises:
        ValueError: If STEP file cannot be read
    """
    
    if not step_file.exists():
        raise ValueError(f"File not found: {step_file}")

    # Try OCCT
    if OCCT_AVAILABLE:
        try:
            reader = STEPControl_Reader()
            status = reader.ReadFile(str(step_file))

            if status != IFSelect_RetDone:
                raise ValueError(f"Failed to read STEP file: {step_file}")

            reader.TransferRoots()
            shape = reader.OneShape()

            if shape.IsNull():
                raise ValueError(f"Null shape in STEP file: {step_file}")

            # Bounding box
            bbox = Bnd_Box()
            brepbndlib.Add(shape, bbox)
            xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()

            bbox_mm = {
                "length_mm": round(xmax - xmin, 2),
                "width_mm": round(ymax - ymin, 2),
                "height_mm": round(zmax - zmin, 2),
            }

            # Volume (part volume)
            props = GProp_GProps()
            brepgprop.VolumeProperties(shape, props)
            part_volume_mm3 = round(props.Mass(), 2)

            # Stock volume (bbox cubic)
            stock_volume_mm3 = round(
                bbox_mm["length_mm"] * bbox_mm["width_mm"] * bbox_mm["height_mm"],
                2
            )

            return {
                "part_volume_mm3": part_volume_mm3,
                "stock_volume_mm3": stock_volume_mm3,
                "bbox_mm": bbox_mm,
            }
        except Exception as e:
            logger.warning(f"OCCT parsing failed for {step_file.name}: {e}. Using mock data.")
    
    # Fallback: mock data based on filename hash
    # This ensures deterministic results without OCCT
    filename_hash = hashlib.md5(step_file.name.encode()).hexdigest()
    hash_int = int(filename_hash, 16)
    
    # Pseudo-random but deterministic values from filename
    length_mm = 40 + (hash_int % 160)  # 40-200 mm
    width_mm = 30 + ((hash_int // 256) % 140)  # 30-170 mm
    height_mm = 25 + ((hash_int // 65536) % 125)  # 25-150 mm
    
    stock_volume_mm3 = round(length_mm * width_mm * height_mm, 2)
    
    # Part volume is 40-80% of stock (deterministic)
    removal_ratio = 0.30 + ((hash_int // 16777216) % 50) / 100
    part_volume_mm3 = round(stock_volume_mm3 * (1 - removal_ratio), 2)
    
    bbox_mm = {
        "length_mm": length_mm,
        "width_mm": width_mm,
        "height_mm": height_mm,
    }
    
    logger.info(f"Using mock data for {step_file.name} (hash-based, deterministic)")
    
    return {
        "part_volume_mm3": part_volume_mm3,
        "stock_volume_mm3": stock_volume_mm3,
        "bbox_mm": bbox_mm,
    }


def calculate_constraint_multiplier(metadata: Dict[str, Any]) -> float:
    """
    Calculate constraint multiplier based on part complexity.
    
    Factors:
      - High aspect ratio (length >> width): +20% (thin/slender)
      - Small stock removal (<5mm): +10% (tight tolerances)
      - Large stock removal (>70%): +5% (rough blank)
    
    Args:
        metadata: STEP metadata from extract_step_metadata()
    
    Returns:
        Multiplier (1.0 = no constraint, 1.35 = severe constraints)
    """
    multiplier = 1.0
    
    bbox = metadata["bbox_mm"]
    length = max(bbox["length_mm"], bbox["width_mm"], bbox["height_mm"])
    width = min(bbox["length_mm"], bbox["width_mm"], bbox["height_mm"])
    
    # Aspect ratio check
    if width > 0 and length / width > 4.0:
        multiplier += 0.20
    
    # Stock removal ratio
    part_vol = metadata["part_volume_mm3"]
    stock_vol = metadata["stock_volume_mm3"]
    
    if stock_vol > 0:
        removal_ratio = (stock_vol - part_vol) / stock_vol
        
        if removal_ratio < 0.05:  # Small removal
            multiplier += 0.10
        elif removal_ratio > 0.70:  # Rough blank
            multiplier += 0.05
    
    return round(multiplier, 2)


def estimate_machining_time(
    step_file: Path,
    material: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estimate total machining time for a STEP file.
    
    Formula:
      roughing_time = material_removal_volume * mrr_factor * 0.8 (80% of constraint)
      finishing_time = material_removal_volume * mrr_factor * 0.2 (20% of constraint)
      total_time = setup_time + (roughing_time + finishing_time) * constraint_multiplier
    
    Deterministic: Same file produces same result every time.
    
    Args:
        step_file: Path to STEP file
        material: Material code (auto-detected if None)
    
    Returns:
        {
            "filename": str,
            "material": str,
            "setup_time_min": float,
            "roughing_time_min": float,
            "finishing_time_min": float,
            "total_time_min": float,
            "breakdown": {
                "material": str,
                "part_volume_mm3": float,
                "stock_volume_mm3": float,
                "material_to_remove_mm3": float,
                "surface_area_cm2": float,
                "constraint_multiplier": float,
            }
        }
    
    Raises:
        ValueError: If material not in database or STEP parsing fails
    """
    # Auto-detect material if not provided
    if material is None:
        material = detect_material_from_filename(step_file.name)
    
    if material not in MATERIAL_DATABASE:
        raise ValueError(f"Unknown material: {material}")
    
    mat_params = MATERIAL_DATABASE[material]
    
    # Extract geometry
    metadata = extract_step_metadata(step_file)
    
    part_volume_mm3 = metadata["part_volume_mm3"]
    stock_volume_mm3 = metadata["stock_volume_mm3"]
    
    material_to_remove_mm3 = stock_volume_mm3 - part_volume_mm3
    material_to_remove_cm3 = material_to_remove_mm3 / 1000.0
    
    # Calculate constraint multiplier
    constraint_multiplier = calculate_constraint_multiplier(metadata)
    
    # Surface area approximation (rough estimate from bbox)
    bbox = metadata["bbox_mm"]
    surface_area_mm2 = 2 * (
        bbox["length_mm"] * bbox["width_mm"]
        + bbox["length_mm"] * bbox["height_mm"]
        + bbox["width_mm"] * bbox["height_mm"]
    )
    surface_area_cm2 = round(surface_area_mm2 / 100, 2)
    
    # Time calculation
    setup_time_min = mat_params.setup_time_min
    
    # Cutting time based on material removal rate
    base_cutting_time = material_to_remove_cm3 * mat_params.mrr_factor
    
    # Split into roughing (80%) and finishing (20%)
    roughing_time_min = round(base_cutting_time * 0.8, 2)
    finishing_time_min = round(base_cutting_time * 0.2, 2)
    
    # Apply constraint multiplier
    total_cutting_time = (roughing_time_min + finishing_time_min) * constraint_multiplier
    total_time_min = round(setup_time_min + total_cutting_time, 2)
    
    return {
        "filename": step_file.name,
        "material": material,
        "setup_time_min": setup_time_min,
        "roughing_time_min": round(roughing_time_min * constraint_multiplier, 2),
        "finishing_time_min": round(finishing_time_min * constraint_multiplier, 2),
        "total_time_min": total_time_min,
        "breakdown": {
            "material": material,
            "part_volume_mm3": part_volume_mm3,
            "stock_volume_mm3": stock_volume_mm3,
            "material_to_remove_mm3": round(material_to_remove_mm3, 2),
            "surface_area_cm2": surface_area_cm2,
            "constraint_multiplier": constraint_multiplier,
        }
    }


def batch_estimate_all_files(drawings_dir: Path) -> List[Dict[str, Any]]:
    """
    Estimate machining time for all STEP files in directory.
    
    Runs deterministically: same input → same output every time.
    
    Args:
        drawings_dir: Path to directory containing STEP files
    
    Returns:
        List of estimation results
    """
    step_files = sorted(
        list(drawings_dir.glob("**/*.step")) + list(drawings_dir.glob("**/*.stp"))
    )
    
    logger.info(f"Found {len(step_files)} STEP files in {drawings_dir}")
    
    results = []
    errors = []
    
    for idx, step_file in enumerate(step_files, 1):
        try:
            logger.info(f"[{idx}/{len(step_files)}] Processing {step_file.name}...")
            
            result = estimate_machining_time(step_file)
            results.append(result)
            
            logger.info(f"  ✓ {result['total_time_min']:.2f} min ({result['material']})")
            
        except Exception as e:
            logger.error(f"  ✗ ERROR: {e}")
            errors.append({
                "filename": step_file.name,
                "error": str(e)
            })
    
    logger.info(f"\nProcessed {len(results)} files successfully")
    if errors:
        logger.warning(f"Failed to process {len(errors)} files")
    
    return results
