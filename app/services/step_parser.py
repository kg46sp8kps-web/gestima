"""
STEP File Parser - OCCT-based geometry extraction

Uses Open CASCADE Technology for precise CAD parsing.
ADR-039: OCCT Integration
"""

import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class StepParser:
    """
    OCCT-only STEP parser.
    
    No regex fallback - OCCT or fail.
    """

    def __init__(self):
        # ADR-042: step_parser_occt.py deleted, replaced by step_raw_extractor.py
        # This class is deprecated along with Feature Recognition module
        self.occt_parser = None

        # try:
        #     from app.services.step_parser_occt import StepParserOCCT
        #     self.occt_parser = StepParserOCCT()
        #     logger.info("✅ OCCT parser enabled")
        # except ImportError as e:
        logger.error("❌ StepParser deprecated (ADR-042). Use step_raw_extractor.py instead.")
        raise RuntimeError(
            "StepParser deprecated (ADR-042). "
            "For raw geometry extraction, use: app.services.step_raw_extractor.extract_raw_geometry()"
        )

    def parse_file(self, step_path: str) -> Dict:
        """
        Parse STEP file using OCCT.
        
        Returns precise B-rep topology extraction.
        """
        if not self.occt_parser:
            raise RuntimeError("OCCT parser not initialized")
            
        return self.occt_parser.parse_file(step_path)

    def parse_step_file(self, step_path: str) -> Dict:
        """Alias for parse_file() - compatibility"""
        return self.parse_file(step_path)
