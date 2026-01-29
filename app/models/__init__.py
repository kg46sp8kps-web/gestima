"""GESTIMA - Modely"""

from app.models.enums import StockType, StockShape, CuttingMode, FeatureType, UserRole, WorkCenterType
from app.models.user import User, UserCreate, UserUpdate, UserResponse, LoginRequest, TokenResponse
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
    MaterialPriceTier
)
from app.models.material_norm import (
    MaterialNorm,
    MaterialNormCreate,
    MaterialNormUpdate,
    MaterialNormResponse,
    MaterialNormWithGroupResponse
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

__all__ = [
    "StockType", "StockShape", "CuttingMode", "FeatureType", "UserRole", "WorkCenterType",
    "User", "UserCreate", "UserUpdate", "UserResponse", "LoginRequest", "TokenResponse",
    "Part", "PartCreate", "PartUpdate", "PartResponse",
    "Operation", "OperationCreate", "OperationUpdate", "OperationResponse",
    "Feature", "FeatureCreate", "FeatureUpdate", "FeatureResponse",
    "Batch", "BatchCreate", "BatchResponse",
    "BatchSet", "BatchSetCreate", "BatchSetUpdate", "BatchSetResponse",
    "BatchSetWithBatchesResponse", "BatchSetListResponse", "generate_batch_set_name",
    "MaterialGroup", "MaterialGroupCreate", "MaterialGroupUpdate", "MaterialGroupResponse",
    "MaterialItem", "MaterialItemCreate", "MaterialItemUpdate", "MaterialItemResponse", "MaterialItemWithGroupResponse",
    "MaterialInput", "MaterialInputCreate", "MaterialInputUpdate", "MaterialInputResponse",
    "MaterialPriceCategory", "MaterialPriceTier",
    "MaterialNorm", "MaterialNormCreate", "MaterialNormUpdate", "MaterialNormResponse", "MaterialNormWithGroupResponse",
    "CuttingConditionDB", "CuttingConditionCreate", "CuttingConditionResponse",
    "SystemConfig", "SystemConfigCreate", "SystemConfigUpdate", "SystemConfigResponse",
    "WorkCenter", "WorkCenterCreate", "WorkCenterUpdate", "WorkCenterResponse",
]
