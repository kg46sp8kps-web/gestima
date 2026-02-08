"""Unit tests for tool_selection_catalog.py

Tests:
- ISO group mapping
- Tool selection by diameter
- Fallback logic (ISO P default)
- Catalog statistics
"""

import pytest
from app.services.tool_selection_catalog import (
    select_tool,
    get_iso_group_from_material,
    get_all_tools_for_operation,
    get_tool_catalog_stats,
    TOOL_CATALOG,
)


class TestISOGroupMapping:
    """Test material group to ISO group conversion."""

    def test_steel_structural(self):
        """Konstrukční ocel → ISO P"""
        assert get_iso_group_from_material("20910004") == "P"

    def test_steel_automatic(self):
        """Automatová ocel → ISO P"""
        assert get_iso_group_from_material("20910003") == "P"

    def test_steel_alloy(self):
        """Legovaná ocel → ISO P"""
        assert get_iso_group_from_material("20910005") == "P"

    def test_stainless(self):
        """Nerez → ISO M"""
        assert get_iso_group_from_material("20910007") == "M"

    def test_aluminum(self):
        """Hliník → ISO N"""
        assert get_iso_group_from_material("20910000") == "N"

    def test_brass(self):
        """Mosaz → ISO N"""
        assert get_iso_group_from_material("20910002") == "N"

    def test_tool_steel(self):
        """Nástrojová ocel → ISO H (hardened materials)"""
        assert get_iso_group_from_material("20910006") == "H"

    def test_unknown_defaults_to_p(self):
        """Unknown material → fallback ISO P"""
        assert get_iso_group_from_material("99999999") == "P"


class TestToolSelection:
    """Test tool selection logic."""

    def test_turning_roughing_steel(self):
        """Turning roughing in steel → CNMG insert"""
        tool = select_tool("turning", "hrubovani", "20910004", diameter=50)
        assert tool["tool_code"] == "CNMG_INSERT"
        assert "CNMG" in tool["tool_name"]

    def test_turning_finishing_steel(self):
        """Turning finishing in steel → DNMG insert"""
        tool = select_tool("turning", "dokoncovani", "20910004", diameter=30)
        assert tool["tool_code"] == "DNMG_INSERT"
        assert "DNMG" in tool["tool_name"]

    def test_drilling_small_diameter_hss(self):
        """Drilling Ø8 in steel → HSS drill"""
        tool = select_tool("drilling", "vrtani", "20910004", diameter=8.0)
        assert tool["tool_code"] == "HSS_DRILL"
        assert "HSS" in tool["tool_name"]

    def test_drilling_mid_diameter_carbide(self):
        """Drilling Ø15 in steel → Carbide drill"""
        tool = select_tool("drilling", "vrtani", "20910004", diameter=15.0)
        assert tool["tool_code"] == "CARBIDE_DRILL"
        assert "VHM" in tool["tool_name"]

    def test_drilling_large_diameter_indexable(self):
        """Drilling Ø25 in steel → Indexable drill"""
        tool = select_tool("drilling", "vrtani", "20910004", diameter=25.0)
        assert tool["tool_code"] == "INDEX_DRILL"
        assert "výměnnými břity" in tool["tool_name"]

    def test_milling_endmill_selection(self):
        """Milling Ø15 roughing → Endmill Ø12"""
        tool = select_tool("milling", "hrubovani", "20910004", diameter=15.0)
        assert tool["tool_code"] == "ENDMILL_12"
        assert "Ø12" in tool["tool_name"]

    def test_threading_external(self):
        """External threading M30 → Thread insert"""
        tool = select_tool("threading", "zavitovani", "20910004", diameter=30.0)
        assert tool["tool_code"] == "THREAD_INSERT_OD"
        assert "vnější" in tool["tool_name"]

    def test_parting_off(self):
        """Parting off Ø40 → Parting insert"""
        tool = select_tool("parting", "upichnuti", "20910004", diameter=40.0)
        assert tool["tool_code"] == "PARTING_INSERT"
        assert "Upichovací" in tool["tool_name"]


class TestMaterialSpecificTools:
    """Test material-specific tool selection."""

    def test_stainless_steel_drilling(self):
        """Drilling in stainless → HSS-Co drill"""
        tool = select_tool("drilling", "vrtani", "20910007", diameter=8.0)
        assert "INOX" in tool["tool_code"] or "nerez" in tool["tool_name"].lower()

    def test_aluminum_milling(self):
        """Milling aluminum → Aluminum-optimized endmill"""
        tool = select_tool("milling", "hrubovani", "20910000", diameter=10.0)
        assert "ALU" in tool["tool_code"] or "hliník" in tool["tool_name"].lower()

    def test_stainless_turning_roughing(self):
        """Turning roughing stainless → CNMG INOX"""
        tool = select_tool("turning", "hrubovani", "20910007", diameter=30.0)
        assert tool["tool_code"] == "CNMG_INOX"


class TestFallbackLogic:
    """Test fallback mechanisms."""

    def test_fallback_to_iso_p(self):
        """Unknown ISO group → fallback to P (steel)"""
        # Use material K (tool steel), but operation only defined for P
        tool = select_tool("threading", "zavitovani", "20910006", diameter=20.0)
        # Should fallback to P and return thread insert
        assert "THREAD" in tool["tool_code"]

    def test_no_diameter_returns_first_tool(self):
        """No diameter specified → return first (smallest) tool"""
        tool = select_tool("drilling", "vrtani", "20910004")
        assert tool["tool_code"] == "HSS_DRILL"  # First in list (Ø1-10)

    def test_diameter_out_of_range_returns_last_tool(self):
        """Diameter outside all ranges → return largest range tool"""
        tool = select_tool("drilling", "vrtani", "20910004", diameter=150.0)
        # Should return largest drill range (Ø40-100)
        assert "LARGE" in tool["tool_code"] or tool["dia_max"] >= 40


class TestCatalogStatistics:
    """Test catalog metadata and statistics."""

    def test_catalog_not_empty(self):
        """Catalog should contain tool entries"""
        assert len(TOOL_CATALOG) > 0

    def test_catalog_stats(self):
        """Catalog stats should return valid counts"""
        stats = get_tool_catalog_stats()
        assert stats["total_entries"] > 0
        assert stats["operations_covered"] > 0
        assert "P" in stats["materials_covered"]
        assert "M" in stats["materials_covered"]
        assert "N" in stats["materials_covered"]

    def test_catalog_has_turning_operations(self):
        """Catalog should cover turning operations"""
        stats = get_tool_catalog_stats()
        operations = stats["operations_list"]
        assert "turning/hrubovani" in operations
        assert "turning/dokoncovani" in operations

    def test_catalog_has_drilling_operations(self):
        """Catalog should cover drilling operations"""
        stats = get_tool_catalog_stats()
        operations = stats["operations_list"]
        assert "drilling/vrtani" in operations
        assert "drilling/vystruzovani" in operations

    def test_catalog_has_milling_operations(self):
        """Catalog should cover milling operations"""
        stats = get_tool_catalog_stats()
        operations = stats["operations_list"]
        assert "milling/hrubovani" in operations
        assert "milling/dokoncovani" in operations


class TestGetAllTools:
    """Test retrieving all tools for an operation."""

    def test_get_all_drilling_tools_steel(self):
        """Get all drilling tools for steel"""
        tools = get_all_tools_for_operation("drilling", "vrtani", "20910004")
        assert len(tools) > 0
        # Should have multiple diameter ranges (HSS, carbide, indexable)
        assert len(tools) >= 3

    def test_get_all_tools_returns_copies(self):
        """Ensure returned tools are copies (not references)"""
        tools = get_all_tools_for_operation("drilling", "vrtani", "20910004")
        # Modify returned tool
        tools[0]["tool_code"] = "MODIFIED"
        # Get again - should be original
        tools2 = get_all_tools_for_operation("drilling", "vrtani", "20910004")
        assert tools2[0]["tool_code"] != "MODIFIED"


class TestDeterminism:
    """Test consistency - same input always produces same output."""

    def test_same_tool_selection_deterministic(self):
        """Same parameters → same tool (100% consistency)"""
        tool1 = select_tool("drilling", "vrtani", "20910004", 15.0)
        tool2 = select_tool("drilling", "vrtani", "20910004", 15.0)
        assert tool1 == tool2

    def test_multiple_calls_identical(self):
        """Call select_tool 10x → identical results"""
        results = [
            select_tool("turning", "hrubovani", "20910004", 50.0)
            for _ in range(10)
        ]
        # All results should be identical
        assert all(r == results[0] for r in results)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_material_group(self):
        """Empty material group → defaults to P"""
        tool = select_tool("turning", "hrubovani", "", diameter=30.0)
        assert tool  # Should return something (fallback to P)

    def test_none_material_group(self):
        """None material group → defaults to P"""
        tool = select_tool("turning", "hrubovani", None, diameter=30.0)
        assert tool  # Should return something (fallback to P)

    def test_zero_diameter(self):
        """Diameter = 0 → should handle gracefully"""
        tool = select_tool("drilling", "vrtani", "20910004", diameter=0.0)
        # Out of range → fallback to last tool (largest range)
        assert tool["tool_code"] == "INDEX_DRILL_LARGE"

    def test_negative_diameter(self):
        """Negative diameter → should handle gracefully"""
        tool = select_tool("drilling", "vrtani", "20910004", diameter=-5.0)
        # Out of range → fallback to last tool (largest range)
        assert tool["tool_code"] == "INDEX_DRILL_LARGE"

    def test_invalid_operation_type(self):
        """Invalid operation_type → returns empty dict"""
        tool = select_tool("invalid_type", "invalid_op", "20910004")
        assert tool == {}

    def test_invalid_operation(self):
        """Valid type, invalid operation → returns empty dict"""
        tool = select_tool("turning", "invalid_operation", "20910004")
        assert tool == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
