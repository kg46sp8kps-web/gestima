"""GESTIMA - Test endpoints for quote request parsing (DEV ONLY)

Mock endpoints that return fixture data for testing without AI API calls.
"""

import json
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.quote_request import QuoteRequestReview
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def load_fixture():
    """Load test fixture"""
    fixture_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "quote_request_gelso_p20971.json"
    if not fixture_path.exists():
        raise HTTPException(500, f"Fixture not found: {fixture_path}")

    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@router.get("/parse-request-mock", response_model=dict)
async def parse_quote_request_mock(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mock endpoint that returns fixture data (GELSO AG P20971).

    Use this for testing the quote creation flow without calling AI API.

    Returns same structure as POST /quotes/parse-request but from fixture.
    """
    if not settings.DEBUG:
        raise HTTPException(403, "Mock endpoints only available in DEBUG mode")

    logger.info(f"Mock parse request by {current_user.username}")

    fixture = load_fixture()

    # Return the review part (what /parse-request returns)
    review_data = fixture['review']

    # Validate with Pydantic
    review = QuoteRequestReview.model_validate(review_data)

    return review.model_dump()


@router.get("/fixture/extraction")
async def get_fixture_extraction(
    current_user: User = Depends(get_current_user)
):
    """Get raw extraction data from fixture"""
    if not settings.DEBUG:
        raise HTTPException(403, "Mock endpoints only available in DEBUG mode")

    fixture = load_fixture()
    return fixture['extraction']


@router.get("/fixture/review")
async def get_fixture_review(
    current_user: User = Depends(get_current_user)
):
    """Get review data from fixture"""
    if not settings.DEBUG:
        raise HTTPException(403, "Mock endpoints only available in DEBUG mode")

    fixture = load_fixture()
    return fixture['review']


@router.get("/fixture/quote-create")
async def get_fixture_quote_create(
    current_user: User = Depends(get_current_user)
):
    """Get quote creation payload from fixture"""
    if not settings.DEBUG:
        raise HTTPException(403, "Mock endpoints only available in DEBUG mode")

    fixture = load_fixture()
    return fixture['quote_create']
