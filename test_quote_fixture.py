#!/usr/bin/env python3
"""Test script for quote request fixture validation"""

import json
from pathlib import Path
from pydantic import ValidationError

# Import schemas
from app.schemas.quote_request import (
    QuoteRequestExtraction,
    QuoteRequestReview,
    QuoteFromRequestCreate
)

def load_fixture():
    """Load fixture from JSON"""
    fixture_path = Path("tests/fixtures/quote_request_gelso_p20971.json")
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def test_extraction_validation():
    """Test extraction schema validation"""
    print("\n=== Testing QuoteRequestExtraction ===")
    fixture = load_fixture()

    try:
        extraction = QuoteRequestExtraction.model_validate(fixture['extraction'])
        print("✅ Extraction validation PASSED")
        print(f"   Customer: {extraction.customer.company_name}")
        print(f"   Items: {len(extraction.items)}")
        for i, item in enumerate(extraction.items, 1):
            print(f"     {i}. {item.article_number} - {item.name} ({item.quantity}x)")
        return extraction
    except ValidationError as e:
        print("❌ Extraction validation FAILED")
        print(e)
        return None

def test_review_validation():
    """Test review schema validation"""
    print("\n=== Testing QuoteRequestReview ===")
    fixture = load_fixture()

    try:
        review = QuoteRequestReview.model_validate(fixture['review'])
        print("✅ Review validation PASSED")
        print(f"   Customer: {review.customer.company_name} (exists: {review.customer.partner_exists})")
        print(f"   Summary: {review.summary.total_items} items, {review.summary.new_parts} new parts")
        return review
    except ValidationError as e:
        print("❌ Review validation FAILED")
        print(e)
        return None

def test_quote_create_validation():
    """Test quote creation schema validation"""
    print("\n=== Testing QuoteFromRequestCreate ===")
    fixture = load_fixture()

    try:
        quote_create = QuoteFromRequestCreate.model_validate(fixture['quote_create'])
        print("✅ Quote creation validation PASSED")
        print(f"   Title: {quote_create.title}")
        print(f"   Partner: {quote_create.partner_data.company_name if quote_create.partner_data else 'Existing'}")
        print(f"   Items: {len(quote_create.items)}")

        # Check for empty article_number or name (new validation)
        for i, item in enumerate(quote_create.items, 1):
            if not item.article_number:
                print(f"   ⚠️  Item {i}: Empty article_number!")
            if not item.name:
                print(f"   ⚠️  Item {i}: Empty name!")
            if item.quantity <= 0:
                print(f"   ⚠️  Item {i}: Invalid quantity ({item.quantity})!")

        return quote_create
    except ValidationError as e:
        print("❌ Quote creation validation FAILED")
        for error in e.errors():
            loc = ' -> '.join(str(l) for l in error['loc'])
            print(f"   ❌ {loc}: {error['msg']}")
        return None

def print_fixture_json():
    """Print fixture as JSON for API testing"""
    print("\n=== JSON for API Testing ===")
    fixture = load_fixture()
    print(json.dumps(fixture['quote_create'], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    print("=" * 60)
    print("QUOTE REQUEST FIXTURE VALIDATION TEST")
    print("=" * 60)

    # Test all schemas
    extraction = test_extraction_validation()
    review = test_review_validation()
    quote_create = test_quote_create_validation()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Extraction:     {'✅ PASS' if extraction else '❌ FAIL'}")
    print(f"Review:         {'✅ PASS' if review else '❌ FAIL'}")
    print(f"Quote Create:   {'✅ PASS' if quote_create else '❌ FAIL'}")

    if all([extraction, review, quote_create]):
        print("\n🎉 All validations passed! Fixture is ready for testing.")
        print_fixture_json()
    else:
        print("\n❌ Some validations failed. Check errors above.")
