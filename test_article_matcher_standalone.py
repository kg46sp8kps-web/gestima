#!/usr/bin/env python3
"""Standalone unit tests for ArticleNumberMatcher (no dependencies)"""

import sys
import re
from typing import Optional, List
from dataclasses import dataclass

# Inline copy for standalone testing
CUSTOMER_PREFIXES = ["byn-", "trgcz-", "gelso-"]
REVISION_PATTERN = r"-([0-9]{2}|[A-Z])$"

@dataclass
class NormalizedArticleNumber:
    original: str
    normalized: str
    base: str
    prefix: Optional[str]
    revision: Optional[str]

def normalize(article_number: str) -> NormalizedArticleNumber:
    original = article_number.strip()
    prefix = None
    revision = None
    normalized = original
    base = original

    for known_prefix in CUSTOMER_PREFIXES:
        if original.lower().startswith(known_prefix.lower()):
            prefix = original[:len(known_prefix)]
            normalized = original[len(known_prefix):]
            break

    revision_match = re.search(REVISION_PATTERN, normalized)
    if revision_match:
        revision = revision_match.group(1)
        base = normalized[:revision_match.start()]
    else:
        base = normalized

    return NormalizedArticleNumber(original, normalized, base, prefix, revision)

def test_normalize_with_prefix():
    result = normalize("byn-10101251")
    assert result.prefix == "byn-", f"Expected prefix 'byn-', got {result.prefix}"
    assert result.normalized == "10101251", f"Expected '10101251', got {result.normalized}"
    assert result.base == "10101251"
    assert result.revision is None
    print("✅ normalize_with_prefix PASSED")

def test_normalize_with_revision():
    result = normalize("90057637-00")
    assert result.prefix is None
    assert result.base == "90057637", f"Expected base '90057637', got {result.base}"
    assert result.revision == "00", f"Expected revision '00', got {result.revision}"
    print("✅ normalize_with_revision PASSED")

def test_normalize_with_prefix_and_revision():
    result = normalize("byn-10101263-01")
    assert result.prefix == "byn-"
    assert result.normalized == "10101263-01"
    assert result.base == "10101263", f"Expected base '10101263', got {result.base}"
    assert result.revision == "01"
    print("✅ normalize_with_prefix_and_revision PASSED")

def test_trgcz_prefix():
    result = normalize("trgcz-123456")
    assert result.prefix == "trgcz-"
    assert result.base == "123456"
    print("✅ trgcz_prefix PASSED")

def run_all_tests():
    print("=" * 60)
    print("ARTICLE NUMBER MATCHER - UNIT TESTS (STANDALONE)")
    print("=" * 60)

    test_normalize_with_prefix()
    test_normalize_with_revision()
    test_normalize_with_prefix_and_revision()
    test_trgcz_prefix()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
