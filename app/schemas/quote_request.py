"""GESTIMA - Quote Request Schemas

AI-powered quote request parsing from PDF.

Workflow:
1. Upload PDF → AI Vision
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
    drawing_number: Optional[str] = Field(None, max_length=50, description="Číslo výkresu (Drawing Number)")
    name: str = Field(..., min_length=1, max_length=200, description="Název dílu")
    quantity: int = Field(..., gt=0, description="Množství kusů")
    notes: Optional[str] = Field(None, description="Poznámky k položce")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="AI confidence score 0-1")


class QuoteRequestExtraction(BaseModel):
    """Complete AI extraction result from PDF"""
    customer: CustomerExtraction
    items: List[ItemExtraction] = Field(..., description="List of items (can have duplicates for same article_number)")
    customer_request_number: Optional[str] = Field(None, max_length=50, description="Číslo poptávky zákazníka (RFQ number)")
    request_date: Optional[date] = Field(None, description="Datum vystavení poptávky")
    offer_deadline: Optional[date] = Field(None, description="Deadline pro předložení nabídky")
    valid_until: Optional[date] = Field(None, description="Platnost nabídky do (deprecated, use offer_deadline)")
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
    drawing_number: Optional[str] = None
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


class ReviewSummary(BaseModel):
    """Summary statistics for quote request review"""
    total_items: int = Field(0, description="Total number of items")
    unique_parts: int = Field(0, description="Number of unique parts")
    matched_parts: int = Field(0, description="Number of existing parts")
    new_parts: int = Field(0, description="Number of new parts to create")
    missing_batches: int = Field(0, description="Number of items without batch match")


class QuoteRequestReview(BaseModel):
    """Complete review data (extraction + matching)"""
    customer: CustomerMatch
    items: List[PartMatch] = Field(..., description="All items with part+batch matching")
    customer_request_number: Optional[str] = Field(None, max_length=50, description="Číslo poptávky zákazníka")
    request_date: Optional[date] = Field(None, description="Datum vystavení poptávky")
    offer_deadline: Optional[date] = Field(None, description="Deadline pro předložení nabídky")
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    summary: ReviewSummary


# =============================================================================
# Quote Creation from Request
# =============================================================================

class PartnerCreateData(BaseModel):
    """Partner data for creating new partner"""
    company_name: str = Field(..., max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    ico: Optional[str] = Field(None, max_length=20)
    dic: Optional[str] = Field(None, max_length=20)
    is_customer: bool = True
    is_supplier: bool = False


class QuoteFromRequestItem(BaseModel):
    """Item for creating quote from request"""
    part_id: Optional[int] = Field(None, description="Existing part ID or None (will create)")
    article_number: str = Field(..., min_length=1, max_length=50, description="Article number for new part creation")
    drawing_number: Optional[str] = Field(None, max_length=50, description="Drawing number for new part creation")
    name: str = Field(..., min_length=1, max_length=200, description="Name for new part creation")
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None


class QuoteFromRequestCreate(BaseModel):
    """Create quote + parts + items from request"""
    partner_id: Optional[int] = Field(None, description="Existing partner ID or None (will create)")
    partner_data: Optional[PartnerCreateData] = Field(None, description="Partner data if creating new")

    items: List[QuoteFromRequestItem] = Field(..., min_length=1)

    title: str = Field(..., max_length=200)
    customer_request_number: Optional[str] = Field(None, max_length=50, description="Číslo poptávky zákazníka")
    request_date: Optional[date] = Field(None, description="Datum vystavení poptávky")
    offer_deadline: Optional[date] = Field(None, description="Deadline pro předložení nabídky")
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    discount_percent: float = Field(0.0, ge=0.0, le=100.0)
    tax_percent: float = Field(21.0, ge=0.0, le=100.0)


# =============================================================================
# V2: Enhanced Quote From Request (with drawings + technology)
# =============================================================================

class DrawingAnalysis(BaseModel):
    """AI Vision analysis result for a single drawing PDF"""
    filename: str = Field(..., description="Original PDF filename")
    drawing_number: Optional[str] = Field(None, max_length=50, description="Drawing number from title block")
    article_number: Optional[str] = Field(None, max_length=50, description="Article number from title block")
    material_hint: Optional[str] = Field(None, max_length=100, description="Material detected from title block")
    dimensions_hint: Optional[str] = Field(None, max_length=200, description="Key dimensions from drawing")

    # TimeVision estimation (from same AI call)
    part_type: str = Field("PRI", description="ROT / PRI / COMBINED")
    complexity: str = Field("medium", description="simple / medium / complex")
    estimated_time_min: float = Field(30.0, ge=0.0, description="AI estimated machining time")
    max_diameter_mm: Optional[float] = Field(None, ge=0.0)
    max_length_mm: Optional[float] = Field(None, ge=0.0)
    confidence: float = Field(0.5, ge=0.0, le=1.0)


class DrawingMatch(BaseModel):
    """Match between an uploaded drawing and a request item"""
    drawing_index: int = Field(..., ge=0, description="Index in drawing_pdfs list")
    item_index: Optional[int] = Field(None, ge=0, description="Matched item index (None = unmatched)")
    match_method: str = Field("none", description="ai_vision / filename / manual / none")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class QuoteRequestReviewV2(BaseModel):
    """Enhanced review data with drawing analysis"""
    customer: CustomerMatch
    items: List[PartMatch] = Field(..., description="All items with part+batch matching")
    customer_request_number: Optional[str] = Field(None, max_length=50)
    request_date: Optional[date] = Field(None, description="Datum vystavení poptávky")
    offer_deadline: Optional[date] = Field(None, description="Deadline pro předložení nabídky")
    notes: Optional[str] = None
    summary: ReviewSummary

    # V2: Drawing analysis
    drawing_analyses: List[DrawingAnalysis] = Field(default_factory=list)
    drawing_matches: List[DrawingMatch] = Field(default_factory=list)


class EstimationData(BaseModel):
    """TimeVision estimation data carried from parse to create step"""
    part_type: str = Field("PRI", description="ROT / PRI / COMBINED")
    complexity: str = Field("medium", description="simple / medium / complex")
    estimated_time_min: float = Field(30.0, ge=0.0)
    max_diameter_mm: Optional[float] = Field(None, ge=0.0)
    max_length_mm: Optional[float] = Field(None, ge=0.0)


class QuoteFromRequestItemV2(BaseModel):
    """Enhanced item for creating quote from request (V2)"""
    part_id: Optional[int] = Field(None, description="Existing part ID or None (will create)")
    article_number: str = Field(..., min_length=1, max_length=50)
    drawing_number: Optional[str] = Field(None, max_length=50)
    name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None
    drawing_index: Optional[int] = Field(None, ge=0, description="Index into drawing_files for this item")
    estimation: Optional[EstimationData] = Field(None, description="AI estimation from parse step")


class QuoteFromRequestCreateV2(BaseModel):
    """Enhanced quote creation from request (V2 — creates everything)"""
    partner_id: Optional[int] = Field(None, description="Existing partner ID")
    partner_data: Optional[PartnerCreateData] = Field(None, description="New partner data")

    items: List[QuoteFromRequestItemV2] = Field(..., min_length=1)

    title: str = Field(..., max_length=200)
    customer_request_number: Optional[str] = Field(None, max_length=50)
    request_date: Optional[date] = Field(None, description="Datum vystavení poptávky")
    offer_deadline: Optional[date] = Field(None, description="Deadline pro předložení nabídky")
    valid_until: Optional[date] = None
    notes: Optional[str] = None
    discount_percent: float = Field(0.0, ge=0.0, le=100.0)
    tax_percent: float = Field(21.0, ge=0.0, le=100.0)


class QuoteCreationPartResult(BaseModel):
    """Result for a single part in quote creation"""
    article_number: str
    part_number: Optional[str] = None
    name: str
    is_new: bool = False
    drawing_linked: bool = False
    technology_generated: bool = False
    batch_set_frozen: bool = False
    unit_price: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class QuoteCreationResult(BaseModel):
    """Complete result of quote-from-request creation"""
    quote_number: str
    quote_id: int
    partner_number: Optional[str] = None
    partner_is_new: bool = False
    parts: List[QuoteCreationPartResult] = Field(default_factory=list)
    parts_created: int = 0
    parts_existing: int = 0
    drawings_linked: int = 0
    total_amount: float = 0.0
    warnings: List[str] = Field(default_factory=list)
