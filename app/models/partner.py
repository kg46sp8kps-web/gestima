"""GESTIMA - Partner model

Partners serve dual purpose:
- Customers (quotations, orders)
- Suppliers (material purchase)

Design principles:
- Shared table with is_customer/is_supplier flags (KISS)
- Czech business validation (ICO, DIC)
- Auto-generated partner_number (70XXXXXX)
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin


class Partner(Base, AuditMixin):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    partner_number = Column(String(8), unique=True, nullable=False, index=True)  # 70XXXXXX

    # Základní info
    company_name = Column(String(200), nullable=False, index=True)
    ico = Column(String(20), nullable=True, index=True)
    dic = Column(String(20), nullable=True)

    # Kontakt
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    contact_person = Column(String(100), nullable=True)

    # Adresa
    street = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(2), default="CZ", nullable=False)

    # Typ partnera (Boolean flags for flexibility)
    is_customer = Column(Boolean, default=True, nullable=False, index=True)
    is_supplier = Column(Boolean, default=False, nullable=False, index=True)

    # Notes
    notes = Column(String(500), default="")

    # AuditMixin provides: created_at, updated_at, created_by, updated_by,
    #                      deleted_at, deleted_by, version

    # Relationships
    quotes = relationship("Quote", back_populates="partner")


class PartnerBase(BaseModel):
    partner_number: str = Field(..., min_length=8, max_length=8, description="Číslo partnera (unikátní, 8-digit)")
    company_name: str = Field(..., min_length=1, max_length=200, description="Název firmy")
    ico: Optional[str] = Field(None, max_length=20, description="IČO (Czech business ID)")
    dic: Optional[str] = Field(None, max_length=20, description="DIČ (Czech VAT ID)")
    email: Optional[str] = Field(None, max_length=100, description="Email")
    phone: Optional[str] = Field(None, max_length=50, description="Telefon")
    contact_person: Optional[str] = Field(None, max_length=100, description="Kontaktní osoba")
    street: Optional[str] = Field(None, max_length=200, description="Ulice")
    city: Optional[str] = Field(None, max_length=100, description="Město")
    postal_code: Optional[str] = Field(None, max_length=20, description="PSČ")
    country: str = Field("CZ", min_length=2, max_length=2, description="Kód země (ISO 3166-1 alpha-2)")
    is_customer: bool = Field(True, description="Je zákazník?")
    is_supplier: bool = Field(False, description="Je dodavatel?")
    notes: Optional[str] = Field(None, max_length=500, description="Poznámky")

    @classmethod
    def validate_ico(cls, v: Optional[str]) -> Optional[str]:
        """Validate Czech IČO (business ID) - basic format check"""
        if v is None or v == "":
            return v
        # Strip whitespace
        v = v.strip()
        # Basic check: 8 digits
        if not v.isdigit() or len(v) != 8:
            raise ValueError("IČO musí obsahovat 8 číslic")
        return v

    @classmethod
    def validate_dic(cls, v: Optional[str]) -> Optional[str]:
        """Validate Czech DIČ (VAT ID) - basic format check"""
        if v is None or v == "":
            return v
        # Strip whitespace
        v = v.strip().upper()
        # Czech format: CZxxxxxxxx (CZ + 8-10 digits)
        if not v.startswith("CZ"):
            raise ValueError("DIČ musí začínat 'CZ'")
        digits = v[2:]
        if not digits.isdigit() or len(digits) < 8 or len(digits) > 10:
            raise ValueError("DIČ musí být ve formátu CZ + 8-10 číslic")
        return v

    @classmethod
    def validate_country(cls, v: str) -> str:
        """Validate country code (ISO 3166-1 alpha-2)"""
        if not v or len(v) != 2:
            raise ValueError("Kód země musí mít 2 znaky (ISO 3166-1 alpha-2)")
        return v.upper()


class PartnerCreate(BaseModel):
    """Create new partner - partner_number is auto-generated if not provided"""
    partner_number: Optional[str] = Field(None, min_length=8, max_length=8, description="Číslo partnera (auto-generated)")
    company_name: str = Field(..., min_length=1, max_length=200, description="Název firmy")
    ico: Optional[str] = Field(None, max_length=20, description="IČO")
    dic: Optional[str] = Field(None, max_length=20, description="DIČ")
    email: Optional[str] = Field(None, max_length=100, description="Email")
    phone: Optional[str] = Field(None, max_length=50, description="Telefon")
    contact_person: Optional[str] = Field(None, max_length=100, description="Kontaktní osoba")
    street: Optional[str] = Field(None, max_length=200, description="Ulice")
    city: Optional[str] = Field(None, max_length=100, description="Město")
    postal_code: Optional[str] = Field(None, max_length=20, description="PSČ")
    country: str = Field("CZ", min_length=2, max_length=2, description="Kód země")
    is_customer: bool = Field(True, description="Je zákazník?")
    is_supplier: bool = Field(False, description="Je dodavatel?")
    notes: str = Field("", max_length=500, description="Poznámky")

    # Reuse validators from PartnerBase
    _validate_ico = field_validator('ico')(PartnerBase.validate_ico.__func__)
    _validate_dic = field_validator('dic')(PartnerBase.validate_dic.__func__)
    _validate_country = field_validator('country')(PartnerBase.validate_country.__func__)


class PartnerUpdate(BaseModel):
    partner_number: Optional[str] = Field(None, min_length=8, max_length=8)
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    ico: Optional[str] = Field(None, max_length=20)
    dic: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    contact_person: Optional[str] = Field(None, max_length=100)
    street: Optional[str] = Field(None, max_length=200)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, min_length=2, max_length=2)
    is_customer: Optional[bool] = None
    is_supplier: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=500)
    version: int  # Optimistic locking (ADR-008)

    # Reuse validators from PartnerBase
    _validate_ico = field_validator('ico')(PartnerBase.validate_ico.__func__)
    _validate_dic = field_validator('dic')(PartnerBase.validate_dic.__func__)
    _validate_country = field_validator('country')(PartnerBase.validate_country.__func__)


class PartnerResponse(PartnerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime
