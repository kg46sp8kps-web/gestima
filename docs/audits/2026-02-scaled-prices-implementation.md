# Scaled Prices Implementation - Volume Pricing

## 📊 Přehled

**Problém:** Zákazník chce cenu na více množství (1/5/10/20 ks), každé s jinou cenou.

**Řešení:** Automatická expanze 1 řádku → 4 řádky (jeden pro každé množství).

---

## 🎯 Příklad

### PŘED (1 řádek):
```
Article: byn-10101251
Name: Halter
Quantity: 1
Notes: Scaled prices: 1/5/10/20 | Drawing: 90057637-00
```

### PO (4 řádky):
```
Article: byn-10101251, Name: Halter, Qty: 1,  Notes: 🎯 Volume tier: 1 pc
Article: byn-10101251, Name: Halter, Qty: 5,  Notes: 🎯 Volume tier: 5 pcs
Article: byn-10101251, Name: Halter, Qty: 10, Notes: 🎯 Volume tier: 10 pcs
Article: byn-10101251, Name: Halter, Qty: 20, Notes: 🎯 Volume tier: 20 pcs
```

Každý řádek dostane **jinou cenu** podle dávky (batch matching).

---

## 🛠️ Implementace

### 1. Scaled Prices Expander
**Soubor:** `app/services/scaled_prices_expander.py`

**Funkce:**
- `extract_quantities(notes)` - extrahuje [1, 5, 10, 20] z "Scaled prices: 1/5/10/20"
- `expand_item(item)` - expanduje 1 item → N items (podle quantities)
- `expand_all_items(items)` - expanduje všechny items v listu

**Podporované formáty:**
```
"Scaled prices: 1/5/10/20"
"Scaled prices: 1 / 5 / 10 / 20"
"Quantities: 1, 5, 10, 20"
"Volume pricing: 100/500/1000"
"SCALED PRICES: 1/5/10/20"  (case insensitive)
```

### 2. Integrace do Backend
**Soubor:** `app/routers/quotes_router.py:491-503`

```python
# Parse with Claude
extraction = await parser.parse_pdf(temp_path)

# Expand scaled prices (1/5/10/20) → multiple items
from app.services.scaled_prices_expander import expand_all_items
original_item_count = len(extraction.items)
extraction.items = expand_all_items(extraction.items)

if len(extraction.items) > original_item_count:
    logger.info(
        f"Scaled prices expansion: {original_item_count} items → "
        f"{len(extraction.items)} items"
    )
```

**Průběh:**
1. AI parsuje PDF → získá 2 items (quantity=1 každý)
2. Expander detekuje "Scaled prices: 1/5/10/20" v notes
3. Expanduje: 2 items → 8 items (4 per part)
4. Každý item matchuje batch podle quantity → jiná cena

---

## 🧪 Testování

### Unit Testy
**Soubor:** `test_scaled_prices_expander.py`

```bash
python3 test_scaled_prices_expander.py
# ✅ ALL TESTS PASSED (11 tests)
```

**Testy pokrývají:**
- Extraction quantities z různých formátů
- Expansion 1 item → N items
- Case insensitivity
- No-op když není "scaled prices"

### Fixture
**Soubor:** `tests/fixtures/quote_request_gelso_p20971_expanded.json`

**Obsahuje:**
- 8 items (expanded z 2 original)
- Article Numbers: byn-10101251 (4x), byn-10101263-01 (4x)
- Quantities: [1, 5, 10, 20] pro každý article

---

## 📋 Workflow

### 1. Upload PDF (GELSO AG P20971)
```
Item 1: Halter (byn-10101251)
  Notes: "Scaled prices: 1/5/10/20"

Item 2: Halter (byn-10101263-01)
  Notes: "SCALED PRICES 1/5/10/20"
```

### 2. AI Extraction
```json
{
  "items": [
    {"article_number": "byn-10101251", "quantity": 1, "notes": "Scaled prices: 1/5/10/20"},
    {"article_number": "byn-10101263-01", "quantity": 1, "notes": "SCALED PRICES 1/5/10/20"}
  ]
}
```

### 3. Scaled Prices Expansion (Backend)
```json
{
  "items": [
    {"article_number": "byn-10101251", "quantity": 1},
    {"article_number": "byn-10101251", "quantity": 5},
    {"article_number": "byn-10101251", "quantity": 10},
    {"article_number": "byn-10101251", "quantity": 20},
    {"article_number": "byn-10101263-01", "quantity": 1},
    {"article_number": "byn-10101263-01", "quantity": 5},
    {"article_number": "byn-10101263-01", "quantity": 10},
    {"article_number": "byn-10101263-01", "quantity": 20}
  ]
}
```

### 4. Batch Matching (pro každý řádek)
- Quantity=1 → hledá batch pro 1 ks → cena X
- Quantity=5 → hledá batch pro 5 ks → cena Y (nižší jednotková)
- Quantity=10 → hledá batch pro 10 ks → cena Z (ještě nižší)
- Quantity=20 → hledá batch pro 20 ks → cena W (nejnižší)

### 5. Quote Creation
Vytvoří Quote s 8 QuoteItems - každý s **jinou unit_price** podle batch!

---

## 🎨 Frontend Display

**Tabulka v UI:**
```
Artikl / Part Number | Název  | Množství | Dávka  | Cena/ks | Celkem
---------------------|--------|----------|--------|---------|--------
byn-10101251         | Halter | 1 ks     | Exact  | 150 Kč  | 150 Kč
byn-10101251         | Halter | 5 ks     | Exact  | 130 Kč  | 650 Kč
byn-10101251         | Halter | 10 ks    | Exact  | 120 Kč  | 1200 Kč
byn-10101251         | Halter | 20 ks    | Exact  | 110 Kč  | 2200 Kč
```

Zákazník vidí **všechny varianty** a může si vybrat nejvýhodnější!

---

## 🔧 Konfigurace

### Přidání Nových Prefixů

**Soubor:** `app/services/scaled_prices_expander.py:19-23`

```python
SCALED_PRICES_PATTERNS = [
    r"scaled\s+prices?\s*[:=]\s*([\d\s/,]+)",
    r"quantities?\s*[:=]\s*([\d\s/,]+)",
    r"volume\s+pricing\s*[:=]\s*([\d\s/,]+)",
    # Přidat vlastní pattern zde:
    r"množství\s*[:=]\s*([\d\s/,]+)",  # Czech
]
```

---

## 📊 Statistiky (GELSO AG P20971)

**PŘED expanzí:**
- Items: 2
- Total quote items: 2

**PO expanzi:**
- Items: 8 (4x per part)
- Total quote items: 8
- Volume tiers: [1, 5, 10, 20] ks
- Price flexibility: 4 ceny per díl

---

## ✅ Výhody

1. **Automatická expanze** - žádná manuální práce
2. **Správné ceny** - každé množství má svou cenu z batch
3. **Flexibilita** - zákazník vidí všechny varianty
4. **Volume discount** - vyšší množství = nižší jednotková cena
5. **Trasovatelnost** - notes obsahují "Volume tier: X pcs"

---

## 🚀 Deploy

1. **Restart backend:**
   ```bash
   python gestima.py run
   ```

2. **Refresh frontend** (Ctrl+F5)

3. **Test workflow:**
   - Upload GELSO AG PDF
   - Zkontroluj: 2 items → 8 items (expansion log v backend)
   - Vytvoř Quote
   - Ověř: 8 QuoteItems s různými cenami

---

## 📝 Notes

- **Original notes preserved** - "Original: Scaled prices: 1/5/10/20"
- **Volume tier indicator** - "🎯 Volume tier: 5 pcs"
- **Drawing numbers kept** - "Drawing: 90057637-00" zůstává v notes
- **Fuzzy matching** - funguje pro všechny expandované items

---

## 🔮 Budoucí Vylepšení

1. **Custom tiers** - umožnit uživateli definovat vlastní množstevní stupně
2. **Price prediction** - predikovat cenu pro missing batches
3. **Recommendations** - doporučit nejlepší tier (ROI)
4. **Bulk operations** - hromadné operace s volume tiers

---

**Version:** 1.0
**Date:** 2026-02-02
**Author:** Claude Sonnet 4.5
