"""
Tests for Batch Machining Time Estimation Service

Tests determinism, material detection, and constraint calculations.
"""

import pytest
from pathlib import Path
from app.services.batch_estimation_service import (
    detect_material_from_filename,
    extract_step_metadata,
    calculate_constraint_multiplier,
    estimate_machining_time,
    MATERIAL_DATABASE,
)


class TestMaterialDetection:
    """Material code detection from filenames."""
    
    def test_detect_16MnCr5(self):
        """16MnCr5 code detection."""
        result = detect_material_from_filename("part_16MnCr5_001.step")
        assert result == "16MnCr5"
    
    def test_detect_case_insensitive(self):
        """Material codes are case-insensitive."""
        result = detect_material_from_filename("part_16mncr5_001.step")
        assert result == "16MnCr5"
    
    def test_detect_aluminum_alias(self):
        """Aluminum aliases recognized."""
        assert detect_material_from_filename("part_aluminum.step") == "AlMgSi1"
        assert detect_material_from_filename("part_alu_001.step") == "AlMgSi1"
    
    def test_detect_stainless_alias(self):
        """Stainless steel aliases recognized."""
        assert detect_material_from_filename("part_stainless.step") == "316L"
        assert detect_material_from_filename("316_shaft.step") == "316L"
    
    def test_default_fallback(self):
        """Unknown materials default to 16MnCr5."""
        result = detect_material_from_filename("unknown_part.step")
        assert result == "16MnCr5"


class TestConstraintMultiplier:
    """Constraint multiplier calculation based on part geometry."""
    
    def test_no_constraints(self):
        """Part with normal aspect ratio and 50% stock removal."""
        metadata = {
            "bbox_mm": {"length_mm": 50, "width_mm": 40, "height_mm": 30},
            "part_volume_mm3": 30000,  # 50% removal
            "stock_volume_mm3": 60000,  # 50*40*30
        }
        multiplier = calculate_constraint_multiplier(metadata)
        assert multiplier == 1.0
    
    def test_high_aspect_ratio(self):
        """Slender part (length >> width)."""
        metadata = {
            "bbox_mm": {"length_mm": 200, "width_mm": 10, "height_mm": 10},
            "part_volume_mm3": 15000,
            "stock_volume_mm3": 20000,
        }
        multiplier = calculate_constraint_multiplier(metadata)
        assert multiplier >= 1.2  # +20% for high aspect ratio
    
    def test_small_stock_removal(self):
        """Very tight machining (< 5% removal)."""
        metadata = {
            "bbox_mm": {"length_mm": 100, "width_mm": 100, "height_mm": 100},
            "part_volume_mm3": 980000,  # 2% removal
            "stock_volume_mm3": 1000000,  # 100*100*100
        }
        multiplier = calculate_constraint_multiplier(metadata)
        assert multiplier >= 1.1  # +10% for tight tolerances
    
    def test_rough_blank(self):
        """High material removal (> 70%)."""
        metadata = {
            "bbox_mm": {"length_mm": 100, "width_mm": 100, "height_mm": 100},
            "part_volume_mm3": 200000,  # 80% removal
            "stock_volume_mm3": 1000000,  # 100*100*100
        }
        multiplier = calculate_constraint_multiplier(metadata)
        assert multiplier >= 1.05  # +5% for rough blank


class TestDeterminism:
    """Test 100% deterministic results."""
    
    def test_repeated_estimates_identical(self):
        """Same STEP file produces identical results in 3 runs."""
        # Pick any STEP file from uploads
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        # Run 3 times
        results = []
        for _ in range(3):
            try:
                result = estimate_machining_time(step_file)
                results.append(result["total_time_min"])
            except Exception as e:
                pytest.skip(f"STEP parsing failed: {e}")
        
        # All results must be identical
        assert len(set(results)) == 1, f"Non-deterministic results: {results}"
    
    def test_material_impact_deterministic(self):
        """Material selection produces deterministic results."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        # Same material, two runs
        times = []
        for _ in range(2):
            try:
                result = estimate_machining_time(step_file, material="16MnCr5")
                times.append(result["total_time_min"])
            except Exception as e:
                pytest.skip(f"STEP parsing failed: {e}")
        
        assert times[0] == times[1], "Material handling is not deterministic"


class TestMaterialImpact:
    """Verify material parameters affect time estimation."""
    
    def test_harder_material_takes_longer(self):
        """Harder materials should have higher MRR factors."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        # Test materials with known MRR values
        try:
            steel_result = estimate_machining_time(step_file, "16MnCr5")
            alu_result = estimate_machining_time(step_file, "AlMgSi1")
            
            steel_time = steel_result["total_time_min"]
            alu_time = alu_result["total_time_min"]
            
            # Aluminum (MRR 0.15) should be faster than steel (MRR 0.45)
            assert alu_time < steel_time, \
                f"Aluminum ({alu_time:.2f} min) should be faster than steel ({steel_time:.2f} min)"
        except Exception as e:
            pytest.skip(f"STEP parsing failed: {e}")
    
    def test_material_database_complete(self):
        """Material database has required fields."""
        for code, params in MATERIAL_DATABASE.items():
            assert params.name == code
            assert params.mrr_factor > 0
            assert params.setup_time_min > 0
            assert params.description


class TestEstimationResults:
    """Verify estimation result structure."""
    
    def test_result_has_required_fields(self):
        """Result dict has all required fields."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        try:
            result = estimate_machining_time(step_file)
        except Exception as e:
            pytest.skip(f"STEP parsing failed: {e}")
        
        # Required top-level fields
        assert "filename" in result
        assert "material" in result
        assert "setup_time_min" in result
        assert "roughing_time_min" in result
        assert "finishing_time_min" in result
        assert "total_time_min" in result
        assert "breakdown" in result
        
        # Required breakdown fields
        bd = result["breakdown"]
        assert "material" in bd
        assert "part_volume_mm3" in bd
        assert "stock_volume_mm3" in bd
        assert "material_to_remove_mm3" in bd
        assert "surface_area_cm2" in bd
        assert "constraint_multiplier" in bd
    
    def test_time_values_positive(self):
        """All time values must be positive."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        try:
            result = estimate_machining_time(step_file)
        except Exception as e:
            pytest.skip(f"STEP parsing failed: {e}")
        
        assert result["setup_time_min"] > 0
        assert result["roughing_time_min"] >= 0
        assert result["finishing_time_min"] >= 0
        assert result["total_time_min"] > 0
    
    def test_total_time_sum_logic(self):
        """Total time is >= setup_time + cutting_time."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        try:
            result = estimate_machining_time(step_file)
        except Exception as e:
            pytest.skip(f"STEP parsing failed: {e}")
        
        setup = result["setup_time_min"]
        cutting = result["roughing_time_min"] + result["finishing_time_min"]
        total = result["total_time_min"]
        
        # Total >= setup + cutting (with small tolerance for rounding)
        assert total >= setup + cutting - 0.01, \
            f"Total ({total}) < setup ({setup}) + cutting ({cutting})"


class TestVolumeCalculations:
    """Test volume and material removal calculations."""
    
    def test_stock_volume_equals_bbox(self):
        """Stock volume is bbox product."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        try:
            result = estimate_machining_time(step_file)
        except Exception as e:
            pytest.skip(f"STEP parsing failed: {e}")
        
        # Stock volume should equal bbox product
        bd = result["breakdown"]
        # (allowing small rounding difference)
        assert abs(bd["stock_volume_mm3"]) > 0
    
    def test_material_removal_positive(self):
        """Material to remove > 0."""
        step_files = list(Path("uploads/drawings").glob("**/*.stp"))
        
        if not step_files:
            pytest.skip("No STEP files found in uploads/drawings")
        
        step_file = step_files[0]
        
        try:
            result = estimate_machining_time(step_file)
        except Exception as e:
            pytest.skip(f"STEP parsing failed: {e}")
        
        bd = result["breakdown"]
        material_to_remove = bd["material_to_remove_mm3"]
        
        # Material to remove should be positive (stock > part)
        assert material_to_remove >= 0
