"""GESTIMA - Unit tests for FRApplyService

Tests the conversion of Feature Recognition results into Operations + Features.
Focus on pure logic methods: _group_features_by_category, _map_suggestion_to_feature, _create_operation
"""

import pytest
from typing import Dict, List
from unittest.mock import MagicMock

from app.services.fr_apply_service import FRApplyService, CATEGORY_OPERATION_MAP
from app.schemas.feature_recognition import OperationSuggestion, FeatureRecognitionResponse
from app.models.enums import FeatureType


class TestGroupFeaturesByCategory:
    """Test _group_features_by_category logic"""

    def setup_method(self):
        """Initialize service for each test"""
        self.service = FRApplyService()

    def test_empty_operations_list(self):
        """Empty operations → empty groups"""
        result = self.service._group_features_by_category([])
        assert result == {}

    def test_turning_features_grouped_correctly(self):
        """face, od_rough, od_finish → turning category"""
        ops = [
            OperationSuggestion(
                operation_type="facing",
                tool="facing_tool",
                estimated_time_min=1.0,
                feature_type="face"
            ),
            OperationSuggestion(
                operation_type="od_roughing",
                tool="tool_od",
                estimated_time_min=2.0,
                feature_type="od_rough"
            ),
            OperationSuggestion(
                operation_type="od_finishing",
                tool="tool_od_finish",
                estimated_time_min=1.5,
                feature_type="od_finish"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "turning" in result
        assert len(result["turning"]) == 3
        assert all(op.feature_type in ["face", "od_rough", "od_finish"] for op in result["turning"])

    def test_drilling_features_merged_into_turning(self):
        """drill, tap, ream (drilling category) → merged into turning"""
        ops = [
            OperationSuggestion(
                operation_type="drilling",
                tool="drill_19",
                estimated_time_min=0.5,
                feature_type="drill"
            ),
            OperationSuggestion(
                operation_type="tapping",
                tool="tap_m30",
                estimated_time_min=0.8,
                feature_type="tap"
            ),
            OperationSuggestion(
                operation_type="reaming",
                tool="ream_tool",
                estimated_time_min=0.3,
                feature_type="ream"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "turning" in result
        assert len(result["turning"]) == 3
        assert "drilling" not in result

    def test_live_tooling_merged_into_turning(self):
        """lt_drill, lt_flat, lt_tap (live_tooling) → merged into turning"""
        ops = [
            OperationSuggestion(
                operation_type="lt_drilling",
                tool="live_drill",
                estimated_time_min=0.4,
                feature_type="lt_drill"
            ),
            OperationSuggestion(
                operation_type="lt_milling",
                tool="live_mill",
                estimated_time_min=0.6,
                feature_type="lt_flat"
            ),
            OperationSuggestion(
                operation_type="lt_tapping",
                tool="live_tap",
                estimated_time_min=0.5,
                feature_type="lt_tap"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "turning" in result
        assert len(result["turning"]) == 3
        assert "live_tooling" not in result

    def test_milling_features_grouped_separately(self):
        """mill_face, mill_pocket, mill_slot → milling category"""
        ops = [
            OperationSuggestion(
                operation_type="milling",
                tool="end_mill",
                estimated_time_min=1.2,
                feature_type="mill_face"
            ),
            OperationSuggestion(
                operation_type="pocketing",
                tool="pocket_mill",
                estimated_time_min=2.0,
                feature_type="mill_pocket"
            ),
            OperationSuggestion(
                operation_type="slotting",
                tool="slot_mill",
                estimated_time_min=1.5,
                feature_type="mill_slot"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "milling" in result
        assert len(result["milling"]) == 3
        assert "turning" not in result

    def test_grinding_features_grouped_separately(self):
        """grind_od, grind_id, grind_face → grinding category"""
        ops = [
            OperationSuggestion(
                operation_type="grinding",
                tool="grind_wheel_od",
                estimated_time_min=0.8,
                feature_type="grind_od"
            ),
            OperationSuggestion(
                operation_type="grinding",
                tool="grind_wheel_id",
                estimated_time_min=1.0,
                feature_type="grind_id"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "grinding" in result
        assert len(result["grinding"]) == 2

    def test_deburr_manual_creates_finishing_group(self):
        """deburr_manual → finishing (separate operation)"""
        ops = [
            OperationSuggestion(
                operation_type="manual_deburr",
                tool="file",
                estimated_time_min=2.0,
                feature_type="deburr_manual"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "finishing" in result
        assert len(result["finishing"]) == 1

    def test_inspect_creates_logistics_inspect_group(self):
        """inspect → logistics_inspect (separate operation)"""
        ops = [
            OperationSuggestion(
                operation_type="quality_check",
                tool="none",
                estimated_time_min=10.0,
                feature_type="inspect"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "logistics_inspect" in result
        assert len(result["logistics_inspect"]) == 1

    def test_wash_feature_is_excluded(self):
        """wash feature → skipped (not yet implemented)"""
        ops = [
            OperationSuggestion(
                operation_type="washing",
                tool="none",
                estimated_time_min=15.0,
                feature_type="wash"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "logistics" not in result
        assert "wash" not in result
        assert len(result) == 0

    def test_unknown_feature_type_skipped_with_warning(self, caplog):
        """Unknown feature type → skipped, warning logged"""
        ops = [
            OperationSuggestion(
                operation_type="unknown_op",
                tool="unknown_tool",
                estimated_time_min=1.0,
                feature_type="unknown_type"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert len(result) == 0
        # Warning should be logged

    def test_mixed_categories_all_preserved(self):
        """Mix of turning + milling + grinding features → separate groups"""
        ops = [
            OperationSuggestion(
                operation_type="facing",
                tool="tool",
                estimated_time_min=1.0,
                feature_type="face"
            ),
            OperationSuggestion(
                operation_type="milling",
                tool="mill",
                estimated_time_min=2.0,
                feature_type="mill_pocket"
            ),
            OperationSuggestion(
                operation_type="grinding",
                tool="grind",
                estimated_time_min=0.8,
                feature_type="grind_od"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert "turning" in result
        assert "milling" in result
        assert "grinding" in result
        assert len(result["turning"]) == 1
        assert len(result["milling"]) == 1
        assert len(result["grinding"]) == 1

    def test_operation_without_feature_type_skipped(self):
        """operation_type without feature_type → skipped"""
        ops = [
            OperationSuggestion(
                operation_type="some_op",
                tool="tool",
                estimated_time_min=1.0,
                feature_type=None
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert len(result) == 0


class TestMapSuggestionToFeature:
    """Test _map_suggestion_to_feature logic"""

    def setup_method(self):
        """Initialize service for each test"""
        self.service = FRApplyService()

    def test_maps_basic_geometry_params(self):
        """Maps from_diameter, to_diameter, length, depth from params"""
        suggestion = OperationSuggestion(
            operation_type="od_roughing",
            tool="tool",
            estimated_time_min=2.0,
            feature_type="od_rough",
            params={
                "from_diameter": 55.0,
                "to_diameter": 40.0,
                "length": 80.0,
                "depth": 2.0,
            }
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.seq == 1
        assert feature.from_diameter == 55.0
        assert feature.to_diameter == 40.0
        assert feature.length == 80.0
        assert feature.depth == 2.0

    def test_maps_cutting_conditions(self):
        """Maps Vc, f, Ap, fz from cutting_conditions"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"to_diameter": 19.0, "depth": 50.0},
            cutting_conditions={
                "Vc": 80.0,
                "f": 0.25,
                "Ap": 10.0,
                "fz": None,
            }
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.Vc == 80.0
        assert feature.f == 0.25
        assert feature.Ap == 10.0
        assert feature.fz is None

    def test_calculates_time_from_calculated_time_min(self):
        """Prefers calculated_time_min over estimated_time_min"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,  # Ignored
            feature_type="drill",
            params={"to_diameter": 19.0, "depth": 30.0},
            calculated_time_min=0.8,  # Used
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        # 0.8 min * 60 = 48.0 sec
        assert feature.predicted_time_sec == 48.0

    def test_falls_back_to_estimated_time_min(self):
        """Falls back to estimated_time_min if calculated_time_min is None"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"to_diameter": 19.0, "depth": 30.0},
            calculated_time_min=None,
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        # 0.5 min * 60 = 30.0 sec
        assert feature.predicted_time_sec == 30.0

    def test_uses_zero_time_if_both_times_missing(self):
        """Uses 0 if both calculated_time_min and estimated_time_min are None"""
        suggestion = OperationSuggestion(
            operation_type="deburr",
            tool="file",
            estimated_time_min=0.0,  # Zero (edge case)
            feature_type="deburr_manual",
            params={},
            calculated_time_min=None,
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.predicted_time_sec == 0.0

    def test_maps_feature_type_to_enum(self):
        """Converts feature_type string to FeatureType enum"""
        suggestion = OperationSuggestion(
            operation_type="facing",
            tool="tool",
            estimated_time_min=1.0,
            feature_type="face",
            params={}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.feature_type == FeatureType.FACE

    def test_defaults_to_face_on_invalid_feature_type(self):
        """Invalid feature_type → defaults to FACE with warning"""
        suggestion = OperationSuggestion(
            operation_type="unknown",
            tool="tool",
            estimated_time_min=1.0,
            feature_type="nonexistent_type",
            params={}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.feature_type == FeatureType.FACE

    def test_handles_none_params_gracefully(self):
        """params={} → feature created with all geometry fields as None"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={},
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.from_diameter is None
        assert feature.to_diameter is None
        assert feature.length is None
        assert feature.depth is None

    def test_handles_none_cutting_conditions_gracefully(self):
        """cutting_conditions=None → all cutting fields None"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"to_diameter": 19.0},
            cutting_conditions=None,
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.Vc is None
        assert feature.f is None
        assert feature.Ap is None
        assert feature.fz is None

    def test_maps_blade_width_with_default(self):
        """blade_width from params with default=3.0"""
        suggestion = OperationSuggestion(
            operation_type="cutoff",
            tool="parting_tool",
            estimated_time_min=0.3,
            feature_type="cutoff",
            params={"from_diameter": 55.0, "blade_width": 2.5}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.blade_width == 2.5

    def test_blade_width_defaults_to_3_when_missing(self):
        """blade_width defaults to 3.0 when not in params"""
        suggestion = OperationSuggestion(
            operation_type="cutoff",
            tool="parting_tool",
            estimated_time_min=0.3,
            feature_type="cutoff",
            params={"from_diameter": 55.0}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.blade_width == 3.0

    def test_maps_count_with_default(self):
        """count from params with default=1"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="lt_drill",
            params={"to_diameter": 19.0, "depth": 30.0, "count": 4}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.count == 4

    def test_count_defaults_to_1_when_missing(self):
        """count defaults to 1 when not in params"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"to_diameter": 19.0, "depth": 30.0}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.count == 1

    def test_maps_pocket_dimensions(self):
        """Maps pocket_length, pocket_width for milling"""
        suggestion = OperationSuggestion(
            operation_type="pocketing",
            tool="end_mill",
            estimated_time_min=2.0,
            feature_type="mill_pocket",
            params={
                "pocket_length": 50.0,
                "pocket_width": 30.0,
                "depth": 5.0,
                "corner_radius": 5.0,
            }
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.pocket_length == 50.0
        assert feature.pocket_width == 30.0
        assert feature.depth == 5.0
        assert feature.corner_radius == 5.0

    def test_maps_thread_pitch(self):
        """Maps thread_pitch for threading operations"""
        suggestion = OperationSuggestion(
            operation_type="threading",
            tool="thread_tool",
            estimated_time_min=0.5,
            feature_type="thread_od",
            params={"from_diameter": 30.0, "length": 20.0, "thread_pitch": 2.0}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.thread_pitch == 2.0

    def test_maps_to_diameter_from_diameter_param(self):
        """Maps to_diameter from 'diameter' param if 'to_diameter' missing"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"diameter": 19.0, "depth": 30.0}  # 'diameter' instead of 'to_diameter'
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.to_diameter == 19.0

    def test_maps_notes_to_note_field(self):
        """Maps suggestion.notes to feature.note"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"to_diameter": 19.0, "depth": 30.0},
            notes="This is a through hole"
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.note == "This is a through hole"

    def test_empty_notes_defaults_to_empty_string(self):
        """notes=None → feature.note = ''"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.5,
            feature_type="drill",
            params={"to_diameter": 19.0, "depth": 30.0},
            notes=None
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.note == ""


class TestCreateOperation:
    """Test _create_operation logic (DB mocking)"""

    def setup_method(self):
        """Initialize service and mock DB for each test"""
        self.service = FRApplyService()
        self.mock_db = MagicMock()

    def test_creates_operation_with_correct_name_for_turning(self):
        """Turning category → Operation name = 'Soustružení'"""
        features = [
            OperationSuggestion(
                operation_type="facing",
                tool="tool",
                estimated_time_min=1.0,
                feature_type="face",
                params={"from_diameter": 55.0}
            )
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.name == "Soustružení"
        assert op.type == "turning"

    def test_creates_operation_with_correct_name_for_milling(self):
        """Milling category → Operation name = 'Frézování'"""
        features = [
            OperationSuggestion(
                operation_type="milling",
                tool="mill",
                estimated_time_min=2.0,
                feature_type="mill_pocket",
                params={}
            )
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="milling", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.name == "Frézování"
        assert op.type == "milling"

    def test_creates_operation_with_correct_name_for_grinding(self):
        """Grinding category → Operation name = 'Broušení'"""
        features = [
            OperationSuggestion(
                operation_type="grinding",
                tool="wheel",
                estimated_time_min=1.0,
                feature_type="grind_od",
                params={}
            )
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="grinding", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.name == "Broušení"
        assert op.type == "grinding"

    def test_creates_operation_with_correct_name_for_finishing(self):
        """Finishing category → Operation name = 'Odjehlení'"""
        features = [
            OperationSuggestion(
                operation_type="deburr",
                tool="file",
                estimated_time_min=2.0,
                feature_type="deburr_manual",
                params={}
            )
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="finishing", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.name == "Odjehlení"
        assert op.type == "generic"

    def test_creates_operation_with_correct_name_for_logistics_inspect(self):
        """Logistics_inspect category → Operation name = 'Kontrola'"""
        features = [
            OperationSuggestion(
                operation_type="inspect",
                tool="none",
                estimated_time_min=10.0,
                feature_type="inspect",
                params={}
            )
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="logistics_inspect", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.name == "Kontrola"
        assert op.type == "generic"

    def test_creates_operation_with_correct_setup_time_per_category(self):
        """Each category has correct setup_time from CATEGORY_OPERATION_MAP"""
        features = []
        
        # Turning: 30.0 min
        op_turning = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        assert op_turning.setup_time_min == 30.0
        
        # Milling: 25.0 min
        op_milling = self.service._create_operation(
            self.mock_db, part_id=1, category="milling", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        assert op_milling.setup_time_min == 25.0
        
        # Grinding: 20.0 min
        op_grinding = self.service._create_operation(
            self.mock_db, part_id=1, category="grinding", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        assert op_grinding.setup_time_min == 20.0

    def test_sets_is_coop_for_coop_category(self):
        """Coop category → is_coop = True"""
        features = []
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="coop", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.is_coop is True

    def test_sets_operation_time_from_sum_of_features(self):
        """operation_time_min = sum(feature.predicted_time_sec) / 60"""
        features = [
            OperationSuggestion(
                operation_type="facing",
                tool="tool",
                estimated_time_min=0.5,  # 30 sec
                feature_type="face",
                params={}
            ),
            OperationSuggestion(
                operation_type="od_rough",
                tool="tool",
                estimated_time_min=1.0,  # 60 sec
                feature_type="od_rough",
                params={}
            ),
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        # 30 + 60 = 90 sec = 1.5 min
        assert op.operation_time_min == 1.5

    def test_creates_child_features_for_operation(self):
        """Creates Feature records as children of Operation"""
        features = [
            OperationSuggestion(
                operation_type="facing",
                tool="tool",
                estimated_time_min=0.5,
                feature_type="face",
                params={"from_diameter": 55.0, "depth": 2.0}
            ),
            OperationSuggestion(
                operation_type="od_rough",
                tool="tool",
                estimated_time_min=1.0,
                feature_type="od_rough",
                params={"from_diameter": 55.0, "to_diameter": 40.0}
            ),
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert len(op.features) == 2
        assert op.features[0].seq == 1
        assert op.features[0].feature_type == FeatureType.FACE
        assert op.features[1].seq == 2
        assert op.features[1].feature_type == FeatureType.OD_ROUGH

    def test_sets_audit_fields_on_operation(self):
        """Operation has audit fields set (created_by)"""
        features = []
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="admin", feature_recognition_id=None
        )
        
        assert op.created_by == "admin"

    def test_sets_audit_fields_on_child_features(self):
        """Child features have audit fields set (created_by)"""
        features = [
            OperationSuggestion(
                operation_type="facing",
                tool="tool",
                estimated_time_min=0.5,
                feature_type="face",
                params={}
            )
        ]
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="operator", feature_recognition_id=None
        )
        
        assert op.features[0].created_by == "operator"

    def test_sets_cutting_mode_on_operation(self):
        """Operation.cutting_mode = cutting_mode parameter"""
        features = []
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="high", username="test", feature_recognition_id=None
        )
        
        assert op.cutting_mode == "high"

    def test_sets_part_id_on_operation(self):
        """Operation.part_id = part_id parameter"""
        features = []
        op = self.service._create_operation(
            self.mock_db, part_id=42, category="turning", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.part_id == 42

    def test_sets_seq_on_operation(self):
        """Operation.seq = seq parameter"""
        features = []
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=30, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        assert op.seq == 30

    def test_operation_not_yet_committed(self):
        """Created Operation object is not committed (ready for caller to flush/commit)"""
        features = []
        op = self.service._create_operation(
            self.mock_db, part_id=1, category="turning", features=features,
            seq=10, cutting_mode="mid", username="test", feature_recognition_id=None
        )
        
        # Operation should have id=None since it's not flushed
        assert op.id is None


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def setup_method(self):
        """Initialize service for each test"""
        self.service = FRApplyService()

    def test_feature_response_with_zero_operations(self):
        """FeatureRecognitionResponse with empty operations list"""
        fr_response = FeatureRecognitionResponse(
            source="pattern_matching",
            confidence=0.95,
            operations=[]
        )
        result = self.service._group_features_by_category(fr_response.operations or [])
        
        assert result == {}

    def test_feature_response_with_only_wash_operations(self):
        """All operations are 'wash' → all filtered out → empty groups"""
        ops = [
            OperationSuggestion(
                operation_type="washing",
                tool="none",
                estimated_time_min=15.0,
                feature_type="wash"
            ),
            OperationSuggestion(
                operation_type="washing",
                tool="none",
                estimated_time_min=15.0,
                feature_type="wash"
            ),
        ]
        result = self.service._group_features_by_category(ops)
        
        assert len(result) == 0

    def test_time_rounding_precision(self):
        """predicted_time_sec is rounded to 1 decimal place"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="drill",
            estimated_time_min=0.123456,  # 7.40736 sec
            feature_type="drill",
            params={}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        # Should be rounded to 1 decimal
        assert feature.predicted_time_sec == round(0.123456 * 60, 1)

    def test_zero_time_operations(self):
        """estimated_time_min=0 → predicted_time_sec=0"""
        suggestion = OperationSuggestion(
            operation_type="marking",
            tool="marker",
            estimated_time_min=0.0,
            feature_type="face",
            params={}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.predicted_time_sec == 0.0

    def test_large_time_values(self):
        """Large time values are handled correctly"""
        suggestion = OperationSuggestion(
            operation_type="long_operation",
            tool="tool",
            estimated_time_min=100.0,  # 6000 sec
            feature_type="face",
            params={}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.predicted_time_sec == 6000.0

    def test_large_diameter_values(self):
        """Large diameter values are handled correctly"""
        suggestion = OperationSuggestion(
            operation_type="od_rough",
            tool="tool",
            estimated_time_min=1.0,
            feature_type="od_rough",
            params={"from_diameter": 500.0, "to_diameter": 450.0}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.from_diameter == 500.0
        assert feature.to_diameter == 450.0

    def test_very_small_geometry_values(self):
        """Very small (but valid) geometry values"""
        suggestion = OperationSuggestion(
            operation_type="drilling",
            tool="micro_drill",
            estimated_time_min=0.1,
            feature_type="drill",
            params={"to_diameter": 0.5, "depth": 1.0}
        )
        feature = self.service._map_suggestion_to_feature(suggestion, seq=1)
        
        assert feature.to_diameter == 0.5
        assert feature.depth == 1.0
