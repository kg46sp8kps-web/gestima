"""GESTIMA - API routers"""

from app.routers import (
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
    data_router,
    pages_router,
    misc_router,
    work_centers_router,
    config_router,
    admin_router,
    quotes_router,
    quote_items_router,
    uploads_router,
    module_layouts_router,  # ADR-031: Visual Editor
    module_defaults_router  # ADR-031: Module Defaults
)
