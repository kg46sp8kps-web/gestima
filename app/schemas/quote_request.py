"""GESTIMA - Quote Request Schemas

AI-powered quote request parsing from PDF.

Workflow:
1. Upload PDF → Claude Vision
2. Extract customer + items
3. Review & edit by user
4. Match Parts + Batches
5. Create Quote + QuoteItems
"""

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# AI Extraction Results (Raw)
# =============================================================================

class CustomerExtraction(BaseModel):
    """Customer data extracted from PDF"""
    company_name: str = Field(..., description="Název společnosti")
    contact_person: Optional[str] = Field(None, description="Kontaktní osoba")
    email: Optional[str] = Field(None, description="Email")
    phone: Optional[str] = Field(None, description="Telefon")
    ico: Optional[str] = Field(None, description="IČO (Czech business ID)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="AI confidence score 0-1")


class ItemExtraction(BaseModel):
    """Single item (part + quantity) extracted from PDF"""
    article_number: str = Field(..., min_length=1, max_length=50, description="Číslo výkresu/article number")
    name: str = Field(..., min_length=1, max_length=200, description="Název dílu")
    quantity: int = Field(..., gt=0, description="Množství kusů")
    notes: Optional[str] = Field(None, description="Poznámky k položce")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="AI confidence score 0-1")


class QuoteRequestExtraction(BaseModel):
    """Complete AI extraction result from PDF"""
    customer: CustomerExtraction
    items: List[ItemExtraction] = Field(..., description="List of items (can have duplicates for same article_number)")
    valid_until: Optional[date] = Field(None, description="Platnost nabídky do")
    notes: Optional[str] = Field(None, description="Obecné poznámky")


# =============================================================================
# Part & Batch Matching Results
# =============================================================================

class BatchMatch(BaseModel):
    """Batch matching result for specific quantity"""
    batch_id: Optional[int] = None
    batch_quantity: Optional[int] = None  # Which batch size (10, 100, 500...)
    status: str = Field(..., description="exact | lower | missing")
    unit_price: float = Field(0.0, ge=0.0)
    line_total: float = Field(0.0, ge=0.0)
    warnings: List[str] = Field(default_factory=list)


class PartMatch(BaseModel):
    """Part matching result"""
    part_id: Optional[int] = None
    part_number: Optional[str] = None
    part_exists: bool = False
    article_number: str
    name: str
    quantity: int
    notes: Optional[str] = None

    # Batch matching
    batch_match: Optional[BatchMatch] = None


class CustomerMatch(BaseModel):
    """Customer matching result"""
    company_name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    ico: Optional[str] = None

    # Matching result
    partner_id: Optional[int] = None
    partner_number: Optional[str] = None
    partner_exists: bool = False
    match_confidence: float = 0.0


class QuoteRequestReview(BaseModel):
    """Complete review data (extraction + matching)"""
    customer: CustomerMatch
    items: List[PartMatch] = Field(..., description="All items with part+batch matching")
    valid_until: Optional[date] = None
    notes: Optional[str] = None

    # Summary
    total_items: int = Field(0, description="Total number of items")
    unique_parts: int = Field(0, description="Number of unique parts")
    matched_parts: int = Field(0, description="Number of existing parts")
    new_parts: int = Field(0, description="Number of new parts to create")
    missing_batches: int = Field(0, description="Number of items without batch match")


# =============================================================================
# Quote Creation from Request
# =============================================================================

class QuoteFromRequestItem(BaseModel):
    """Item for creating quote from request"""
    part_id: Optional[int] = Field(None, description="Existing part ID or None (will create)")
    article_number: str = Field(..., description="Article number for new part creation")
    name: str = Field(..., description="Name for new part creation")
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None


class QuoteFromRequestCreate(BaseModel):
    """Create quote + parts + items from request"""
    partner_id: Optional[int] = Field(None, description="Existing partner ID or None (will create)")
    partner_data: Optional[CustomerMatch] = Field(None, description="Partner data if creating new")

    items: List[QuoteFromRequestItem] = Field(..., min_length=1)

    title: str = Field(..., max_length=200)
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    discount_percent: float = Field(0.0, ge=0.0, le=100.0)
    tax_percent: float = Field(21.0, ge=0.0, le=100.0)
