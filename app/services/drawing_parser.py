"""
Drawing Parser Service - Extract manufacturing data from SVG/PDF/STEP
Žádný ML - pure pattern matching + regex
"""

import re
import logging
from typing import Dict, List, Optional
from pathlib import Path
import xml.etree.ElementTree as ET

from app.services.feature_utils import deduplicate_features

logger = logging.getLogger(__name__)


class DrawingParser:
    """Parse technical drawings and extract manufacturing features"""

    # Pattern matching rules (NO ML NEEDED!)
    FEATURE_PATTERNS = {
        'thread': {
            'regex': r'M(\d+)(?:×|x)?(\d+\.?\d*)?',
            'operation': 'threading',
            'examples': ['M30×2', 'M8x1.25', 'M12']
        },
        'hole': {
            'regex': r'[ØΦ](\d+\.?\d*)',
            'operation': 'drilling',
            'examples': ['Ø19', 'Ø7', 'Φ12.5']
        },
        'chamfer': {
            'regex': r'(\d+\.?\d*)\s*[×x]\s*(\d+)°',
            'operation': 'chamfering',
            'examples': ['1.5×45°', '2x45°']
        },
        'radius': {
            'regex': r'R(\d+\.?\d*)',
            'operation': 'radius_milling',
            'examples': ['R1', 'R2.5']
        },
        'cone': {
            'regex': r'(\d+)°',
            'operation': 'conical_turning',
            'examples': ['31°', '82°']
        }
    }

    def parse_svg(self, svg_path: str) -> Dict:
        """Parse SVG technical drawing"""
        try:
            tree = ET.parse(svg_path)
            root = tree.getroot()

            # Extract all text content
            all_text = self._extract_all_text(root)

            # Parse features
            features = self._extract_features(all_text)

            # Parse metadata
            metadata = self._extract_metadata(all_text)

            return {
                'success': True,
                'format': 'svg',
                'metadata': metadata,
                'features': features,
                'suggested_operations': self._features_to_operations(features),
                'confidence': self._calculate_confidence(features)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _extract_all_text(self, root: ET.Element) -> str:
        """Get all text from SVG"""
        texts = []

        # SVG namespace
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        for text_elem in root.findall('.//svg:text', ns):
            if text_elem.text:
                texts.append(text_elem.text)

        # Fallback - bez namespace
        for text_elem in root.iter():
            if text_elem.tag.endswith('text') and text_elem.text:
                texts.append(text_elem.text)

        return ' '.join(texts)

    def _extract_metadata(self, text: str) -> Dict:
        """Extract part info, material, etc."""
        metadata = {}

        # Part number (různé formáty)
        part_match = re.search(r'(\d{6})\s*[—-]\s*(.+?)(?:PDM|$)', text)
        if part_match:
            metadata['part_number'] = part_match.group(1)
            metadata['part_name'] = part_match.group(2).strip()

        # PDM/Drawing number
        pdm_match = re.search(r'PDM[- ]?(\d+[-_]\d+)', text)
        if pdm_match:
            metadata['drawing_number'] = pdm_match.group(1)

        # Revision
        rev_match = re.search(r'Rev\.?\s*(\d+)', text, re.IGNORECASE)
        if rev_match:
            metadata['revision'] = rev_match.group(1)

        # Material (evropské standardy)
        mat_match = re.search(r'Mat:\s*(\d+\.\d+)\s*\(([^)]+)\)', text)
        if mat_match:
            metadata['material_number'] = mat_match.group(1)
            metadata['material_grade'] = mat_match.group(2)

        # Surface treatment
        treat_match = re.search(r'(Rheinnitrieren|Verzinkt|Eloxiert|[^\d]{10,})\s*→\s*(\d+)\s*HV', text)
        if treat_match:
            metadata['surface_treatment'] = treat_match.group(1)
            metadata['hardness'] = treat_match.group(2) + ' HV'

        # Tolerance standard
        tol_match = re.search(r'ISO\s*\d+[-:]\w+', text)
        if tol_match:
            metadata['tolerance_standard'] = tol_match.group(0)

        return metadata

    def _extract_features(self, text: str) -> List[Dict]:
        """Extract manufacturing features using pattern matching"""
        features = []

        for feature_type, pattern_info in self.FEATURE_PATTERNS.items():
            matches = re.finditer(pattern_info['regex'], text)

            for match in matches:
                feature = {
                    'type': feature_type,
                    'raw_text': match.group(0),
                    'operation_hint': pattern_info['operation']
                }

                # Parse specific values
                if feature_type == 'thread':
                    feature['diameter'] = int(match.group(1))
                    feature['pitch'] = float(match.group(2)) if match.group(2) else None

                elif feature_type == 'hole':
                    feature['diameter'] = float(match.group(1))
                    # Check if through-hole
                    context = text[max(0, match.start()-30):match.end()+30].lower()
                    feature['through'] = 'pruchozi' in context or 'through' in context

                elif feature_type == 'chamfer':
                    feature['size'] = float(match.group(1))
                    feature['angle'] = int(match.group(2))

                elif feature_type == 'radius':
                    feature['radius'] = float(match.group(1))

                elif feature_type == 'cone':
                    feature['angle'] = int(match.group(1))

                features.append(feature)

        # Deduplicate using shared utility
        return deduplicate_features(features)

    def _features_to_operations(self, features: List[Dict]) -> List[Dict]:
        """Map features to manufacturing operations (pattern database)"""
        operations = []

        for feature in features:
            op_type = feature['operation_hint']

            if op_type == 'threading':
                # Thread → tap or thread mill
                diameter = feature.get('diameter', 0)
                operations.append({
                    'operation_type': 'thread_cutting',
                    'tool': 'tap' if diameter <= 20 else 'thread_mill',
                    'params': {
                        'thread_spec': feature['raw_text'],
                        'diameter': diameter,
                        'pitch': feature.get('pitch')
                    },
                    'estimated_time_min': diameter * 0.5,  # Simple heuristic
                    'source_feature': feature
                })

            elif op_type == 'drilling':
                diameter = feature.get('diameter', 0)
                through = feature.get('through', False)

                # Center drill first for holes < 5mm
                if diameter < 5:
                    operations.append({
                        'operation_type': 'center_drilling',
                        'tool': 'center_drill',
                        'params': {'diameter': diameter},
                        'estimated_time_min': 0.5
                    })

                operations.append({
                    'operation_type': 'drilling',
                    'tool': f'drill_{diameter}mm',
                    'params': {
                        'diameter': diameter,
                        'depth': 'through' if through else 'blind',
                    },
                    'estimated_time_min': (diameter / 10) * (2 if through else 1),
                    'source_feature': feature
                })

            elif op_type == 'chamfering':
                operations.append({
                    'operation_type': 'chamfering',
                    'tool': 'chamfer_mill',
                    'params': {
                        'size': feature.get('size'),
                        'angle': feature.get('angle')
                    },
                    'estimated_time_min': 0.3,
                    'source_feature': feature
                })

            elif op_type == 'conical_turning':
                operations.append({
                    'operation_type': 'turning_conical',
                    'tool': 'lathe_tool',
                    'params': {
                        'angle': feature.get('angle')
                    },
                    'estimated_time_min': 2.0,
                    'source_feature': feature
                })

        return operations

    def _calculate_confidence(self, features: List[Dict]) -> float:
        """Simple confidence based on how many features we found"""
        if not features:
            return 0.0

        # More features = higher confidence (pattern matching is deterministic)
        confidence = min(0.95, 0.6 + (len(features) * 0.05))
        return round(confidence, 2)


class ClaudeFallbackParser:
    """Use Claude API for complex cases that pattern matching can't handle"""

    def __init__(self, api_key: str):
        from anthropic import Anthropic
        from app.services.claude_utils import parse_claude_json_response
        self.client = Anthropic(api_key=api_key)
        self._parse_response = parse_claude_json_response

    async def analyze_complex_drawing(
        self,
        file_path: str,
        basic_features: List[Dict],
        similar_cases: List[Dict] = None
    ) -> Dict:
        """
        Když pattern matching nestačí → Claude API
        """

        # Read file
        content = Path(file_path).read_text()

        # Build prompt with context
        prompt = self._build_prompt(content, basic_features, similar_cases)

        # Call Claude API
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )

        return self._parse_claude_response(response.content)

    def _build_prompt(self, content: str, basic_features: List, similar_cases: List) -> str:
        return f"""
Analyzuj tento technický výkres a doplň chybějící manufacturing features.

BASIC FEATURES (už rozpoznané pattern matchingem):
{basic_features}

PODOBNÉ DÍLY Z HISTORIE (expert-verified):
{similar_cases or 'Žádné podobné případy zatím'}

VÝKRES CONTENT:
{content[:3000]}  # Limit pro API

OUTPUT (JSON):
{{
  "additional_features": [...],
  "corrections": [...],
  "suggested_operations": [...]
}}
"""

    def _parse_claude_response(self, content) -> Dict:
        """Parse Claude's JSON response using shared utility"""
        return self._parse_response(content)


# Quick test function
def test_parser():
    """Test na stuetzfuss_contour.svg"""
    parser = DrawingParser()
    result = parser.parse_svg('stuetzfuss_contour.svg')

    logger.debug("=" * 60)
    logger.debug("PARSED DRAWING DATA")
    logger.debug("=" * 60)

    logger.debug("\n📋 METADATA:")
    for key, value in result.get('metadata', {}).items():
        logger.debug(f"  {key}: {value}")

    logger.debug(f"\n🔧 FEATURES FOUND: {len(result.get('features', []))}")
    for i, feature in enumerate(result.get('features', []), 1):
        logger.debug(f"  {i}. {feature['type']}: {feature['raw_text']}")

    logger.debug(f"\n⚙️  SUGGESTED OPERATIONS: {len(result.get('suggested_operations', []))}")
    for i, op in enumerate(result.get('suggested_operations', []), 1):
        logger.debug(f"  {i}. {op['operation_type']}")
        logger.debug(f"     Tool: {op['tool']}")
        logger.debug(f"     Time: ~{op['estimated_time_min']} min")

    logger.debug(f"\n✅ CONFIDENCE: {result.get('confidence', 0)*100}%")
    logger.debug("=" * 60)

    return result


if __name__ == '__main__':
    test_parser()
