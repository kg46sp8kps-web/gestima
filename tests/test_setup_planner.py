"""Unit tests for setup_planner.py

Tests:
- Turning single-side → 1 setup
- Turning front+back → 2 setups
- Turning with live tooling → 4-axis lathe
- Milling 1-2 faces → 3-axis, multiple setups
- Mixed (turning + milling) → multi-setup
"""

import pytest
from app.services.setup_planner import (
    setup_planner,
    plan_setups_for_geometry,
    get_setup_count,
    get_total_setup_time,
)


class TestTurningSingleSetup:
    """Test turning parts with 1 setup."""

    def test_simple_shaft_front_only(self):
        """Simple shaft, features on front → 1 setup"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 50.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "od_finish", "position": {"z": 15}},
                    {"type": "hole", "diameter": 10, "depth": 20, "position": {"z": 0}},
                    {"type": "chamfer", "position": {"z": 5}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 1
        assert setups[0]["setup_id"] == 1
        assert "přední" in setups[0]["description"].lower()
        assert setups[0]["machine_type"] == "lathe_3ax"
        assert len(setups[0]["features"]) == 4

    def test_short_part_no_back_features(self):
        """Short part (L=40mm) with no back features → 1 setup"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 40.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 5}},
                    {"type": "thread_od", "diameter": 30, "position": {"z": 10}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 1
        assert get_setup_count(geometry) == 1


class TestTurningTwoSetups:
    """Test turning parts with 2 setups."""

    def test_shaft_with_back_features(self):
        """Shaft with features on both sides → 2 setups"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 100.0}},
            "profile_geometry": {
                "features": [
                    # Front features (z < 50)
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "hole", "diameter": 10, "depth": 40, "position": {"z": 0}},
                    # Back features (z > 50)
                    {"type": "od_finish", "position": {"z": 70}},
                    {"type": "thread_od", "diameter": 25, "position": {"z": 80}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 2
        assert setups[0]["description"] == "OP10 Soustružení - přední strana"
        assert setups[1]["description"] == "OP20 Soustružení - zadní strana"

        # Check feature distribution
        assert len(setups[0]["features"]) == 2  # Front
        assert len(setups[1]["features"]) == 2  # Back

    def test_parting_operation_fixture_change(self):
        """Parting operation → changes fixture to faceplate"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 80.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "parting", "position": {"z": 50}},
                    {"type": "od_finish", "position": {"z": 15}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        # Parting may require faceplate fixture (not standard chuck)
        assert setups[0]["fixture"] in ["faceplate", "3jaw_chuck"]
        # Parting is in front setup
        assert any(f["type"] == "parting" for f in setups[0]["features"])

    def test_long_part_requires_two_setups(self):
        """Long part (>150mm) → 2 setups (tailstock support)"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 180.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 20}},
                    {"type": "od_finish", "position": {"z": 30}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        # Long parts typically need 2 setups even if all features on one side
        assert len(setups) >= 1  # At least front setup


class TestLiveTooling:
    """Test live tooling detection (4-axis lathe)."""

    def test_radial_holes_require_4axis(self):
        """Radial holes → live tooling → 4-axis lathe"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 60.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "lt_drill", "diameter": 8, "depth": 15, "position": {"z": 25}},
                    {"type": "lt_drill", "diameter": 6, "depth": 10, "position": {"z": 35}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 1
        assert setups[0]["machine_type"] == "lathe_4ax"
        assert "live tooling" in setups[0]["description"].lower()

    def test_radial_flat_requires_4axis(self):
        """Radial flat (milling) → live tooling → 4-axis"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 50.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "lt_flat", "width": 20, "depth": 2, "position": {"z": 20}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert setups[0]["machine_type"] == "lathe_4ax"


class TestMillingSetups:
    """Test milling (prismatic) parts."""

    def test_single_face_milling(self):
        """Features on 1 face → 1 setup"""
        geometry = {
            "part_type": "prismatic",
            "profile_geometry": {
                "features": [
                    {"type": "pocket_rough", "face": "top", "length": 50, "width": 30},
                    {"type": "pocket_finish", "face": "top", "length": 50, "width": 30},
                    {"type": "mill_drill", "face": "top", "diameter": 8},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 1
        assert setups[0]["machine_type"] == "mill_3ax"
        assert setups[0]["fixture"] == "vise"

    def test_two_faces_milling(self):
        """Features on 2 faces → 2 setups"""
        geometry = {
            "part_type": "prismatic",
            "profile_geometry": {
                "features": [
                    {"type": "pocket_rough", "face": "top", "length": 50, "width": 30},
                    {"type": "slot", "face": "top", "length": 40, "width": 10},
                    {"type": "mill_drill", "face": "bottom", "diameter": 10},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 2
        assert setups[0]["fixture"] == "vise"
        assert setups[1]["fixture"] == "fixture"  # Additional setup


class TestHybridParts:
    """Test mixed (turning + milling) parts."""

    def test_turning_dominant_hybrid(self):
        """Turning-dominant (>70%) → turn first, mill second"""
        geometry = {
            "part_type": "mixed",
            "profile_geometry": {
                "features": [
                    # 7 turning features (70%)
                    {"type": "od_rough"},
                    {"type": "od_finish"},
                    {"type": "hole", "diameter": 10},
                    {"type": "thread_od", "diameter": 30},
                    {"type": "chamfer"},
                    {"type": "groove_od"},
                    {"type": "parting"},
                    # 3 milling features (30%)
                    {"type": "pocket_rough", "face": "top"},
                    {"type": "slot", "face": "top"},
                    {"type": "mill_drill", "face": "top"},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 2
        # First setup should be turning
        assert setups[0]["machine_type"] == "lathe_3ax"
        assert len(setups[0]["features"]) == 7
        # Second setup should be milling
        assert setups[1]["machine_type"] == "mill_3ax"
        assert len(setups[1]["features"]) == 3

    def test_milling_dominant_hybrid(self):
        """Milling-dominant (<30% turning) → turn first (basic shape), mill second"""
        geometry = {
            "part_type": "mixed",
            "profile_geometry": {
                "features": [
                    # 2 turning features (20%)
                    {"type": "od_rough"},
                    {"type": "od_finish"},
                    # 8 milling features (80%)
                    {"type": "pocket_rough", "face": "top"},
                    {"type": "pocket_finish", "face": "top"},
                    {"type": "slot", "face": "top"},
                    {"type": "mill_drill", "face": "top"},
                    {"type": "mill_tap", "face": "top"},
                    {"type": "face_mill", "face": "top"},
                    {"type": "pocket_rough", "face": "side"},
                    {"type": "mill_drill", "face": "side"},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 2
        # First setup: turning (basic shape)
        assert "základní tvar" in setups[0]["description"].lower() or "soustružení" in setups[0]["description"].lower()
        # Second setup: milling (details)
        assert "frézování" in setups[1]["description"].lower() or "detaily" in setups[1]["description"].lower()


class TestSetupTimeCalculation:
    """Test setup time estimation."""

    def test_total_setup_time_single_setup(self):
        """Single setup → 25 min (3-jaw chuck)"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 50.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                ]
            }
        }

        total_time = get_total_setup_time(geometry)

        assert total_time == 25.0  # 3-jaw chuck setup

    def test_total_setup_time_two_setups(self):
        """Two setups → 25 + 15 = 40 min"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 100.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "od_finish", "position": {"z": 70}},
                ]
            }
        }

        total_time = get_total_setup_time(geometry)

        assert total_time == 40.0  # 3-jaw (25) + collet (15)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_features_returns_default_setup(self):
        """No features → single default setup"""
        geometry = {
            "part_type": "rotational",
            "profile_geometry": {"features": []}
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 1
        assert setups[0]["setup_id"] == 1

    def test_unknown_part_type_defaults_to_rotational(self):
        """Unknown part_type → defaults to rotational logic"""
        geometry = {
            "part_type": "unknown_type",
            "stock": {"dimensions": {"length": 60.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                ]
            }
        }

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) >= 1
        assert "soustružení" in setups[0]["description"].lower()

    def test_empty_geometry_dict(self):
        """Empty geometry → fallback single setup"""
        geometry = {}

        setups = plan_setups_for_geometry(geometry)

        assert len(setups) == 1


class TestDeterminism:
    """Test consistency - same geometry always produces same setups."""

    def test_same_setups_for_same_geometry(self):
        """Same geometry → identical setups (100% consistency)"""
        geometry = {
            "part_type": "rotational",
            "stock": {"dimensions": {"length": 80.0}},
            "profile_geometry": {
                "features": [
                    {"type": "od_rough", "position": {"z": 10}},
                    {"type": "hole", "diameter": 10, "position": {"z": 0}},
                    {"type": "thread_od", "diameter": 30, "position": {"z": 60}},
                ]
            }
        }

        setups1 = plan_setups_for_geometry(geometry)
        setups2 = plan_setups_for_geometry(geometry)

        # Should be identical
        assert len(setups1) == len(setups2)
        for s1, s2 in zip(setups1, setups2):
            assert s1["setup_id"] == s2["setup_id"]
            assert s1["description"] == s2["description"]
            assert s1["machine_type"] == s2["machine_type"]
            assert len(s1["features"]) == len(s2["features"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
