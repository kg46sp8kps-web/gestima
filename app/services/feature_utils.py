"""
Feature extraction utilities - shared helpers for feature recognition
"""
from typing import List, Dict


def deduplicate_features(features: List[Dict]) -> List[Dict]:
    """
    Deduplicate features using consistent key strategy.

    Features are considered duplicates if they have same:
    - type
    - diameter (rounded to 2 decimals)
    - angle (rounded to 1 decimal)
    - radius (rounded to 2 decimals)

    Args:
        features: List of feature dicts with type, diameter, angle, radius

    Returns:
        List of unique features (first occurrence kept)

    Example:
        >>> features = [
        ...     {'type': 'hole', 'diameter': 19.0},
        ...     {'type': 'hole', 'diameter': 19.001},  # Duplicate (rounds to 19.0)
        ...     {'type': 'cone', 'angle': 31.2}
        ... ]
        >>> deduplicate_features(features)
        [{'type': 'hole', 'diameter': 19.0}, {'type': 'cone', 'angle': 31.2}]
    """
    seen = set()
    unique = []

    for feature in features:
        # Create tuple key with normalized floats
        key = (
            feature.get('type', 'unknown'),
            normalize_feature_value(feature.get('diameter'), 2),
            normalize_feature_value(feature.get('angle'), 1),
            normalize_feature_value(feature.get('radius'), 2)
        )

        if key not in seen:
            seen.add(key)
            unique.append(feature)

    return unique


def normalize_feature_value(value: any, decimal_places: int = 2) -> float:
    """
    Normalize feature value to consistent precision.

    Handles None, strings, ints, floats.

    Args:
        value: Value to normalize
        decimal_places: Number of decimal places

    Returns:
        Normalized float value (0.0 if invalid)
    """
    if value is None:
        return 0.0
    try:
        return round(float(value), decimal_places)
    except (ValueError, TypeError):
        return 0.0
