"""GESTIMA - Konfigurace typů kroků"""

FEATURE_FIELDS = {
    # === SOUSTRUŽENÍ ===
    "face": {
        "name": "Zarovnání čela",
        "icon": "🔵",
        "category": "turning",
        "fields": ["from_diameter", "depth"],
        "cutting": ["Vc", "f", "Ap"],
    },
    "od_rough": {
        "name": "Vnější hrubování",
        "icon": "🔄",
        "category": "turning",
        "fields": ["from_diameter", "to_diameter", "length"],
        "cutting": ["Vc", "f", "Ap"],
    },
    "od_finish": {
        "name": "Vnější dokončení",
        "icon": "✨",
        "category": "turning",
        "fields": ["from_diameter", "to_diameter", "length"],
        "cutting": ["Vc", "f", "Ap"],
    },
    "id_rough": {
        "name": "Vnitřní hrubování",
        "icon": "🕳️",
        "category": "turning",
        "fields": ["from_diameter", "to_diameter", "length"],
        "cutting": ["Vc", "f", "Ap"],
    },
    "id_finish": {
        "name": "Vnitřní dokončení",
        "icon": "💎",
        "category": "turning",
        "fields": ["from_diameter", "to_diameter", "length"],
        "cutting": ["Vc", "f", "Ap"],
    },
    "thread_od": {
        "name": "Vnější závit",
        "icon": "🔩",
        "category": "turning",
        "fields": ["from_diameter", "length", "thread_pitch"],
        "cutting": ["Vc"],
    },
    "thread_id": {
        "name": "Vnitřní závit",
        "icon": "🔩",
        "category": "turning",
        "fields": ["from_diameter", "length", "thread_pitch"],
        "cutting": ["Vc"],
    },
    "groove_od": {
        "name": "Vnější zápich",
        "icon": "➖",
        "category": "turning",
        "fields": ["from_diameter", "to_diameter", "width"],
        "cutting": ["Vc", "f"],
    },
    "parting": {
        "name": "Upíchnutí",
        "icon": "✂️",
        "category": "turning",
        "fields": ["from_diameter", "blade_width"],
        "cutting": ["Vc", "f"],
    },
    "chamfer": {
        "name": "Sražení hrany",
        "icon": "📐",
        "category": "turning",
        "fields": ["width"],
        "cutting": [],
        "constant_time": 1.0,
    },
    
    # === VRTÁNÍ ===
    "center_drill": {
        "name": "Navrtání",
        "icon": "🎯",
        "category": "drilling",
        "fields": ["to_diameter", "depth"],
        "cutting": ["Vc", "f"],
    },
    "drill": {
        "name": "Vrtání",
        "icon": "🔘",
        "category": "drilling",
        "fields": ["to_diameter", "depth"],
        "cutting": ["Vc", "f"],
    },
    "drill_deep": {
        "name": "Hluboké vrtání",
        "icon": "🔘",
        "category": "drilling",
        "fields": ["to_diameter", "depth"],
        "cutting": ["Vc", "f"],
    },
    "tap": {
        "name": "Závitování",
        "icon": "🔩",
        "category": "drilling",
        "fields": ["to_diameter", "depth", "thread_pitch"],
        "cutting": ["Vc"],
    },
    
    # === FRÉZOVÁNÍ ===
    "mill_face": {
        "name": "Frézování čela",
        "icon": "⬜",
        "category": "milling",
        "fields": ["length", "pocket_width", "depth"],
        "cutting": ["Vc", "fz", "Ap"],
    },
    "mill_pocket": {
        "name": "Kapsa",
        "icon": "⬜",
        "category": "milling",
        "fields": ["pocket_length", "pocket_width", "depth", "corner_radius"],
        "cutting": ["Vc", "fz", "Ap"],
    },
    "mill_slot": {
        "name": "Drážka",
        "icon": "═",
        "category": "milling",
        "fields": ["length", "width", "depth"],
        "cutting": ["Vc", "fz", "Ap"],
    },
    "mill_drill": {
        "name": "Vrtání",
        "icon": "🔘",
        "category": "milling",
        "fields": ["to_diameter", "depth", "count"],
        "cutting": ["Vc", "f"],
    },
    
    # === BROUŠENÍ ===
    "grind_od": {
        "name": "Broušení vnější",
        "icon": "🔵",
        "category": "grinding",
        "fields": ["from_diameter", "to_diameter", "length"],
        "cutting": ["Vc", "f", "Ap"],
    },
    
    # === LOGISTIKA ===
    "wash": {
        "name": "Mytí",
        "icon": "🚿",
        "category": "logistics",
        "fields": [],
        "cutting": [],
        "constant_time": 15.0,
    },
    "inspect": {
        "name": "Kontrola",
        "icon": "🔍",
        "category": "logistics",
        "fields": [],
        "cutting": [],
        "constant_time": 30.0,
    },
    "pack": {
        "name": "Balení",
        "icon": "📦",
        "category": "logistics",
        "fields": [],
        "cutting": [],
        "constant_time": 10.0,
    },
}
