"""GESTIMA - API routers"""

from . import (
    auth_router,
    parts_router,
    drawings_router,  # Multiple drawings per part support
    operations_router,
    features_router,
    batches_router,
    pricing_router,
    materials_router,
    material_inputs_router,  # ADR-024
    partners_router,
    work_centers_router,
    config_router,
    admin_router,
    quotes_router,
    quote_items_router,
    uploads_router,
    module_layouts_router,  # ADR-031: Visual Editor
    module_defaults_router,  # ADR-031: Module Defaults
    infor_router,  # Infor CloudSuite Industrial integration
    infor_import_router,  # Infor Jobs import (Parts, Operations, ProductionRecords)
    cutting_conditions_router,  # Cutting conditions catalog (v1.28.0)
    accounting_router,  # CsiXls accounting integration
    time_vision_router,  # TimeVision AI estimation
    technology_builder_router,  # Technology Builder (Phase 1)
    files_router,  # Centralized File Manager (ADR-044)
    production_records_router,  # Production records (Infor actual times)
    drawing_import_router,  # Drawing import from network share (ADR-044)
    ft_debug_router,  # FT Debug — fine-tuning data inspection
    infor_sync_router,  # Infor Smart Polling Sync
)
