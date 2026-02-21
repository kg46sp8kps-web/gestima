"""GESTIMA - Modely"""

from app.models.enums import StockType, StockShape, CuttingMode, FeatureType, UserRole, WorkCenterType, QuoteStatus
from app.models.user import User, UserCreate, UserUpdate, UserResponse, LoginRequest, TokenResponse, PasswordChange
from app.models.part import Part, PartCreate, PartUpdate, PartResponse
from app.models.operation import Operation, OperationCreate, OperationUpdate, OperationResponse
from app.models.feature import Feature, FeatureCreate, FeatureUpdate, FeatureResponse
from app.models.batch import Batch, BatchCreate, BatchResponse
from app.models.batch_set import (
    BatchSet,
    BatchSetCreate,
    BatchSetUpdate,
    BatchSetResponse,
    BatchSetWithBatchesResponse,
    BatchSetListResponse,
    generate_batch_set_name
)
# Machine model removed - replaced by WorkCenter (ADR-021)
from app.models.material import (
    MaterialGroup,
    MaterialGroupCreate,
    MaterialGroupUpdate,
    MaterialGroupResponse,
    MaterialItem,
    MaterialItemCreate,
    MaterialItemUpdate,
    MaterialItemResponse,
    MaterialItemWithGroupResponse,
    MaterialPriceCategory,
    MaterialPriceCategoryCreate,
    MaterialPriceCategoryUpdate,
    MaterialPriceCategoryResponse,
    MaterialPriceTier
)
from app.models.material_norm import (
    MaterialNorm,
    MaterialNormCreate,
    MaterialNormUpdate,
    MaterialNormResponse
)
from app.models.material_input import (
    MaterialInput,
    MaterialInputCreate,
    MaterialInputUpdate,
    MaterialInputResponse
)
from app.models.cutting_condition import CuttingConditionDB, CuttingConditionCreate, CuttingConditionResponse
from app.models.config import SystemConfig, SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse
from app.models.work_center import (
    WorkCenter,
    WorkCenterCreate,
    WorkCenterUpdate,
    WorkCenterResponse
)
from app.models.partner import (
    Partner,
    PartnerCreate,
    PartnerUpdate,
    PartnerResponse
)
from app.models.quote import (
    Quote,
    QuoteItem,
    QuoteCreate,
    QuoteUpdate,
    QuoteResponse,
    QuoteWithItemsResponse,
    QuoteListResponse,
    QuoteItemCreate,
    QuoteItemUpdate,
    QuoteItemResponse
)
from app.models.module_layout import (
    ModuleLayout,
    ModuleLayoutCreate,
    ModuleLayoutUpdate,
    ModuleLayoutResponse
)
from app.models.module_defaults import (
    ModuleDefaults,
    ModuleDefaultsCreate,
    ModuleDefaultsUpdate,
    ModuleDefaultsResponse
)
from app.models.file_record import FileRecord, FileLink
from app.models.production_record import (
    ProductionRecord,
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordResponse,
)
from app.models.time_vision import (
    TimeVisionEstimation,
    TimeVisionResponse,
    TimeVisionListItem,
    TimeVisionActualTimeUpdate,
    VisionExtractionResult,
    TimeEstimationResult,
    OperationBreakdown,
    SimilarPartMatch,
)
from app.models.sync_state import (
    SyncState,
    SyncLog,
    SyncStateRead,
    SyncStateUpdate,
    SyncLogRead,
    SyncStatusResponse,
    SyncTriggerResponse,
)

__all__ = [
    "StockType", "StockShape", "CuttingMode", "FeatureType", "UserRole", "WorkCenterType", "QuoteStatus",
    "User", "UserCreate", "UserUpdate", "UserResponse", "LoginRequest", "TokenResponse", "PasswordChange",
    "Part", "PartCreate", "PartUpdate", "PartResponse",
    "Operation", "OperationCreate", "OperationUpdate", "OperationResponse",
    "Feature", "FeatureCreate", "FeatureUpdate", "FeatureResponse",
    "Batch", "BatchCreate", "BatchResponse",
    "BatchSet", "BatchSetCreate", "BatchSetUpdate", "BatchSetResponse",
    "BatchSetWithBatchesResponse", "BatchSetListResponse", "generate_batch_set_name",
    "MaterialGroup", "MaterialGroupCreate", "MaterialGroupUpdate", "MaterialGroupResponse",
    "MaterialItem", "MaterialItemCreate", "MaterialItemUpdate", "MaterialItemResponse", "MaterialItemWithGroupResponse",
    "MaterialInput", "MaterialInputCreate", "MaterialInputUpdate", "MaterialInputResponse",
    "MaterialPriceCategory", "MaterialPriceCategoryCreate", "MaterialPriceCategoryUpdate", "MaterialPriceCategoryResponse", "MaterialPriceTier",
    "MaterialNorm", "MaterialNormCreate", "MaterialNormUpdate", "MaterialNormResponse", "MaterialNormWithGroupResponse",
    "CuttingConditionDB", "CuttingConditionCreate", "CuttingConditionResponse",
    "SystemConfig", "SystemConfigCreate", "SystemConfigUpdate", "SystemConfigResponse",
    "WorkCenter", "WorkCenterCreate", "WorkCenterUpdate", "WorkCenterResponse",
    "Partner", "PartnerCreate", "PartnerUpdate", "PartnerResponse",
    "Quote", "QuoteItem", "QuoteCreate", "QuoteUpdate", "QuoteResponse",
    "QuoteWithItemsResponse", "QuoteListResponse",
    "QuoteItemCreate", "QuoteItemUpdate", "QuoteItemResponse",
    "ModuleLayout", "ModuleLayoutCreate", "ModuleLayoutUpdate", "ModuleLayoutResponse",
    "ModuleDefaults", "ModuleDefaultsCreate", "ModuleDefaultsUpdate", "ModuleDefaultsResponse",
    "FileRecord", "FileLink",
    "TimeVisionEstimation", "TimeVisionResponse", "TimeVisionListItem", "TimeVisionActualTimeUpdate",
    "VisionExtractionResult", "TimeEstimationResult", "OperationBreakdown", "SimilarPartMatch",
    "ProductionRecord", "ProductionRecordCreate", "ProductionRecordUpdate", "ProductionRecordResponse",
    "SyncState", "SyncLog", "SyncStateRead", "SyncStateUpdate", "SyncLogRead",
    "SyncStatusResponse", "SyncTriggerResponse",
]
