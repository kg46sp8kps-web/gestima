"""GESTIMA - Integration Tests for Machining Time Estimation

Tests with real STEP files to verify end-to-end functionality.
ADR-040: Machining Time Estimation System
"""

import pytest
from pathlib import Path

from app.services.machining_time_estimation_service import MachiningTimeEstimationService


class TestMachiningTimeIntegration:
    """Integration tests with real STEP files."""

    @pytest.fixture
    def step_file_path(self):
        """Get path to a real STEP file for testing."""
        # Use a STEP file from uploads/drawings if available
        step_file = Path("uploads/drawings/10383459_7f06bbe6.stp")
        if not step_file.exists():
            pytest.skip("STEP file not found for integration test")
        return step_file

    def test_estimate_time_real_step_file_alloy_steel(self, step_file_path):
        """Test time estimation with real STEP file - alloy steel."""
        result = MachiningTimeEstimationService.estimate_time(
            step_path=step_file_path,
            material="20910005",  # Alloy steel (42CrMo4, 16MnCr5)
            stock_type="bbox"
        )

        # Verify response structure
        assert "total_time_min" in result
        assert "roughing_time_min" in result
        assert "finishing_time_min" in result
        assert "setup_time_min" in result
        assert "breakdown" in result
        assert result["deterministic"] is True

        # Verify all times are positive and rounded
        assert result["total_time_min"] > 0
        assert result["roughing_time_min"] >= 0
        assert result["finishing_time_min"] > 0
        assert result["setup_time_min"] > 0

        # Verify total = roughing + finishing + setup
        expected_total = (
            result["roughing_time_min"] +
            result["finishing_time_min"] +
            result["setup_time_min"]
        )
        assert result["total_time_min"] == pytest.approx(expected_total, abs=0.01)

        # Verify breakdown structure
        breakdown = result["breakdown"]
        assert breakdown["material"] == "20910005"
        assert breakdown["material_category"] == "alloy_steel"
        assert breakdown["iso_group"] == "P"
        assert breakdown["stock_volume_mm3"] > 0
        assert breakdown["part_volume_mm3"] > 0
        assert breakdown["material_to_remove_mm3"] >= 0
        assert breakdown["surface_area_mm2"] > 0
        assert breakdown["constraint_multiplier"] >= 1.0

        # Print results for manual verification
        print(f"\n{'='*60}")
        print(f"INTEGRATION TEST RESULTS")
        print(f"{'='*60}")
        print(f"Material: {breakdown['material_category']} (ISO {breakdown['iso_group']})")
        print(f"Part volume: {breakdown['part_volume_mm3']:.2f} mm³")
        print(f"Stock volume: {breakdown['stock_volume_mm3']:.2f} mm³")
        print(f"Material to remove: {breakdown['material_to_remove_mm3']:.2f} mm³")
        print(f"Surface area: {breakdown['surface_area_mm2']:.2f} mm²")
        print(f"Constraint multiplier: {breakdown['constraint_multiplier']:.2f}")
        print(f"Constraints: {breakdown['critical_constraints']}")
        print(f"\nTIME BREAKDOWN:")
        print(f"  Roughing: {result['roughing_time_min']:.2f} min")
        print(f"  Finishing: {result['finishing_time_min']:.2f} min")
        print(f"  Setup: {result['setup_time_min']:.2f} min")
        print(f"  TOTAL: {result['total_time_min']:.2f} min ({result['total_time_min']/60:.2f} hours)")
        print(f"{'='*60}\n")

    def test_estimate_time_real_step_file_aluminum(self, step_file_path):
        """Test time estimation with real STEP file - aluminum."""
        result = MachiningTimeEstimationService.estimate_time(
            step_path=step_file_path,
            material="20910000",  # Aluminum
            stock_type="cylinder"
        )

        # Verify aluminum has faster machining times than steel
        # (higher MRR: 800 cm³/min vs 180 cm³/min for alloy steel)
        assert result["total_time_min"] > 0
        assert result["breakdown"]["material_category"] == "aluminum"
        assert result["breakdown"]["iso_group"] == "N"

    def test_estimate_time_real_step_file_stainless(self, step_file_path):
        """Test time estimation with real STEP file - stainless steel."""
        result = MachiningTimeEstimationService.estimate_time(
            step_path=step_file_path,
            material="20910007",  # Stainless steel
            stock_type="bbox"
        )

        # Verify stainless has slower machining times (low MRR: 150 cm³/min)
        assert result["total_time_min"] > 0
        assert result["breakdown"]["material_category"] == "stainless_steel"
        assert result["breakdown"]["iso_group"] == "M"

    def test_determinism_multiple_runs(self, step_file_path):
        """Test that multiple runs with same input produce identical results."""
        result1 = MachiningTimeEstimationService.estimate_time(
            step_path=step_file_path,
            material="20910005",
            stock_type="bbox"
        )

        result2 = MachiningTimeEstimationService.estimate_time(
            step_path=step_file_path,
            material="20910005",
            stock_type="bbox"
        )

        # All values must be identical (deterministic)
        assert result1["total_time_min"] == result2["total_time_min"]
        assert result1["roughing_time_min"] == result2["roughing_time_min"]
        assert result1["finishing_time_min"] == result2["finishing_time_min"]
        assert result1["setup_time_min"] == result2["setup_time_min"]
        assert result1["breakdown"] == result2["breakdown"]
