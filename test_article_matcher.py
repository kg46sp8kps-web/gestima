#!/usr/bin/env python3
"""Unit tests for ArticleNumberMatcher"""

from app.services.article_number_matcher import (
    ArticleNumberMatcher,
    normalize_article_number,
    get_search_variants
)

def test_normalize_with_prefix():
    """Test normalization with customer prefix"""
    result = ArticleNumberMatcher.normalize("byn-10101251")

    assert result.original == "byn-10101251"
    assert result.prefix == "byn-"
    assert result.normalized == "10101251"
    assert result.base == "10101251"
    assert result.revision is None

    print("✅ normalize_with_prefix PASSED")


def test_normalize_with_revision():
    """Test normalization with drawing revision"""
    result = ArticleNumberMatcher.normalize("90057637-00")

    assert result.original == "90057637-00"
    assert result.prefix is None
    assert result.normalized == "90057637-00"
    assert result.base == "90057637"
    assert result.revision == "00"

    print("✅ normalize_with_revision PASSED")


def test_normalize_with_prefix_and_revision():
    """Test normalization with both prefix and revision"""
    result = ArticleNumberMatcher.normalize("byn-10101263-01")

    assert result.original == "byn-10101263-01"
    assert result.prefix == "byn-"
    assert result.normalized == "10101263-01"
    assert result.base == "10101263"
    assert result.revision == "01"

    print("✅ normalize_with_prefix_and_revision PASSED")


def test_normalize_plain():
    """Test normalization without prefix or revision"""
    result = ArticleNumberMatcher.normalize("123456")

    assert result.original == "123456"
    assert result.prefix is None
    assert result.normalized == "123456"
    assert result.base == "123456"
    assert result.revision is None

    print("✅ normalize_plain PASSED")


def test_generate_variants():
    """Test variant generation for fuzzy search"""
    variants = ArticleNumberMatcher.generate_variants("byn-10101251")

    assert "byn-10101251" in variants  # Original
    assert "10101251" in variants      # Without prefix

    print("✅ generate_variants PASSED")


def test_generate_variants_with_revision():
    """Test variant generation with revision"""
    variants = ArticleNumberMatcher.generate_variants("byn-10101263-01")

    assert "byn-10101263-01" in variants  # Original
    assert "10101263-01" in variants      # Without prefix
    assert "10101263" in variants         # Without prefix AND revision

    print("✅ generate_variants_with_revision PASSED")


def test_match_type_exact():
    """Test exact match"""
    match_type, warning = ArticleNumberMatcher.match_type(
        "byn-10101251",
        "byn-10101251"
    )

    assert match_type == "exact"
    assert warning == ""

    print("✅ match_type_exact PASSED")


def test_match_type_prefix_stripped():
    """Test match after stripping prefix"""
    match_type, warning = ArticleNumberMatcher.match_type(
        "byn-10101251",  # Input
        "10101251"       # DB (no prefix)
    )

    assert match_type == "prefix_stripped"
    assert "Prefix mismatch" in warning

    print("✅ match_type_prefix_stripped PASSED")


def test_match_type_revision_ignored():
    """Test match with different revisions"""
    match_type, warning = ArticleNumberMatcher.match_type(
        "90057637-00",  # Input (rev 00)
        "90057637-01"   # DB (rev 01)
    )

    assert match_type == "revision_ignored"
    assert "Revision mismatch" in warning

    print("✅ match_type_revision_ignored PASSED")


def test_convenience_function():
    """Test convenience function"""
    normalized = normalize_article_number("byn-10101263-01")
    assert normalized == "10101263"

    variants = get_search_variants("byn-10101263-01")
    assert len(variants) >= 2

    print("✅ convenience_function PASSED")


def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("ARTICLE NUMBER MATCHER - UNIT TESTS")
    print("=" * 60)

    test_normalize_with_prefix()
    test_normalize_with_revision()
    test_normalize_with_prefix_and_revision()
    test_normalize_plain()
    test_generate_variants()
    test_generate_variants_with_revision()
    test_match_type_exact()
    test_match_type_prefix_stripped()
    test_match_type_revision_ignored()
    test_convenience_function()

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
