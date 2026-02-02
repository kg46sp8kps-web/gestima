#!/usr/bin/env python3
"""Test case demonstrating Part deduplication logic"""

def test_part_deduplication_logic():
    """
    Simulate the deduplication logic for creating Parts from Quote Items.

    Scenario:
        8 items with 2 unique article_numbers (4 items each)
        Should create only 2 Parts (not 8)
    """

    # Mock items (like QuoteFromRequestItem)
    class Item:
        def __init__(self, article_number, name, quantity):
            self.article_number = article_number
            self.name = name
            self.quantity = quantity
            self.part_id = None  # Initially null

    items = [
        # 4 items for byn-10101251 (different quantities)
        Item("byn-10101251", "Halter", 1),
        Item("byn-10101251", "Halter", 5),
        Item("byn-10101251", "Halter", 10),
        Item("byn-10101251", "Halter", 20),

        # 4 items for byn-10101263-01 (different quantities)
        Item("byn-10101263-01", "Halter", 1),
        Item("byn-10101263-01", "Halter", 5),
        Item("byn-10101263-01", "Halter", 10),
        Item("byn-10101263-01", "Halter", 20),
    ]

    # Simulate deduplication logic
    article_to_part_id = {}
    parts_created = 0
    part_id_counter = 1000  # Mock ID generator

    for item in items:
        if not item.part_id:
            if item.article_number in article_to_part_id:
                # Reuse existing part_id
                item.part_id = article_to_part_id[item.article_number]
                print(f"  ♻️  Reusing Part {item.part_id} for {item.article_number} (qty={item.quantity})")
            else:
                # Create new part
                part_id_counter += 1
                parts_created += 1
                article_to_part_id[item.article_number] = part_id_counter
                item.part_id = part_id_counter
                print(f"  ✅ Created Part {item.part_id} for {item.article_number} (qty={item.quantity})")

    # Verify results
    print(f"\n📊 Results:")
    print(f"  Total items: {len(items)}")
    print(f"  Unique article_numbers: {len(set(i.article_number for i in items))}")
    print(f"  Parts created: {parts_created}")
    print(f"  Part ID mapping:")
    for article, part_id in article_to_part_id.items():
        count = sum(1 for i in items if i.article_number == article)
        print(f"    {article} → Part {part_id} (used by {count} items)")

    # Assertions
    assert parts_created == 2, f"Expected 2 parts created, got {parts_created}"
    assert len(article_to_part_id) == 2, f"Expected 2 unique article_numbers, got {len(article_to_part_id)}"

    # Verify all items with same article_number have same part_id
    for article_number in set(i.article_number for i in items):
        part_ids = [i.part_id for i in items if i.article_number == article_number]
        assert len(set(part_ids)) == 1, f"Items with {article_number} have different part_ids: {part_ids}"

    print("\n✅ Deduplication test PASSED!")
    print("\n💡 Summary:")
    print("  - 8 items → 2 Parts (not 8)")
    print("  - Each article_number creates only 1 Part")
    print("  - Multiple quantities share the same Part")


if __name__ == "__main__":
    print("=" * 70)
    print("PART DEDUPLICATION TEST")
    print("=" * 70)
    print("\nScenario: 8 QuoteItems with 2 unique article_numbers")
    print("Expected: Create only 2 Parts (deduplicated)\n")

    test_part_deduplication_logic()

    print("\n" + "=" * 70)
    print("Example Database State After Quote Creation:")
    print("=" * 70)
    print("""
Parts Table:
  ID   | part_number | article_number    | name
  -----|-------------|-------------------|--------
  1001 | 10000123    | byn-10101251      | Halter
  1002 | 10000124    | byn-10101263-01   | Halter

QuoteItems Table:
  ID  | quote_id | part_id | quantity | unit_price | line_total
  ----|----------|---------|----------|------------|------------
  1   | 501      | 1001    | 1        | 150.00     | 150.00
  2   | 501      | 1001    | 5        | 130.00     | 650.00
  3   | 501      | 1001    | 10       | 120.00     | 1200.00
  4   | 501      | 1001    | 20       | 110.00     | 2200.00
  5   | 501      | 1002    | 1        | 150.00     | 150.00
  6   | 501      | 1002    | 5        | 130.00     | 650.00
  7   | 501      | 1002    | 10       | 120.00     | 1200.00
  8   | 501      | 1002    | 20       | 110.00     | 2200.00

✅ 2 Parts, 8 QuoteItems (correct!)
    """)
