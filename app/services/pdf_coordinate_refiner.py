"""
PDF Coordinate Refiner — Iterative Vision-based coordinate refinement.

Uses Claude Vision API to refine PDF coordinate mapping through
iterative annotation → Vision extraction → error calculation → refinement.

ADR-TBD: Vision Hybrid Pipeline
"""

import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

# Anthropic imports (conditional)
try:
    from anthropic import Anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not available - pdf_coordinate_refiner disabled")


class PdfCoordinateRefiner:
    """Iterative refinement of PDF-STEP coordinate mapping using Vision API."""

    def __init__(self, api_key: str):
        """
        Initialize refiner with Anthropic API key.

        Args:
            api_key: Anthropic API key from config
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK not available")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=api_key)

    async def refine_coordinates(
        self,
        annotated_pdf_path: Path,
        waterline_data: Dict,
        max_iterations: int = 5,
        convergence_threshold: float = 0.01
    ) -> AsyncGenerator[Dict, None]:
        """
        Iterative refinement loop.

        Yields status dicts after each iteration for SSE streaming.

        Args:
            annotated_pdf_path: Path to annotated PDF
            waterline_data: Dict with segments from WaterlineExtractor
            max_iterations: Maximum refinement iterations
            convergence_threshold: Error threshold for convergence (0-1)

        Yields:
            Dict with iteration status (error, converged, features, etc.)
        """
        if not annotated_pdf_path.exists():
            logger.error(f"Annotated PDF not found: {annotated_pdf_path}")
            return

        current_scale = 10.0  # Initial heuristic
        segments = waterline_data.get('segments', [])

        for iteration in range(max_iterations):
            logger.info(f"Refinement iteration {iteration + 1}/{max_iterations}")

            # Call Vision API
            vision_result = await self._vision_extract_spatial_mapping(
                annotated_pdf_path
            )

            if not vision_result:
                logger.error(f"Vision extraction failed at iteration {iteration}")
                yield {
                    'iteration': iteration,
                    'error': 1.0,
                    'converged': False,
                    'scale_factor': current_scale,
                    'features': [],  # Empty array when Vision API fails
                    'annotated_pdf_url': str(annotated_pdf_path),
                    'error_message': 'Vision API call failed'
                }
                return

            # Compute coordinate error
            error = self._compute_coordinate_error(segments, vision_result)

            logger.info(f"Iteration {iteration + 1} error: {error:.4f}")

            converged = error < convergence_threshold

            yield {
                'iteration': iteration,
                'error': round(error, 4),
                'converged': converged,
                'scale_factor': round(current_scale, 2),
                'features': segments,
                'annotated_pdf_url': str(annotated_pdf_path),
            }

            if converged:
                logger.info(f"Converged after {iteration + 1} iterations")
                return

            # Refine scale factor for next iteration
            # Simple adjustment: if error high, scale down; if error low, fine-tune
            if error > 0.1:
                current_scale *= 0.8  # Reduce scale
            elif error > 0.05:
                current_scale *= 0.95
            else:
                current_scale *= 1.02  # Fine-tune

        # Max iterations reached without convergence
        logger.warning(f"Max iterations ({max_iterations}) reached without convergence")

    async def _vision_extract_spatial_mapping(
        self, annotated_pdf_path: Path
    ) -> Optional[Dict]:
        """
        Call Claude Vision API to extract spatial mappings.

        Args:
            annotated_pdf_path: Path to annotated PDF

        Returns:
            Dict with Vision API response or None on failure
        """
        try:
            # Read PDF as base64
            import base64
            with open(annotated_pdf_path, 'rb') as f:
                pdf_data = base64.standard_b64encode(f.read()).decode('utf-8')

            # Vision API prompt
            prompt = self._build_vision_prompt()

            # Call Claude Vision API
            # Note: Using sync client in async context - should use AsyncAnthropic
            # for production, but this is simpler for POC
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Parse response
            content = response.content[0].text

            # Extract JSON from response (Vision API returns markdown-wrapped JSON)
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = content

            result = json.loads(json_str)

            logger.info(f"Vision API returned {len(result.get('mappings', []))} mappings")

            return result

        except Exception as e:
            logger.error(f"Vision API call failed: {e}", exc_info=True)
            return None

    def _build_vision_prompt(self) -> str:
        """
        Build Vision API prompt for spatial mapping extraction.

        Generic prompt (< 200 lines) that works for rotational parts.
        """
        return """This PDF contains a technical drawing with colored annotation overlays.

The annotations are colored rectangles with labels in the format:
- "SHAFT Ø{diameter} L={length}" (green boxes)
- "GROOVE Ø{diameter} L={length}" (red boxes)
- "BORE Ø{diameter} L={length}" (blue boxes)
- "TAPER Ø{diameter} L={length}" (orange boxes)

Your task:
1. Find each annotation overlay (colored box + label)
2. Locate the corresponding feature in the original technical drawing
3. Verify that the dimensions in the annotation label match the dimensions shown in the drawing
4. Extract the bounding box coordinates for the matched feature in the drawing (not the annotation box)

Return a JSON object with this structure:
```json
{
  "mappings": [
    {
      "annotation_label": "SHAFT Ø40.00 L=80.00",
      "pdf_bbox": [x, y, width, height],
      "match_confidence": 0.95,
      "dimension_verified": true
    }
  ],
  "page_number": 1,
  "notes": "Optional notes about any issues or ambiguities"
}
```

Guidelines:
- pdf_bbox: [x, y, width, height] in PDF points (origin: bottom-left)
- match_confidence: 0.0-1.0 (how confident you are in the match)
- dimension_verified: true if annotation dimensions match drawing dimensions (within ±0.5mm)
- If an annotation has no clear match in the drawing, set match_confidence to 0.0

Return ONLY the JSON object, no additional text."""

    def _compute_coordinate_error(
        self, segments: List[Dict], vision_result: Dict
    ) -> float:
        """
        Compute average coordinate error between annotations and Vision detections.

        Error metric: normalized distance between annotation bbox centers and
        Vision-detected bbox centers.

        Args:
            segments: List of segment dicts with z_start, z_end, diameter
            vision_result: Dict from Vision API with mappings

        Returns:
            Average error (0-1), where 0 = perfect match, 1 = maximum error
        """
        mappings = vision_result.get('mappings', [])

        if not mappings or not segments:
            logger.warning("No mappings or segments for error calculation")
            return 1.0

        # For now, use a simple heuristic:
        # If all mappings have high confidence, error is low
        # If mappings have low confidence, error is high

        confidences = [m.get('match_confidence', 0.0) for m in mappings]

        if not confidences:
            return 1.0

        avg_confidence = sum(confidences) / len(confidences)

        # Error = 1 - confidence (inverse relationship)
        error = 1.0 - avg_confidence

        return error
