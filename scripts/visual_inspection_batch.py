"""
Visual Inspection Batch Test

Calls backend API for all STEP+PDF pairs and generates visual inspection report.
User will manually review each result in browser.

Usage:
    python scripts/visual_inspection_batch.py

Then open: http://localhost:8000/visual-inspection-report.html
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BACKEND_URL = "http://localhost:8000"
DRAWINGS_DIR = Path("uploads/drawings")


def find_step_pdf_pairs() -> List[Dict[str, str]]:
    """Find all STEP+PDF pairs."""
    step_files = list(DRAWINGS_DIR.glob("*.stp")) + list(DRAWINGS_DIR.glob("*.step"))

    pairs = []
    for step_file in sorted(step_files):
        # Look for matching PDF
        base_name = step_file.stem
        pdf_candidates = [
            DRAWINGS_DIR / f"{base_name}.pdf",
            DRAWINGS_DIR / f"{base_name}_Gelso.pdf",
            DRAWINGS_DIR / f"{base_name.replace('_3D', '_2D')}_Gelso.pdf",
            DRAWINGS_DIR / f"{base_name.replace('.1', '.3')}_2D_Gelso.pdf",
        ]

        # Special case mappings
        special_mappings = {
            "10138363-01_21.03.2024": "10138363_01 Kunde_Gelso.pdf",
            "3DM_90057637_000_00": "DRM_90057637_DE0_00.pdf",
        }

        if base_name in special_mappings:
            pdf_candidates.insert(0, DRAWINGS_DIR / special_mappings[base_name])

        pdf_file = None
        for candidate in pdf_candidates:
            if candidate.exists():
                pdf_file = candidate
                break

        if pdf_file:
            pairs.append({
                "step": step_file.name,
                "pdf": pdf_file.name,
                "step_path": str(step_file),
                "pdf_path": str(pdf_file)
            })
        else:
            logger.warning(f"No PDF found for {step_file.name}")

    return pairs


async def test_single_pair(client: httpx.AsyncClient, pair: Dict[str, str], index: int, total: int) -> Dict[str, Any]:
    """Test single STEP+PDF pair via backend API."""
    logger.info(f"[{index}/{total}] Testing: {pair['step']}")

    try:
        # Upload files to backend
        with open(pair['step_path'], 'rb') as step_f, open(pair['pdf_path'], 'rb') as pdf_f:
            files = {
                'step_file': (pair['step'], step_f, 'application/octet-stream'),
                'pdf_file': (pair['pdf'], pdf_f, 'application/pdf'),
            }

            response = await client.post(
                f"{BACKEND_URL}/api/feature-recognition/analyze",
                files=files,
                data={"pipeline": "deterministic"},  # Use AI Vision pipeline
                timeout=120.0
            )

        if response.status_code == 200:
            result = response.json()

            # Extract key metrics
            profile = result.get("profile_geometry", {})
            outer = profile.get("outer_contour", [])
            inner = profile.get("inner_contour", [])
            features = profile.get("features", [])

            max_diameter = max((pt.get("r", 0) * 2 for pt in outer), default=0)
            total_length = max((pt.get("z", 0) for pt in outer), default=0)
            bore_diameter = max((pt.get("r", 0) * 2 for pt in inner), default=0) if inner else 0

            return {
                "index": index,
                "filename": pair['step'],
                "pdf": pair['pdf'],
                "status": "success",
                "part_type": result.get("part_type"),
                "material": result.get("material_spec"),
                "confidence": result.get("confidence", 0),
                "metrics": {
                    "max_diameter": round(max_diameter, 1),
                    "total_length": round(total_length, 1),
                    "bore_diameter": round(bore_diameter, 1),
                    "outer_points": len(outer),
                    "inner_points": len(inner),
                    "features_count": len(features)
                },
                "features": features,
                "svg_data": result.get("profile_svg_base64", ""),
                "raw_result": result
            }
        else:
            logger.error(f"API error {response.status_code}: {response.text[:200]}")
            return {
                "index": index,
                "filename": pair['step'],
                "pdf": pair['pdf'],
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:100]}"
            }

    except Exception as e:
        logger.error(f"Error testing {pair['step']}: {e}")
        return {
            "index": index,
            "filename": pair['step'],
            "pdf": pair['pdf'],
            "status": "error",
            "error": str(e)
        }


async def run_batch_test():
    """Run batch test on all pairs."""
    logger.info("="*80)
    logger.info("VISUAL INSPECTION BATCH TEST")
    logger.info("="*80)

    # Find pairs
    pairs = find_step_pdf_pairs()
    logger.info(f"Found {len(pairs)} STEP+PDF pairs\n")

    # Test each pair
    results = []
    async with httpx.AsyncClient() as client:
        for i, pair in enumerate(pairs, 1):
            result = await test_single_pair(client, pair, i, len(pairs))
            results.append(result)

            # Show quick summary
            if result["status"] == "success":
                m = result["metrics"]
                logger.info(
                    f"  ✓ Ø{m['max_diameter']:.0f}mm × {m['total_length']:.0f}mm, "
                    f"{m['outer_points']}+{m['inner_points']} pts, "
                    f"{m['features_count']} features, "
                    f"conf={result['confidence']:.2f}"
                )
            else:
                logger.info(f"  ✗ {result['error']}")

    # Save results
    output_file = Path("docs/testing/visual_inspection_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n{'='*80}")
    logger.info(f"Results saved to: {output_file}")
    logger.info(f"Success: {sum(1 for r in results if r['status'] == 'success')}/{len(results)}")

    # Generate HTML report
    generate_html_report(results)

    return results


def generate_html_report(results: List[Dict[str, Any]]):
    """Generate interactive HTML report for visual inspection."""

    success_results = [r for r in results if r["status"] == "success"]
    error_results = [r for r in results if r["status"] == "error"]

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Visual Inspection Report - {len(results)} files</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2563eb;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .file-card {{
            background: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .file-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .file-name {{
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }}
        .file-index {{
            background: #e5e7eb;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            color: #6b7280;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
            margin-bottom: 15px;
        }}
        .metric {{
            display: flex;
            flex-direction: column;
        }}
        .metric-label {{
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 18px;
            font-weight: 600;
            color: #1f2937;
        }}
        .svg-container {{
            margin: 15px 0;
            padding: 15px;
            background: #f9fafb;
            border-radius: 4px;
            text-align: center;
        }}
        .svg-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #e5e7eb;
            background: white;
        }}
        .evaluation-buttons {{
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }}
        .btn {{
            padding: 10px 24px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-correct {{
            background: #10b981;
            color: white;
        }}
        .btn-correct:hover {{
            background: #059669;
        }}
        .btn-wrong {{
            background: #ef4444;
            color: white;
        }}
        .btn-wrong:hover {{
            background: #dc2626;
        }}
        .btn-skip {{
            background: #6b7280;
            color: white;
        }}
        .btn-skip:hover {{
            background: #4b5563;
        }}
        .evaluation-result {{
            display: none;
            margin-top: 15px;
            padding: 10px;
            border-radius: 6px;
            font-weight: 600;
        }}
        .evaluation-result.correct {{
            background: #d1fae5;
            color: #065f46;
            display: block;
        }}
        .evaluation-result.wrong {{
            background: #fee2e2;
            color: #991b1b;
            display: block;
        }}
        .error-card {{
            background: #fee2e2;
            border-left: 4px solid #dc2626;
        }}
        .progress {{
            position: sticky;
            top: 20px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            z-index: 100;
        }}
        .progress-bar {{
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }}
        .progress-fill {{
            height: 100%;
            background: #2563eb;
            transition: width 0.3s;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Visual Inspection Report</h1>
        <p>Review each extraction and mark as CORRECT or WRONG</p>
    </div>

    <div class="progress" id="progress">
        <div>Progress: <strong><span id="evaluated">0</span> / {len(success_results)}</strong> evaluated</div>
        <div class="progress-bar">
            <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
        </div>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{len(results)}</div>
            <div class="stat-label">Total Files</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(success_results)}</div>
            <div class="stat-label">Successful Extractions</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(error_results)}</div>
            <div class="stat-label">Errors</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="accuracy">--%</div>
            <div class="stat-label">Accuracy (after review)</div>
        </div>
    </div>
"""

    # Success results
    for r in success_results:
        m = r["metrics"]
        features_list = ", ".join(f["type"] for f in r.get("features", []))

        html += f"""
    <div class="file-card" data-index="{r['index']}">
        <div class="file-header">
            <div class="file-name">{r['filename']}</div>
            <div class="file-index">#{r['index']}</div>
        </div>

        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-label">Part Type</div>
                <div class="metric-value">{r.get('part_type', 'N/A')}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Max Diameter</div>
                <div class="metric-value">Ø{m['max_diameter']:.1f} mm</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Length</div>
                <div class="metric-value">{m['total_length']:.1f} mm</div>
            </div>
            <div class="metric">
                <div class="metric-label">Bore Diameter</div>
                <div class="metric-value">{"Ø" + f"{m['bore_diameter']:.1f} mm" if m['bore_diameter'] > 0 else "N/A"}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Contour Points</div>
                <div class="metric-value">{m['outer_points']} + {m['inner_points']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Features</div>
                <div class="metric-value">{m['features_count']}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Confidence</div>
                <div class="metric-value">{r['confidence']:.2f}</div>
            </div>
        </div>

        <div class="metric">
            <div class="metric-label">Extracted Features</div>
            <div style="margin-top: 5px; color: #4b5563;">{features_list if features_list else "None"}</div>
        </div>

        <div class="svg-container">
            <img src="data:image/svg+xml;base64,{r.get('svg_data', '')}" alt="Profile SVG" />
        </div>

        <div class="evaluation-buttons">
            <button class="btn btn-correct" onclick="evaluate({r['index']}, 'correct')">✓ CORRECT</button>
            <button class="btn btn-wrong" onclick="evaluate({r['index']}, 'wrong')">✗ WRONG</button>
            <button class="btn btn-skip" onclick="evaluate({r['index']}, 'skip')">→ SKIP</button>
        </div>

        <div class="evaluation-result" id="result-{r['index']}"></div>
    </div>
"""

    # Error results
    if error_results:
        html += "<h2>Failed Extractions</h2>"
        for r in error_results:
            html += f"""
    <div class="file-card error-card">
        <div class="file-header">
            <div class="file-name">{r['filename']}</div>
            <div class="file-index">#{r['index']}</div>
        </div>
        <p><strong>Error:</strong> {r.get('error', 'Unknown error')}</p>
    </div>
"""

    html += """
    <script>
        const evaluations = {};

        function evaluate(index, result) {
            evaluations[index] = result;

            const resultDiv = document.getElementById(`result-${index}`);
            resultDiv.className = 'evaluation-result ' + result;

            if (result === 'correct') {
                resultDiv.textContent = '✓ Marked as CORRECT';
            } else if (result === 'wrong') {
                resultDiv.textContent = '✗ Marked as WRONG';
            } else {
                resultDiv.textContent = '→ Skipped';
                resultDiv.style.background = '#f3f4f6';
                resultDiv.style.color = '#6b7280';
            }

            // Update progress
            const evaluated = Object.keys(evaluations).filter(k => evaluations[k] !== 'skip').length;
            const total = """ + str(len(success_results)) + """;
            const correct = Object.values(evaluations).filter(v => v === 'correct').length;

            document.getElementById('evaluated').textContent = evaluated;
            document.getElementById('progress-fill').style.width = (evaluated / total * 100) + '%';

            if (evaluated > 0) {
                const accuracy = (correct / evaluated * 100).toFixed(1);
                document.getElementById('accuracy').textContent = accuracy + '%';
            }

            // Save to localStorage
            localStorage.setItem('visual_inspection_evals', JSON.stringify(evaluations));

            // Scroll to next unevaluated
            const cards = document.querySelectorAll('.file-card:not(.error-card)');
            for (let card of cards) {
                const cardIndex = card.getAttribute('data-index');
                if (!evaluations[cardIndex]) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    break;
                }
            }
        }

        // Load previous evaluations
        const saved = localStorage.getItem('visual_inspection_evals');
        if (saved) {
            const evals = JSON.parse(saved);
            for (let [index, result] of Object.entries(evals)) {
                evaluate(parseInt(index), result);
            }
        }
    </script>
</body>
</html>
"""

    report_file = Path("visual_inspection_report.html")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"HTML report generated: {report_file}")
    logger.info(f"\n{'='*80}")
    logger.info(f"🌐 Open in browser: http://localhost:8000/{report_file.name}")
    logger.info(f"   Or: file://{report_file.absolute()}")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(run_batch_test())
