"""
GESTIMA - Diagnostický test Claude API pipeline

Testuje CELÝ řetězec:
1. Načte STEP + PDF soubory
2. Zavolá Claude API se STEJNÝM promptem jako produkce
3. Ukáže RAW odpověď Claude
4. Ukáže výsledek parse_claude_json_response
5. Ukáže výsledek _flatten_operations
6. Ukáže enrichment výsledek

Spuštění: python test_claude_pipeline.py
"""

import asyncio
import base64
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


async def main():
    # === 1. Load config ===
    from app.config import settings
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        return

    print(f"API Key: ...{api_key[-8:]}")
    print()

    # === 2. Find test files ===
    step_file = "uploads/drawings/PDM-249322_03.stp"
    pdf_file = "uploads/drawings/PDM-249322_03_Gelso.pdf"

    if not os.path.exists(step_file):
        print(f"ERROR: STEP file not found: {step_file}")
        return
    if not pdf_file:
        print("ERROR: No PDF files found in drawings/")
        return

    print(f"STEP: {step_file} ({os.path.getsize(step_file)} bytes)")
    print(f"PDF:  {pdf_file} ({os.path.getsize(pdf_file)} bytes)")
    print()

    # === 3. Parse STEP internally ===
    from app.services.step_parser import StepParser
    step_parser = StepParser()
    step_result = step_parser.parse_file(step_file)
    step_features = step_result.get("features", []) if step_result.get("success") else []
    print(f"STEP features parsed: {len(step_features)}")
    for f in step_features[:5]:
        print(f"  {f}")
    print()

    # === 4. Build prompt (same as production) ===
    from app.services.step_pdf_parser import (
        _build_manufacturing_prompt,
        _flatten_operations,
        _extract_raw_features,
        trim_pdf_pages,
        CLAUDE_MODEL,
    )
    from app.services.claude_utils import parse_claude_json_response

    prompt = _build_manufacturing_prompt(
        step_features=step_features,
        has_step=True,
        has_pdf=True,
    )
    print(f"Prompt length: {len(prompt)} chars")
    print(f"Prompt preview (first 200 chars): {prompt[:200]}...")
    print()

    # === 5. Prepare PDF ===
    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    trimmed_pdf = trim_pdf_pages(pdf_b64)
    print(f"PDF base64 length: {len(pdf_b64)}")
    print(f"Trimmed PDF base64 length: {len(trimmed_pdf)}")
    print()

    # === 6. Call Claude API ===
    print(f"Calling Claude API (model: {CLAUDE_MODEL})...")
    print("=" * 60)

    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)

    response = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": trimmed_pdf,
                    }
                },
                {
                    "type": "text",
                    "text": prompt,
                }
            ]
        }]
    )

    # === 7. Show RAW response ===
    print(f"\nResponse content blocks: {len(response.content)}")
    for i, block in enumerate(response.content):
        print(f"  Block[{i}]: type={block.type}, has_text={hasattr(block, 'text')}")

    raw_text = ""
    if response.content and hasattr(response.content[0], "text"):
        raw_text = response.content[0].text
    else:
        raw_text = str(response.content[0]) if response.content else "EMPTY"

    print(f"\nRAW TEXT LENGTH: {len(raw_text)}")
    print(f"\nRAW TEXT (first 2000 chars):")
    print("-" * 60)
    print(raw_text[:2000])
    print("-" * 60)

    # Save full raw text
    with open("/tmp/gestima_claude_raw.txt", "w") as f:
        f.write(raw_text)
    print(f"\nFull raw text saved to /tmp/gestima_claude_raw.txt")

    # === 8. Test parse_claude_json_response ===
    print("\n" + "=" * 60)
    print("TESTING: parse_claude_json_response(response.content)")
    parsed = parse_claude_json_response(response.content)
    print(f"  Type: {type(parsed).__name__}")
    print(f"  Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'N/A'}")
    print(f"  Has 'operations': {'operations' in parsed if isinstance(parsed, dict) else False}")
    if isinstance(parsed, dict) and "operations" in parsed:
        ops = parsed["operations"]
        print(f"  Operations count: {len(ops)}")
        if ops:
            print(f"  First operation keys: {list(ops[0].keys())}")
            is_hierarchical = "features" in ops[0] and isinstance(ops[0].get("features"), list)
            print(f"  Is hierarchical: {is_hierarchical}")
            if is_hierarchical:
                total_features = sum(len(op.get("features", [])) for op in ops)
                print(f"  Total features in hierarchy: {total_features}")

    # Save parsed result
    with open("/tmp/gestima_claude_parsed.json", "w") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nParsed result saved to /tmp/gestima_claude_parsed.json")

    # === 9. Test _flatten_operations ===
    print("\n" + "=" * 60)
    print("TESTING: _flatten_operations(parsed)")
    flat_ops = _flatten_operations(parsed)
    print(f"  Flat operations count: {len(flat_ops)}")
    for i, op in enumerate(flat_ops[:5]):
        print(f"  [{i}] type={op.get('operation_type')}, "
              f"feature={op.get('feature_type')}, "
              f"tool={op.get('tool', '?')}")

    # === 10. Test enrichment ===
    print("\n" + "=" * 60)
    print("TESTING: enrich_ai_operations(flat_ops)")
    from app.services.ai_feature_mapper import enrich_ai_operations, summarize_operations

    material_group = parsed.get("material_group") if isinstance(parsed, dict) else None
    material_spec = parsed.get("material_spec") if isinstance(parsed, dict) else None
    print(f"  Material group: {material_group}")
    print(f"  Material spec: {material_spec}")

    try:
        enriched = await enrich_ai_operations(
            ai_operations=flat_ops,
            material_spec=material_spec,
            material_group=material_group,
        )
        print(f"  Enriched operations: {len(enriched)}")
        for i, op in enumerate(enriched[:5]):
            print(f"  [{i}] {op.get('feature_type')}: "
                  f"Vc={op.get('cutting_conditions', {}).get('Vc', '?')}, "
                  f"time={op.get('calculated_time_min', '?')} min")

        summary = summarize_operations(enriched)
        print(f"\n  Summary: {json.dumps(summary, indent=2)}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # === 11. Token cost ===
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)
    print(f"\n{'=' * 60}")
    print(f"COST: input={input_tokens} tokens, output={output_tokens} tokens, ${cost:.4f}")

    # === 12. Profile geometry check ===
    if isinstance(parsed, dict) and "profile_geometry" in parsed:
        geo = parsed["profile_geometry"]
        print(f"\nProfile geometry: type={geo.get('type')}, "
              f"sections={len(geo.get('sections', []))}, "
              f"total_length={geo.get('total_length')}, "
              f"max_diameter={geo.get('max_diameter')}")
    else:
        print("\nProfile geometry: NOT PRESENT")

    print(f"\n{'=' * 60}")
    print("DIAGNOSTIC COMPLETE")
    print(f"  Raw response: /tmp/gestima_claude_raw.txt")
    print(f"  Parsed JSON:  /tmp/gestima_claude_parsed.json")


if __name__ == "__main__":
    asyncio.run(main())
