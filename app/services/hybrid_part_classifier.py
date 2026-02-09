"""GESTIMA - Hybrid Part Classifier (OCCT + Vision)

Confidence-based classifier combining OCCT geometry analysis with Vision API hints.

DECISION LOGIC:
1. OCCT confident (score > 0.7 or < 0.3) → Trust OCCT
2. OCCT ambiguous (0.3-0.7) + Vision available → Trust Vision
3. Both ambiguous → Default to PRI (safer for milling setup)

Use case: Resolve edge cases where rotational_score is borderline.

Architecture:
- Input: OCCT rotational_score (0.0-1.0) + Vision hint (ROT/PRI/UNKNOWN) + confidence
- Output: Final classification (ROT/PRI) + confidence score

See: ADR-042 (Proxy Features ML Architecture - hybrid classification)
"""

import logging
from typing import Literal, Optional, Tuple

logger = logging.getLogger(__name__)


class HybridPartClassifier:
    """Classify part type using OCCT geometry + Vision API context."""

    # Classification thresholds
    OCCT_CONFIDENT_ROT_THRESHOLD = 0.7   # Above this = confident ROT
    OCCT_CONFIDENT_PRI_THRESHOLD = 0.3   # Below this = confident PRI
    VISION_CONFIDENCE_THRESHOLD = 0.6     # Vision must exceed this to override

    def classify(
        self,
        occt_rotational_score: float,
        vision_hint: Optional[Literal["ROT", "PRI", "UNKNOWN"]] = None,
        vision_confidence: Optional[float] = None
    ) -> Tuple[Literal["ROT", "PRI"], float]:
        """
        Classify part type using hybrid OCCT + Vision approach.

        Decision tree:
        1. If OCCT confident (>0.7 or <0.3) → Trust OCCT
        2. If OCCT ambiguous (0.3-0.7):
           a. Vision available + confident (>0.6) → Trust Vision
           b. Vision unavailable/uncertain → Default to PRI
        3. Return (part_type, confidence_score)

        Args:
            occt_rotational_score: OCCT geometry score (0.0=PRI, 1.0=ROT)
            vision_hint: Vision API hint (ROT/PRI/UNKNOWN), optional
            vision_confidence: Vision extraction confidence (0.0-1.0), optional

        Returns:
            Tuple of (part_type, confidence_score)
            - part_type: "ROT" or "PRI"
            - confidence_score: 0.0-1.0 (classification confidence)

        Examples:
            >>> classifier = HybridPartClassifier()
            >>> classifier.classify(0.85, None, None)
            ("ROT", 0.85)  # OCCT confident ROT

            >>> classifier.classify(0.45, "PRI", 0.8)
            ("PRI", 0.8)  # OCCT ambiguous, Vision confident PRI

            >>> classifier.classify(0.5, "UNKNOWN", 0.3)
            ("PRI", 0.5)  # Both ambiguous, default PRI
        """
        # Case 1: OCCT confident ROT
        if occt_rotational_score > self.OCCT_CONFIDENT_ROT_THRESHOLD:
            logger.debug(
                f"OCCT confident ROT (score={occt_rotational_score:.2f}), "
                f"ignoring Vision hint"
            )
            return ("ROT", occt_rotational_score)

        # Case 2: OCCT confident PRI
        if occt_rotational_score < self.OCCT_CONFIDENT_PRI_THRESHOLD:
            logger.debug(
                f"OCCT confident PRI (score={occt_rotational_score:.2f}), "
                f"ignoring Vision hint"
            )
            return ("PRI", 1.0 - occt_rotational_score)

        # Case 3: OCCT ambiguous (0.3-0.7 range)
        logger.debug(
            f"OCCT ambiguous (score={occt_rotational_score:.2f}), "
            f"checking Vision hint"
        )

        # Use Vision if available and confident
        if (
            vision_hint in ["ROT", "PRI"] and
            vision_confidence is not None and
            vision_confidence > self.VISION_CONFIDENCE_THRESHOLD
        ):
            logger.debug(
                f"Vision override: {vision_hint} "
                f"(confidence={vision_confidence:.0%})"
            )
            return (vision_hint, vision_confidence)

        # Case 4: Both ambiguous or Vision unavailable
        # Default to PRI (safer - milling machines can handle ROT parts, but not vice versa)
        logger.debug(
            f"Both ambiguous (OCCT={occt_rotational_score:.2f}, "
            f"Vision={vision_hint or 'N/A'}), defaulting to PRI"
        )
        return ("PRI", 0.5)  # Low confidence indicates uncertainty

    def get_decision_explanation(
        self,
        occt_rotational_score: float,
        vision_hint: Optional[Literal["ROT", "PRI", "UNKNOWN"]],
        vision_confidence: Optional[float],
        final_type: Literal["ROT", "PRI"],
        final_confidence: float
    ) -> str:
        """
        Generate human-readable explanation of classification decision.

        Useful for debugging and UI display.

        Args:
            occt_rotational_score: OCCT geometry score
            vision_hint: Vision API hint
            vision_confidence: Vision confidence
            final_type: Final classification result
            final_confidence: Final confidence score

        Returns:
            Explanation string (e.g., "OCCT confident ROT (score=0.85)")
        """
        if occt_rotational_score > self.OCCT_CONFIDENT_ROT_THRESHOLD:
            return (
                f"OCCT confident {final_type} "
                f"(rotational_score={occt_rotational_score:.2f})"
            )

        if occt_rotational_score < self.OCCT_CONFIDENT_PRI_THRESHOLD:
            return (
                f"OCCT confident {final_type} "
                f"(rotational_score={occt_rotational_score:.2f})"
            )

        if (
            vision_hint in ["ROT", "PRI"] and
            vision_confidence and
            vision_confidence > self.VISION_CONFIDENCE_THRESHOLD
        ):
            return (
                f"Vision override: {final_type} "
                f"(OCCT ambiguous={occt_rotational_score:.2f}, "
                f"Vision={vision_hint} @ {vision_confidence:.0%})"
            )

        return (
            f"Both ambiguous, default {final_type} "
            f"(OCCT={occt_rotational_score:.2f}, "
            f"Vision={vision_hint or 'N/A'})"
        )
