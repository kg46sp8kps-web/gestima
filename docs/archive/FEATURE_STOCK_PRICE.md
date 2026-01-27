# Live výpočet ceny polotovaru

**Datum:** 2026-01-23  
**Status:** ✅ Implementováno

---

## 📋 Popis

Při zadávání nového dílu se **automaticky počítá cena polotovaru** na základě:
- Typu polotovaru (tyč, trubka, přířez, plech, odlitek)
- Rozměrů (průměr, délka, šířka, výška)
- Materiálové skupiny (konstrukcní ocel, nerez, hliník...)

Uživatel vidí **live update**:
- Hmotnost [kg]
- Cena za kg [Kč/kg]
- Celková cena polotovaru [Kč]

---

## 🎯 Implementace

### Backend

#### 1. Rozšířená funkce `calculate_material_cost()`

**Soubor:** `app/services/price_calculator.py`

```python
async def calculate_material_cost(
    stock_diameter: float,
    stock_length: float,
    material_group: str,
    stock_diameter_inner: float = 0,
    stock_type: str = "tyc",
    stock_width: float = 0,
    stock_height: float = 0,
) -> MaterialCost
```

**Podporované typy:**
- `tyc` - plná tyč: π × r² × délka
- `trubka` - dutá trubka: π × (r_outer² - r_inner²) × délka
- `prizez` - přířez (kvádr): délka × šířka × výška
- `plech` - plech: délka × šířka × tloušťka
- `odlitek` - jako tyč

#### 2. API Endpoint

**Endpoint:** `GET /api/data/stock-price`

**Query parametry:**
- `stock_type` (required): tyc, trubka, prizez, plech, odlitek
- `material_group` (required): konstrukcni_ocel, nerez_austeniticka, ...
- `stock_diameter` (optional): průměr [mm]
- `stock_length` (optional): délka [mm]
- `stock_diameter_inner` (optional): vnitřní průměr pro trubku [mm]
- `stock_width` (optional): šířka pro přířez/plech [mm]
- `stock_height` (optional): výška/tloušťka [mm]

**Response:**
```json
{
    "volume_mm3": 196350.0,
    "weight_kg": 1.541,
    "price_per_kg": 30.0,
    "cost": 46.24
}
```

**Příklady:**
```bash
# Tyč ø50 × 100mm (konstrukcní ocel)
GET /api/data/stock-price?stock_type=tyc&material_group=konstrukcni_ocel&stock_diameter=50&stock_length=100

# Trubka ø50/40 × 100mm
GET /api/data/stock-price?stock_type=trubka&material_group=konstrukcni_ocel&stock_diameter=50&stock_diameter_inner=40&stock_length=100

# Přířez 100×50×30mm
GET /api/data/stock-price?stock_type=prizez&material_group=konstrukcni_ocel&stock_length=100&stock_width=50&stock_height=30
```

---

### Frontend

#### 1. Formulář pro nový díl

**Soubor:** `app/templates/parts/new.html`

**Změny:**
- Přidán `@input="updateStockPrice"` na všechna pole rozměrů
- Přidán `@change="updateStockPrice"` na dropdown materiálu a typu polotovaru
- Přidán vizuální box s live cenou (zobrazuje se pouze když `stockPrice.cost > 0`)

**Live cena box:**
```html
<div x-show="stockPrice.cost > 0" class="mt-4 p-4 bg-gray-700 rounded-lg">
    <div class="text-sm font-semibold mb-2">💰 Cena polotovaru</div>
    <div class="grid grid-cols-3 gap-4">
        <div>
            <div class="text-xs text-gray-400">Hmotnost</div>
            <div x-text="stockPrice.weight_kg.toFixed(3) + ' kg'"></div>
        </div>
        <div>
            <div class="text-xs text-gray-400">Cena/kg</div>
            <div x-text="stockPrice.price_per_kg.toFixed(0) + ' Kč'"></div>
        </div>
        <div>
            <div class="text-xs text-gray-400">Celkem</div>
            <div class="text-lg font-bold text-blue-400" 
                 x-text="stockPrice.cost.toFixed(0) + ' Kč'"></div>
        </div>
    </div>
</div>
```

#### 2. JavaScript logika

**Funkce:**
```javascript
async updateStockPrice() {
    // Debounce - čekej 300ms po posledním inputu
    clearTimeout(this.updateTimeout);
    this.updateTimeout = setTimeout(async () => {
        await this.fetchStockPrice();
    }, 300);
}

async fetchStockPrice() {
    const params = new URLSearchParams({
        stock_type: this.form.stock_type,
        material_group: this.form.material_group,
        stock_diameter: this.form.stock_diameter || 0,
        stock_length: this.form.stock_length || 0,
        stock_diameter_inner: this.form.stock_diameter_inner || 0,
        stock_width: this.form.stock_width || 0,
        stock_height: this.form.stock_height || 0,
    });
    
    const response = await fetch(`/api/data/stock-price?${params}`);
    if (response.ok) {
        this.stockPrice = await response.json();
    }
}
```

**Debouncing:**
- Výpočet se nespustí okamžitě při každém stisku klávesy
- Čeká se 300ms po posledním inputu
- Šetří API volání a zlepšuje UX

---

## 🧪 Testy

**Soubor:** `tests/test_pricing.py`

**Nové testy:**
1. `test_material_cost_rod_steel` - tyč ø50 × 100mm
2. `test_material_cost_tube` - trubka ø50/40 × 100mm
3. `test_material_cost_billet` - přířez 100×50×30mm
4. `test_material_cost_stainless` - nerez tyč (jiná hustota/cena)

**Spuštění:**
```bash
pytest tests/test_pricing.py -v
```

**Výsledek:**
```
✅ 5 passed in 0.08s
```

---

## 📊 Příklad výpočtu

### Tyč ø50 × 100mm (konstrukcní ocel)

**Vstup:**
- Typ: tyč
- Průměr: 50 mm
- Délka: 100 mm
- Materiál: konstrukcní ocel

**Výpočet:**
```
Objem = π × (25)² × 100 = 196 350 mm³
Objem = 0.196 dm³
Hmotnost = 0.196 × 7.85 = 1.541 kg
Cena = 1.541 × 30 = 46.24 Kč
```

**Výstup:**
```json
{
    "volume_mm3": 196350.0,
    "weight_kg": 1.541,
    "price_per_kg": 30.0,
    "cost": 46.24
}
```

---

## 🎨 UX Flow

1. **Uživatel vybere typ polotovaru** → API volání
2. **Uživatel zadá rozměry** → Debounce 300ms → API volání
3. **Uživatel změní materiál** → API volání
4. **Box s cenou se zobrazí** (pouze když cost > 0)
5. **Live update** při každé změně

---

## 🔮 Budoucí rozšíření (KROK 2)

### Databáze polotovarů

**Nový model:**
```python
class StockItem(Base):
    id = Column(Integer, primary_key=True)
    stock_type = Column(Enum(StockType))
    material_group = Column(String)
    material_name = Column(String)  # "1.4301"
    
    diameter = Column(Float)
    diameter_inner = Column(Float)
    length = Column(Float)
    
    price_per_kg = Column(Float)
    supplier = Column(String)
    in_stock = Column(Boolean)
```

### Live filtrování

**Endpoint:**
```
GET /api/stock-items/search?q=1.4301+D5
```

**Response:**
```json
[
    {
        "id": 1,
        "display": "Tyč 1.4301 D50 × 3000mm",
        "stock_type": "tyc",
        "diameter": 50,
        "length": 3000,
        "price": 450.00,
        "in_stock": true
    },
    {
        "id": 2,
        "display": "Tyč 1.4301 D55 × 3000mm",
        "stock_type": "tyc",
        "diameter": 55,
        "length": 3000,
        "price": 520.00,
        "in_stock": false
    }
]
```

**UI:**
```
┌─────────────────────────────────────┐
│ Materiál: [1.4301 D5_________]      │
│                                     │
│ ✓ Tyč 1.4301 D50 × 3000mm (450 Kč) │
│   Tyč 1.4301 D55 × 3000mm (520 Kč) │
│   Tyč 1.4301 D60 × 3000mm (610 Kč) │
└─────────────────────────────────────┘
```

---

## ✅ Checklist dokončení

- [x] Rozšířit `calculate_material_cost()` pro všechny typy
- [x] API endpoint `/api/data/stock-price`
- [x] Frontend live update s debouncing
- [x] Vizuální box s cenou
- [x] Testy pro tyč, trubku, přířez
- [x] Dokumentace

---

## 📝 Poznámky k implementaci

### Materiály v databázi
- **Seed script:** `scripts/seed_materials.py`
- **15 materiálů** s reálnými cenami (28-337 Kč/kg)
- **Dynamické načítání:** Dropdown materiálů se plní z API `/api/data/materials`
- **Žádné hardcoded hodnoty** - vše z databáze

### Budoucí filtrování
- Tyč → zobrazit jen `*_kruhova`, `*_plocha`
- Trubka → zobrazit jen `*_trubka`
- Přířez/Plech → zobrazit jen `*_desky`

---

**Implementoval:** AI Assistant  
**Datum:** 2026-01-23  
**Verze:** GESTIMA 1.0
