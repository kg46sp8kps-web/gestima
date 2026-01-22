"""GESTIMA - Enumerace"""

from enum import Enum


class StockType(str, Enum):
    ROD = "tyc"
    TUBE = "trubka"
    BILLET = "prizez"
    CASTING = "odlitek"
    SHEET = "plech"


class PartStatus(str, Enum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    QUOTED = "quoted"
    APPROVED = "approved"
    COMPLETED = "completed"


class CuttingMode(str, Enum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"


class FeatureType(str, Enum):
    # === SOUSTRUŽENÍ ===
    FACE = "face"
    OD_ROUGH = "od_rough"
    OD_FINISH = "od_finish"
    OD_PROFILE = "od_profile"
    ID_ROUGH = "id_rough"
    ID_FINISH = "id_finish"
    ID_PROFILE = "id_profile"
    BORE = "bore"
    THREAD_OD = "thread_od"
    THREAD_ID = "thread_id"
    GROOVE_OD = "groove_od"
    GROOVE_ID = "groove_id"
    GROOVE_FACE = "groove_face"
    PARTING = "parting"
    CUTOFF = "cutoff"
    CHAMFER = "chamfer"
    RADIUS = "radius"
    KNURL = "knurl"
    
    # === VRTÁNÍ ===
    CENTER_DRILL = "center_drill"
    DRILL = "drill"
    DRILL_DEEP = "drill_deep"
    REAM = "ream"
    TAP = "tap"
    
    # === LIVE TOOLING ===
    LT_DRILL = "lt_drill"
    LT_DRILL_AXIAL = "lt_drill_axial"
    LT_TAP = "lt_tap"
    LT_FLAT = "lt_flat"
    LT_SLOT = "lt_slot"
    LT_POLYGON = "lt_polygon"
    LT_KEYWAY = "lt_keyway"
    LT_CONTOUR = "lt_contour"
    
    # === FRÉZOVÁNÍ ===
    MILL_FACE = "mill_face"
    MILL_SHOULDER = "mill_shoulder"
    MILL_POCKET = "mill_pocket"
    MILL_POCKET_ROUND = "mill_pocket_round"
    MILL_SLOT = "mill_slot"
    MILL_KEYWAY = "mill_keyway"
    MILL_CONTOUR_OD = "mill_contour_od"
    MILL_CONTOUR_ID = "mill_contour_id"
    MILL_3D = "mill_3d"
    MILL_CENTER = "mill_center"
    MILL_DRILL = "mill_drill"
    MILL_DRILL_DEEP = "mill_drill_deep"
    MILL_REAM = "mill_ream"
    MILL_TAP = "mill_tap"
    MILL_THREAD = "mill_thread"
    MILL_CHAMFER = "mill_chamfer"
    MILL_DEBURR = "mill_deburr"
    MILL_ENGRAVE = "mill_engrave"
    
    # === BROUŠENÍ ===
    GRIND_OD = "grind_od"
    GRIND_ID = "grind_id"
    GRIND_FACE = "grind_face"
    
    # === DOKONČOVACÍ ===
    HONE = "hone"
    POLISH = "polish"
    DEBURR_MANUAL = "deburr_manual"
    
    # === LOGISTIKA ===
    WASH = "wash"
    INSPECT = "inspect"
    PACK = "pack"
