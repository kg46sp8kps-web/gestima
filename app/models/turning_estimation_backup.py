"""GESTIMA - Turning Estimation Model (Phase 1: ML Time Estimation)

Stores extracted geometry features from STEP files for turning (ROT) parts.
Used to collect ground truth data for ML-based machining time estimation.

Classification: rotational_score > 0.6 → TurningEstimation
Feature count: 79 fields from GeometryFeatureExtractor
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database import Base


class TurningEstimation(Base):
    """
    Turning (ROT) part estimation record with 79 extracted geometry features.

    Features auto-extracted from STEP files via GeometryFeatureExtractor.
    Manual time estimates collected via UI for ML training data.
    Actual times imported from ERP/machine logs as ground truth.
    """
    __tablename__ = "turning_estimations"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Metadata
    filename = Column(String(255), unique=True, nullable=False, index=True)
    part_type = Column(String(50), nullable=False, default="ROT")
    extraction_timestamp = Column(DateTime, nullable=False)

    # ========== VOLUME METRICS (8 fields) ==========
    part_volume_mm3 = Column(Float, nullable=False)
    stock_volume_mm3 = Column(Float, nullable=False)
    removal_volume_mm3 = Column(Float, nullable=False)
    removal_ratio = Column(Float, nullable=False)
    surface_area_mm2 = Column(Float, nullable=False)
    surface_to_volume_ratio = Column(Float, nullable=False)
    part_mass_kg = Column(Float, nullable=False)
    removal_mass_kg = Column(Float, nullable=False)

    # ========== BOUNDING BOX METRICS (10 fields) ==========
    bbox_x_mm = Column(Float, nullable=False)
    bbox_y_mm = Column(Float, nullable=False)
    bbox_z_mm = Column(Float, nullable=False)
    bbox_diagonal_mm = Column(Float, nullable=False)
    bbox_volume_ratio = Column(Float, nullable=False)
    aspect_ratio_xy = Column(Float, nullable=False)
    aspect_ratio_xz = Column(Float, nullable=False)
    aspect_ratio_yz = Column(Float, nullable=False)
    bbox_orientation_score = Column(Float, nullable=False)
    max_dimension_mm = Column(Float, nullable=False)

    # ========== SURFACE ANALYSIS (15 fields) ==========
    planar_surface_count = Column(Integer, nullable=False)
    planar_surface_area_mm2 = Column(Float, nullable=False)
    planar_surface_ratio = Column(Float, nullable=False)
    cylindrical_surface_count = Column(Integer, nullable=False)
    cylindrical_surface_area_mm2 = Column(Float, nullable=False)
    cylindrical_surface_ratio = Column(Float, nullable=False)
    conical_surface_count = Column(Integer, nullable=False)
    conical_surface_area_mm2 = Column(Float, nullable=False)
    toroidal_surface_count = Column(Integer, nullable=False)
    toroidal_surface_area_mm2 = Column(Float, nullable=False)
    bspline_surface_count = Column(Integer, nullable=False)
    bspline_surface_area_mm2 = Column(Float, nullable=False)
    surface_type_diversity = Column(Float, nullable=False)
    largest_planar_face_area_mm2 = Column(Float, nullable=False)
    average_face_area_mm2 = Column(Float, nullable=False)

    # ========== EDGE ANALYSIS (13 fields) ==========
    total_edge_count = Column(Integer, nullable=False)
    linear_edge_count = Column(Integer, nullable=False)
    circular_edge_count = Column(Integer, nullable=False)
    bspline_edge_count = Column(Integer, nullable=False)
    edge_type_diversity = Column(Float, nullable=False)
    total_edge_length_mm = Column(Float, nullable=False)
    average_edge_length_mm = Column(Float, nullable=False)
    min_edge_length_mm = Column(Float, nullable=False)
    max_edge_length_mm = Column(Float, nullable=False)
    edge_length_std_dev = Column(Float, nullable=False)
    concave_edge_count = Column(Integer, nullable=False)
    concave_edge_ratio = Column(Float, nullable=False)

    # ========== TOPOLOGY (8 fields) ==========
    shell_count = Column(Integer, nullable=False)
    face_count = Column(Integer, nullable=False)
    edge_count = Column(Integer, nullable=False)
    vertex_count = Column(Integer, nullable=False)
    euler_characteristic = Column(Integer, nullable=False)
    genus = Column(Integer, nullable=False)
    hole_count_estimate = Column(Integer, nullable=False)
    closed_loop_count = Column(Integer, nullable=False)

    # ========== ROTATIONAL FEATURES (8 fields) ==========
    rotational_score = Column(Float, nullable=False, index=True)
    cylindrical_axis_alignment = Column(Float, nullable=False)
    diameter_to_length_ratio = Column(Float, nullable=False)
    cross_section_circularity = Column(Float, nullable=False)
    cross_section_variance = Column(Float, nullable=False)
    open_side_count = Column(Integer, nullable=False)
    undercut_score = Column(Float, nullable=False)
    thin_wall_score = Column(Float, nullable=False)

    # ========== MATERIAL REMOVAL FEATURES (6 fields) ==========
    pocket_volume_estimate_mm3 = Column(Float, nullable=False)
    pocket_count_estimate = Column(Integer, nullable=False)
    pocket_depth_avg_mm = Column(Float, nullable=False)
    pocket_depth_max_mm = Column(Float, nullable=False)
    groove_volume_estimate_mm3 = Column(Float, nullable=False)
    feature_density = Column(Float, nullable=False)

    # ========== CONSTRAINTS (6 fields) ==========
    min_wall_thickness_mm = Column(Float, nullable=False)
    max_wall_thickness_mm = Column(Float, nullable=False)
    min_hole_diameter_mm = Column(Float, nullable=False)
    max_hole_diameter_mm = Column(Float, nullable=False)
    min_pocket_width_mm = Column(Float, nullable=False)
    aspect_ratio_max_feature = Column(Float, nullable=False)

    # ========== MATERIAL PROPERTIES (3 fields) ==========
    material_group_code = Column(String(8), nullable=False, default="20910000")
    material_machinability_index = Column(Float, nullable=False)
    material_hardness_hb = Column(Float, nullable=False)

    # ========== VALIDATION WORKFLOW ==========
    validation_status = Column(String(20), nullable=False, default="pending")
    # Enum: "pending", "validated", "estimated", "trained"

    # Corrected features (user-validated data)
    corrected_material_code = Column(String(20), nullable=True)
    corrected_bbox_x_mm = Column(Float, nullable=True)
    corrected_bbox_y_mm = Column(Float, nullable=True)
    corrected_bbox_z_mm = Column(Float, nullable=True)
    corrected_part_type = Column(String(10), nullable=True)  # "ROT" or "PRI" override
    correction_notes = Column(String(500), nullable=True)
    validated_by_user_id = Column(Integer, nullable=True)
    validation_date = Column(DateTime, nullable=True)

    # ========== AUTO ESTIMATION (physics-based MRR) ==========
    auto_estimated_time_min = Column(Float, nullable=True)
    auto_estimate_date = Column(DateTime, nullable=True)

    # ========== MANUAL ESTIMATION (user correction) ==========
    estimated_time_min = Column(Float, nullable=True)  # User's final estimate
    correction_reason = Column(String(200), nullable=True)  # Why different from auto?
    estimated_by_user_id = Column(Integer, nullable=True)  # FK to users (Phase 7+)
    estimation_date = Column(DateTime, nullable=True)

    # ========== ACTUAL TIME (ground truth from ERP/machine) ==========
    actual_time_min = Column(Float, nullable=True)
    actual_time_source = Column(String(50), nullable=True)  # "ERP", "machine", etc.
    actual_time_date = Column(DateTime, nullable=True)

    # ========== AUDIT TIMESTAMPS ==========
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<TurningEstimation(id={self.id}, filename='{self.filename}', rotational_score={self.rotational_score:.2f})>"
