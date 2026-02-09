"""Add turning and milling estimation tables with 79 feature columns

Revision ID: 14ae23df5813
Revises: 09d8cd5db466
Create Date: 2026-02-09 09:54:10.363475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14ae23df5813'
down_revision: Union[str, Sequence[str], None] = '09d8cd5db466'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create turning_estimations table
    op.create_table(
        'turning_estimations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('part_type', sa.String(length=50), nullable=False),
        sa.Column('extraction_timestamp', sa.DateTime(), nullable=False),
        # Volume metrics (8)
        sa.Column('part_volume_mm3', sa.Float(), nullable=False),
        sa.Column('stock_volume_mm3', sa.Float(), nullable=False),
        sa.Column('removal_volume_mm3', sa.Float(), nullable=False),
        sa.Column('removal_ratio', sa.Float(), nullable=False),
        sa.Column('surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('surface_to_volume_ratio', sa.Float(), nullable=False),
        sa.Column('part_mass_kg', sa.Float(), nullable=False),
        sa.Column('removal_mass_kg', sa.Float(), nullable=False),
        # BBox metrics (10)
        sa.Column('bbox_x_mm', sa.Float(), nullable=False),
        sa.Column('bbox_y_mm', sa.Float(), nullable=False),
        sa.Column('bbox_z_mm', sa.Float(), nullable=False),
        sa.Column('bbox_diagonal_mm', sa.Float(), nullable=False),
        sa.Column('bbox_volume_ratio', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_xy', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_xz', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_yz', sa.Float(), nullable=False),
        sa.Column('bbox_orientation_score', sa.Float(), nullable=False),
        sa.Column('max_dimension_mm', sa.Float(), nullable=False),
        # Surface analysis (15)
        sa.Column('planar_surface_count', sa.Integer(), nullable=False),
        sa.Column('planar_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('planar_surface_ratio', sa.Float(), nullable=False),
        sa.Column('cylindrical_surface_count', sa.Integer(), nullable=False),
        sa.Column('cylindrical_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('cylindrical_surface_ratio', sa.Float(), nullable=False),
        sa.Column('conical_surface_count', sa.Integer(), nullable=False),
        sa.Column('conical_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('toroidal_surface_count', sa.Integer(), nullable=False),
        sa.Column('toroidal_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('bspline_surface_count', sa.Integer(), nullable=False),
        sa.Column('bspline_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('surface_type_diversity', sa.Float(), nullable=False),
        sa.Column('largest_planar_face_area_mm2', sa.Float(), nullable=False),
        sa.Column('average_face_area_mm2', sa.Float(), nullable=False),
        # Edge analysis (13)
        sa.Column('total_edge_count', sa.Integer(), nullable=False),
        sa.Column('linear_edge_count', sa.Integer(), nullable=False),
        sa.Column('circular_edge_count', sa.Integer(), nullable=False),
        sa.Column('bspline_edge_count', sa.Integer(), nullable=False),
        sa.Column('edge_type_diversity', sa.Float(), nullable=False),
        sa.Column('total_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('average_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('min_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('max_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('edge_length_std_dev', sa.Float(), nullable=False),
        sa.Column('concave_edge_count', sa.Integer(), nullable=False),
        sa.Column('concave_edge_ratio', sa.Float(), nullable=False),
        # Topology (8)
        sa.Column('shell_count', sa.Integer(), nullable=False),
        sa.Column('face_count', sa.Integer(), nullable=False),
        sa.Column('edge_count', sa.Integer(), nullable=False),
        sa.Column('vertex_count', sa.Integer(), nullable=False),
        sa.Column('euler_characteristic', sa.Integer(), nullable=False),
        sa.Column('genus', sa.Integer(), nullable=False),
        sa.Column('hole_count_estimate', sa.Integer(), nullable=False),
        sa.Column('closed_loop_count', sa.Integer(), nullable=False),
        # Rotational features (8)
        sa.Column('rotational_score', sa.Float(), nullable=False),
        sa.Column('cylindrical_axis_alignment', sa.Float(), nullable=False),
        sa.Column('diameter_to_length_ratio', sa.Float(), nullable=False),
        sa.Column('cross_section_circularity', sa.Float(), nullable=False),
        sa.Column('cross_section_variance', sa.Float(), nullable=False),
        sa.Column('open_side_count', sa.Integer(), nullable=False),
        sa.Column('undercut_score', sa.Float(), nullable=False),
        sa.Column('thin_wall_score', sa.Float(), nullable=False),
        # Material removal features (6)
        sa.Column('pocket_volume_estimate_mm3', sa.Float(), nullable=False),
        sa.Column('pocket_count_estimate', sa.Integer(), nullable=False),
        sa.Column('pocket_depth_avg_mm', sa.Float(), nullable=False),
        sa.Column('pocket_depth_max_mm', sa.Float(), nullable=False),
        sa.Column('groove_volume_estimate_mm3', sa.Float(), nullable=False),
        sa.Column('feature_density', sa.Float(), nullable=False),
        # Constraints (6)
        sa.Column('min_wall_thickness_mm', sa.Float(), nullable=False),
        sa.Column('max_wall_thickness_mm', sa.Float(), nullable=False),
        sa.Column('min_hole_diameter_mm', sa.Float(), nullable=False),
        sa.Column('max_hole_diameter_mm', sa.Float(), nullable=False),
        sa.Column('min_pocket_width_mm', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_max_feature', sa.Float(), nullable=False),
        # Material properties (3)
        sa.Column('material_group_code', sa.String(length=8), nullable=False),
        sa.Column('material_machinability_index', sa.Float(), nullable=False),
        sa.Column('material_hardness_hb', sa.Float(), nullable=False),
        # Manual estimation (3)
        sa.Column('estimated_time_min', sa.Float(), nullable=True),
        sa.Column('estimated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('estimation_date', sa.DateTime(), nullable=True),
        # Actual time (3)
        sa.Column('actual_time_min', sa.Float(), nullable=True),
        sa.Column('actual_time_source', sa.String(length=50), nullable=True),
        sa.Column('actual_time_date', sa.DateTime(), nullable=True),
        # Audit timestamps (2)
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename')
    )
    op.create_index(op.f('ix_turning_estimations_filename'), 'turning_estimations', ['filename'], unique=False)
    op.create_index(op.f('ix_turning_estimations_id'), 'turning_estimations', ['id'], unique=False)
    op.create_index(op.f('ix_turning_estimations_rotational_score'), 'turning_estimations', ['rotational_score'], unique=False)

    # Create milling_estimations table (identical structure)
    op.create_table(
        'milling_estimations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('part_type', sa.String(length=50), nullable=False),
        sa.Column('extraction_timestamp', sa.DateTime(), nullable=False),
        # Volume metrics (8)
        sa.Column('part_volume_mm3', sa.Float(), nullable=False),
        sa.Column('stock_volume_mm3', sa.Float(), nullable=False),
        sa.Column('removal_volume_mm3', sa.Float(), nullable=False),
        sa.Column('removal_ratio', sa.Float(), nullable=False),
        sa.Column('surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('surface_to_volume_ratio', sa.Float(), nullable=False),
        sa.Column('part_mass_kg', sa.Float(), nullable=False),
        sa.Column('removal_mass_kg', sa.Float(), nullable=False),
        # BBox metrics (10)
        sa.Column('bbox_x_mm', sa.Float(), nullable=False),
        sa.Column('bbox_y_mm', sa.Float(), nullable=False),
        sa.Column('bbox_z_mm', sa.Float(), nullable=False),
        sa.Column('bbox_diagonal_mm', sa.Float(), nullable=False),
        sa.Column('bbox_volume_ratio', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_xy', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_xz', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_yz', sa.Float(), nullable=False),
        sa.Column('bbox_orientation_score', sa.Float(), nullable=False),
        sa.Column('max_dimension_mm', sa.Float(), nullable=False),
        # Surface analysis (15)
        sa.Column('planar_surface_count', sa.Integer(), nullable=False),
        sa.Column('planar_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('planar_surface_ratio', sa.Float(), nullable=False),
        sa.Column('cylindrical_surface_count', sa.Integer(), nullable=False),
        sa.Column('cylindrical_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('cylindrical_surface_ratio', sa.Float(), nullable=False),
        sa.Column('conical_surface_count', sa.Integer(), nullable=False),
        sa.Column('conical_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('toroidal_surface_count', sa.Integer(), nullable=False),
        sa.Column('toroidal_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('bspline_surface_count', sa.Integer(), nullable=False),
        sa.Column('bspline_surface_area_mm2', sa.Float(), nullable=False),
        sa.Column('surface_type_diversity', sa.Float(), nullable=False),
        sa.Column('largest_planar_face_area_mm2', sa.Float(), nullable=False),
        sa.Column('average_face_area_mm2', sa.Float(), nullable=False),
        # Edge analysis (13)
        sa.Column('total_edge_count', sa.Integer(), nullable=False),
        sa.Column('linear_edge_count', sa.Integer(), nullable=False),
        sa.Column('circular_edge_count', sa.Integer(), nullable=False),
        sa.Column('bspline_edge_count', sa.Integer(), nullable=False),
        sa.Column('edge_type_diversity', sa.Float(), nullable=False),
        sa.Column('total_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('average_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('min_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('max_edge_length_mm', sa.Float(), nullable=False),
        sa.Column('edge_length_std_dev', sa.Float(), nullable=False),
        sa.Column('concave_edge_count', sa.Integer(), nullable=False),
        sa.Column('concave_edge_ratio', sa.Float(), nullable=False),
        # Topology (8)
        sa.Column('shell_count', sa.Integer(), nullable=False),
        sa.Column('face_count', sa.Integer(), nullable=False),
        sa.Column('edge_count', sa.Integer(), nullable=False),
        sa.Column('vertex_count', sa.Integer(), nullable=False),
        sa.Column('euler_characteristic', sa.Integer(), nullable=False),
        sa.Column('genus', sa.Integer(), nullable=False),
        sa.Column('hole_count_estimate', sa.Integer(), nullable=False),
        sa.Column('closed_loop_count', sa.Integer(), nullable=False),
        # Rotational features (8)
        sa.Column('rotational_score', sa.Float(), nullable=False),
        sa.Column('cylindrical_axis_alignment', sa.Float(), nullable=False),
        sa.Column('diameter_to_length_ratio', sa.Float(), nullable=False),
        sa.Column('cross_section_circularity', sa.Float(), nullable=False),
        sa.Column('cross_section_variance', sa.Float(), nullable=False),
        sa.Column('open_side_count', sa.Integer(), nullable=False),
        sa.Column('undercut_score', sa.Float(), nullable=False),
        sa.Column('thin_wall_score', sa.Float(), nullable=False),
        # Material removal features (6)
        sa.Column('pocket_volume_estimate_mm3', sa.Float(), nullable=False),
        sa.Column('pocket_count_estimate', sa.Integer(), nullable=False),
        sa.Column('pocket_depth_avg_mm', sa.Float(), nullable=False),
        sa.Column('pocket_depth_max_mm', sa.Float(), nullable=False),
        sa.Column('groove_volume_estimate_mm3', sa.Float(), nullable=False),
        sa.Column('feature_density', sa.Float(), nullable=False),
        # Constraints (6)
        sa.Column('min_wall_thickness_mm', sa.Float(), nullable=False),
        sa.Column('max_wall_thickness_mm', sa.Float(), nullable=False),
        sa.Column('min_hole_diameter_mm', sa.Float(), nullable=False),
        sa.Column('max_hole_diameter_mm', sa.Float(), nullable=False),
        sa.Column('min_pocket_width_mm', sa.Float(), nullable=False),
        sa.Column('aspect_ratio_max_feature', sa.Float(), nullable=False),
        # Material properties (3)
        sa.Column('material_group_code', sa.String(length=8), nullable=False),
        sa.Column('material_machinability_index', sa.Float(), nullable=False),
        sa.Column('material_hardness_hb', sa.Float(), nullable=False),
        # Manual estimation (3)
        sa.Column('estimated_time_min', sa.Float(), nullable=True),
        sa.Column('estimated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('estimation_date', sa.DateTime(), nullable=True),
        # Actual time (3)
        sa.Column('actual_time_min', sa.Float(), nullable=True),
        sa.Column('actual_time_source', sa.String(length=50), nullable=True),
        sa.Column('actual_time_date', sa.DateTime(), nullable=True),
        # Audit timestamps (2)
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename')
    )
    op.create_index(op.f('ix_milling_estimations_filename'), 'milling_estimations', ['filename'], unique=False)
    op.create_index(op.f('ix_milling_estimations_id'), 'milling_estimations', ['id'], unique=False)
    op.create_index(op.f('ix_milling_estimations_rotational_score'), 'milling_estimations', ['rotational_score'], unique=False)

    # Schema drift detected but skipped (models are source of truth)
    # - FK ondelete already applied in migration 09d8cd5db466
    # - parts.stock_* columns already removed
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # Drop estimation tables
    op.drop_index(op.f('ix_milling_estimations_rotational_score'), table_name='milling_estimations')
    op.drop_index(op.f('ix_milling_estimations_id'), table_name='milling_estimations')
    op.drop_index(op.f('ix_milling_estimations_filename'), table_name='milling_estimations')
    op.drop_table('milling_estimations')

    op.drop_index(op.f('ix_turning_estimations_rotational_score'), table_name='turning_estimations')
    op.drop_index(op.f('ix_turning_estimations_id'), table_name='turning_estimations')
    op.drop_index(op.f('ix_turning_estimations_filename'), table_name='turning_estimations')
    op.drop_table('turning_estimations')

    # Downgrade skipped for schema drift changes (not created by this migration)
    pass
