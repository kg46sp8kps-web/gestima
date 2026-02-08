"""GESTIMA - AI Feature Mapper

Bridge mezi Claude API outputem a interním Feature/Operation systémem.

Zodpovědnosti:
1. Mapuje feature_type z AI → FeatureType enum
2. Mapuje materiál → material_group (8-digit)
3. Dohledá řezné podmínky (Vc, f, Ap) z katalogu
4. Přepočítá strojní časy přes FeatureCalculator
5. Vrátí enriched operations s reálnými řeznými parametry

Použití:
    result = await enrich_ai_operations(
        ai_operations=claude_result['operations'],
        material_group="20910004",
        mode="mid",
    )
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from app.services.cutting_conditions_catalog import (
    get_catalog_conditions,
    resolve_material_group,
    MATERIAL_GROUP_MAP,
)
from app.services.feature_definitions import FEATURE_FIELDS
from app.services.time_calculator import FeatureCalculator

logger = logging.getLogger(__name__)

# Valid feature types from our enum
VALID_FEATURE_TYPES = set(FEATURE_FIELDS.keys())

# All valid FeatureType enum values (superset of FEATURE_FIELDS keys)
from app.models.enums import FeatureType
ALL_FEATURE_TYPE_VALUES = {ft.value for ft in FeatureType}


def validate_feature_type(feature_type: str) -> str:
    """
    Validuje a normalizuje feature_type z AI outputu.

    Claude by měl vracet přesné hodnoty z FEATURE_FIELDS,
    ale pro robustnost normalizujeme běžné variace.
    """
    if feature_type in VALID_FEATURE_TYPES:
        return feature_type

    # Normalizace běžných variací
    normalize_map = {
        # Variations Claude might use
        'drilling': 'drill',
        'deep_drill': 'drill_deep',
        'deep_drilling': 'drill_deep',
        'reaming': 'ream',
        'tapping': 'tap',
        'threading': 'thread_od',
        'thread': 'thread_od',
        'turning_face': 'face',
        'turning_od_rough': 'od_rough',
        'turning_od_finish': 'od_finish',
        'turning_id_rough': 'id_rough',
        'turning_id_finish': 'id_finish',
        'turning_groove': 'groove_od',
        'turning_parting': 'parting',
        'milling_face': 'mill_face',
        'milling_pocket': 'mill_pocket',
        'milling_slot': 'mill_slot',
        'milling_shoulder': 'mill_shoulder',
        'milling_contour': 'mill_contour_od',
        'milling_3d': 'mill_3d',
        'milling_drill': 'mill_drill',
        'chamfering': 'chamfer',
        'center_drilling': 'center_drill',
        'boring': 'bore',
        'od_profile': 'od_rough',
        'id_profile': 'id_rough',
        'grinding_od': 'grind_od',
        'grinding_id': 'grind_id',
        'washing': 'wash',
        'inspection': 'inspect',
        'packing': 'pack',
        'deburring': 'deburr_manual',
    }

    normalized = normalize_map.get(feature_type.lower())
    if normalized:
        logger.debug(f"Normalized feature_type: '{feature_type}' → '{normalized}'")
        return normalized

    # Check if it's a valid enum value but missing from FEATURE_FIELDS
    ft_lower = feature_type.lower()
    if ft_lower in ALL_FEATURE_TYPE_VALUES:
        if ft_lower not in VALID_FEATURE_TYPES:
            logger.info(f"Feature type '{ft_lower}' is valid enum but has no FEATURE_FIELDS entry — no enrichment available")
        return ft_lower

    logger.warning(f"Unknown feature_type from AI: '{feature_type}', keeping as-is")
    return feature_type


def map_feature_to_geometry(feature: Dict) -> Dict[str, Any]:
    """
    Mapuje AI feature parametry na geometrii pro FeatureCalculator.

    AI output:
        {"feature_type": "od_rough", "from_diameter": 55, "to_diameter": 40, "length": 30}

    FeatureCalculator geometry:
        {"from_diameter": 55, "to_diameter": 40, "length": 30}
    """
    geometry = {}

    # Přímé mapování parametrů
    field_map = {
        'from_diameter': 'from_diameter',
        'to_diameter': 'to_diameter',
        'length': 'length',
        'depth': 'depth',
        'width': 'width',
        'pocket_length': 'pocket_length',
        'pocket_width': 'pocket_width',
        'corner_radius': 'corner_radius',
        'thread_pitch': 'thread_pitch',
        'blade_width': 'blade_width',
        'count': 'count',
    }

    for ai_key, geo_key in field_map.items():
        value = feature.get(ai_key)
        if value is not None and value != 'through':
            geometry[geo_key] = value

    # Fallback: 'diameter' → 'to_diameter' (pro vrtání)
    if 'to_diameter' not in geometry and 'diameter' in feature:
        geometry['to_diameter'] = feature['diameter']

    # 'depth' → 'length' fallback (pro díry kde length = depth)
    if 'length' not in geometry and 'depth' in geometry:
        depth = geometry['depth']
        if isinstance(depth, (int, float)):
            geometry['length'] = depth

    return geometry


async def _enrich_single_operation(
    op: Dict,
    material_group: str,
    mode: str,
    calculator: FeatureCalculator,
) -> Dict:
    """
    Enrichuje jednu AI operaci o řezné podmínky a strojní čas.

    Tuto funkci lze volat paralelně (asyncio.gather).

    Args:
        op: Jedna operace z Claude API
        material_group: 8-digit kód materiálu
        mode: Řezný režim (low/mid/high)
        calculator: FeatureCalculator instance

    Returns:
        Enriched operation dict
    """
    feature_type = validate_feature_type(
        op.get('feature_type', op.get('operation_type', 'unknown'))
    )

    # Get feature definition
    feature_def = FEATURE_FIELDS.get(feature_type)

    # Build geometry from params
    params = op.get('params', {})
    # Merge top-level feature fields with params (AI v2 puts them at top level)
    merged = {**params, **{k: v for k, v in op.items()
                           if k not in ('operation_type', 'feature_type', 'tool',
                                        'params', 'estimated_time_min', 'confidence',
                                        'notes', 'note', 'seq')
                           and v is not None}}
    geometry = map_feature_to_geometry(merged)

    # Lookup cutting conditions from catalog
    cutting_conditions = {}
    if feature_def and 'db_operation' in feature_def:
        op_type, operation = feature_def['db_operation']
        cutting_conditions = get_catalog_conditions(
            material_group=material_group,
            operation_type=op_type,
            operation=operation,
            mode=mode,
        )

    # Constant time features (chamfer, wash, inspect, etc.)
    constant_time = feature_def.get('constant_time') if feature_def else None

    # Calculate machining time
    calculated_time = None
    calc_result = None
    if constant_time is not None:
        calculated_time = constant_time
    elif geometry and cutting_conditions:
        try:
            calc_result = await calculator.calculate(
                feature_type=feature_type,
                material_group=material_group,
                cutting_mode=mode,
                geometry=geometry,
            )
            calculated_time = round(calc_result.total_time_sec / 60, 2)
        except Exception as e:
            logger.warning(f"Time calculation failed for {feature_type}: {e}")

    # Build enriched operation
    enriched_op = {
        **op,
        'feature_type': feature_type,
        'material_group': material_group,
    }

    # Add cutting conditions
    if cutting_conditions:
        enriched_op['cutting_conditions'] = {
            'Vc': cutting_conditions.get('Vc'),
            'f': cutting_conditions.get('f'),
            'Ap': cutting_conditions.get('Ap'),
            'fz': cutting_conditions.get('fz'),
            'mode': mode,
            'source': 'catalog',
        }

    # Add calculated time (prefer over AI estimate)
    if calculated_time is not None and calculated_time > 0:
        enriched_op['calculated_time_min'] = calculated_time
        # Keep AI estimate for comparison
        enriched_op['ai_estimated_time_min'] = op.get('estimated_time_min', 0)
        # Use calculated time as primary
        enriched_op['estimated_time_min'] = calculated_time
    elif calc_result and calc_result.total_time_sec > 0:
        enriched_op['calculated_time_min'] = round(calc_result.total_time_sec / 60, 2)

    # Add calculation details
    if calc_result:
        enriched_op['calculation'] = {
            'rpm': calc_result.rpm,
            'num_passes': calc_result.num_passes,
            'cutting_time_sec': round(calc_result.cutting_time_sec, 1),
        }

    return enriched_op


async def enrich_ai_operations(
    ai_operations: List[Dict],
    material_spec: Optional[str] = None,
    material_group: Optional[str] = None,
    mode: str = "mid",
    max_rpm: int = 4000,
) -> List[Dict]:
    """
    Enrichuje AI operace o řezné podmínky a přesné strojní časy.

    PERFORMANCE: Operace se enrichují paralelně pomocí asyncio.gather().

    Args:
        ai_operations: Flat list operací z Claude API (po _flatten_operations)
        material_spec: Textový popis materiálu (1.1191, C45, etc.)
        material_group: 8-digit kód (pokud už známe)
        mode: Řezný režim (low/mid/high)
        max_rpm: Max otáčky stroje

    Returns:
        Enriched operations s Vc, f, Ap, rpm, přepočítaný čas
    """
    # Resolve material group
    if not material_group and material_spec:
        material_group = resolve_material_group(material_spec)
    if not material_group:
        material_group = "20910004"  # Default: konstrukční ocel
        logger.warning("No material specified, defaulting to 20910004 (konstrukční ocel)")

    calculator = FeatureCalculator(max_rpm=max_rpm)

    # Parallel enrichment (PERFORMANCE FIX: 10s → <1s)
    tasks = [
        _enrich_single_operation(op, material_group, mode, calculator)
        for op in ai_operations
    ]
    enriched = await asyncio.gather(*tasks)

    logger.info(
        f"Enriched {len(enriched)} operations: "
        f"material={material_group}, mode={mode}, "
        f"with_conditions={sum(1 for e in enriched if 'cutting_conditions' in e)}, "
        f"with_calc_time={sum(1 for e in enriched if 'calculated_time_min' in e)}"
    )

    return list(enriched)


def summarize_operations(enriched_operations: List[Dict]) -> Dict[str, Any]:
    """
    Vytvoří souhrn enriched operací pro frontend.

    Returns:
        {
            "total_time_min": 15.3,
            "total_time_ai_min": 18.5,
            "operation_count": 8,
            "feature_count": 12,
            "material_group": "20910004",
            "has_cutting_conditions": True,
        }
    """
    total_calc = sum(op.get('calculated_time_min', 0) for op in enriched_operations)
    total_ai = sum(op.get('ai_estimated_time_min', op.get('estimated_time_min', 0))
                   for op in enriched_operations)
    has_conditions = any('cutting_conditions' in op for op in enriched_operations)

    return {
        'total_time_min': round(total_calc, 1) if total_calc > 0 else round(total_ai, 1),
        'total_time_calculated_min': round(total_calc, 1),
        'total_time_ai_min': round(total_ai, 1),
        'operation_count': len(enriched_operations),
        'has_cutting_conditions': has_conditions,
        'material_group': enriched_operations[0].get('material_group') if enriched_operations else None,
    }
