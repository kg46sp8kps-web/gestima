"""
Visualize contours from batch log (no API needed)

Extracts geometry from log and generates SVG files.
"""

import re
import json
from pathlib import Path

# Extracted data from batch log
BATCH_RESULTS = [
    {
        "file": "JR 810665.ipt.step",
        "part_type": "rotational",
        "max_diameter": 9,
        "length": 88,
        "outer_points": 10,
        "inner_points": 9,
        "material": "1.4305 X8CrNiS18-9",
    },
    {
        "file": "JR 810671.ipt.step",
        "part_type": "rotational",
        "max_diameter": 12,
        "length": 49,
        "outer_points": 10,
        "inner_points": 4,
        "material": "1.4305 X8CrNiS18-9",
    },
    {
        "file": "JR 810670.ipt.step",
        "part_type": "rotational",
        "max_diameter": 36,
        "length": 24,
        "outer_points": 10,
        "inner_points": 12,
        "material": "1.4305 X8CrNiS18-9",
    },
    {
        "file": "3DM_90057637_000_00.stp",
        "part_type": "rotational",
        "max_diameter": 75,
        "length": 58,
        "outer_points": 10,
        "inner_points": 2,
        "material": "Unknown",
    },
]

def generate_simple_svg(data):
    """Generate simple SVG representation of rotational part."""
    max_d = data["max_diameter"]
    length = data["length"]

    # Scale factors
    scale_x = 400 / max(length, 1)
    scale_y = 200 / max(max_d, 1)

    svg_width = 600
    svg_height = 400
    margin = 50

    # Center line
    center_y = svg_height // 2

    # Outer contour (simplified rectangle for now)
    outer_height = max_d * scale_y
    outer_width = length * scale_x

    svg = f'''<svg width="{svg_width}" height="{svg_height}" xmlns="http://www.w3.org/2000/svg">
    <style>
        .axis {{ stroke: #ccc; stroke-width: 1; stroke-dasharray: 5,5; }}
        .outer {{ fill: none; stroke: red; stroke-width: 2; }}
        .inner {{ fill: none; stroke: blue; stroke-width: 2; }}
        .dimension {{ fill: #333; font-size: 12px; font-family: monospace; }}
        .label {{ fill: #666; font-size: 10px; font-family: monospace; }}
    </style>

    <!-- Centerline (Z-axis) -->
    <line class="axis" x1="{margin}" y1="{center_y}" x2="{svg_width - margin}" y2="{center_y}" />

    <!-- Outer contour (profile) -->
    <rect class="outer"
          x="{margin}"
          y="{center_y - outer_height/2}"
          width="{outer_width}"
          height="{outer_height}" />

    <!-- Inner contour (bore) if exists -->
    {f'<rect class="inner" x="{margin}" y="{center_y - 10}" width="{outer_width * 0.8}" height="20" />' if data["inner_points"] > 0 else ''}

    <!-- Dimensions -->
    <text class="dimension" x="{margin + outer_width/2}" y="{center_y - outer_height/2 - 10}" text-anchor="middle">
        Ø{max_d} mm
    </text>

    <text class="dimension" x="{margin + outer_width/2}" y="{svg_height - 20}" text-anchor="middle">
        L = {length} mm
    </text>

    <!-- Labels -->
    <text class="label" x="{margin}" y="20">{data["file"]}</text>
    <text class="label" x="{margin}" y="35">Part: {data["part_type"]}</text>
    <text class="label" x="{margin}" y="50">Material: {data["material"][:30]}</text>
    <text class="label" x="{margin}" y="65">Contour: {data["outer_points"]} outer + {data["inner_points"]} inner pts</text>

    <!-- Legend -->
    <line class="outer" x1="{svg_width - 150}" y1="30" x2="{svg_width - 100}" y2="30" />
    <text class="label" x="{svg_width - 90}" y="35">Outer contour</text>

    <line class="inner" x1="{svg_width - 150}" y1="50" x2="{svg_width - 100}" y2="50" />
    <text class="label" x="{svg_width - 90}" y="55">Inner bore</text>
</svg>'''

    return svg


def main():
    output_dir = Path("svg_visualizations")
    output_dir.mkdir(exist_ok=True)

    print("Generating SVG visualizations...")

    for data in BATCH_RESULTS:
        svg = generate_simple_svg(data)

        filename = data["file"].replace(".step", "").replace(".stp", "") + ".svg"
        output_path = output_dir / filename

        with open(output_path, 'w') as f:
            f.write(svg)

        print(f"✓ {filename}")

    # Generate index HTML
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Batch Results Visualization</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(600px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        img { max-width: 100%; height: auto; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>🔍 Batch Test Visualizations (4 Rotational Parts)</h1>
    <p>Simplified SVG contours from batch log data (no API needed)</p>

    <div class="grid">
'''

    for data in BATCH_RESULTS:
        filename = data["file"].replace(".step", "").replace(".stp", "") + ".svg"
        html += f'''
        <div class="card">
            <h3>{data["file"]}</h3>
            <img src="{filename}" alt="{data['file']}" />
            <p><strong>Dimensions:</strong> Ø{data["max_diameter"]}mm × {data["length"]}mm</p>
            <p><strong>Contour:</strong> {data["outer_points"]} outer + {data["inner_points"]} inner points</p>
        </div>
'''

    html += '''
    </div>
</body>
</html>'''

    index_path = output_dir / "index.html"
    with open(index_path, 'w') as f:
        f.write(html)

    print(f"\n✅ Generated {len(BATCH_RESULTS)} SVG files")
    print(f"📂 Output: {output_dir.absolute()}")
    print(f"🌐 Open: file://{index_path.absolute()}")


if __name__ == "__main__":
    main()
