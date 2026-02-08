"""
Vision Feature Extractor — Extract manufacturing features from PDF drawings.

Uses Claude Vision API to analyze PDF technical drawings combined with
STEP 3D geometry data to extract precise manufacturing features.

WORKFLOW:
1. Original PDF + STEP segments → Claude Vision
2. Claude identifies features, dimensions, contour
3. Returns features JSON for machining time calculation
"""

import logging
import base64
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Anthropic imports
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK not available")


class VisionFeatureExtractor:
    """Extract manufacturing features using Claude Vision API."""

    def __init__(self, api_key: str):
        """Initialize with Anthropic API key."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic SDK not available")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.client = Anthropic(api_key=api_key)

    async def extract_features(
        self,
        pdf_path: Path,
        step_geometry: Dict
    ) -> Optional[Dict]:
        """
        Extract manufacturing features from PDF + STEP data.

        Args:
            pdf_path: Path to original PDF drawing
            step_geometry: STEP waterline data with segments

        Returns:
            {
                "features": [
                    {
                        "type": "shaft",
                        "dimension": 12.0,  # diameter in mm
                        "depth": 20.0,      # length/depth in mm
                        "pdf_bbox": [x, y, w, h],
                        "step_data": { "r_avg": 6.0, "length": 20.0, "type": "shaft" },
                        "dimension_error": 0.02,  # % error vs STEP
                        "machining_ops": ["external_turning", "finish"]
                    }
                ]
            }
        """
        if not pdf_path.exists():
            logger.error(f"PDF not found: {pdf_path}")
            return None

        try:
            # Read PDF as base64
            with open(pdf_path, 'rb') as f:
                pdf_data = base64.standard_b64encode(f.read()).decode('utf-8')

            # Build Vision prompt
            prompt = self._build_vision_prompt(step_geometry)

            logger.info(f"Calling Vision API for {pdf_path.name}")

            # Call Claude Vision API
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4000,
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

            # Parse Vision response
            content = response.content[0].text.strip()
            logger.info(f"Vision API response: {len(content)} chars")

            # Extract JSON from response (handle multiple formats)
            import json
            import re

            # Try different JSON extraction patterns
            json_str = None

            # Pattern 1: ```json ... ```
            match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if match:
                json_str = match.group(1)

            # Pattern 2: ``` ... ``` (no language tag)
            if not json_str:
                match = re.search(r'```\s*(\{.*?\})\s*```', content, re.DOTALL)
                if match:
                    json_str = match.group(1)

            # Pattern 3: Raw JSON (no wrapper)
            if not json_str:
                json_str = content

            # Parse JSON
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse failed: {e}\nContent: {content[:500]}")
                return None

            # Validate confidence
            confidence = result.get("confidence", 0)
            if confidence < 0.5:
                logger.warning(f"Low confidence ({confidence}): {result.get('notes')}")
                # Continue anyway but log warning

            # Extract contour
            contour = result.get("contour", [])
            if len(contour) < 2:
                logger.error(f"Contour has only {len(contour)} points (need at least 2)")
                return None

            logger.info(f"Extracted contour with {len(contour)} points (confidence: {confidence})")

            return {
                "contour": contour,
                "confidence": confidence,
                "notes": result.get("notes", "")
            }

        except Exception as e:
            logger.error(f"Vision API call failed: {e}", exc_info=True)
            return None

    def _build_vision_prompt(self, step_geometry: Dict) -> str:
        """
        Build Vision API prompt for r(z) contour extraction.

        Based on successful chat interaction - precise, structured prompt.
        """
        segments = step_geometry.get("segments", [])
        r_values = step_geometry.get("r_values", [])
        z_values = step_geometry.get("z_values", [])

        # Build STEP waterline context (point-by-point)
        step_context = "STEP 3D model waterline (radius vs axial position):\n"
        for i, (z, r) in enumerate(zip(z_values, r_values)):
            step_context += f"  Point {i}: z={z:.2f}mm, r={r:.2f}mm\n"

        return f"""You are analyzing a technical drawing of a ROTATIONAL PART (turning/lathe machining).

I have extracted the 3D STEP model waterline:
{step_context}

Your task:
1. Find the part's PROFILE/CONTOUR on the PDF drawing (right-side silhouette for rotational parts)
2. Extract EXACT r(z) coordinate points from the drawing's dimension annotations
3. Match drawing points to STEP points above (they should be very similar)
4. Return contour as ordered list of [z, r] coordinates

CRITICAL RULES:
- r = RADIUS in mm (NOT diameter! If drawing shows Ø12, then r=6)
- z = axial position in mm (along the rotation axis)
- Use dimensions shown ON THE DRAWING (may differ slightly from STEP - that's OK)
- Return ONLY outer contour points (right-side profile)
- Points MUST be ordered from left to right (increasing z values)
- Include ALL dimensional transition points (steps, chamfers, grooves, etc.)

Return ONLY this JSON structure (NO markdown wrapper, NO explanation):
{{
  "contour": [
    {{"z": -10.2, "r": 3.3}},
    {{"z": -8.2, "r": 6.0}},
    {{"z": -0.5, "r": 3.3}},
    {{"z": 0.0, "r": 6.0}}
  ],
  "confidence": 0.95,
  "notes": "Found all dimension points clearly marked on drawing"
}}

If dimensions are unclear or missing, set confidence < 0.5 and explain why in notes.
"""

    def _validate_features(self, features: List[Dict], step_geometry: Dict) -> List[Dict]:
        """
        Validate and enrich Vision-extracted features.

        Ensures all required fields exist and are valid.
        """
        segments = step_geometry.get("segments", [])
        validated = []

        for feat in features:
            # Ensure required fields
            if not all(k in feat for k in ["type", "dimension", "depth"]):
                logger.warning(f"Skipping incomplete feature: {feat}")
                continue

            # Ensure step_data exists (match to STEP segment)
            if "step_data" not in feat and segments:
                # Auto-match to closest segment by dimension
                feat["step_data"] = self._match_to_step_segment(feat, segments)

            # Calculate error if missing
            if "dimension_error" not in feat and feat.get("step_data"):
                step_diam = feat["step_data"].get("diameter", 0)
                if step_diam > 0:
                    feat["dimension_error"] = abs(
                        (feat["dimension"] - step_diam) / step_diam
                    ) * 100

            validated.append(feat)

        return validated

    def _match_to_step_segment(self, feature: Dict, segments: List[Dict]) -> Dict:
        """Match Vision feature to closest STEP segment by dimension."""
        feat_diam = feature.get("dimension", 0)
        feat_depth = feature.get("depth", 0)

        best_match = None
        best_score = float('inf')

        for seg in segments:
            seg_diam = seg.get("diameter", 0)
            seg_length = seg.get("length", 0)

            # Score by dimension similarity
            diam_diff = abs(feat_diam - seg_diam) / max(seg_diam, 1)
            depth_diff = abs(feat_depth - seg_length) / max(seg_length, 1)
            score = diam_diff + depth_diff

            if score < best_score:
                best_score = score
                best_match = {
                    "r_avg": seg.get("r_avg", 0),
                    "length": seg_length,
                    "type": seg.get("type", "unknown"),
                    "diameter": seg_diam
                }

        return best_match or {}
