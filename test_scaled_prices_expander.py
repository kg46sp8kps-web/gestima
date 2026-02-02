#!/usr/bin/env python3
"""Unit tests for Scaled Prices Expander"""

import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.scaled_prices_expander import (
    extract_quantities,
    should_expand_scaled_prices,
    expand_item,
    expand_all_items
)
from app.schemas.quote_request import ItemExtraction


def test_extract_quantities_basic():
    """Test basic quantity extraction"""
    notes = "Scaled prices: 1/5/10/20"
    quantities = extract_quantities(notes)

    assert quantities == [1, 5, 10, 20], f"Expected [1, 5, 10, 20], got {quantities}"
    print("✅ extract_quantities_basic PASSED")


def test_extract_quantities_with_spaces():
    """Test extraction with spaces"""
    notes = "Scaled prices: 1 / 5 / 10 / 20"
    quantities = extract_quantities(notes)

    assert quantities == [1, 5, 10, 20]
    print("✅ extract_quantities_with_spaces PASSED")


def test_extract_quantities_comma_separated():
    """Test comma-separated format"""
    notes = "Quantities: 1, 5, 10, 20"
    quantities = extract_quantities(notes)

    assert quantities == [1, 5, 10, 20]
    print("✅ extract_quantities_comma_separated PASSED")


def test_extract_quantities_uppercase():
    """Test case insensitivity"""
    notes = "SCALED PRICES: 1/5/10/20"
    quantities = extract_quantities(notes)

    assert quantities == [1, 5, 10, 20]
    print("✅ extract_quantities_uppercase PASSED")


def test_extract_quantities_volume_pricing():
    """Test volume pricing keyword"""
    notes = "Volume pricing: 100/500/1000"
    quantities = extract_quantities(notes)

    assert quantities == [100, 500, 1000]
    print("✅ extract_quantities_volume_pricing PASSED")


def test_extract_quantities_none():
    """Test no quantities found"""
    notes = "Regular order, no scaled prices"
    quantities = extract_quantities(notes)

    assert quantities == []
    print("✅ extract_quantities_none PASSED")


def test_should_expand_true():
    """Test expansion detection - should expand"""
    item = ItemExtraction(
        article_number="TEST-001",
        name="Test Part",
        quantity=1,
        notes="Scaled prices: 1/5/10/20",
        confidence=0.95
    )

    assert should_expand_scaled_prices(item) == True
    print("✅ should_expand_true PASSED")


def test_should_expand_false():
    """Test expansion detection - should NOT expand"""
    item = ItemExtraction(
        article_number="TEST-002",
        name="Test Part",
        quantity=1,
        notes="Regular order",
        confidence=0.95
    )

    assert should_expand_scaled_prices(item) == False
    print("✅ should_expand_false PASSED")


def test_expand_item_basic():
    """Test single item expansion"""
    item = ItemExtraction(
        article_number="byn-10101251",
        name="Halter",
        quantity=1,
        notes="Scaled prices: 1/5/10/20",
        confidence=0.98
    )

    expanded = expand_item(item)

    assert len(expanded) == 4, f"Expected 4 items, got {len(expanded)}"
    assert expanded[0].quantity == 1
    assert expanded[1].quantity == 5
    assert expanded[2].quantity == 10
    assert expanded[3].quantity == 20

    # Check all have same article_number and name
    for exp_item in expanded:
        assert exp_item.article_number == "byn-10101251"
        assert exp_item.name == "Halter"
        assert "Volume tier:" in exp_item.notes

    print("✅ expand_item_basic PASSED")


def test_expand_item_no_scaling():
    """Test item without scaling (should return as-is)"""
    item = ItemExtraction(
        article_number="TEST-003",
        name="Regular Part",
        quantity=10,
        notes="No scaling",
        confidence=0.95
    )

    expanded = expand_item(item)

    assert len(expanded) == 1, f"Expected 1 item, got {len(expanded)}"
    assert expanded[0] == item
    print("✅ expand_item_no_scaling PASSED")


def test_expand_all_items():
    """Test expanding multiple items"""
    items = [
        ItemExtraction(
            article_number="byn-10101251",
            name="Halter",
            quantity=1,
            notes="Scaled prices: 1/5/10/20",
            confidence=0.98
        ),
        ItemExtraction(
            article_number="REGULAR-001",
            name="Regular Part",
            quantity=50,
            notes="No scaling",
            confidence=0.95
        ),
        ItemExtraction(
            article_number="byn-10101263-01",
            name="Halter 2",
            quantity=1,
            notes="SCALED PRICES: 1/5/10/20",  # Fixed: added colon
            confidence=0.98
        )
    ]

    expanded = expand_all_items(items)

    # Expect: 4 (first item) + 1 (second item) + 4 (third item) = 9 items
    assert len(expanded) == 9, f"Expected 9 items, got {len(expanded)}"

    # First 4 should be from byn-10101251
    assert expanded[0].article_number == "byn-10101251"
    assert expanded[0].quantity == 1
    assert expanded[3].quantity == 20

    # 5th should be regular item (unchanged)
    assert expanded[4].article_number == "REGULAR-001"
    assert expanded[4].quantity == 50

    # Last 4 should be from byn-10101263-01
    assert expanded[5].article_number == "byn-10101263-01"
    assert expanded[8].quantity == 20

    print("✅ expand_all_items PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("SCALED PRICES EXPANDER - UNIT TESTS")
    print("=" * 60)

    test_extract_quantities_basic()
    test_extract_quantities_with_spaces()
    test_extract_quantities_comma_separated()
    test_extract_quantities_uppercase()
    test_extract_quantities_volume_pricing()
    test_extract_quantities_none()
    test_should_expand_true()
    test_should_expand_false()
    test_expand_item_basic()
    test_expand_item_no_scaling()
    test_expand_all_items()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nExpansion Example:")
    print("  Input:  1 item (quantity=1, notes='Scaled prices: 1/5/10/20')")
    print("  Output: 4 items (quantities=[1, 5, 10, 20])")
    print("\nThis allows separate pricing for each volume tier!")


if __name__ == "__main__":
    run_all_tests()
