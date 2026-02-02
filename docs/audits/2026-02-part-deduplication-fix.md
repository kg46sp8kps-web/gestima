# Part Deduplication Fix

## 🐛 Problém

**Scénář:** Scaled prices expanze vytvoří 8 QuoteItems (4x pro každý díl)

**Bug:** Původní kód vytvořil **8 duplikátních Parts** (1 Part per QuoteItem)

**Správně:** Mělo by se vytvořit pouze **2 Parts** (1 per unique article_number)

---

## ❌ PŘED (špatně)

```python
# ❌ Vytvoří Part pro KAŽDÝ item (duplikáty!)
for item in data.items:  # 8 items
    if not item.part_id:
        new_part = Part(
            article_number=item.article_number,
            name=item.name,
            ...
        )
        db.add(new_part)
        item.part_id = new_part.id
```

**Výsledek:**
```
Parts Table:
  10000123 | byn-10101251      | Halter  ← Item 1 (qty=1)
  10000124 | byn-10101251      | Halter  ← Item 2 (qty=5)  ❌ DUPLIKÁT!
  10000125 | byn-10101251      | Halter  ← Item 3 (qty=10) ❌ DUPLIKÁT!
  10000126 | byn-10101251      | Halter  ← Item 4 (qty=20) ❌ DUPLIKÁT!
  10000127 | byn-10101263-01   | Halter  ← Item 5 (qty=1)
  10000128 | byn-10101263-01   | Halter  ← Item 6 (qty=5)  ❌ DUPLIKÁT!
  10000129 | byn-10101263-01   | Halter  ← Item 7 (qty=10) ❌ DUPLIKÁT!
  10000130 | byn-10101263-01   | Halter  ← Item 8 (qty=20) ❌ DUPLIKÁT!
```

**8 Parts vytvořeno** ❌ (měly být 2!)

---

## ✅ PO (správně)

```python
# ✅ Deduplikace pomocí article_number → part_id mapping
article_to_part_id = {}  # Track created parts

for item in data.items:
    if not item.part_id:
        if item.article_number in article_to_part_id:
            # Reuse existing part_id
            item.part_id = article_to_part_id[item.article_number]
            logger.debug(f"Reusing part for {item.article_number}")
        else:
            # Create new part (first occurrence)
            new_part = Part(
                article_number=item.article_number,
                name=item.name,
                ...
            )
            db.add(new_part)
            article_to_part_id[item.article_number] = new_part.id
            item.part_id = new_part.id
            logger.info(f"Created part: {new_part.part_number}")
```

**Výsledek:**
```
Parts Table:
  ID   | part_number | article_number    | name
  -----|-------------|-------------------|--------
  1001 | 10000123    | byn-10101251      | Halter    ✅ JEDINÝ
  1002 | 10000124    | byn-10101263-01   | Halter    ✅ JEDINÝ

QuoteItems Table:
  ID  | part_id | quantity | notes
  ----|---------|----------|---------------------------
  1   | 1001    | 1        | Volume tier: 1 pc   ✅
  2   | 1001    | 5        | Volume tier: 5 pcs  ✅ Sdílí Part 1001
  3   | 1001    | 10       | Volume tier: 10 pcs ✅ Sdílí Part 1001
  4   | 1001    | 20       | Volume tier: 20 pcs ✅ Sdílí Part 1001
  5   | 1002    | 1        | Volume tier: 1 pc   ✅
  6   | 1002    | 5        | Volume tier: 5 pcs  ✅ Sdílí Part 1002
  7   | 1002    | 10       | Volume tier: 10 pcs ✅ Sdílí Part 1002
  8   | 1002    | 20       | Volume tier: 20 pcs ✅ Sdílí Part 1002
```

**2 Parts vytvořeno** ✅ (správně!)

---

## 🧪 Test

**Soubor:** `test_part_deduplication.py`

```bash
python3 test_part_deduplication.py
```

**Výstup:**
```
✅ Created Part 1001 for byn-10101251 (qty=1)
♻️  Reusing Part 1001 for byn-10101251 (qty=5)
♻️  Reusing Part 1001 for byn-10101251 (qty=10)
♻️  Reusing Part 1001 for byn-10101251 (qty=20)
✅ Created Part 1002 for byn-10101263-01 (qty=1)
♻️  Reusing Part 1002 for byn-10101263-01 (qty=5)
♻️  Reusing Part 1002 for byn-10101263-01 (qty=10)
♻️  Reusing Part 1002 for byn-10101263-01 (qty=20)

📊 Results:
  Total items: 8
  Parts created: 2 ✅
```

---

## 📊 Workflow Example

### Input (GELSO AG P20971 PDF):
```
Item 1: byn-10101251, Halter, Scaled prices: 1/5/10/20
Item 2: byn-10101263-01, Halter, Scaled prices: 1/5/10/20
```

### After AI Parsing + Expansion:
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

### Part Creation (with deduplication):
```
Processing item 1: article_number=byn-10101251
  ✅ NEW article_number → Create Part 10000123
  ✅ Set item.part_id = 10000123

Processing item 2: article_number=byn-10101251
  ♻️  SEEN article_number → Reuse Part 10000123
  ✅ Set item.part_id = 10000123

Processing item 3: article_number=byn-10101251
  ♻️  SEEN article_number → Reuse Part 10000123
  ✅ Set item.part_id = 10000123

Processing item 4: article_number=byn-10101251
  ♻️  SEEN article_number → Reuse Part 10000123
  ✅ Set item.part_id = 10000123

Processing item 5: article_number=byn-10101263-01
  ✅ NEW article_number → Create Part 10000124
  ✅ Set item.part_id = 10000124

... (items 6-8 reuse Part 10000124)
```

### Final Database State:
```
Parts: 2 (10000123, 10000124)
QuoteItems: 8 (all with correct part_id references)
```

---

## 🔍 Verification

### Check Parts Count:
```sql
SELECT COUNT(*) FROM parts WHERE article_number = 'byn-10101251';
-- Expected: 1 (not 4!)
```

### Check QuoteItems Link:
```sql
SELECT qi.id, qi.quantity, qi.part_id, p.part_number, p.article_number
FROM quote_items qi
JOIN parts p ON qi.part_id = p.id
WHERE p.article_number = 'byn-10101251';

-- Expected: 4 rows, all with SAME part_id
```

---

## 📝 Summary

| Metric | PŘED | PO |
|--------|------|-----|
| **Items** | 8 | 8 |
| **Unique article_numbers** | 2 | 2 |
| **Parts created** | 8 ❌ | 2 ✅ |
| **Part duplicates** | 6 ❌ | 0 ✅ |
| **Database bloat** | High | Minimal |
| **Data integrity** | Poor | Good |

---

## 🎯 Benefits

1. **No duplicates** - každý article_number = 1 Part
2. **Správné relace** - všechny QuoteItems správně linkují na Part
3. **Čistá databáze** - žádné zbytečné záznamy
4. **Konzistence** - jeden zdroj pravdy pro každý díl
5. **Performance** - méně záznamů = rychlejší queries

---

## 🚀 Deploy

```bash
# Backend změny jsou v quotes_router.py
python gestima.py run
```

**Test workflow:**
1. Upload GELSO AG PDF (nebo použij mock)
2. Zkontroluj backend log: "Created new part: ..." (měl by být 2x, ne 8x)
3. Vytvoř nabídku
4. Zkontroluj DB:
   ```sql
   SELECT COUNT(*) FROM parts WHERE created_at > NOW() - INTERVAL '1 hour';
   -- Expected: 2 (not 8)
   ```

---

**Version:** 1.0
**Fixed:** 2026-02-02
**Impact:** Critical (data integrity)
