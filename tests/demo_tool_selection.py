#!/usr/bin/env python3
"""Demo script: Tool Selection Catalog in action

Shows how tool selection catalog works for real-world scenarios.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.tool_selection_catalog import (
    select_tool,
    get_tool_catalog_stats,
    get_all_tools_for_operation,
)

print("=" * 70)
print("GESTIMA - Tool Selection Catalog Demo")
print("=" * 70)

# === SCENARIO 1: Turning part (PDM-249322) ===
print("\n📌 SCENARIO 1: Turning hřídel C45 (Ø55mm)")
print("-" * 70)

material = "20910004"  # C45 konstrukční ocel

# Roughing OD
tool = select_tool("turning", "hrubovani", material, diameter=55.0)
print(f"  Hrubování OD Ø55: {tool['tool_name']} ({tool['tool_code']})")

# Finishing OD
tool = select_tool("turning", "dokoncovani", material, diameter=55.0)
print(f"  Dokončování OD Ø55: {tool['tool_name']} ({tool['tool_code']})")

# Drilling hole Ø19
tool = select_tool("drilling", "vrtani", material, diameter=19.0)
print(f"  Vrtání Ø19: {tool['tool_name']} ({tool['tool_code']})")

# Reaming H7
tool = select_tool("drilling", "vystruzovani", material, diameter=19.0)
print(f"  Vystružení Ø19 H7: {tool['tool_name']} ({tool['tool_code']})")

# Threading M30×2
tool = select_tool("threading", "zavitovani", material, diameter=30.0)
print(f"  Závit M30×2: {tool['tool_name']} ({tool['tool_code']})")

# Parting off
tool = select_tool("parting", "upichnuti", material, diameter=55.0)
print(f"  Upíchnutí Ø55: {tool['tool_name']} ({tool['tool_code']})")

# === SCENARIO 2: Stainless steel part ===
print("\n\n📌 SCENARIO 2: Stainless steel part (X5CrNi18-10)")
print("-" * 70)

material_inox = "20910007"  # Nerez

tool = select_tool("turning", "hrubovani", material_inox, diameter=40.0)
print(f"  Hrubování OD Ø40: {tool['tool_name']} ({tool['tool_code']})")

tool = select_tool("drilling", "vrtani", material_inox, diameter=10.0)
print(f"  Vrtání Ø10: {tool['tool_name']} ({tool['tool_code']})")

# === SCENARIO 3: Aluminum milling ===
print("\n\n📌 SCENARIO 3: Aluminum milling part (AlMg3)")
print("-" * 70)

material_alu = "20910000"  # Hliník

tool = select_tool("milling", "hrubovani", material_alu, diameter=12.0)
print(f"  Frézování pocket Ø12: {tool['tool_name']} ({tool['tool_code']})")

tool = select_tool("milling", "dokoncovani", material_alu, diameter=8.0)
print(f"  Dokončování Ø8: {tool['tool_name']} ({tool['tool_code']})")

tool = select_tool("drilling", "vrtani", material_alu, diameter=6.0)
print(f"  Vrtání Ø6: {tool['tool_name']} ({tool['tool_code']})")

# === SCENARIO 4: Diameter-specific tool selection ===
print("\n\n📌 SCENARIO 4: Drilling - diameter-specific tool selection")
print("-" * 70)

diameters = [3.0, 8.0, 15.0, 25.0, 50.0]
for dia in diameters:
    tool = select_tool("drilling", "vrtani", "20910004", diameter=dia)
    print(f"  Vrtání Ø{dia}: {tool['tool_name']} ({tool['tool_code']})")

# === SCENARIO 5: Show all available tools for drilling ===
print("\n\n📌 SCENARIO 5: All available drilling tools for steel")
print("-" * 70)

tools = get_all_tools_for_operation("drilling", "vrtani", "20910004")
for i, tool in enumerate(tools, 1):
    print(f"  {i}. {tool['tool_name']} ({tool['tool_code']})")
    print(f"     Range: Ø{tool['dia_min']}-{tool['dia_max']}mm")
    print(f"     Notes: {tool['notes']}")

# === CATALOG STATISTICS ===
print("\n\n📊 CATALOG STATISTICS")
print("=" * 70)

stats = get_tool_catalog_stats()
print(f"  Total catalog entries: {stats['total_entries']}")
print(f"  Operations covered: {stats['operations_covered']}")
print(f"  Materials covered: {', '.join(stats['materials_covered'])}")

print("\n  Operations list:")
for op in sorted(stats['operations_list']):
    print(f"    - {op}")

print("\n\n✅ Tool Selection Catalog Demo Complete!")
print("=" * 70)
