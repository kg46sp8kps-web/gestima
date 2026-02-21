"""GESTIMA - Feature CRUD service

Thin service layer for features (cutting steps within operations).
Domain-specific: locked field validation on update.
"""

from fastapi import HTTPException

from app.models.feature import Feature, FeatureCreate, FeatureUpdate
from app.services.base_service import BaseCrudService


class FeatureService(BaseCrudService[Feature, FeatureCreate, FeatureUpdate]):
    model = Feature
    entity_name = "krok"
    default_order = (Feature.seq,)
    parent_field = "operation_id"

    def _validate_update(self, record: Feature, update_data: dict) -> None:
        """Block changes to locked cutting parameters."""
        if record.Vc_locked and "Vc" in update_data:
            raise HTTPException(
                status_code=400,
                detail="Řezná rychlost (Vc) je uzamčena a nelze ji změnit",
            )
        if record.f_locked and "f" in update_data:
            raise HTTPException(
                status_code=400,
                detail="Posuv (f) je uzamčen a nelze jej změnit",
            )
        if record.Ap_locked and "Ap" in update_data:
            raise HTTPException(
                status_code=400,
                detail="Hloubka řezu (Ap) je uzamčena a nelze ji změnit",
            )
