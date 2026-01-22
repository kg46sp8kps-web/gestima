# GESTIMA 1.0 - SPECIFIKACE PRO NOVÝ PROJEKT

**Účel:** Kompletní specifikace pro vytvoření nové verze kalkulátoru CNC obrábění  
**Zdroj:** Extrahováno z Kalkulator3000 v9.2 (očištěno o legacy kód)  
**Autor:** Automaticky generováno  
**Datum:** 2026-01-22

---

## 1. PŘEHLED PROJEKTU

### 1.1 Co je GESTIMA?
Webová aplikace pro **kalkulaci nákladů CNC obrábění**. Uživatel zadá díl, operace a kroky → systém vypočítá časy a ceny pro různé velikosti dávek.

### 1.2 Klíčové funkce
- **Zadání dílu:** rozměry, materiál, polotovar
- **Definice operací:** soustružení, frézování, vrtání, broušení, kooperace
- **Kroky operací:** geometrie + řezné podmínky → výpočet času
- **Cenová kalkulace:** materiál + strojní čas + seřízení + kooperace
- **Porovnání dávek:** 1ks vs 10ks vs 100ks

### 1.3 Technologie (doporučeno)
- **Backend:** Python FastAPI + SQLAlchemy + SQLite
- **Frontend:** React/Vue + TypeScript + TailwindCSS
- **Referenční data:** Excel soubory (stroje, ceny materiálů, řezné podmínky)

---

## 2. DATOVÝ MODEL

### 2.1 Hierarchie entit
```
PART (Díl)
  ├── OPERATION (Operace) - technologický krok
  │     └── FEATURE (Krok) - konkrétní úkon s geometrií
  └── BATCH (Dávka) - cenová kalkulace pro konkrétní množství
```

### 2.2 Part (Díl)
```python
@dataclass
class Part:
    id: int
    part_number: str          # Číslo výkresu
    name: str                 # Název dílu
    
    # Materiál
    material_name: str        # "Ocel 11 523 (S355)"
    material_group: str       # "konstrukcni_ocel" (klíč pro řezné podmínky)
    
    # Polotovar
    stock_type: StockType     # tyc, trubka, prizez, odlitek, plech
    stock_diameter: float     # Vnější průměr [mm]
    stock_diameter_inner: float  # Vnitřní průměr (trubka) [mm]
    stock_length: float       # Délka polotovaru [mm]
    
    # Finální rozměry
    final_diameter: float     # Finální průměr [mm]
    final_length: float       # Finální délka [mm]
    
    # Metadata
    status: PartStatus        # draft, calculated, quoted...
    notes: str
    created_at: datetime
    updated_at: datetime
```

### 2.3 Operation (Operace)
```python
@dataclass
class Operation:
    id: int
    part_id: int              # FK na Part
    seq: int                  # Pořadí (10, 20, 30...)
    
    # Popis
    name: str                 # "OP10 - Soustružení"
    type: str                 # turning, milling, drilling, grinding, cooperation
    icon: str                 # Emoji ikona
    
    # Stroj a režim
    machine_id: int           # FK na Machine
    cutting_mode: str         # low, mid, high
    
    # Časy
    setup_time_min: float     # Seřizovací čas [min]
    operation_time_min: float # Strojní čas [min] - SOUČET z features
    
    # Zamykání (ruční hodnota nepřepočítávat)
    setup_time_locked: bool
    operation_time_locked: bool
    
    # Kooperace
    is_coop: bool
    coop_type: str            # "tepelne_zpracovani", "povrchova_uprava"
    coop_price: float         # Cena za kus [Kč]
    coop_min_price: float     # Minimální cena za dávku [Kč]
    coop_days: int            # Dodací lhůta [dny]
```

### 2.4 Feature (Krok operace)
```python
@dataclass
class Feature:
    id: int
    operation_id: int         # FK na Operation
    seq: int                  # Pořadí kroků
    
    # Typ
    feature_type: FeatureType # face, od_rough, drill, mill_pocket...
    
    # === GEOMETRIE ===
    from_diameter: float      # Ds - startovní průměr [mm]
    to_diameter: float        # Df - finální průměr [mm]
    length: float             # Délka [mm]
    depth: float              # Hloubka [mm]
    width: float              # Šířka [mm]
    pocket_length: float      # Délka kapsy [mm]
    pocket_width: float       # Šířka kapsy [mm]
    corner_radius: float      # Rohový radius [mm]
    thread_pitch: float       # Stoupání závitu [mm]
    
    # === ŘEZNÉ PODMÍNKY ===
    Vc: float                 # Řezná rychlost [m/min]
    f: float                  # Posuv [mm/ot]
    Ap: float                 # Hloubka řezu [mm]
    fz: float                 # Posuv na zub [mm/zub] - frézování
    
    # Zámky (True = ručně nastaveno, nepřepočítávat)
    Vc_locked: bool
    f_locked: bool
    Ap_locked: bool
    
    # === NÁSTROJ ===
    blade_width: float        # Šířka břitu (zápichy) [mm]
    count: int                # Počet opakování (např. 4 díry)
    
    # === VÝPOČET ===
    predicted_time_sec: float # Vypočtený strojní čas [s]
```

### 2.5 Batch (Dávka)
```python
@dataclass
class Batch:
    id: int
    part_id: int              # FK na Part
    quantity: int             # Velikost dávky [ks]
    is_default: bool          # Výchozí dávka pro zobrazení
    
    # Čas
    unit_time_min: float      # Strojní čas na kus [min]
    
    # Cenová kalkulace
    material_cost: float      # Materiál/ks [Kč]
    machining_cost: float     # Výroba/ks [Kč]
    setup_cost: float         # Seřízení/ks [Kč] = total_setup / quantity
    coop_cost: float          # Kooperace/ks [Kč]
    
    # Součty
    unit_cost: float          # Celkem/ks [Kč]
    total_cost: float         # Celkem za dávku [Kč]
```

### 2.6 Machine (Stroj) - REFERENČNÍ DATA
```python
@dataclass
class Machine:
    id: int
    name: str                 # "NLX 2000"
    type: str                 # lathe, mill, lathe_mill, saw, grinding
    
    # Parametry
    max_rpm: int              # Max otáčky [ot/min]
    max_diameter: float       # Max průměr [mm]
    max_length: float         # Max délka [mm]
    has_live_tooling: bool    # Má poháněné nástroje?
    has_bar_feeder: bool      # Má podavač tyčí?
    bar_feeder_max_dia: float # Max průměr pro podavač [mm]
    
    # Ekonomika
    hourly_rate: float        # Hodinová sazba [Kč/hod]
```

---

## 3. ENUMERACE

### 3.1 StockType (Typ polotovaru)
```python
class StockType(str, Enum):
    ROD = "tyc"           # Plná tyč
    TUBE = "trubka"       # Trubka
    BILLET = "prizez"     # Přířez
    CASTING = "odlitek"   # Odlitek
    SHEET = "plech"       # Plech
```

### 3.2 PartStatus (Stav dílu)
```python
class PartStatus(str, Enum):
    DRAFT = "draft"           # Rozpracovaný
    CALCULATED = "calculated" # Vypočtený
    QUOTED = "quoted"         # Nacenený
    APPROVED = "approved"     # Schválený
    COMPLETED = "completed"   # Dokončený
```

### 3.3 CuttingMode (Řezný režim)
```python
class CuttingMode(str, Enum):
    LOW = "low"    # Nízký výkon, delší životnost nástroje
    MID = "mid"    # Střední (výchozí)
    HIGH = "high"  # Vysoký výkon, kratší životnost
```

### 3.4 FeatureType (Typ kroku) - 51 TYPŮ
```python
class FeatureType(str, Enum):
    # === SOUSTRUŽENÍ ===
    FACE = "face"                 # Zarovnání čela
    OD_ROUGH = "od_rough"         # Vnější hrubování
    OD_FINISH = "od_finish"       # Vnější dokončení
    OD_PROFILE = "od_profile"     # Vnější profil
    ID_ROUGH = "id_rough"         # Vnitřní hrubování
    ID_FINISH = "id_finish"       # Vnitřní dokončení
    ID_PROFILE = "id_profile"     # Vnitřní profil
    BORE = "bore"                 # Vyvrtávání
    THREAD_OD = "thread_od"       # Vnější závit
    THREAD_ID = "thread_id"       # Vnitřní závit
    GROOVE_OD = "groove_od"       # Vnější zápich
    GROOVE_ID = "groove_id"       # Vnitřní zápich
    GROOVE_FACE = "groove_face"   # Čelní zápich
    PARTING = "parting"           # Upíchnutí
    CUTOFF = "cutoff"             # Odřezání (pila)
    CHAMFER = "chamfer"           # Sražení hrany
    RADIUS = "radius"             # Zaoblení
    KNURL = "knurl"               # Rádlování
    
    # === VRTÁNÍ ===
    CENTER_DRILL = "center_drill" # Navrtání
    DRILL = "drill"               # Vrtání
    DRILL_DEEP = "drill_deep"     # Hluboké vrtání
    REAM = "ream"                 # Vystružování
    TAP = "tap"                   # Závitování
    
    # === LIVE TOOLING ===
    LT_DRILL = "lt_drill"         # Příčné vrtání
    LT_DRILL_AXIAL = "lt_drill_axial"  # Osové vrtání
    LT_TAP = "lt_tap"             # Příčné závitování
    LT_FLAT = "lt_flat"           # Frézování plošky
    LT_SLOT = "lt_slot"           # Frézování drážky
    LT_POLYGON = "lt_polygon"     # Frézování polygonu
    LT_KEYWAY = "lt_keyway"       # Drážka pro pero
    LT_CONTOUR = "lt_contour"     # Frézování kontury
    
    # === FRÉZOVÁNÍ ===
    MILL_FACE = "mill_face"           # Čelní frézování
    MILL_SHOULDER = "mill_shoulder"   # Frézování osazení
    MILL_POCKET = "mill_pocket"       # Kapsa
    MILL_POCKET_ROUND = "mill_pocket_round"  # Kruhová kapsa
    MILL_SLOT = "mill_slot"           # Drážka
    MILL_KEYWAY = "mill_keyway"       # Drážka pro pero
    MILL_CONTOUR_OD = "mill_contour_od"  # Vnější kontura
    MILL_CONTOUR_ID = "mill_contour_id"  # Vnitřní kontura
    MILL_3D = "mill_3d"               # 3D frézování
    MILL_CENTER = "mill_center"       # Navrtání
    MILL_DRILL = "mill_drill"         # Vrtání
    MILL_DRILL_DEEP = "mill_drill_deep"  # Hluboké vrtání
    MILL_REAM = "mill_ream"           # Vystružování
    MILL_TAP = "mill_tap"             # Závitování
    MILL_THREAD = "mill_thread"       # Frézování závitu
    MILL_CHAMFER = "mill_chamfer"     # Sražení hran
    MILL_DEBURR = "mill_deburr"       # Odjehlení
    MILL_ENGRAVE = "mill_engrave"     # Gravírování
    
    # === BROUŠENÍ ===
    GRIND_OD = "grind_od"         # Broušení vnější
    GRIND_ID = "grind_id"         # Broušení vnitřní
    GRIND_FACE = "grind_face"     # Broušení čela
    
    # === DOKONČOVACÍ ===
    HONE = "hone"                 # Honování
    POLISH = "polish"            # Leštění
    DEBURR_MANUAL = "deburr_manual"  # Ruční odjehlení
    
    # === LOGISTIKA ===
    WASH = "wash"                 # Mytí
    INSPECT = "inspect"           # Kontrola
    PACK = "pack"                 # Balení
```

---

## 4. VÝPOČETNÍ VZORCE

### 4.1 Základní vzorce CNC obrábění

```python
# OTÁČKY
n = (1000 × Vc) / (π × D)
# n = otáčky [ot/min]
# Vc = řezná rychlost [m/min]
# D = průměr [mm]

# STROJNÍ ČAS
t = L / (n × f)
# t = čas [min]
# L = délka dráhy [mm]
# f = posuv [mm/ot]

# POČET PRŮCHODŮ (hrubování)
i = ceil(přídavek / Ap)
# i = počet průchodů
# Ap = hloubka řezu [mm]
```

### 4.2 Výpočet času podle typu kroku

#### Soustružení vnější (od_rough, od_finish)
```python
def calc_od_turning(feature, Vc, f, Ap):
    from_d = feature.from_diameter  # Startovní průměr
    to_d = feature.to_diameter      # Finální průměr
    length = feature.length
    
    # Přídavek na poloměru
    allowance = (from_d - to_d) / 2
    num_passes = ceil(allowance / Ap)
    
    # Průměrný průměr
    avg_diameter = (from_d + to_d) / 2
    rpm = calc_rpm(Vc, avg_diameter)
    
    # Čas jednoho průchodu × počet průchodů
    time_sec = ((length + 2) / (rpm × f)) × 60 × num_passes
    return time_sec
```

#### Vrtání
```python
def calc_drilling(feature, Vc, f):
    diameter = feature.to_diameter
    depth = feature.depth or feature.length
    
    rpm = calc_rpm(Vc, diameter)
    
    # Hluboké vrtání - cykly
    if depth > 3 × diameter:
        num_cycles = ceil(depth / (2 × diameter))
        time_sec = ((depth / (rpm × f)) × 60) × num_cycles × 0.7
    else:
        time_sec = (depth / (rpm × f)) × 60
    
    return time_sec
```

#### Frézování kapsy
```python
def calc_mill_pocket(feature, Vc, fz, Ap):
    width = feature.pocket_width
    length = feature.pocket_length
    depth = feature.depth
    corner_radius = feature.corner_radius
    
    # Fréza = 2× rohový radius, max 16mm
    tool_dia = min(corner_radius × 2, 16)
    
    # Záběr = 40% průměru frézy
    Ae = tool_dia × 0.4
    
    num_passes_z = ceil(depth / Ap)
    
    rpm = calc_milling_rpm(Vc, tool_dia)
    vf = fz × 4 × rpm  # 4 zuby
    
    # Plocha kapsy / šířka záběru = délka dráhy
    pocket_area = width × length
    path_length = pocket_area / Ae
    total_path = path_length × num_passes_z
    
    time_sec = (total_path / vf) × 60
    return time_sec
```

#### Závitování
```python
def calc_threading(feature, Vc, pitch, num_passes):
    diameter = feature.to_diameter
    length = feature.length
    
    rpm = calc_rpm(Vc, diameter)
    
    # f = stoupání závitu
    # Tam + zpět pro každý průchod
    time_sec = ((length / (rpm × pitch)) × 60) × num_passes × 2
    return time_sec
```

### 4.3 Konstantní časy (sekund)
```python
CONSTANT_TIMES = {
    "chamfer": 1.0,
    "radius": 1.0,
    "mill_chamfer": 2.0,
    "mill_deburr": 5.0,
    "mill_engrave": 10.0,
    "hone": 30.0,
    "polish": 60.0,
    "deburr_manual": 30.0,
    "wash": 15.0,
    "inspect": 30.0,
    "pack": 10.0,
}
```

---

## 5. ŘEZNÉ PODMÍNKY

### 5.1 Struktura dat
Řezné podmínky se načítají z Excel souboru `operations_base.xlsx`:

```
| category  | operation | mode | Vc  | f    | Ap  |
|-----------|-----------|------|-----|------|-----|
| turning   | od_rough  | low  | 120 | 0.25 | 2.5 |
| turning   | od_rough  | mid  | 180 | 0.30 | 3.0 |
| turning   | od_rough  | high | 250 | 0.35 | 3.5 |
| turning   | od_finish | low  | 150 | 0.10 | 0.3 |
| ...       | ...       | ...  | ... | ...  | ... |
```

### 5.2 Materiálové koeficienty
Z `material_coefficients.xlsx`:

```
| material_group      | K_Vc | K_f  | threading_category |
|---------------------|------|------|-------------------|
| automatova_ocel     | 1.30 | 1.20 | easy              |
| konstrukcni_ocel    | 1.00 | 1.00 | medium            |
| legovana_ocel       | 0.75 | 0.85 | medium            |
| nastrojova_ocel     | 0.50 | 0.70 | hard              |
| nerez_feriticka     | 0.55 | 0.80 | medium            |
| nerez_austeniticka  | 0.45 | 0.70 | hard              |
| hlinik              | 1.80 | 1.50 | easy              |
| mosaz_bronz         | 1.50 | 1.30 | easy              |
| med                 | 1.20 | 1.10 | easy              |
| plasty              | 2.00 | 1.50 | easy              |
```

### 5.3 Výpočet finálních podmínek
```python
def get_conditions(feature_type, material_group, mode):
    # 1. Načti základní hodnoty z operations_base.xlsx
    base = get_base_conditions(feature_type, mode)
    
    # 2. Načti koeficienty materiálu
    mat = get_material_coefficients(material_group)
    
    # 3. Vypočti finální hodnoty
    Vc = base.Vc × mat.K_Vc
    f = base.f × mat.K_f
    Ap = base.Ap  # Nemění se podle materiálu
    
    return (Vc, f, Ap)
```

### 5.4 Speciální koeficienty pro vrtání
Podle průměru vrtáku (referenční Ø16mm = 1.0):

```python
DRILLING_COEFFICIENTS = [
    # (max_diameter, K_Vc, K_f)
    (3,   0.60, 0.25),   # Ø1-3mm
    (6,   0.70, 0.40),   # Ø3-6mm
    (10,  0.85, 0.60),   # Ø6-10mm
    (16,  1.00, 0.80),   # Ø10-16mm (referenční)
    (25,  1.00, 1.00),   # Ø16-25mm
    (40,  0.95, 1.15),   # Ø25-40mm
    (999, 0.85, 1.25),   # Ø40+mm
]
```

### 5.5 Parametry závitování
Počet průchodů podle stoupání a materiálu:

```python
THREADING_PASSES = {
    "easy": {      # Automatová ocel, hliník
        (0, 1.0): 4,
        (1.0, 1.5): 5,
        (1.5, 2.0): 6,
        (2.0, 3.0): 7,
        (3.0, 999): 9,
    },
    "medium": {    # Konstrukční ocel
        (0, 1.0): 5,
        (1.0, 1.5): 6,
        (1.5, 2.0): 7,
        (2.0, 3.0): 9,
        (3.0, 999): 11,
    },
    "hard": {      # Nerez, nástrojová ocel
        (0, 1.0): 6,
        (1.0, 1.5): 7,
        (1.5, 2.0): 9,
        (2.0, 3.0): 11,
        (3.0, 999): 14,
    },
}
```

---

## 6. CENOVÁ KALKULACE

### 6.1 Materiálové náklady
```python
def calc_material_cost(part):
    # Objem polotovaru [mm³]
    if part.stock_type == "trubka":
        r_outer = part.stock_diameter / 2
        r_inner = part.stock_diameter_inner / 2
        volume_mm3 = π × (r_outer² - r_inner²) × part.stock_length
    else:
        volume_mm3 = π × (part.stock_diameter / 2)² × part.stock_length
    
    # Objem [dm³] → Hmotnost [kg]
    volume_dm3 = volume_mm3 / 1_000_000
    weight_kg = volume_dm3 × density  # 7.85 pro ocel
    
    # Cena
    cost = weight_kg × price_per_kg
    return cost
```

### 6.2 Strojní náklady
```python
def calc_machining_cost(operation, machine):
    # Strojní náklady na kus
    machining_cost = (operation.operation_time_min / 60) × machine.hourly_rate
    return machining_cost
```

### 6.3 Seřizovací náklady
```python
def calc_setup_cost(operation, machine, quantity):
    # Seřízení rozpočítané na kus
    total_setup = (operation.setup_time_min / 60) × machine.hourly_rate
    setup_per_piece = total_setup / quantity
    return setup_per_piece
```

### 6.4 Kooperace
```python
def calc_coop_cost(operation, quantity):
    if not operation.is_coop:
        return 0
    
    # Minimální cena za dávku
    raw_total = operation.coop_price × quantity
    total = max(raw_total, operation.coop_min_price)
    
    cost_per_piece = total / quantity
    return cost_per_piece
```

### 6.5 Celková cena
```python
def calc_batch_price(part, batch_quantity):
    # 1. Materiál
    material = calc_material_cost(part)
    
    # 2. Strojní + seřízení + kooperace
    machining = 0
    setup = 0
    coop = 0
    
    for operation in part.operations:
        machine = get_machine(operation.machine_id)
        
        if operation.is_coop:
            coop += calc_coop_cost(operation, batch_quantity)
        else:
            machining += calc_machining_cost(operation, machine)
            setup += calc_setup_cost(operation, machine, batch_quantity)
    
    # 3. Celkem
    unit_cost = material + machining + setup + coop
    total_cost = unit_cost × batch_quantity
    
    return {
        "material_cost": material,
        "machining_cost": machining,
        "setup_cost": setup,
        "coop_cost": coop,
        "unit_cost": unit_cost,
        "total_cost": total_cost,
    }
```

---

## 7. VÝPOČET POLOTOVARU

### 7.1 Přídavky
```python
STOCK_ALLOWANCE_DIAMETER = 3.0  # mm na průměru
STOCK_ALLOWANCE_LENGTH = 5.0    # mm na délce
STOCK_ALLOWANCE_CUT = 3.0       # mm upíchnutí/řez
STANDARD_BAR_LENGTH = 3000      # mm (3m tyč)
MAX_BAR_FEEDER_LENGTH = 1200    # mm (max délka pro podavač)
```

### 7.2 Standardní průměry tyčí
```python
STANDARD_DIAMETERS = [
    6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 25, 26, 28, 30,
    32, 35, 36, 38, 40, 42, 45, 48, 50, 52, 55, 58, 60,
    63, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120,
    130, 140, 150, 160, 170, 180, 190, 200, 220, 250
]
```

### 7.3 Určení typu polotovaru
```python
def calc_stock(final_diameter, final_length, machine):
    # Minimální rozměry
    min_dia = final_diameter + STOCK_ALLOWANCE_DIAMETER
    stock_length = final_length + STOCK_ALLOWANCE_LENGTH
    
    # Standardní průměr
    stock_diameter = find_next_standard_diameter(min_dia)
    
    # Typ polotovaru
    if stock_diameter > machine.bar_feeder_max_dia:
        return "prizez"  # Přířez
    elif stock_length > MAX_BAR_FEEDER_LENGTH:
        return "prizez"
    elif not machine.has_bar_feeder:
        return "prizez"
    else:
        # Tyč do podavače
        piece_with_cut = stock_length + STOCK_ALLOWANCE_CUT
        pieces_per_bar = int(STANDARD_BAR_LENGTH / piece_with_cut)
        return "tyc"
```

---

## 8. MATERIÁLOVÉ SKUPINY

### 8.1 Seznam skupin
```python
MATERIAL_GROUPS = {
    "automatova_ocel": {
        "name": "Automatová ocel",
        "density": 7.85,           # kg/dm³
        "price_per_kg": 35,        # Kč/kg
        "color": "#42A5F5",        # ISO P - modrá
    },
    "konstrukcni_ocel": {
        "name": "Konstrukční ocel",
        "density": 7.85,
        "price_per_kg": 28,
        "color": "#2196F3",
    },
    "legovana_ocel": {
        "name": "Legovaná ocel",
        "density": 7.85,
        "price_per_kg": 45,
        "color": "#1976D2",
    },
    "nastrojova_ocel": {
        "name": "Nástrojová ocel",
        "density": 7.85,
        "price_per_kg": 85,
        "color": "#1565C0",
    },
    "nerez_feriticka": {
        "name": "Nerez feritická",
        "density": 7.75,
        "price_per_kg": 95,
        "color": "#FFD54F",        # ISO M - žlutá
    },
    "nerez_austeniticka": {
        "name": "Nerez austenitická",
        "density": 7.90,
        "price_per_kg": 120,
        "color": "#FFC107",
    },
    "hlinik": {
        "name": "Hliník",
        "density": 2.70,
        "price_per_kg": 75,
        "color": "#4CAF50",        # ISO N - zelená
    },
    "mosaz_bronz": {
        "name": "Mosaz / Bronz",
        "density": 8.50,
        "price_per_kg": 180,
        "color": "#388E3C",
    },
    "med": {
        "name": "Měď",
        "density": 8.96,
        "price_per_kg": 220,
        "color": "#2E7D32",
    },
    "plasty": {
        "name": "Plasty",
        "density": 1.40,
        "price_per_kg": 45,
        "color": "#81C784",
    },
}
```

### 8.2 Mapování materiálů
Rozpoznání skupiny z názvu materiálu (viz `MATERIAL_MAPPING` - 350+ položek).

---

## 9. KONFIGURACE KROKŮ (FEATURE_FIELDS)

Každý typ kroku má definováno:
- `name`: Český název
- `icon`: Emoji ikona
- `category`: Kategorie (turning, milling, drilling...)
- `fields`: Povinná geometrická pole (Ds, Df, length, depth, width...)
- `cutting`: Řezné podmínky (Vc, f, Ap, fz)
- `defaults`: Výchozí hodnoty
- `constant_time`: Konstantní čas v sekundách (volitelné)
- `is_cooperation`: Je to kooperace? (volitelné)

**Příklad:**
```python
FEATURE_FIELDS = {
    "od_rough": {
        "name": "Vnější hrubování",
        "icon": "🔄",
        "category": "turning",
        "fields": ["Ds", "Df", "length"],
        "cutting": ["Vc", "f", "Ap"],
        "defaults": {}
    },
    "mill_pocket": {
        "name": "Kapsa",
        "icon": "⬜",
        "category": "milling",
        "fields": ["pocket_length", "pocket_width", "depth", "corner_radius"],
        "cutting": ["Vc", "fz", "Ap"],
        "defaults": {"corner_radius": 5.0}
    },
    "wash": {
        "name": "Mytí",
        "icon": "🚿",
        "category": "logistics",
        "fields": [],
        "cutting": [],
        "defaults": {},
        "constant_time": 15.0
    },
    "heat_treat": {
        "name": "Tepelné zpracování",
        "icon": "🔥",
        "category": "cooperation",
        "fields": [],
        "cutting": [],
        "defaults": {},
        "is_cooperation": True
    },
}
```

---

## 10. API ENDPOINTY

### 10.1 Parts
```
GET    /api/parts              # Seznam dílů
POST   /api/parts              # Vytvořit díl
GET    /api/parts/{id}         # Detail dílu
PUT    /api/parts/{id}         # Aktualizovat díl
DELETE /api/parts/{id}         # Smazat díl
```

### 10.2 Operations
```
GET    /api/parts/{id}/operations      # Operace dílu
POST   /api/parts/{id}/operations      # Vytvořit operaci
GET    /api/operations/{id}            # Detail operace
PUT    /api/operations/{id}            # Aktualizovat operaci
DELETE /api/operations/{id}            # Smazat operaci
POST   /api/operations/{id}/change-mode  # Změnit režim (low/mid/high)
```

### 10.3 Features
```
GET    /api/operations/{id}/features   # Kroky operace
POST   /api/operations/{id}/features   # Vytvořit krok
GET    /api/features/{id}              # Detail kroku
PUT    /api/features/{id}              # Aktualizovat krok
DELETE /api/features/{id}              # Smazat krok
```

### 10.4 Batches
```
GET    /api/parts/{id}/batches         # Dávky dílu
POST   /api/parts/{id}/batches         # Vytvořit dávku
GET    /api/parts/{id}/all-batch-prices  # Všechny ceny (cenový ribbon)
PUT    /api/batches/{id}               # Aktualizovat dávku
DELETE /api/batches/{id}               # Smazat dávku
```

### 10.5 Referenční data
```
GET    /api/data/machines              # Seznam strojů
GET    /api/data/materials             # Materiálové skupiny
GET    /api/data/material-prices       # Ceny materiálů
GET    /api/data/operation-types       # Typy operací s vzorci
GET    /api/data/cooperations          # Typy kooperací
```

---

## 11. FRONTEND - UI KOMPONENTY

### 11.1 Hlavní obrazovky
1. **Seznam dílů** - tabulka s filtrem a vyhledáváním
2. **Detail dílu** - přehled operací a cen
3. **Editace dílu** - hlavní pracovní plocha
4. **Správa dat** - stroje, materiály, ceny

### 11.2 Editace dílu (hlavní UI)
```
┌─────────────────────────────────────────────────────────────┐
│ HEADER: Číslo dílu, Název, Materiál, [ULOŽIT]               │
├─────────────────────────────────────┬───────────────────────┤
│ LEVÝ PANEL (70%)                    │ PRAVÝ PANEL (30%)     │
│                                     │                       │
│ ┌─────────────────────────────────┐ │ ┌───────────────────┐ │
│ │ OPERACE 10 - Soustružení       │ │ │ CENOVÝ RIBBON     │ │
│ │ [LOW] [MID] [HIGH]             │ │ │                   │ │
│ │ Stroj: NLX 2000                │ │ │  1ks:  850 Kč    │ │
│ │ Čas: 12.5 min                  │ │ │ 10ks:  420 Kč    │ │
│ │                                │ │ │ 50ks:  320 Kč    │ │
│ │ ├── Zarovnání čela  [2.1s]     │ │ │ 100ks: 290 Kč    │ │
│ │ ├── OD Hrubování    [45.2s]    │ │ │                   │ │
│ │ ├── OD Dokončení    [18.3s]    │ │ └───────────────────┘ │
│ │ └── Upíchnutí       [8.5s]     │ │                       │
│ │                                │ │ ┌───────────────────┐ │
│ │ [+ PŘIDAT KROK]                │ │ │ ROZPAD CENY       │ │
│ └─────────────────────────────────┘ │ │                   │ │
│                                     │ │ Materiál: 45 Kč   │ │
│ ┌─────────────────────────────────┐ │ │ Výroba: 180 Kč    │ │
│ │ OPERACE 20 - Frézování         │ │ │ Seřízení: 85 Kč   │ │
│ │ ...                            │ │ │ ─────────────     │ │
│ └─────────────────────────────────┘ │ │ CELKEM: 310 Kč    │ │
│                                     │ └───────────────────┘ │
│ [+ PŘIDAT OPERACI]                  │                       │
└─────────────────────────────────────┴───────────────────────┘
```

### 11.3 Barevné téma
**Tmavé téma (doporučeno):**
```css
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-card: #1f2937;
    --text-primary: #e5e5e5;
    --text-secondary: #9ca3af;
    --accent: #3b82f6;
    --success: #22c55e;
    --warning: #f59e0b;
    --error: #ef4444;
}
```

---

## 12. DATOVÉ SOUBORY

### 12.1 SQLite databáze
```
gestima.db
├── parts
├── operations
├── features
├── batches
└── machines (volitelně)
```

### 12.2 Excel referenční data
```
data/
├── operations_base.xlsx       # Základní řezné podmínky
├── material_coefficients.xlsx # Materiálové koeficienty
├── material_prices.xlsx       # Ceny materiálů za kg
├── machines.xlsx              # Seznam strojů
├── cooperations.xlsx          # Typy kooperací
└── tools.xlsx                 # Nástroje (volitelné)
```

---

## 13. PRINCIP: JEDEN ZDROJ PRAVDY

```
API POČÍTÁ → DB UKLÁDÁ → UI ZOBRAZUJE
```

**NIKDY:**
- Nepočítat stejnou hodnotu na více místech
- Nepočítat v JavaScriptu co počítá backend
- Neukládat odvozené hodnoty (počítat při zobrazení)

**VŽDY:**
- Backend počítá a vrací hotové hodnoty
- Frontend jen zobrazuje co dostane
- Po změně dat zavolat API a aktualizovat celé UI

---

## 14. MIGRACE DAT

### 14.1 Skript pro migraci
```python
import pandas as pd
import sqlite3

# 1. Načíst z Excel
parts = pd.read_excel('data/parts.xlsx')
operations = pd.read_excel('data/operations.xlsx')
features = pd.read_excel('data/features.xlsx')
batches = pd.read_excel('data/batches.xlsx')

# 2. Vyčistit data
# - Odstranit deprecated sloupce
# - Přejmenovat sloupce
# - Doplnit chybějící hodnoty

# 3. Uložit do SQLite
conn = sqlite3.connect('gestima.db')
parts.to_sql('parts', conn, if_exists='replace', index=False)
operations.to_sql('operations', conn, if_exists='replace', index=False)
features.to_sql('features', conn, if_exists='replace', index=False)
batches.to_sql('batches', conn, if_exists='replace', index=False)
conn.close()
```

---

## 15. CO NEIMPLEMENTOVAT

**Odstraněno z původního projektu:**
- ❌ AI Vision (analýza výkresů)
- ❌ Batch Optimizer (automatický výběr stroje)
- ❌ MasterOperation, BatchOperation (legacy modely)
- ❌ is_variable (všechny operace jsou stejné pro všechny dávky)
- ❌ TPVVariant (varianty technologického postupu)

---

## 16. DOPORUČENÝ POSTUP IMPLEMENTACE

### Fáze 1: Backend základ (2-3 dny)
1. FastAPI skeleton
2. SQLAlchemy modely
3. SQLite databáze
4. CRUD endpointy pro Part, Operation, Feature, Batch

### Fáze 2: Výpočetní engine (2-3 dny)
1. `feature_calculator.py` - výpočet časů
2. `cutting_conditions.py` - řezné podmínky
3. `price_calculator.py` - cenová kalkulace
4. Excel reader pro referenční data

### Fáze 3: Frontend SPA (5-7 dní)
1. React/Vue projekt
2. API client
3. Seznam dílů
4. Editace dílu (hlavní UI)
5. Cenový ribbon
6. Správa dat

### Fáze 4: Testování + dokončení (2-3 dny)
1. End-to-end testování
2. Opravy bugů
3. Optimalizace UI

---

*Dokument vygenerován 2026-01-22 z Kalkulator3000 v9.2*
