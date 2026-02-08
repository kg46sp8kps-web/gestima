"""GESTIMA - Scaled Prices Expander

Expands items with "Scaled prices: 1/5/10/20" into multiple quote items.

Example:
    Input:  1 item with quantity=1, notes="Scaled prices: 1/5/10/20"
    Output: 4 items with quantity=[1, 5, 10, 20]

Use case:
    Customer wants pricing for multiple quantities (volume pricing).
    Each quantity tier gets different unit price from batches.
"""

import re
import logging
from typing import List
from app.schemas.quote_request import ItemExtraction

logger = logging.getLogger(__name__)

# Pattern for scaled prices: "1/5/10/20", "1 / 5 / 10 / 20", "1, 5, 10, 20"
SCALED_PRICES_PATTERNS = [
    r"scaled\s+prices?\s*[:=]\s*([\d\s/,]+)",  # "Scaled prices: 1/5/10/20"
    r"quantities?\s*[:=]\s*([\d\s/,]+)",        # "Quantities: 1/5/10/20"
    r"volume\s+pricing\s*[:=]\s*([\d\s/,]+)",  # "Volume pricing: 1/5/10/20"
]


def extract_quantities(notes: str) -> List[int]:
    """
    Extract quantity values from scaled prices notation.

    Examples:
        "Scaled prices: 1/5/10/20" → [1, 5, 10, 20]
        "1 / 5 / 10 / 20" → [1, 5, 10, 20]
        "1, 5, 10, 20" → [1, 5, 10, 20]
        "Quantities: 100/500/1000" → [100, 500, 1000]

    Returns:
        List of quantities (sorted, deduplicated)
    """
    if not notes:
        return []

    notes_lower = notes.lower()

    for pattern in SCALED_PRICES_PATTERNS:
        match = re.search(pattern, notes_lower, re.IGNORECASE)
        if match:
            # Extract numbers from matched string
            numbers_str = match.group(1)

            # Split by / or , and extract integers
            quantities = []
            for part in re.split(r'[/,\s]+', numbers_str):
                part = part.strip()
                if part and part.isdigit():
                    quantities.append(int(part))

            if quantities:
                # Sort and deduplicate
                quantities = sorted(set(quantities))
                logger.debug(f"Extracted quantities from '{notes}': {quantities}")
                return quantities

    return []


def should_expand_scaled_prices(item: ItemExtraction) -> bool:
    """
    Check if item should be expanded based on scaled prices in notes.

    Criteria:
    - Has "scaled prices" or similar pattern in notes
    - Extracted quantities list is not empty

    Returns:
        True if item should be expanded to multiple rows
    """
    if not item.notes:
        return False

    quantities = extract_quantities(item.notes)
    return len(quantities) > 1  # Need at least 2 quantities to expand


def expand_item(item: ItemExtraction) -> List[ItemExtraction]:
    """
    Expand single item into multiple items based on scaled prices.

    Example:
        Input:
            ItemExtraction(
                article_number="byn-10101251",
                name="Halter",
                quantity=1,
                notes="Scaled prices: 1/5/10/20"
            )

        Output:
            [
                ItemExtraction(..., quantity=1, notes="Volume tier: 1 pc | Original: Scaled prices: 1/5/10/20"),
                ItemExtraction(..., quantity=5, notes="Volume tier: 5 pcs | Original: Scaled prices: 1/5/10/20"),
                ItemExtraction(..., quantity=10, notes="Volume tier: 10 pcs | Original: Scaled prices: 1/5/10/20"),
                ItemExtraction(..., quantity=20, notes="Volume tier: 20 pcs | Original: Scaled prices: 1/5/10/20"),
            ]

    Returns:
        List of expanded items (one per quantity tier)
    """
    quantities = extract_quantities(item.notes or "")

    if len(quantities) <= 1:
        # No expansion needed (only 1 quantity or none found)
        return [item]

    expanded_items = []
    original_notes = item.notes or ""

    for qty in quantities:
        # Create new item for this quantity tier
        expanded_item = ItemExtraction(
            article_number=item.article_number,
            drawing_number=item.drawing_number,
            name=item.name,
            quantity=qty,
            notes=f"🎯 Volume tier: {qty} {'pc' if qty == 1 else 'pcs'} | Original: {original_notes}",
            confidence=item.confidence
        )
        expanded_items.append(expanded_item)

    logger.info(
        f"Expanded '{item.article_number}' from 1 row → {len(expanded_items)} rows "
        f"(quantities: {quantities})"
    )

    return expanded_items


def expand_all_items(items: List[ItemExtraction]) -> List[ItemExtraction]:
    """
    Expand all items that have scaled prices notation.

    Example:
        Input: [
            Item1 (scaled prices: 1/5/10/20),
            Item2 (no scaled prices),
            Item3 (scaled prices: 100/500)
        ]

        Output: [
            Item1 qty=1,
            Item1 qty=5,
            Item1 qty=10,
            Item1 qty=20,
            Item2 (unchanged),
            Item3 qty=100,
            Item3 qty=500
        ]

    Returns:
        Expanded list of items
    """
    expanded = []

    for item in items:
        if should_expand_scaled_prices(item):
            # Expand this item to multiple rows
            expanded.extend(expand_item(item))
        else:
            # Keep as-is
            expanded.append(item)

    logger.info(f"Expanded {len(items)} items → {len(expanded)} items (scaled prices expansion)")

    return expanded
