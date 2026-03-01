"""GESTIMA - Enumerace"""

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    MISTR = "mistr"


class PartSource(str, Enum):
    """Zdroj/původ dílu"""
    MANUAL = "manual"              # Ručně vytvořen v Gestimě
    INFOR_IMPORT = "infor_import"  # Importován z Infor ERP
    QUOTE_REQUEST = "quote_request"  # Z poptávkového modulu (budoucí)


class PartStatus(str, Enum):
    """Status dílu (lifecycle)"""
    DRAFT = "draft"        # Rozpracovaný (wizard nedokončen)
    ACTIVE = "active"      # Aktivní (v provozu)
    ARCHIVED = "archived"  # Archivovaný
    QUOTE = "quote"        # Nabídka (importováno z Inforu)


class StockType(str, Enum):
    ROD = "tyc"
    TUBE = "trubka"
    BILLET = "prizez"
    CASTING = "odlitek"
    SHEET = "deska"


class StockShape(str, Enum):
    """Tvary polotovarů (geometrické kategorie)"""
    ROUND_BAR = "round_bar"       # Tyč kruhová
    SQUARE_BAR = "square_bar"     # Tyč čtvercová
    FLAT_BAR = "flat_bar"         # Tyč plochá
    HEXAGONAL_BAR = "hexagonal_bar"  # Tyč šestihranná
    PLATE = "plate"               # Deska
    TUBE = "tube"                 # Trubka
    CASTING = "casting"           # Odlitek
    FORGING = "forging"           # Výkovek


class UnitOfMeasure(str, Enum):
    """Měrné jednotky (ADR-050)"""
    KS = "ks"   # kusy / pieces (Infor: EA)
    KG = "kg"   # kilogramy
    M  = "m"    # metry (typicky jen conv_uom)
    MM = "mm"   # milimetry (typicky jen conv_uom)


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


class WorkCenterType(str, Enum):
    """Typy pracovišť (ADR-021)"""

    # CNC Soustruhy
    CNC_LATHE = "CNC_LATHE"

    # CNC Frézky
    CNC_MILL_3AX = "CNC_MILL_3AX"    # 3-axis
    CNC_MILL_4AX = "CNC_MILL_4AX"    # 4-axis (horizontal)
    CNC_MILL_5AX = "CNC_MILL_5AX"    # 5-axis

    # Ostatní stroje
    SAW = "SAW"                      # Pily
    DRILL = "DRILL"                  # Vrtačky

    # Virtuální pracoviště
    QUALITY_CONTROL = "QUALITY_CONTROL"   # Kontrola
    MANUAL_ASSEMBLY = "MANUAL_ASSEMBLY"   # Mechanik/montáž
    EXTERNAL = "EXTERNAL"                 # Kooperace


class QuoteStatus(str, Enum):
    """Quote workflow status (ADR-VIS-002)"""
    DRAFT = "draft"          # Can be edited
    SENT = "sent"            # Sent to customer (read-only, snapshot created)
    APPROVED = "approved"    # Customer accepted
    REJECTED = "rejected"    # Customer declined


class WorkshopTransType(str, Enum):
    """Typ dílnické transakce — mapování na Infor @TTransType:
      setup_start → '1' (ZahajitNastaveni — start seřízení)
      setup_end   → '2' (UkoncitNastaveni — ukončit seřízení)
      start       → '3' (ZahajitPraci — start výroby)
      qty_complete, stop, time, scrap → '4' (UkoncitPraci — odvod/ukončení)
    """
    QTY_COMPLETE = "qty_complete"  # Odvod hotových kusů (@TTransType='4')
    SCRAP = "scrap"                # Zmetkové kusy (@TTransType='4')
    TIME = "time"                  # Odpracovaný čas — manuální (@TTransType='4')
    START = "start"                # Start výroby — posílá se OKAMŽITĚ (@TTransType='3')
    STOP = "stop"                  # Stop výroby s hodinami (@TTransType='4')
    SETUP_START = "setup_start"    # Start seřízení — posílá se OKAMŽITĚ (@TTransType='1')
    SETUP_END = "setup_end"        # Ukončení seřízení s hodinami (@TTransType='2')


class WorkshopTxStatus(str, Enum):
    """Status transakce vůči Inforu"""
    PENDING = "pending"    # Čeká na odeslání do Inforu
    POSTING = "posting"    # Odesílání probíhá
    POSTED = "posted"      # Odesláno úspěšně
    FAILED = "failed"      # Chyba při odesílání
