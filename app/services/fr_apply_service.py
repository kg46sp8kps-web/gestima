"""GESTIMA - Feature Recognition Apply Service

Converts FR analysis results into Part Operations + Features.

Transaction handling: L-008 compliant (try/except/rollback on all DB operations)
Validation: L-009 compliant (uses validated Pydantic schemas)
"""

import logging
from typing import Optional
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db_helpers import set_audit, safe_commit
from app.models.feature import Feature
from app.models.operation import Operation
from app.models.feature_recognition import FeatureRecognition
from app.models.enums import FeatureType
from app.schemas.feature_recognition import FeatureRecognitionResponse, OperationSuggestion
from app.services.feature_definitions import FEATURE_FIELDS
from app.services.ai_feature_mapper import validate_feature_type

logger = logging.getLogger(__name__)

# Category → Operation config
CATEGORY_OPERATION_MAP = {
    "turning": {"name": "Soustružení", "type": "turning", "icon": "settings", "setup_time": 30.0},
    "milling": {"name": "Frézování", "type": "milling", "icon": "settings", "setup_time": 25.0},
    "grinding": {"name": "Broušení", "type": "grinding", "icon": "settings", "setup_time": 20.0},
    "finishing": {"name": "Odjehlení", "type": "generic", "icon": "hand", "setup_time": 5.0},
    "logistics_inspect": {"name": "Kontrola", "type": "generic", "icon": "check", "setup_time": 10.0},
    "coop": {"name": "Kooperace", "type": "generic", "icon": "truck", "setup_time": 0.0, "is_coop": True},
}


class FRApplyService:
    """Converts FeatureRecognitionResponse → Operations + Features on a Part."""

    async def apply_to_part(
        self,
        db: AsyncSession,
        part_id: int,
        fr_response: FeatureRecognitionResponse,
        cutting_mode: str = "mid",
        delete_existing: bool = False,
        username: str = "system",
        feature_recognition_id: Optional[int] = None,
    ) -> list[Operation]:
        """
        Main entry point: Apply FR analysis results to a Part.

        Transaction handling (L-008):
        - All DB operations in try/except with rollback
        - Uses safe_commit() helper

        Args:
            db: Database session
            part_id: Target part ID
            fr_response: Feature recognition analysis result
            cutting_mode: Cutting mode (low/mid/high)
            delete_existing: Delete existing operations before applying
            username: User performing the action (for audit trail)
            feature_recognition_id: Optional FR record ID to link

        Returns:
            List of created Operation objects

        Raises:
            HTTPException: If database operation fails
        """
        try:
            # 1. Optionally delete existing operations
            if delete_existing:
                existing = await db.execute(
                    select(Operation).where(
                        Operation.part_id == part_id,
                        Operation.deleted_at.is_(None)
                    )
                )
                for op in existing.scalars().all():
                    await db.delete(op)
                await db.flush()

            # 2. NEW v2.1: Use operation_groups if available (structured by setup)
            if fr_response.operation_groups and len(fr_response.operation_groups) > 0:
                logger.info(f"Using structured operation_groups (v2.1): {len(fr_response.operation_groups)} setups")
                created_ops = self._create_from_operation_groups(
                    db, part_id, fr_response.operation_groups,
                    cutting_mode, username, feature_recognition_id
                )
            else:
                # Fallback: Old category-based grouping (backward compat)
                logger.info(f"Using legacy category grouping (v2.0)")
                groups = self._group_features_by_category(fr_response.operations or [])

                if not groups:
                    logger.warning(f"No features to apply for part {part_id}")
                    return []

                # 3. Create operations + features per group
                created_ops = []
                seq = 10
                for category in ["turning", "milling", "grinding", "finishing", "logistics_inspect", "coop"]:
                    if category not in groups:
                        continue
                    op = self._create_operation(
                        db, part_id, category, groups[category], seq,
                        cutting_mode, username, feature_recognition_id
                    )
                    created_ops.append(op)
                    seq += 10

            # PERFORMANCE FIX: Bulk add operations (5s → 0.2s)
            db.add_all(created_ops)

            # 4. Commit (L-008)
            await safe_commit(db, action="FR apply operations")

            # 5. Refresh operations with eager loading (1 query instead of N)
            op_ids = [op.id for op in created_ops]
            result = await db.execute(
                select(Operation)
                .where(Operation.id.in_(op_ids))
                .options(selectinload(Operation.features))
            )
            created_ops = list(result.scalars().all())

            logger.info(
                f"Applied FR to part {part_id}: {len(created_ops)} operations created",
                extra={"part_id": part_id, "user": username}
            )
            return created_ops

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to apply FR to part {part_id}: {e}", exc_info=True)
            raise

    def _group_features_by_category(
        self, operations: list[OperationSuggestion]
    ) -> dict[str, list[OperationSuggestion]]:
        """
        Group AI features by FEATURE_FIELDS category.

        Merging logic:
        - drilling + live_tooling → turning (same machine)
        - deburr_manual → finishing
        - inspect → logistics_inspect
        - wash → skip (not implemented yet)

        Returns:
            Dict[category, list of suggestions]
        """
        groups: dict[str, list[OperationSuggestion]] = {}

        for op in operations:
            # Normalize feature type
            ft_str = op.feature_type or (op.operation_type if hasattr(op, 'operation_type') else None)
            if not ft_str:
                continue
            ft_str = validate_feature_type(ft_str) or ft_str

            feature_def = FEATURE_FIELDS.get(ft_str)
            if not feature_def:
                logger.warning(f"Unknown feature type: {ft_str}, skipping")
                continue

            category = feature_def["category"]

            # Skip wash per requirements
            if ft_str == "wash":
                continue

            # Merge drilling + live_tooling into turning (same machine)
            if category in ("drilling", "live_tooling"):
                category = "turning"

            # Separate deburr_manual
            if ft_str == "deburr_manual":
                category = "finishing"

            # Separate inspect
            if ft_str == "inspect":
                category = "logistics_inspect"

            groups.setdefault(category, []).append(op)

        return groups

    def _create_operation(
        self,
        db: AsyncSession,
        part_id: int,
        category: str,
        features: list[OperationSuggestion],
        seq: int,
        cutting_mode: str,
        username: str,
        feature_recognition_id: Optional[int],
    ) -> Operation:
        """
        Create Operation + child Features from a category group.

        Sets up:
        - Operation with config from CATEGORY_OPERATION_MAP
        - Child Features mapped from OperationSuggestion
        - Audit trail
        - Total operation time from sum of features

        Args:
            db: Database session
            part_id: Target part ID
            category: Category key (turning, milling, etc.)
            features: List of suggestions for this category
            seq: Operation sequence number
            cutting_mode: Cutting mode
            username: User for audit
            feature_recognition_id: Optional FR record ID

        Returns:
            Operation entity (not yet committed)
        """
        config = CATEGORY_OPERATION_MAP.get(category, CATEGORY_OPERATION_MAP["turning"])

        op = Operation(
            part_id=part_id,
            seq=seq,
            name=config["name"],
            type=config["type"],
            icon=config.get("icon", "settings"),
            cutting_mode=cutting_mode,
            setup_time_min=config.get("setup_time", 30.0),
            is_coop=config.get("is_coop", False),
        )

        # Add feature_recognition_id if column exists
        if feature_recognition_id and hasattr(Operation, 'feature_recognition_id'):
            op.feature_recognition_id = feature_recognition_id

        set_audit(op, username)

        # Create child features
        total_time_sec = 0.0
        for i, suggestion in enumerate(features, start=1):
            feature = self._map_suggestion_to_feature(suggestion, seq=i)
            feature.operation = op  # Use relationship, not operation_id (not yet flushed)
            set_audit(feature, username)
            total_time_sec += feature.predicted_time_sec or 0.0

        # Set operation_time_min from sum of features
        op.operation_time_min = round(total_time_sec / 60, 2)

        return op

    def _create_from_operation_groups(
        self,
        db: AsyncSession,
        part_id: int,
        operation_groups: list,
        cutting_mode: str,
        username: str,
        feature_recognition_id: Optional[int],
    ) -> list[Operation]:
        """
        Create Operations directly from structured operation_groups (v2.1).

        Each OperationGroup becomes ONE Operation with multiple child Features.
        This preserves the AI's setup/upnutí grouping logic.

        Args:
            db: Database session
            part_id: Target part ID
            operation_groups: List of OperationGroup from Claude (setup-based)
            cutting_mode: Cutting mode
            username: User for audit
            feature_recognition_id: Optional FR record ID

        Returns:
            List of Operation entities (not yet committed)
        """
        created_ops = []

        for group in operation_groups:
            # Extract group metadata
            setup_id = group.get('setup_id', 'OP10')
            description = group.get('description', 'Operace')
            seq = group.get('seq', 10)
            category = group.get('operation_category', 'turning')
            op_type = group.get('operation_type', 'výrobní')
            machine_type = group.get('machine_type', 'lathe_3ax')
            machine_name = group.get('machine_name')
            features = group.get('features', [])

            if not features:
                logger.warning(f"Skipping empty operation group: {setup_id}")
                continue

            # Map category to operation config
            config = CATEGORY_OPERATION_MAP.get(category, CATEGORY_OPERATION_MAP["turning"])

            # Create Operation entity
            op = Operation(
                part_id=part_id,
                seq=seq,
                name=f"{setup_id}: {description}",  # e.g., "OP10: Soustružení - přední strana"
                type=config["type"],
                icon=config.get("icon", "settings"),
                cutting_mode=cutting_mode,
                setup_time_min=config.get("setup_time", 30.0),
                is_coop=config.get("is_coop", False),
            )

            # Add feature_recognition_id if column exists
            if feature_recognition_id and hasattr(Operation, 'feature_recognition_id'):
                op.feature_recognition_id = feature_recognition_id

            set_audit(op, username)

            # Create child features from group.features
            total_time_sec = 0.0
            for i, feat_data in enumerate(features, start=1):
                feature = self._map_feature_dict_to_entity(feat_data, seq=i)
                feature.operation = op  # Use relationship
                set_audit(feature, username)
                total_time_sec += feature.predicted_time_sec or 0.0

            # Set operation_time_min from sum of features
            op.operation_time_min = round(total_time_sec / 60, 2)

            created_ops.append(op)

        return created_ops

    def _map_feature_dict_to_entity(
        self, feat_dict: dict, seq: int
    ) -> Feature:
        """
        Map feature dict from OperationGroup.features[] → Feature entity.

        Similar to _map_suggestion_to_feature() but works with raw dicts
        from operation_groups (not OperationSuggestion objects).

        Args:
            feat_dict: Feature dict from operation_groups[].features[]
            seq: Feature sequence number

        Returns:
            Feature entity (not yet committed)
        """
        # Extract feature type
        ft_str = feat_dict.get('feature_type', 'face')
        ft_str = validate_feature_type(ft_str) or ft_str

        try:
            feature_type = FeatureType(ft_str)
        except (ValueError, KeyError):
            feature_type = FeatureType.FACE
            logger.warning(f"Invalid feature type '{ft_str}', defaulting to FACE")

        # Extract geometry params
        from_diameter = feat_dict.get('from_diameter')
        to_diameter = feat_dict.get('to_diameter') or feat_dict.get('diameter')
        length = feat_dict.get('length')
        depth = feat_dict.get('depth')
        width = feat_dict.get('width')
        pocket_length = feat_dict.get('pocket_length')
        pocket_width = feat_dict.get('pocket_width')
        corner_radius = feat_dict.get('corner_radius')
        thread_pitch = feat_dict.get('thread_pitch')
        blade_width = feat_dict.get('blade_width', 3.0)
        count = feat_dict.get('count', 1)
        tool_number = feat_dict.get('tool_number')
        tool_name = feat_dict.get('tool_name', 'Nástroj')
        note = feat_dict.get('note', '')

        # Time: AI estimate from feature (enrichment happens later in ai_feature_mapper)
        time_min = feat_dict.get('estimated_time_min', 0)
        time_sec = time_min * 60

        return Feature(
            seq=seq,
            feature_type=feature_type,
            from_diameter=from_diameter,
            to_diameter=to_diameter,
            length=length,
            depth=depth,
            width=width,
            pocket_length=pocket_length,
            pocket_width=pocket_width,
            corner_radius=corner_radius,
            thread_pitch=thread_pitch,
            blade_width=blade_width,
            count=count,
            tool_number=tool_number,
            tool_name=tool_name,
            predicted_time_sec=round(time_sec, 1),
            note=note,
        )

    def _map_suggestion_to_feature(
        self, suggestion: OperationSuggestion, seq: int
    ) -> Feature:
        """
        Map OperationSuggestion → Feature model.

        Extracts:
        - Geometry params (diameter, length, depth, etc.)
        - Cutting conditions (Vc, f, Ap, fz)
        - Time (prefers calculated_time_min over estimated_time_min)
        - Metadata (notes)

        Args:
            suggestion: AI operation suggestion
            seq: Feature sequence number

        Returns:
            Feature entity (not yet committed)
        """
        params = suggestion.params or {}
        cutting = suggestion.cutting_conditions or {}

        # Normalize feature type to enum
        ft_str = suggestion.feature_type or ""
        ft_str = validate_feature_type(ft_str) or ft_str

        try:
            feature_type = FeatureType(ft_str)
        except (ValueError, KeyError):
            feature_type = FeatureType.FACE
            logger.warning(f"Invalid feature type '{ft_str}', defaulting to FACE")

        # Calculate time: prefer calculated_time_min, fallback to estimated_time_min
        time_min = suggestion.calculated_time_min or suggestion.estimated_time_min or 0
        time_sec = time_min * 60

        return Feature(
            seq=seq,
            feature_type=feature_type,
            from_diameter=params.get("from_diameter"),
            to_diameter=params.get("to_diameter") or params.get("diameter"),
            length=params.get("length"),
            depth=params.get("depth"),
            width=params.get("width"),
            pocket_length=params.get("pocket_length"),
            pocket_width=params.get("pocket_width"),
            corner_radius=params.get("corner_radius"),
            thread_pitch=params.get("thread_pitch"),
            Vc=cutting.get("Vc"),
            f=cutting.get("f"),
            Ap=cutting.get("Ap"),
            fz=cutting.get("fz"),
            blade_width=params.get("blade_width", 3.0),
            count=params.get("count", 1),
            tool_number=suggestion.tool_number,
            tool_name=suggestion.tool_name or suggestion.tool,
            predicted_time_sec=round(time_sec, 1),
            note=suggestion.notes or "",
        )


# Singleton
fr_apply_service = FRApplyService()
