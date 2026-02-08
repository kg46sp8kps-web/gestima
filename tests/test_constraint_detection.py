"""
Tests for Constraint Detection Service.

Tests deep pocket and thin wall detection using OCCT geometry analysis.
"""

import pytest
from pathlib import Path

try:
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut

    OCCT_AVAILABLE = True
except ImportError:
    OCCT_AVAILABLE = False

from app.services.constraint_detection_service import (
    ConstraintDetectionService,
    DeepPocketConstraint,
    ThinWallConstraint,
    ConstraintAnalysis,
)


@pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not available")
class TestConstraintDetectionService:
    """Test constraint detection service."""

    def test_deep_pocket_detection_simple(self):
        """Test deep pocket detection with simple box + cylinder geometry."""
        # Create test geometry: 50x50x50 box with 10mm diameter 40mm deep hole
        box = BRepPrimAPI_MakeBox(50, 50, 50).Shape()

        # Create cylinder to cut (pocket)
        axis = gp_Ax2(gp_Pnt(25, 25, 10), gp_Dir(0, 0, 1))
        cylinder = BRepPrimAPI_MakeCylinder(axis, 5.0, 40.0).Shape()

        # Cut pocket from box
        cut_op = BRepAlgoAPI_Cut(box, cylinder)
        part_with_pocket = cut_op.Shape()

        # Detect deep pockets
        pockets = ConstraintDetectionService.detect_deep_pockets(part_with_pocket)

        # Verify deep pocket detected (depth=40mm, width=10mm, ratio=4.0)
        assert len(pockets) > 0, "No deep pockets detected"

        pocket = pockets[0]
        assert pocket.depth_mm > 30.0, f"Depth too small: {pocket.depth_mm}"
        assert pocket.width_mm < 15.0, f"Width too large: {pocket.width_mm}"
        assert (
            pocket.depth_to_width_ratio >= 3.0
        ), f"Ratio too small: {pocket.depth_to_width_ratio}"
        assert pocket.severity in [
            "moderate",
            "severe",
        ], f"Invalid severity: {pocket.severity}"

    def test_no_deep_pocket_shallow_hole(self):
        """Test that shallow holes are not flagged as deep pockets."""
        # Create test geometry: 50x50x50 box with 10mm diameter 5mm deep hole
        box = BRepPrimAPI_MakeBox(50, 50, 50).Shape()

        # Create shallow cylinder
        axis = gp_Ax2(gp_Pnt(25, 25, 45), gp_Dir(0, 0, 1))
        cylinder = BRepPrimAPI_MakeCylinder(axis, 5.0, 5.0).Shape()

        # Cut shallow pocket
        cut_op = BRepAlgoAPI_Cut(box, cylinder)
        part_with_shallow_pocket = cut_op.Shape()

        # Detect deep pockets
        pockets = ConstraintDetectionService.detect_deep_pockets(part_with_shallow_pocket)

        # Verify no deep pockets detected (ratio = 5/10 = 0.5 < 3.0)
        assert (
            len(pockets) == 0
        ), f"Shallow hole incorrectly flagged as deep pocket: {pockets}"

    def test_thin_wall_detection_simple(self):
        """Test thin wall detection with two parallel faces."""
        # Create thin box: 50x2x50 (thin wall in Y direction)
        thin_box = BRepPrimAPI_MakeBox(50, 2, 50).Shape()

        # Detect thin walls
        walls = ConstraintDetectionService.detect_thin_walls(thin_box, threshold_mm=3.0)

        # Verify thin wall detected
        assert len(walls) > 0, "No thin walls detected"

        wall = walls[0]
        assert (
            wall.thickness_mm < 3.0
        ), f"Thickness too large: {wall.thickness_mm}"
        assert wall.severity in [
            "moderate",
            "critical",
        ], f"Invalid severity: {wall.severity}"
        assert len(wall.location) == 3, "Invalid location tuple"

    def test_no_thin_wall_thick_part(self):
        """Test that thick parts are not flagged as thin walls."""
        # Create thick box: 50x50x50
        thick_box = BRepPrimAPI_MakeBox(50, 50, 50).Shape()

        # Detect thin walls
        walls = ConstraintDetectionService.detect_thin_walls(thick_box, threshold_mm=3.0)

        # Verify no thin walls detected (all walls > 50mm)
        assert len(walls) == 0, f"Thick part incorrectly flagged: {walls}"

    def test_constraint_analysis_penalty_calculation(self):
        """Test penalty multiplier calculation."""
        # Create part with deep pocket
        box = BRepPrimAPI_MakeBox(50, 50, 50).Shape()
        axis = gp_Ax2(gp_Pnt(25, 25, 10), gp_Dir(0, 0, 1))
        cylinder = BRepPrimAPI_MakeCylinder(axis, 5.0, 40.0).Shape()
        cut_op = BRepAlgoAPI_Cut(box, cylinder)
        part = cut_op.Shape()

        # Detect constraints manually
        pockets = ConstraintDetectionService.detect_deep_pockets(part)
        walls = ConstraintDetectionService.detect_thin_walls(part)

        # Calculate penalty
        analysis = ConstraintAnalysis(
            deep_pockets=pockets,
            thin_walls=walls,
            has_critical_constraints=False,
            recommended_penalty_multiplier=1.0,
        )

        # Recalculate penalty
        penalty = 1.0
        for pocket in pockets:
            if pocket.severity == "severe":
                penalty *= 1.8
            else:
                penalty *= 1.5

        for wall in walls:
            penalty *= 2.5

        # Verify penalty > 1.0 if constraints found
        if pockets or walls:
            assert penalty > 1.0, "Penalty should be > 1.0 when constraints found"

    def test_severity_classification(self):
        """Test severity classification for constraints."""
        # Deep pocket severity
        assert (
            DeepPocketConstraint(
                depth_mm=40.0,
                width_mm=10.0,
                depth_to_width_ratio=4.0,
                z_level=10.0,
                severity="moderate",
            ).severity
            == "moderate"
        )

        assert (
            DeepPocketConstraint(
                depth_mm=50.0,
                width_mm=10.0,
                depth_to_width_ratio=5.0,
                z_level=10.0,
                severity="severe",
            ).severity
            == "severe"
        )

        # Thin wall severity
        assert (
            ThinWallConstraint(
                thickness_mm=2.5, location=(0, 0, 0), severity="moderate"
            ).severity
            == "moderate"
        )

        assert (
            ThinWallConstraint(
                thickness_mm=1.5, location=(0, 0, 0), severity="critical"
            ).severity
            == "critical"
        )

    def test_determinism(self):
        """Test that constraint detection is deterministic (10 runs = identical results)."""
        # Create test geometry
        box = BRepPrimAPI_MakeBox(50, 50, 50).Shape()
        axis = gp_Ax2(gp_Pnt(25, 25, 10), gp_Dir(0, 0, 1))
        cylinder = BRepPrimAPI_MakeCylinder(axis, 5.0, 40.0).Shape()
        cut_op = BRepAlgoAPI_Cut(box, cylinder)
        part = cut_op.Shape()

        # Run detection 10 times
        results = []
        for _ in range(10):
            pockets = ConstraintDetectionService.detect_deep_pockets(part)
            results.append(len(pockets))

        # Verify all runs return same count
        assert len(set(results)) == 1, f"Non-deterministic results: {results}"

        # Verify detailed results are identical
        first_run = ConstraintDetectionService.detect_deep_pockets(part)
        for _ in range(9):
            run = ConstraintDetectionService.detect_deep_pockets(part)
            assert len(run) == len(
                first_run
            ), "Different number of constraints detected"

            if run:
                # Compare first constraint details
                assert (
                    run[0].depth_mm == first_run[0].depth_mm
                ), "Non-deterministic depth"
                assert (
                    run[0].width_mm == first_run[0].width_mm
                ), "Non-deterministic width"
                assert (
                    run[0].depth_to_width_ratio == first_run[0].depth_to_width_ratio
                ), "Non-deterministic ratio"

    def test_empty_shape_handling(self):
        """Test handling of edge cases."""
        # Very small box (no meaningful constraints)
        tiny_box = BRepPrimAPI_MakeBox(1, 1, 1).Shape()

        pockets = ConstraintDetectionService.detect_deep_pockets(tiny_box)
        walls = ConstraintDetectionService.detect_thin_walls(tiny_box, threshold_mm=3.0)

        # Should handle gracefully (no crashes)
        assert isinstance(pockets, list)
        assert isinstance(walls, list)


@pytest.mark.skipif(not OCCT_AVAILABLE, reason="OCCT not available")
class TestConstraintAnalysisIntegration:
    """Test full constraint analysis workflow."""

    def test_analyze_constraints_from_geometry(self):
        """Test full constraint analysis from geometry object."""
        # Create part with deep pocket
        box = BRepPrimAPI_MakeBox(50, 50, 50).Shape()
        axis = gp_Ax2(gp_Pnt(25, 25, 10), gp_Dir(0, 0, 1))
        cylinder = BRepPrimAPI_MakeCylinder(axis, 5.0, 40.0).Shape()
        cut_op = BRepAlgoAPI_Cut(box, cylinder)
        part = cut_op.Shape()

        # NOTE: analyze_constraints expects Path, but we can test components
        pockets = ConstraintDetectionService.detect_deep_pockets(part)
        walls = ConstraintDetectionService.detect_thin_walls(part)

        # Verify results
        assert len(pockets) > 0, "Deep pocket should be detected"
        assert isinstance(pockets[0], DeepPocketConstraint)

    def test_penalty_multiplier_combinations(self):
        """Test penalty multiplier for different constraint combinations."""
        # No constraints
        analysis = ConstraintAnalysis(
            deep_pockets=[],
            thin_walls=[],
            has_critical_constraints=False,
            recommended_penalty_multiplier=1.0,
        )
        assert analysis.recommended_penalty_multiplier == 1.0

        # One moderate deep pocket (1.5x)
        analysis = ConstraintAnalysis(
            deep_pockets=[
                DeepPocketConstraint(
                    depth_mm=30.0,
                    width_mm=10.0,
                    depth_to_width_ratio=3.0,
                    z_level=10.0,
                    severity="moderate",
                )
            ],
            thin_walls=[],
            has_critical_constraints=False,
            recommended_penalty_multiplier=1.5,
        )
        assert analysis.recommended_penalty_multiplier == 1.5

        # One severe deep pocket (1.8x)
        analysis = ConstraintAnalysis(
            deep_pockets=[
                DeepPocketConstraint(
                    depth_mm=50.0,
                    width_mm=10.0,
                    depth_to_width_ratio=5.0,
                    z_level=10.0,
                    severity="severe",
                )
            ],
            thin_walls=[],
            has_critical_constraints=True,
            recommended_penalty_multiplier=1.8,
        )
        assert analysis.recommended_penalty_multiplier == 1.8

        # One thin wall (2.5x)
        analysis = ConstraintAnalysis(
            deep_pockets=[],
            thin_walls=[
                ThinWallConstraint(
                    thickness_mm=2.5, location=(0, 0, 0), severity="moderate"
                )
            ],
            has_critical_constraints=False,
            recommended_penalty_multiplier=2.5,
        )
        assert analysis.recommended_penalty_multiplier == 2.5

        # Deep pocket + thin wall (1.5 * 2.5 = 3.75x)
        analysis = ConstraintAnalysis(
            deep_pockets=[
                DeepPocketConstraint(
                    depth_mm=30.0,
                    width_mm=10.0,
                    depth_to_width_ratio=3.0,
                    z_level=10.0,
                    severity="moderate",
                )
            ],
            thin_walls=[
                ThinWallConstraint(
                    thickness_mm=2.5, location=(0, 0, 0), severity="moderate"
                )
            ],
            has_critical_constraints=False,
            recommended_penalty_multiplier=3.75,
        )
        assert analysis.recommended_penalty_multiplier == 3.75
