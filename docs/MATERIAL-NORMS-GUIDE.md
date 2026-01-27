# Material Norms - Uživatelská příručka

**Verze:** 1.0 | **Datum:** 2026-01-26

---

## Přehled

**MaterialNorm** je převodní tabulka pro automatické přiřazení materiálových kategorií podle označení normy.

**Problém který řeší:**
- Máte 4000-5000 polotovarů s různými označeními (1.0503, C45, 12050, AISI 1045)
- Všechna označení popisují **stejný materiál** → stejná hustota, řezné podmínky
- Manuální vyplnění kategorie pro každou položku = neefektivní

**Řešení:**
- Převodní tabulka: **norma → MaterialGroup (kategorie)**
- Systém automaticky najde normu a přiřadí správnou kategorii

---

## Koncept

### 4 sloupce norem

Každý řádek v tabulce = **převodní záznam** s 4 sloupci:

| W.Nr | EN ISO | ČSN | AISI | → Kategorie |
|------|--------|-----|------|-------------|
| 1.0503 | C45 | 12050 | 1045 | Ocel konstrukční (C45) |
| 1.4301 | X5CrNi18-10 | 17240 | 304 | Nerez (304) |
| - | 6060 | - | - | Hliník (6060) |

**Význam sloupců:**
- **W.Nr** (Werkstoffnummer) - Německé materiálové číslo (např. 1.4301, 1.0503)
- **EN ISO** - Evropské označení podle EN standardu (např. C45, X5CrNi18-10)
- **ČSN** - České označení podle ČSN normy (např. 12050, 11109)
- **AISI** - Americké označení podle AISI (např. 304, 1045, 4140)

**Pravidla:**
- ✅ Min. 1 sloupec musí být vyplněn (ostatní mohou být prázdné)
- ✅ Case-insensitive vyhledávání (c45 = C45 = C45)
- ✅ Hledání napříč **všemi 4 sloupci** (OR logika)

---

## Jak to funguje

### User Workflow

```
1. Uživatel vytváří MaterialItem:
   Input: code = "D20 11109" (nebo "1.0036-HR005w05-T")
         shape = "round_bar"

2. Systém extrahuje normu:
   "D20 11109" → "11109"
   "1.0036-HR005w05-T" → "1.0036"

3. Lookup v MaterialNorm tabulce:
   Hledá "11109" v W.Nr? ❌
   Hledá "11109" v EN ISO? ❌
   Hledá "11109" v ČSN? ✅ Našel!
   → MaterialGroup: "Ocel konstrukční (automatová)" (density: 7.85 kg/dm³)

4. Auto-assign PriceCategory:
   MaterialGroup: "Ocel konstrukční" + Shape: "round_bar"
   → PriceCategory: "OCEL-KRUHOVA" (150 Kč/kg pro 0-10 kg)

5. Result:
   MaterialItem vytvořen s:
   - material_group_id → Ocel konstrukční
   - price_category_id → OCEL-KRUHOVA
   - density → 7.85 kg/dm³
```

---

## Admin konzole

### Přístup

1. Přihlaste se jako **Admin**
2. Dashboard → **⚙️ Nastavení** (fialová dlaždice)
3. Tab: **📋 Material Norms**

URL: `/admin/material-norms`

**Oprávnění:** Pouze Admin role

---

### Tabulka norem

Zobrazení:
```
┌──────────┬────────────────┬────────┬────────┬────────────────────┬────────────┬────────┐
│ W.Nr     │ EN ISO         │ ČSN    │ AISI   │ Kategorie          │ Hustota    │ Akce   │
├──────────┼────────────────┼────────┼────────┼────────────────────┼────────────┼────────┤
│ 1.0503   │ C45            │ 12050  │ 1045   │ Ocel konstrukční   │ 7.85 kg/dm³│ Upravit│
│ 1.4301   │ X5CrNi18-10    │ 17240  │ 304    │ Nerez (304)        │ 7.90 kg/dm³│ Upravit│
│ 1.0715   │ 11SMnPb30      │ 11109  │ -      │ Ocel konstrukční   │ 7.85 kg/dm³│ Upravit│
└──────────┴────────────────┴────────┴────────┴────────────────────┴────────────┴────────┘
```

**Funkce:**
- **Vyhledávání** - 🔍 Search box (hledá napříč všemi 4 sloupci, 300ms debounce)
- **Přidat normu** - ➕ Tlačítko vpravo nahoře
- **Upravit** - Tlačítko v řádku
- **Info box** - Vysvětlení jak převodní tabulka funguje

---

### Přidání nové normy

1. Klikni **➕ Přidat normu**
2. Vyplň min. 1 sloupec (doporučeno vyplnit všechny známé)
3. Vyber **Kategorii materiálu** (povinné)
4. Přidej poznámku (volitelné)
5. **Uložit**

**Příklad:**
```
W.Nr:      1.7225
EN ISO:    42CrMo4
ČSN:       15142
AISI:      4140
Kategorie: Ocel legovaná (42CrMo4)
Poznámka:  Ocel legovaná chromem a molybdenem
```

**Validace:**
- ❌ Všechny 4 sloupce prázdné → chyba "Musíš vyplnit aspoň jednu normu"
- ❌ Kategorie nevybrána → chyba "Pole je povinné"
- ✅ Min. 1 sloupec + kategorie → úspěch

---

### Úprava existující normy

1. Najdi normu v tabulce (použij search)
2. Klikni **Upravit** v řádku
3. Modal se nahraje s existujícími daty
4. Uprav pole
5. **Uložit**

**Optimistic Locking:**
- Pokud někdo jiný upravil normu mezitím → chyba "Norma byla změněna jiným uživatelem"
- Obnovte stránku a zkuste znovu

---

## Seed data

### Předvyplněné normy

Systém je dodáván s **~22 běžnými normami**:

**Ocel konstrukční/automatová:**
- 1.0715 | 11SMnPb30 | 11109 | - → Ocel konstrukční (automatová)
- 1.0038 | S235JR | - | - → Ocel konstrukční (S235)
- 1.0503 | C45 | 12050 | 1045 → Ocel konstrukční (C45)
- 1.1191 | C45E | - | - → Ocel konstrukční (C45)

**Ocel legovaná:**
- 1.7225 | 42CrMo4 | 15142 | 4140 → Ocel legovaná (42CrMo4)
- 1.7131 | 16MnCr5 | 14220 | 5115 → Ocel legovaná (16MnCr5)

**Nerez:**
- 1.4301 | X5CrNi18-10 | 17240 | 304 → Nerez (304)
- 1.4303 | X5CrNi18-9 | - | 304L → Nerez (304)
- 1.4404 | X2CrNiMo17-12-2 | 17350 | 316L → Nerez (316L)
- 1.4401 | X5CrNiMo17-12-2 | - | 316 → Nerez (316L)

**Hliník:**
- - | 6060 | - | - → Hliník (6060)
- - | EN AW-6060 | - | - → Hliník (6060)
- - | 7075 | - | - → Hliník (7075 dural)
- - | EN AW-7075 | - | - → Hliník (7075 dural)

**Mosaz:**
- 2.0321 | CuZn37 | - | - → Mosaz (CuZn37)
- - | CW508L | - | C27400 → Mosaz (CuZn37)
- 2.0401 | CuZn39Pb3 | - | C38500 → Mosaz (automatová)
- - | CW614N | - | - → Mosaz (automatová)

**Plasty:**
- - | PA6 | - | - → Plasty (PA6)
- - | POM | - | - → Plasty (POM)
- - | POM-C | - | - → Plasty (POM)
- - | POM-H | - | - → Plasty (POM)

**Seed script:** `scripts/seed_material_norms.py`

### Spuštění seed scriptu

```bash
# Spustit seed manuálně
python scripts/seed_material_norms.py

# Nebo při inicializaci databáze
python gestima.py setup
```

---

## Kategorie materiálů

### MaterialGroups (13 kategorií)

| Code | Název | Hustota (kg/dm³) |
|------|-------|------------------|
| 11xxx | Ocel konstrukční (automatová) | 7.85 |
| S235 | Ocel konstrukční (S235) | 7.85 |
| C45 | Ocel konstrukční (C45) | 7.85 |
| 42CrMo4 | Ocel legovaná (42CrMo4) | 7.85 |
| 16MnCr5 | Ocel legovaná (16MnCr5) | 7.80 |
| X5CrNi18-10 | Nerez (304) | 7.90 |
| X2CrNiMo17-12-2 | Nerez (316L) | 8.00 |
| 6060 | Hliník (6060) | 2.70 |
| 7075 | Hliník (7075 dural) | 2.81 |
| CuZn37 | Mosaz (CuZn37) | 8.40 |
| CuZn39Pb3 | Mosaz (automatová) | 8.50 |
| PA6 | Plasty (PA6) | 1.14 |
| POM | Plasty (POM) | 1.42 |

**Význam:**
- **Hustota** - používá se pro výpočet váhy polotovaru
- **Název** - zobrazuje se v UI (user-friendly)
- **Code** - interní kód (používá se v API)

---

## Use Cases

### 1. Nový díl s automatickým přiřazením

**Scénář:** Vytvářím díl z tyče ⌀20 mm, materiál C45

```
1. Otevřu formulář pro nový Part
2. MaterialItem dropdown:
   - Zadám "C45" → autocomplete najde: "C45 ⌀20 mm - tyč kruhová ocel"
   - Nebo zadám "12050" → autocomplete najde stejnou položku
3. Vyberu "C45 ⌀20 mm"
4. Systém automaticky:
   - MaterialGroup: "Ocel konstrukční (C45)" (7.85 kg/dm³)
   - PriceCategory: "OCEL-KRUHOVA" (150 Kč/kg)
5. Zadám rozměry dílu (stock_diameter, stock_length)
6. Systém vypočítá:
   - Objem = π × (diameter/2)² × length
   - Váha = objem × 7.85 kg/dm³
   - Cena = váha × 150 Kč/kg
```

**Výhody:**
- ✅ Nemusíte vybírat kategorii manuálně
- ✅ Automatická hustota pro výpočty
- ✅ Automatická cenová kategorie

---

### 2. Bulk import 4000 položek

**Scénář:** Máte Excel s 4000 polotovary, chcete importovat

**Krok 1: Rozšíření převodní tabulky**
```
1. Export Excelu do CSV (sloupec: Norma)
2. Získat unikátní normy: =UNIQUE(A:A)
3. Pro každou normu najít správnou kategorii
4. Importovat přes Admin konzolu (nebo bulk SQL insert)
```

**Krok 2: Import položek**
```
FOR EACH row in Excel:
    code = row["Označení"]      # "D20 11109"
    shape = row["Tvar"]          # "round_bar"
    diameter = row["Průměr"]     # 20

    # Auto-assign
    norm = extract_norm(code)    # "11109"
    group = lookup_norm(norm)    # MaterialGroup ID
    category = get_price_category(group, shape)

    # Create MaterialItem
    INSERT INTO material_items (code, shape, diameter, material_group_id, price_category_id)
```

**Alternativa: Python script**
```python
import pandas as pd
from app.services.material_mapping import auto_assign_categories

async def bulk_import(excel_file):
    df = pd.read_excel(excel_file)

    for _, row in df.iterrows():
        code = row["Označení"]
        shape = StockShape(row["Tvar"])

        # Extract norm (např. "D20 11109" → "11109")
        norm = extract_norm(code)

        # Auto-assign
        group, category = await auto_assign_categories(db, norm, shape)

        # Create MaterialItem
        item = MaterialItem(
            code=code,
            shape=shape,
            diameter=row["Průměr"],
            material_group_id=group.id,
            price_category_id=category.id
        )
        db.add(item)

    await db.commit()
```

---

### 3. Web scraping (budoucí rozšíření)

**Scénář:** Automatické doplňování aliasů z veřejných databází

**Zdroje:**
- steelnumber.com (EN, DIN, AISI, ČSN převody)
- matweb.com (materiálové vlastnosti)
- Wikipedia (normy, aliasy)

**Implementace:**
```python
async def scrape_material_norm(w_nr: str):
    """
    Scrape material norm from steelnumber.com
    """
    url = f"https://www.steelnumber.com/en/steel_composition_eu.php?name_id={w_nr}"
    response = await httpx.get(url)

    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract norms
    en_iso = soup.find("td", text="EN").find_next("td").text
    csn = soup.find("td", text="ČSN").find_next("td").text
    aisi = soup.find("td", text="AISI").find_next("td").text

    return {
        "w_nr": w_nr,
        "en_iso": en_iso,
        "csn": csn,
        "aisi": aisi
    }
```

---

## API Reference

### Endpoints

**Admin API:**
```
GET    /admin/material-norms              # Stránka s tabulkou
GET    /api/material-groups                # List kategorií (pro dropdown)
GET    /api/material-norms/search?q={q}   # Search norem
POST   /api/material-norms                 # Vytvořit normu
PUT    /api/material-norms/{id}            # Upravit normu
DELETE /api/material-norms/{id}            # Smazat normu (soft delete)
```

**Service Functions:**
```python
from app.services.material_mapping import auto_assign_group, auto_assign_categories

# Auto-assign MaterialGroup
group = await auto_assign_group(db, norm_code="C45")
# → MaterialGroup(name="Ocel konstrukční (C45)", density=7.85)

# Auto-assign MaterialGroup + PriceCategory
group, category = await auto_assign_categories(db, norm_code="C45", shape=StockShape.ROUND_BAR)
# → (MaterialGroup, MaterialPriceCategory("OCEL-KRUHOVA"))
```

---

## FAQ

### Q: Můžu mít víc řádků pro stejnou kategorii?
**A:** Ano! Příklad:
```
1.0503  | C45      | 12050 | 1045 → Ocel konstrukční (C45)
1.1191  | C45E     | -     | -    → Ocel konstrukční (C45)
```
Obě normy vedou na stejnou kategorii (C45).

---

### Q: Co když norma není v tabulce?
**A:** Systém vyhodí chybu "Neznámá norma: {kod}". Musíte přidat normu do tabulky přes Admin konzolu.

---

### Q: Můžu změnit kategorii u existující normy?
**A:** Ano, klikněte "Upravit" a vyberte jinou kategorii. **Pozor:** Změna ovlivní všechny MaterialItems které používají tuto normu!

---

### Q: Co když chci smazat normu?
**A:** API endpoint `DELETE /api/material-norms/{id}` provede **soft delete** (nastaví `deleted_at`). Norma zmizí z tabulky, ale zůstane v DB pro audit.

---

### Q: Jak vím která kategorie má jakou cenu?
**A:** Přejděte na tab **⚙️ Systémové nastavení** v Admin konzole. Tam vidíte cenové koeficienty. Pro detailní ceny materiálů viz `/admin/price-categories`.

---

### Q: Podporuje systém custom formát "1.0036-HR005w05-T"?
**A:** Ano! Systém extrahuje normu z kódu:
- "1.0036-HR005w05-T" → "1.0036" (první část před pomlčkou)
- "D20 11109" → "11109" (druhá část za mezerou)

**Custom extrakce:** Pokud máte specifický formát, upravte funkci `extract_norm()` v `app/services/material_mapping.py`.

---

## Troubleshooting

### Norma se nenašla
**Symptom:** Chyba "Neznámá norma: {kod}"

**Řešení:**
1. Zkontrolujte překlepy (C45 vs c45 - system je case-insensitive)
2. Ověřte že norma existuje v tabulce (Admin konzole → Material Norms)
3. Přidejte normu pokud chybí

---

### Edit vytvoří nový záznam místo update
**Symptom:** Po kliknutí "Upravit" se vytvoří duplikát

**Řešení:** ✅ OPRAVENO (2026-01-26)
- Bug fix: Alpine.js events pro komunikaci mezi components
- Pokud problém přetrvává: Hard refresh prohlížeče (Ctrl+Shift+R)

---

### Form se nenahral s daty
**Symptom:** Modal se otevře prázdný při editaci

**Řešení:** ✅ OPRAVENO (2026-01-26)
- Bug fix: Event listener `'edit-material-norm'` nyní volá `openEdit()`
- Pokud problém přetrvává: Zkontrolujte konzoli prohlížeče (F12) na JS errory

---

### Optimistic locking error
**Symptom:** "Norma byla změněna jiným uživatelem"

**Řešení:**
1. Obnovte stránku (F5)
2. Otevřete edit znovu (data se nahrají s aktuální `version`)
3. Proveďte změny
4. Uložte

**Důvod:** Někdo jiný upravil normu mezi vaším otevřením a uložením.

---

## Odkazy

**Dokumentace:**
- [ADR-015: Material Norm Auto-Mapping](../ADR/015-material-norm-mapping.md) - Architektonické rozhodnutí
- [ADR-011: Material Hierarchy](../ADR/011-material-hierarchy.md) - Two-tier systém (Group vs Item)
- [ADR-014: Material Price Tiers](../ADR/014-material-price-tiers.md) - Cenové tabulky

**Kód:**
- [app/models/material_norm.py](../../app/models/material_norm.py) - DB model + schemas
- [app/services/material_mapping.py](../../app/services/material_mapping.py) - Auto-assign logika
- [app/routers/admin_router.py](../../app/routers/admin_router.py) - Admin API
- [scripts/seed_material_norms.py](../../scripts/seed_material_norms.py) - Seed data

**Externí zdroje:**
- [steelnumber.com](https://www.steelnumber.com) - Mezinárodní databáze materiálů
- [matweb.com](http://www.matweb.com) - Materiálové vlastnosti
- [ČSN normy](https://www.agentura-cas.cz) - České technické normy

---

**Verze:** 1.0 | **Datum:** 2026-01-26 | **Autor:** Claude Sonnet 4.5
