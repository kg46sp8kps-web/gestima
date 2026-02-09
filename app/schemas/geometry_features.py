"""GESTIMA - Geometry Complexity Metrics (Proxy Features)

Pydantic schemas for ML-based machining time estimation.
40+ geometric PROXY metrics extracted from STEP files via OCCT.

APPROACH: Measure complexity metrics instead of classifying features
- No "pocket_count" or "hole_count" (OCCT can't reliably classify)
- Yes "concave_edge_ratio", "internal_cavity_volume" (objective measurements)

See: ADR-042 (Proxy Features ML Architecture)
Supersedes: ADR-041 (Feature Detection - DEPRECATED)
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class GeometryFeatures(BaseModel):
    """
    40+ geometric PROXY features for ML time estimation.

    All metrics are deterministic (same STEP file → identical output).
    Categories: Volume, BBox, Surface, Edge, Topology, ROT/PRI, Complexity, Material.

    KEY INSIGHT: Measure "how complex" instead of "what features".
    - Simple part: low concave_ratio, low cavity_volume → fast
    - Complex part: high concave_ratio, high cavity_volume → slow
    """

    # ============ METADATA ============
    filename: str = Field(..., min_length=1, max_length=255, description="STEP filename")
    part_type: str = Field(..., pattern=r"^(ROT|PRI)$", description="Auto-detected part type (ROT=turning, PRI=milling)")
    extraction_timestamp: str = Field(..., description="ISO 8601 timestamp of extraction")

    # ============ CATEGORY 1: VOLUME & MASS (8 features) ============
    part_volume_mm3: float = Field(..., gt=0, description="Part solid volume (OCCT VolumeProperties)")
    stock_volume_mm3: float = Field(..., gt=0, description="Stock volume (bbox or cylinder based on rotational_score)")
    removal_volume_mm3: float = Field(..., ge=0, description="Material to remove (stock - part)")
    removal_ratio: float = Field(..., ge=0.0, le=1.0, description="Removal / stock ratio")
    surface_area_mm2: float = Field(..., gt=0, description="Machined surface area (ROT: excludes OD cylinder)")
    surface_to_volume_ratio: float = Field(..., gt=0, description="Surface / volume ratio")
    part_mass_kg: float = Field(..., gt=0, description="Part mass (volume × density)")
    removal_mass_kg: float = Field(..., ge=0, description="Mass to remove (removal_volume × density)")

    # ============ CATEGORY 2: BOUNDING BOX & SHAPE (10 features) ============
    bbox_x_mm: float = Field(..., gt=0, description="Bounding box X dimension")
    bbox_y_mm: float = Field(..., gt=0, description="Bounding box Y dimension")
    bbox_z_mm: float = Field(..., gt=0, description="Bounding box Z dimension")
    bbox_diagonal_mm: float = Field(..., gt=0, description="Bounding box diagonal length")
    bbox_volume_ratio: float = Field(..., ge=0.0, le=1.0, description="Part volume / bbox volume (compactness)")
    aspect_ratio_xy: float = Field(..., ge=1.0, description="max(X,Y) / min(X,Y)")
    aspect_ratio_xz: float = Field(..., ge=1.0, description="max(X,Z) / min(X,Z)")
    aspect_ratio_yz: float = Field(..., ge=1.0, description="max(Y,Z) / min(Y,Z)")
    bbox_orientation_score: float = Field(..., ge=0.0, le=1.0, description="Alignment with principal axes")
    max_dimension_mm: float = Field(..., gt=0, description="max(X, Y, Z)")

    # ============ CATEGORY 3: SURFACE ANALYSIS (17 features) ============
    planar_surface_count: int = Field(..., ge=0, description="Number of planar faces")
    planar_surface_area_mm2: float = Field(..., ge=0, description="Total planar surface area")
    planar_surface_ratio: float = Field(..., ge=0.0, le=1.0, description="Planar area / total area (high = simple)")
    cylindrical_surface_count: int = Field(..., ge=0, description="Number of cylindrical faces")
    cylindrical_surface_area_mm2: float = Field(..., ge=0, description="Total cylindrical surface area")
    cylindrical_surface_ratio: float = Field(..., ge=0.0, le=1.0, description="Cylindrical area / total (KEY for ROT/PRI)")
    conical_surface_count: int = Field(..., ge=0, description="Number of conical faces")
    conical_surface_area_mm2: float = Field(..., ge=0, description="Total conical surface area")
    toroidal_surface_count: int = Field(..., ge=0, description="Number of toroidal faces (fillets)")
    toroidal_surface_area_mm2: float = Field(..., ge=0, description="Total toroidal surface area")
    bspline_surface_count: int = Field(..., ge=0, description="Number of B-spline/complex surfaces")
    bspline_surface_area_mm2: float = Field(..., ge=0, description="Total B-spline surface area")
    freeform_surface_ratio: float = Field(..., ge=0.0, le=1.0, description="B-spline area / total (high = complex surfacing)")
    inner_surface_area_mm2: float = Field(..., ge=0, description="Inner surface area (REVERSED orientation)")
    inner_surface_ratio: float = Field(..., ge=0.0, le=1.0, description="Inner area / total (KEY: cavities, holes)")
    surface_type_diversity: float = Field(..., ge=0.0, description="Shannon entropy of surface types")
    average_face_area_mm2: float = Field(..., gt=0, description="Average face area")

    # ============ CATEGORY 4: EDGE ANALYSIS (12 features) ============
    total_edge_count: int = Field(..., ge=0, description="Total number of edges")
    linear_edge_count: int = Field(..., ge=0, description="Number of linear edges")
    circular_edge_count: int = Field(..., ge=0, description="Number of circular edges")
    bspline_edge_count: int = Field(..., ge=0, description="Number of B-spline/complex edges")
    edge_type_diversity: float = Field(..., ge=0.0, description="Shannon entropy of edge types")
    total_edge_length_mm: float = Field(..., ge=0, description="Total edge length")
    average_edge_length_mm: float = Field(..., gt=0, description="Average edge length")
    min_edge_length_mm: float = Field(..., ge=0, description="Minimum edge length (can be 0 for degenerate edges)")
    max_edge_length_mm: float = Field(..., gt=0, description="Maximum edge length")
    edge_length_std_dev: float = Field(..., ge=0, description="Edge length standard deviation")
    concave_edge_count: int = Field(..., ge=0, description="Number of concave edges")
    concave_edge_ratio: float = Field(..., ge=0.0, le=1.0, description="Concave / total edges")

    # ============ CATEGORY 5: TOPOLOGY (8 features) ============
    shell_count: int = Field(..., ge=1, description="Number of separate shells (bodies)")
    face_count: int = Field(..., ge=4, description="Total face count")
    edge_count: int = Field(..., ge=6, description="Total edge count")
    vertex_count: int = Field(..., ge=4, description="Total vertex count")
    euler_characteristic: int = Field(..., description="V - E + F (topological invariant)")
    genus: int = Field(..., ge=0, description="Topological genus (handles/holes)")
    hole_count_estimate: int = Field(..., ge=0, description="Approximate hole count")
    closed_loop_count: int = Field(..., ge=0, description="Internal contour count")

    # ============ CATEGORY 6: ROTATIONAL VS PRISMATIC (8 features) ============
    rotational_score: float = Field(..., ge=0.0, le=1.0, description="ROT likelihood (0.0=PRI, 1.0=ROT)")
    cylindrical_axis_alignment: float = Field(..., ge=0.0, le=1.0, description="Cylinder alignment with Z-axis")
    diameter_to_length_ratio: float = Field(..., gt=0, description="max(X,Y) / Z for ROT parts")
    cross_section_circularity: float = Field(..., ge=0.0, le=1.0, description="XY cross-section circularity")
    cross_section_variance: float = Field(..., ge=0.0, description="Variance of cross-section area along Z")
    open_side_count: int = Field(..., ge=0, le=6, description="Sides without material (PRI parts)")
    undercut_score: float = Field(..., ge=0.0, le=1.0, description="Presence of undercuts")
    thin_wall_score: float = Field(..., ge=0.0, le=1.0, description="Presence of thin walls")

    # ============ CATEGORY 7: COMPLEXITY METRICS (10 features) ============
    # 7.1 VOLUME DISTRIBUTION (CRITICAL for detecting cavities)
    internal_cavity_volume_mm3: float = Field(..., ge=0, description="Volume 'inside' part (below top surface)")
    cavity_to_stock_ratio: float = Field(..., ge=0.0, le=1.0, description="Cavity / stock (high = complex)")

    # 7.2 DEPTH METRICS (tool overhang, feed rate impact)
    max_feature_depth_mm: float = Field(..., ge=0, description="Deepest feature from Z-top")
    avg_feature_depth_mm: float = Field(..., ge=0, description="Average feature depth")
    depth_variance_mm2: float = Field(..., ge=0, description="Variance of feature depths")

    # 7.3 ACCESSIBILITY METRICS (tool access restrictions)
    restricted_access_surface_area_mm2: float = Field(..., ge=0, description="Surface with limited tool access")
    openness_ratio: float = Field(..., ge=0.0, le=1.0, description="Open surface / total (high = easier)")
    undercut_surface_area_mm2: float = Field(..., ge=0, description="Surfaces requiring special tooling")

    # 7.4 COMPLEXITY INDICATORS
    sharp_edge_ratio: float = Field(..., ge=0.0, le=1.0, description="Edges with small/no fillet (sharp corners)")
    feature_density_per_cm3: float = Field(..., ge=0, description="Face count / volume (complexity indicator)")

    # ============ CATEGORY 8: REMOVED (Feature Detection - DEPRECATED) ============
    # Removed: min_hole_diameter, max_hole_diameter, min_pocket_width
    # Reason: Can't reliably detect "holes" vs "bosses", "pockets" vs "steps"
    # Replacement: inner_surface_ratio, internal_cavity_volume (proxy metrics)

    # ============ CATEGORY 9: MATERIAL (3 features) ============
    material_group_code: str = Field(..., min_length=1, max_length=20, description="Material code (e.g., '20910000')")
    material_machinability_index: float = Field(..., ge=0.0, le=1.0, description="Machinability index (0=hard, 1=easy)")
    material_hardness_hb: float = Field(..., gt=0, description="Hardness in Brinell (HB)")

    # ============ TOTAL: 50+ PROXY METRICS ============
    # Categories:
    # 1. Volume (8) - part, stock, removal, surface area
    # 2. BBox (10) - dimensions, aspect ratios
    # 3. Surface (17) - type distribution, inner/outer ratio, freeform
    # 4. Edge (12) - counts, lengths, concave ratio
    # 5. Topology (8) - shells, faces, Euler
    # 6. ROT/PRI (8) - rotational score, axis alignment
    # 7. Complexity (10) - cavity volume, depth, accessibility
    # 8. Material (3) - machinability, hardness

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "filename": "JR811181.step",
                "part_type": "ROT",
                "extraction_timestamp": "2026-02-09T10:30:00Z",
                "part_volume_mm3": 8900.0,
                "stock_volume_mm3": 12500.0,
                "removal_volume_mm3": 3600.0,
                "removal_ratio": 0.288,
                "surface_area_mm2": 3200.0,
                "cylindrical_surface_ratio": 0.68,
                "inner_surface_ratio": 0.15,
                "concave_edge_ratio": 0.25,
                "internal_cavity_volume_mm3": 450.0,
                "cavity_to_stock_ratio": 0.036,
                "max_feature_depth_mm": 18.5,
                "openness_ratio": 0.82,
                "rotational_score": 0.72,
                "material_group_code": "20910000",
                "material_machinability_index": 0.85,
                "material_hardness_hb": 180.0
            }
        }
    )
