#!/usr/bin/env python3
"""
Diagnostic script: Find where operations are lost in Feature Recognition pipeline.

Pipeline: Claude API → parse_claude_json_response → _flatten_operations → enrich → frontend

Usage:
    source .venv/bin/activate
    python test_feature_pipeline_debug.py
"""

import asyncio
import base64
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env from project root
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
print(f"Loaded .env from: {env_path}, exists={env_path.exists()}")
print(f"ANTHROPIC_API_KEY set: {'ANTHROPIC_API_KEY' in os.environ}")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("pipeline_debug")


# ============================================================
# STEP 0: Find files
# ============================================================
def find_files():
    """Find STEP and PDF files for testing."""
    drawings_dir = Path(__file__).parent / "drawings"

    step_file = drawings_dir / "PDM-249322_03.stp"
    if not step_file.exists():
        logger.error(f"STEP file not found: {step_file}")
        sys.exit(1)

    # Find a PDF to use (any PDF in drawings/)
    pdf_files = sorted(drawings_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found in drawings/")
        sys.exit(1)

    # Use smallest PDF for speed
    pdf_file = min(pdf_files, key=lambda p: p.stat().st_size)

    logger.info(f"STEP file: {step_file} ({step_file.stat().st_size} bytes)")
    logger.info(f"PDF file:  {pdf_file} ({pdf_file.stat().st_size} bytes)")

    return step_file, pdf_file


# ============================================================
# STEP 1: Parse STEP features (internal parser)
# ============================================================
def test_step_parser(step_file: Path):
    """Test internal STEP parser."""
    logger.info("=" * 60)
    logger.info("STEP 1: Internal STEP Parser")
    logger.info("=" * 60)

    from app.services.step_parser import StepParser
    parser = StepParser()
    result = parser.parse_file(str(step_file))

    logger.info(f"  Success: {result.get('success')}")
    logger.info(f"  Features: {len(result.get('features', []))}")
    for i, f in enumerate(result.get('features', [])):
        logger.info(f"    [{i}] {f}")

    return result.get('features', [])


# ============================================================
# STEP 2: Build prompt
# ============================================================
def test_prompt_building(step_features):
    """Test prompt construction."""
    logger.info("=" * 60)
    logger.info("STEP 2: Build Manufacturing Prompt")
    logger.info("=" * 60)

    from app.services.step_pdf_parser import _build_compact_prompt
    prompt = _build_compact_prompt(step_features)

    logger.info(f"  Prompt length: {len(prompt)} chars")
    logger.info(f"  Prompt preview (first 200 chars):")
    logger.info(f"    {prompt[:200]}...")

    return prompt


# ============================================================
# STEP 3: Call Claude API (the expensive part)
# ============================================================
async def test_claude_api_call(step_features, pdf_file, prompt):
    """Call Claude API and inspect raw response."""
    logger.info("=" * 60)
    logger.info("STEP 3: Claude API Call")
    logger.info("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # Try reading directly from .env file
        env_path = Path(__file__).parent / ".env"
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set in .env!")
        sys.exit(1)
    logger.info(f"  API key found: {api_key[:12]}...")

    # Encode PDF
    pdf_bytes = pdf_file.read_bytes()
    pdf_base64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')

    # Trim PDF
    from app.services.step_pdf_parser import trim_pdf_pages, CLAUDE_MODEL
    trimmed_pdf = trim_pdf_pages(pdf_base64)
    logger.info(f"  PDF base64 length: {len(pdf_base64)} -> trimmed: {len(trimmed_pdf)}")

    # Call Claude
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic(api_key=api_key)

    logger.info(f"  Calling Claude model: {CLAUDE_MODEL}...")

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
                        "data": trimmed_pdf
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
    )

    # Inspect raw response
    raw_text = ""
    if response.content and len(response.content) > 0:
        raw_text = getattr(response.content[0], 'text', '')

    logger.info(f"  Response tokens: in={response.usage.input_tokens}, out={response.usage.output_tokens}")
    logger.info(f"  Raw response length: {len(raw_text)} chars")
    logger.info(f"  Raw response preview (first 500 chars):")
    logger.info(f"    {raw_text[:500]}")

    return response, raw_text


# ============================================================
# STEP 4: Parse JSON from Claude response
# ============================================================
def test_json_parsing(response, raw_text):
    """Test parse_claude_json_response."""
    logger.info("=" * 60)
    logger.info("STEP 4: parse_claude_json_response()")
    logger.info("=" * 60)

    from app.services.claude_utils import parse_claude_json_response
    result = parse_claude_json_response(response.content)

    logger.info(f"  Result type: {type(result).__name__}")
    if isinstance(result, dict):
        logger.info(f"  Result keys: {list(result.keys())}")
        logger.info(f"  Has 'operations': {'operations' in result}")
        ops = result.get('operations', [])
        logger.info(f"  Operations count: {len(ops)}")
        if ops:
            logger.info(f"  First operation type: {type(ops[0]).__name__}")
            logger.info(f"  First operation keys: {list(ops[0].keys()) if isinstance(ops[0], dict) else 'NOT A DICT'}")
            logger.info(f"  First operation: {json.dumps(ops[0], default=str)[:300]}")

            # Check hierarchical vs flat format detection
            first = ops[0]
            is_hierarchical = 'features' in first and isinstance(first.get('features'), list)
            logger.info(f"  Is hierarchical format: {is_hierarchical}")
            if is_hierarchical:
                logger.info(f"  First op 'features' count: {len(first.get('features', []))}")
                if first.get('features'):
                    logger.info(f"  First feature: {json.dumps(first['features'][0], default=str)[:300]}")
            else:
                has_operation_type = 'operation_type' in first
                has_feature_type = 'feature_type' in first
                logger.info(f"  Has 'operation_type': {has_operation_type}")
                logger.info(f"  Has 'feature_type': {has_feature_type}")
        else:
            logger.error("  ZERO operations in parsed result!")
            logger.info(f"  Full result: {json.dumps(result, default=str)[:1000]}")
    else:
        logger.error(f"  Result is NOT a dict! Type: {type(result).__name__}")
        logger.info(f"  Result: {str(result)[:500]}")

    return result


# ============================================================
# STEP 5: _flatten_operations
# ============================================================
def test_flatten_operations(claude_result):
    """Test _flatten_operations."""
    logger.info("=" * 60)
    logger.info("STEP 5: _flatten_operations()")
    logger.info("=" * 60)

    from app.services.step_pdf_parser import _flatten_operations
    try:
        flat = _flatten_operations(claude_result)
        logger.info(f"  Flat operations count: {len(flat)}")
        for i, op in enumerate(flat):
            logger.info(
                f"    [{i}] type={op.get('operation_type')}, "
                f"feature={op.get('feature_type')}, "
                f"params={op.get('params')}"
            )
        return flat
    except Exception as e:
        logger.error(f"  _flatten_operations CRASHED: {e}", exc_info=True)
        return []


# ============================================================
# STEP 6: Enrich operations
# ============================================================
async def test_enrichment(flat_operations, claude_result):
    """Test enrich_ai_operations."""
    logger.info("=" * 60)
    logger.info("STEP 6: enrich_ai_operations()")
    logger.info("=" * 60)

    if not flat_operations:
        logger.warning("  No operations to enrich (empty list)")
        return []

    from app.services.ai_feature_mapper import enrich_ai_operations
    material_spec = claude_result.get('material_spec')
    material_group = claude_result.get('material_group')

    logger.info(f"  Material spec: {material_spec}")
    logger.info(f"  Material group: {material_group}")

    try:
        enriched = await enrich_ai_operations(
            ai_operations=flat_operations,
            material_spec=material_spec,
            material_group=material_group,
        )
        logger.info(f"  Enriched operations count: {len(enriched)}")
        for i, op in enumerate(enriched):
            logger.info(
                f"    [{i}] type={op.get('operation_type')}, "
                f"feature={op.get('feature_type')}, "
                f"calc_time={op.get('calculated_time_min')}"
            )
        return enriched
    except Exception as e:
        logger.error(f"  Enrichment CRASHED: {e}", exc_info=True)
        return flat_operations


# ============================================================
# STEP 7: Pydantic serialization (OperationSuggestion)
# ============================================================
def test_pydantic_serialization(enriched_ops):
    """Test OperationSuggestion serialization."""
    logger.info("=" * 60)
    logger.info("STEP 7: OperationSuggestion Pydantic serialization")
    logger.info("=" * 60)

    if not enriched_ops:
        logger.warning("  No operations to serialize")
        return []

    from app.schemas.feature_recognition import OperationSuggestion
    valid = []
    for i, op in enumerate(enriched_ops):
        try:
            suggestion = OperationSuggestion(
                operation_type=op.get('operation_type', 'unknown'),
                tool=op.get('tool', 'unknown'),
                params=op.get('params', {}),
                estimated_time_min=op.get('estimated_time_min', 0.0),
                confidence=op.get('confidence', 1.0),
                notes=op.get('notes'),
                feature_type=op.get('feature_type'),
                material_group=op.get('material_group'),
                cutting_conditions=op.get('cutting_conditions'),
                calculated_time_min=op.get('calculated_time_min'),
                calculation=op.get('calculation'),
            )
            valid.append(suggestion)
        except Exception as e:
            logger.error(f"  Operation [{i}] FAILED Pydantic validation: {e}")
            logger.error(f"    Raw data: {json.dumps(op, default=str)[:300]}")

    logger.info(f"  Valid operations: {len(valid)} / {len(enriched_ops)}")
    return valid


# ============================================================
# STEP 8: Full integration test via analyze_step_pdf_with_claude
# ============================================================
async def test_full_pipeline(step_file, pdf_file):
    """Test complete analyze_step_pdf_with_claude pipeline."""
    logger.info("=" * 60)
    logger.info("STEP 8: Full pipeline (analyze_step_pdf_with_claude)")
    logger.info("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    step_text = step_file.read_text(encoding='utf-8', errors='ignore')[:50000]
    pdf_bytes = pdf_file.read_bytes()
    pdf_base64 = base64.standard_b64encode(pdf_bytes).decode('utf-8')

    # Parse STEP features
    from app.services.step_parser import StepParser
    parser = StepParser()
    step_result = parser.parse_file(str(step_file))
    step_features = step_result.get('features', [])

    from app.services.step_pdf_parser import analyze_step_pdf_with_claude
    result = await analyze_step_pdf_with_claude(
        step_text=step_text,
        pdf_base64=pdf_base64,
        step_features=step_features,
        anthropic_api_key=api_key,
    )

    logger.info(f"  Success: {result.get('success')}")
    logger.info(f"  Operations: {len(result.get('operations', []))}")
    logger.info(f"  Features: {len(result.get('features', []))}")
    logger.info(f"  Confidence: {result.get('confidence')}")
    logger.info(f"  Warnings: {result.get('warnings')}")
    logger.info(f"  Error: {result.get('error')}")

    if result.get('operations'):
        for i, op in enumerate(result['operations']):
            logger.info(f"    Op[{i}]: {op.get('feature_type')} / {op.get('operation_type')}")
    else:
        # Check raw_operations
        raw = result.get('raw_operations', [])
        logger.warning(f"  raw_operations: {len(raw)}")
        if raw:
            logger.warning(f"  raw_operations[0]: {json.dumps(raw[0], default=str)[:300]}")

    return result


# ============================================================
# MAIN
# ============================================================
async def main():
    logger.info("Feature Recognition Pipeline Diagnostic")
    logger.info("=" * 60)

    step_file, pdf_file = find_files()

    # Step 1: STEP parser
    step_features = test_step_parser(step_file)

    # Step 2: Prompt
    prompt = test_prompt_building(step_features)

    # Step 3: Claude API (costs money!)
    logger.info("")
    logger.info("About to call Claude API (this costs ~$0.01-0.03)...")
    response, raw_text = await test_claude_api_call(step_features, pdf_file, prompt)

    # Step 4: JSON parsing
    claude_result = test_json_parsing(response, raw_text)

    # Step 5: Flatten
    flat_ops = test_flatten_operations(claude_result)

    # Step 6: Enrich
    enriched = await test_enrichment(flat_ops, claude_result)

    # Step 7: Pydantic
    valid_ops = test_pydantic_serialization(enriched)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"  STEP features (internal):    {len(step_features)}")
    logger.info(f"  Claude JSON parsed:          {type(claude_result).__name__}, ops={len(claude_result.get('operations', []))}")
    logger.info(f"  After _flatten_operations:   {len(flat_ops)}")
    logger.info(f"  After enrich_ai_operations:  {len(enriched)}")
    logger.info(f"  After Pydantic validation:   {len(valid_ops)}")

    if len(flat_ops) == 0 and len(claude_result.get('operations', [])) > 0:
        logger.error("BUG CONFIRMED: Operations lost in _flatten_operations!")
    elif len(claude_result.get('operations', [])) == 0:
        logger.error("BUG CONFIRMED: parse_claude_json_response returned no operations!")
    elif len(valid_ops) < len(enriched):
        logger.error("BUG CONFIRMED: Some operations fail Pydantic validation!")
    elif len(valid_ops) > 0:
        logger.info("PIPELINE OK: All steps produced operations!")
    else:
        logger.error("PIPELINE BROKEN: No operations at any stage!")


if __name__ == "__main__":
    asyncio.run(main())
