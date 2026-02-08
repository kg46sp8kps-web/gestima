"""GESTIMA - Material models (ADR-011: Two-Tier Hierarchy, ADR-014: Price Tiers)"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.database import Base, AuditMixin
from app.models.enums import StockShape


class MaterialGroup(Base, AuditMixin):
    """
    Kategorie materiálu pro výpočty (hustota, řezné podmínky).
    Příklad: "Ocel automatová", "Hliník 6060", "Mosaz".

    Migration t3u4v5w6x7y8: Přidány řezné parametry pro machining time estimation.
    """
    __tablename__ = "material_groups"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)    # "11xxx", "S235"
    name = Column(String(100), nullable=False)                            # "Ocel automatová"
    density = Column(Float, nullable=False)                               # kg/dm³ (pro výpočet váhy)

    # Cutting parameters (Migration t3u4v5w6x7y8) - nullable for backward compatibility
    iso_group = Column(String(5), index=True, nullable=True)              # P, M, K, N, S, H
    hardness_hb = Column(Float, nullable=True)                            # Brinell hardness

    # Material Removal Rates (cm³/min)
    mrr_turning_roughing = Column(Float, nullable=True)
    mrr_turning_finishing = Column(Float, nullable=True)
    mrr_milling_roughing = Column(Float, nullable=True)
    mrr_milling_finishing = Column(Float, nullable=True)

    # Cutting speeds (m/min)
    cutting_speed_turning = Column(Float, nullable=True)
    cutting_speed_milling = Column(Float, nullable=True)

    # Feed rates
    feed_turning = Column(Float, nullable=True)                           # mm/rev
    feed_milling = Column(Float, nullable=True)                           # mm/tooth

    # Constraint penalties
    deep_pocket_penalty = Column(Float, nullable=True, default=1.8)
    thin_wall_penalty = Column(Float, nullable=True, default=2.5)

    # Metadata
    cutting_data_source = Column(String(100), nullable=True)              # "Sandvik Coromant 2024"

    # Relationships
    items = relationship("MaterialItem", back_populates="group", cascade="all, delete-orphan")
    norms = relationship("MaterialNorm", back_populates="material_group", cascade="all, delete-orphan")
    # cutting_conditions = relationship("CuttingCondition", back_populates="material_group")  # Future


class MaterialPriceCategory(Base, AuditMixin):
    """
    Cenová kategorie pro skupiny polotovarů (ADR-014 + Migration 2026-01-26).
    Příklad: "OCEL konstrukční - kruhová tyč" → všechny průměry sdílí tyto price tiers.

    Migration 2026-01-26: Přidán material_group_id FK pro propojení s MaterialGroup.
    Migration 2026-02-03: Code změněn na 8-digit formát (20900000-20909999) dle ADR-017.
    Migration 2026-02-08: Přidány řezné parametry pro machining time estimation.
    """
    __tablename__ = "material_price_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(8), unique=True, nullable=False, index=True)     # "20900000" (8-digit: 20900000-20909999)
    name = Column(String(200), nullable=False)                            # "Hliník - tyč kruhová"

    # FK → MaterialGroup (Migration 2026-01-26: pro auto-assign hustoty)
    material_group_id = Column(Integer, ForeignKey("material_groups.id"), nullable=True, index=True)

    # Cutting parameters (Migration 2026-02-08) - nullable for old records
    iso_group = Column(String(5), index=True, nullable=True)              # P, M, K, N, S, H
    hardness_hb = Column(Float, nullable=True)                            # Brinell hardness
    density = Column(Float, nullable=True)                                # kg/dm³

    # Material Removal Rates (cm³/min)
    mrr_turning_roughing = Column(Float, nullable=True)
    mrr_turning_finishing = Column(Float, nullable=True)
    mrr_milling_roughing = Column(Float, nullable=True)
    mrr_milling_finishing = Column(Float, nullable=True)

    # Cutting speeds (m/min)
    cutting_speed_turning = Column(Float, nullable=True)
    cutting_speed_milling = Column(Float, nullable=True)

    # Feed rates
    feed_turning = Column(Float, nullable=True)                           # mm/rev
    feed_milling = Column(Float, nullable=True)                           # mm/tooth

    # Constraint penalties
    deep_pocket_penalty = Column(Float, nullable=True, default=1.8)
    thin_wall_penalty = Column(Float, nullable=True, default=2.5)

    # Metadata
    cutting_data_source = Column(String(100), nullable=True)              # "Sandvik Coromant 2024"
    cutting_data_notes = Column(String, nullable=True)                    # Additional notes

    # Relationships
    material_group = relationship("MaterialGroup", foreign_keys=[material_group_id])
    items = relationship("MaterialItem", back_populates="price_category")
    tiers = relationship("MaterialPriceTier", back_populates="category", cascade="all, delete-orphan")


class MaterialPriceTier(Base, AuditMixin):
    """
    Cenový tier pro kategorii (konfigurovatelné hranice) (ADR-014).
    Příklad: 0-15 kg → 49.4 Kč/kg
    """
    __tablename__ = "material_price_tiers"

    id = Column(Integer, primary_key=True, index=True)
    price_category_id = Column(Integer, ForeignKey("material_price_categories.id", ondelete="CASCADE"), nullable=False)

    # Hranice (kg)
    min_weight = Column(Float, nullable=False)                            # 0, 15, 100
    max_weight = Column(Float, nullable=True)                             # 15, 100, NULL (= infinite)

    # Cena
    price_per_kg = Column(Float, nullable=False)                          # 49.4, 34.5, 26.3

    # Relationship
    category = relationship("MaterialPriceCategory", back_populates="tiers")


class MaterialItem(Base, AuditMixin):
    """
    Konkrétní polotovar (skladová položka).
    Příklad: "1.0715 D20 - tyč kruhová ocel".

    Migration 2026-01-27: Přidány katalogové sloupce (weight_per_meter, standard_length, norms, supplier_code).
    """
    __tablename__ = "material_items"

    id = Column(Integer, primary_key=True, index=True)
    material_number = Column(String(8), unique=True, nullable=False, index=True)  # 8-digit random: 20XXXXXX
    code = Column(String(50), unique=True, nullable=False, index=True)    # "1.0715-D20"
    name = Column(String(200), nullable=False)                            # "1.0715 D20 - tyč kruhová ocel"

    # Geometrie polotovaru
    shape = Column(Enum(StockShape), nullable=False)                      # ROUND_BAR, SQUARE_BAR, ...
    diameter = Column(Float, nullable=True)                               # mm (pro round_bar, hexagonal_bar)
    width = Column(Float, nullable=True)                                  # mm (pro square_bar, flat_bar, plate)
    thickness = Column(Float, nullable=True)                              # mm (pro plate, flat_bar)
    wall_thickness = Column(Float, nullable=True)                         # mm (pro tube - tloušťka stěny)

    # Katalogové informace (Migration 2026-01-27)
    weight_per_meter = Column(Float, nullable=True)                       # kg/m (z katalogu dodavatele)
    standard_length = Column(Float, nullable=True)                        # mm (typicky 6000mm)
    norms = Column(String(200), nullable=True)                            # "EN 10025, EN 10060"
    supplier_code = Column(String(50), nullable=True)                     # "T125110001" (TheSteel kód)

    # Povrchová úprava (Migration 2026-02-03: ADR-033)
    surface_treatment = Column(String(20), nullable=True)                 # "T", "V", "P", "O", "F", etc. (z Infor Item suffix)

    # Ekonomika (LIVE data)
    supplier = Column(String(100), nullable=True)                         # Dodavatel
    stock_available = Column(Float, nullable=True, default=0.0)           # kg (dostupné skladem)

    # Vazby
    material_group_id = Column(Integer, ForeignKey("material_groups.id", ondelete="RESTRICT"), nullable=False)
    price_category_id = Column(Integer, ForeignKey("material_price_categories.id", ondelete="RESTRICT"), nullable=False)  # ADR-014

    group = relationship("MaterialGroup", back_populates="items")
    price_category = relationship("MaterialPriceCategory", back_populates="items")


# ========== PYDANTIC SCHEMAS ==========

# ----- MaterialGroup -----

class MaterialGroupBase(BaseModel):
    code: str = Field(..., max_length=20, description="Kód skupiny (např. 11xxx, S235)")
    name: str = Field(..., max_length=100, description="Název skupiny")
    density: float = Field(..., gt=0, description="Hustota v kg/dm³")

    # Cutting parameters (optional)
    iso_group: Optional[str] = Field(None, max_length=5, description="ISO material group: P, M, K, N, S, H")
    hardness_hb: Optional[float] = Field(None, gt=0, description="Hardness (Brinell)")
    mrr_turning_roughing: Optional[float] = Field(None, gt=0, description="Material removal rate - turning roughing (cm³/min)")
    mrr_turning_finishing: Optional[float] = Field(None, gt=0, description="Material removal rate - turning finishing (cm³/min)")
    mrr_milling_roughing: Optional[float] = Field(None, gt=0, description="Material removal rate - milling roughing (cm³/min)")
    mrr_milling_finishing: Optional[float] = Field(None, gt=0, description="Material removal rate - milling finishing (cm³/min)")
    cutting_speed_turning: Optional[float] = Field(None, gt=0, description="Cutting speed - turning (m/min)")
    cutting_speed_milling: Optional[float] = Field(None, gt=0, description="Cutting speed - milling (m/min)")
    feed_turning: Optional[float] = Field(None, gt=0, description="Feed rate - turning (mm/rev)")
    feed_milling: Optional[float] = Field(None, gt=0, description="Feed rate - milling (mm/tooth)")
    deep_pocket_penalty: Optional[float] = Field(None, ge=1.0, description="Time penalty multiplier for deep pockets")
    thin_wall_penalty: Optional[float] = Field(None, ge=1.0, description="Time penalty multiplier for thin walls")
    cutting_data_source: Optional[str] = Field(None, max_length=100, description="Source of cutting data (e.g., 'Sandvik 2024')")


class MaterialGroupCreate(MaterialGroupBase):
    pass


class MaterialGroupUpdate(BaseModel):
    code: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    density: Optional[float] = Field(None, gt=0)

    # Cutting parameters (optional)
    iso_group: Optional[str] = Field(None, max_length=5)
    hardness_hb: Optional[float] = Field(None, gt=0)
    mrr_turning_roughing: Optional[float] = Field(None, gt=0)
    mrr_turning_finishing: Optional[float] = Field(None, gt=0)
    mrr_milling_roughing: Optional[float] = Field(None, gt=0)
    mrr_milling_finishing: Optional[float] = Field(None, gt=0)
    cutting_speed_turning: Optional[float] = Field(None, gt=0)
    cutting_speed_milling: Optional[float] = Field(None, gt=0)
    feed_turning: Optional[float] = Field(None, gt=0)
    feed_milling: Optional[float] = Field(None, gt=0)
    deep_pocket_penalty: Optional[float] = Field(None, ge=1.0)
    thin_wall_penalty: Optional[float] = Field(None, ge=1.0)
    cutting_data_source: Optional[str] = Field(None, max_length=100)

    version: int  # Optimistic locking


class MaterialGroupResponse(MaterialGroupBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


# ----- MaterialPriceCategory -----

class MaterialPriceCategoryBase(BaseModel):
    code: str = Field(..., min_length=8, max_length=8, description="Kód kategorie (8-digit: 20900000-20909999)")
    name: str = Field(..., max_length=200, description="Název kategorie")
    material_group_id: Optional[int] = Field(None, gt=0, description="ID materiálové skupiny")

    # Cutting parameters (optional)
    iso_group: Optional[str] = Field(None, max_length=5, description="ISO material group: P, M, K, N, S, H")
    hardness_hb: Optional[float] = Field(None, gt=0, description="Hardness (Brinell)")
    density: Optional[float] = Field(None, gt=0, description="Density (kg/dm³)")
    mrr_turning_roughing: Optional[float] = Field(None, gt=0, description="Material removal rate - turning roughing (cm³/min)")
    mrr_turning_finishing: Optional[float] = Field(None, gt=0, description="Material removal rate - turning finishing (cm³/min)")
    mrr_milling_roughing: Optional[float] = Field(None, gt=0, description="Material removal rate - milling roughing (cm³/min)")
    mrr_milling_finishing: Optional[float] = Field(None, gt=0, description="Material removal rate - milling finishing (cm³/min)")
    cutting_speed_turning: Optional[float] = Field(None, gt=0, description="Cutting speed - turning (m/min)")
    cutting_speed_milling: Optional[float] = Field(None, gt=0, description="Cutting speed - milling (m/min)")
    feed_turning: Optional[float] = Field(None, gt=0, description="Feed rate - turning (mm/rev)")
    feed_milling: Optional[float] = Field(None, gt=0, description="Feed rate - milling (mm/tooth)")
    deep_pocket_penalty: Optional[float] = Field(None, ge=1.0, description="Time penalty multiplier for deep pockets")
    thin_wall_penalty: Optional[float] = Field(None, ge=1.0, description="Time penalty multiplier for thin walls")
    cutting_data_source: Optional[str] = Field(None, max_length=100, description="Source of cutting data (e.g., 'Sandvik 2024')")
    cutting_data_notes: Optional[str] = Field(None, description="Additional notes about cutting parameters")


class MaterialPriceCategoryCreate(MaterialPriceCategoryBase):
    pass


class MaterialPriceCategoryUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=8, max_length=8)
    name: Optional[str] = Field(None, max_length=200)
    material_group_id: Optional[int] = Field(None, gt=0)

    # Cutting parameters (optional)
    iso_group: Optional[str] = Field(None, max_length=5)
    hardness_hb: Optional[float] = Field(None, gt=0)
    density: Optional[float] = Field(None, gt=0)
    mrr_turning_roughing: Optional[float] = Field(None, gt=0)
    mrr_turning_finishing: Optional[float] = Field(None, gt=0)
    mrr_milling_roughing: Optional[float] = Field(None, gt=0)
    mrr_milling_finishing: Optional[float] = Field(None, gt=0)
    cutting_speed_turning: Optional[float] = Field(None, gt=0)
    cutting_speed_milling: Optional[float] = Field(None, gt=0)
    feed_turning: Optional[float] = Field(None, gt=0)
    feed_milling: Optional[float] = Field(None, gt=0)
    deep_pocket_penalty: Optional[float] = Field(None, ge=1.0)
    thin_wall_penalty: Optional[float] = Field(None, ge=1.0)
    cutting_data_source: Optional[str] = Field(None, max_length=100)
    cutting_data_notes: Optional[str] = None

    version: int  # Optimistic locking


class MaterialPriceCategoryResponse(MaterialPriceCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_group_id: Optional[int] = None
    version: int
    created_at: datetime
    updated_at: datetime


class MaterialPriceCategoryWithGroupResponse(MaterialPriceCategoryResponse):
    """MaterialPriceCategory s eager-loaded MaterialGroup (pro dropdown)"""
    material_group: Optional[MaterialGroupResponse] = None


# ----- MaterialPriceTier -----

class MaterialPriceTierBase(BaseModel):
    price_category_id: int = Field(..., gt=0, description="ID cenové kategorie")
    min_weight: float = Field(..., ge=0, description="Minimální váha v kg")
    max_weight: Optional[float] = Field(None, ge=0, description="Maximální váha v kg (NULL = nekonečno)")
    price_per_kg: float = Field(..., gt=0, description="Cena za kg v Kč")


class MaterialPriceTierCreate(MaterialPriceTierBase):
    pass


class MaterialPriceTierUpdate(BaseModel):
    price_category_id: Optional[int] = Field(None, gt=0)
    min_weight: Optional[float] = Field(None, ge=0)
    max_weight: Optional[float] = Field(None, ge=0)
    price_per_kg: Optional[float] = Field(None, gt=0)
    version: int  # Optimistic locking


class MaterialPriceTierResponse(MaterialPriceTierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class MaterialPriceCategoryWithTiersResponse(MaterialPriceCategoryResponse):
    """MaterialPriceCategory s eager-loaded tiers"""
    tiers: List[MaterialPriceTierResponse] = []


# ----- MaterialItem -----

class MaterialItemBase(BaseModel):
    material_number: str = Field(..., min_length=8, max_length=8, description="Číslo materiálu (8-digit)")
    code: str = Field(..., max_length=50, description="Kód položky (např. 1.0715-D20)")
    name: str = Field(..., max_length=200, description="Název položky")
    shape: StockShape = Field(..., description="Tvar polotovaru")
    diameter: Optional[float] = Field(None, ge=0, description="Průměr v mm (pro round_bar)")
    width: Optional[float] = Field(None, ge=0, description="Šířka v mm (pro square/flat/plate)")
    thickness: Optional[float] = Field(None, ge=0, description="Tloušťka v mm (pro plate)")
    wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm (pro tube)")
    weight_per_meter: Optional[float] = Field(None, gt=0, description="Hmotnost na metr v kg/m (z katalogu)")
    standard_length: Optional[float] = Field(None, gt=0, description="Standardní dodací délka v mm (typicky 6000)")
    norms: Optional[str] = Field(None, max_length=200, description="Normy (např. EN 10025, EN 10060)")
    supplier_code: Optional[str] = Field(None, max_length=50, description="Kód dodavatele (např. T125110001)")
    surface_treatment: Optional[str] = Field(None, max_length=20, description="Povrchová úprava (T=tažená, V=válená, P=lisovaná, O=loupaná, F=frézovaná)")
    supplier: Optional[str] = Field(None, max_length=100, description="Dodavatel")
    stock_available: Optional[float] = Field(0.0, ge=0, description="Dostupné skladem (kg)")
    material_group_id: int = Field(..., gt=0, description="ID nadřazené skupiny")
    price_category_id: int = Field(..., gt=0, description="ID cenové kategorie (ADR-014)")


class MaterialItemCreate(BaseModel):
    """Create new material item - material_number is auto-generated if not provided"""
    material_number: Optional[str] = Field(None, min_length=8, max_length=8, description="Číslo materiálu (auto-generated)")
    code: str = Field(..., max_length=50, description="Kód položky (např. 1.0715-D20)")
    name: str = Field(..., max_length=200, description="Název položky")
    shape: StockShape = Field(..., description="Tvar polotovaru")
    diameter: Optional[float] = Field(None, ge=0, description="Průměr v mm (pro round_bar)")
    width: Optional[float] = Field(None, ge=0, description="Šířka v mm (pro square/flat/plate)")
    thickness: Optional[float] = Field(None, ge=0, description="Tloušťka v mm (pro plate)")
    wall_thickness: Optional[float] = Field(None, ge=0, description="Tloušťka stěny v mm (pro tube)")
    weight_per_meter: Optional[float] = Field(None, gt=0, description="Hmotnost na metr v kg/m (z katalogu)")
    standard_length: Optional[float] = Field(None, gt=0, description="Standardní dodací délka v mm (typicky 6000)")
    norms: Optional[str] = Field(None, max_length=200, description="Normy (např. EN 10025, EN 10060)")
    supplier_code: Optional[str] = Field(None, max_length=50, description="Kód dodavatele (např. T125110001)")
    surface_treatment: Optional[str] = Field(None, max_length=20, description="Povrchová úprava (T=tažená, V=válená, P=lisovaná, O=loupaná, F=frézovaná)")
    supplier: Optional[str] = Field(None, max_length=100, description="Dodavatel")
    stock_available: Optional[float] = Field(0.0, ge=0, description="Dostupné skladem (kg)")
    material_group_id: int = Field(..., gt=0, description="ID nadřazené skupiny")
    price_category_id: int = Field(..., gt=0, description="ID cenové kategorie (ADR-014)")


class MaterialItemUpdate(BaseModel):
    material_number: Optional[str] = Field(None, min_length=8, max_length=8)
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    shape: Optional[StockShape] = None
    diameter: Optional[float] = Field(None, ge=0)
    width: Optional[float] = Field(None, ge=0)
    thickness: Optional[float] = Field(None, ge=0)
    wall_thickness: Optional[float] = Field(None, ge=0)
    weight_per_meter: Optional[float] = Field(None, gt=0)
    standard_length: Optional[float] = Field(None, gt=0)
    norms: Optional[str] = Field(None, max_length=200)
    supplier_code: Optional[str] = Field(None, max_length=50)
    surface_treatment: Optional[str] = Field(None, max_length=20)
    supplier: Optional[str] = Field(None, max_length=100)
    stock_available: Optional[float] = Field(None, ge=0)
    material_group_id: Optional[int] = Field(None, gt=0)
    price_category_id: Optional[int] = Field(None, gt=0)
    version: int  # Optimistic locking


class MaterialItemResponse(MaterialItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: int
    created_at: datetime
    updated_at: datetime


class MaterialItemWithGroupResponse(MaterialItemResponse):
    """MaterialItem s eager-loaded group a price_category informací"""
    group: MaterialGroupResponse
    price_category: MaterialPriceCategoryResponse
