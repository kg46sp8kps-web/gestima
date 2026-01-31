# ADR VIS-002: Quotes Workflow & Snapshot Protection

**Date:** 2026-01-31
**Status:** Implemented
**Context:** Quotes module implementation
**Related:**
- ADR-012 (Minimal Snapshot)
- ADR VIS-001 (Soft Delete for Future Modules)
- ADR-022 (Batch Set Model)

---

## Context

GESTIMA nabídky (Quotes) jsou **právně závazné obchodní dokumenty** které:
1. Obsahují **snapshot** cen a materiálů v okamžiku odeslání klientovi
2. Musí být **neměnné** po odeslání (audit trail, compliance)
3. Musí být **chráněné před smazáním** (právní důvody)
4. Nesmí obsahovat editovatelné ceny (pouze z frozen batches)

---

## Decision

### 1. **Pricing Policy: Frozen Batches Only**

**Pravidlo:** Ceny v nabídkách pochází POUZE z frozen batch_sets.

```python
# ❌ ZAKÁZÁNO: Editace ceny v nabídce
class QuoteItemUpdate(BaseModel):
    quantity: Optional[int]
    notes: Optional[str]
    # REMOVED: unit_price (read-only from frozen batch)

# ✅ POVOLENO: Auto-load z frozen batch při vytvoření
@router.post("/quotes/{quote_number}/items")
async def create_quote_item(data: QuoteItemCreate):
    # Načte cenu z BatchSet.status == "frozen"
    unit_price = await QuoteService.get_latest_frozen_batch_price(part_id, db)

    # Pokud není frozen batch → HTTP 400
    if not frozen_batch:
        raise HTTPException(400, "Část nemá zmrazenou kalkulaci. Nejdříve zmrazte batch.")
```

**Důvod:**
- ✅ Single source of truth (frozen batch)
- ✅ Konzistence: všechny nabídky používají stejnou cenu
- ✅ Audit trail: cena je trackovatelná zpět k batch kalkulaci
- ❌ Eliminace manuálních chyb (překlepy v cenách)

---

### 2. **Workflow States & Edit Lock**

**Status flow:**
```
DRAFT → SENT → APPROVED / REJECTED
  ↓       ↓          ↓
  ✏️      🔒         🔒
```

**Edit lock pravidla:**

| Action | DRAFT | SENT | APPROVED | REJECTED |
|--------|-------|------|----------|----------|
| Edit quote | ✅ | ❌ | ❌ | ❌ |
| Add/remove items | ✅ | ❌ | ❌ | ❌ |
| Change prices | ❌ | ❌ | ❌ | ❌ |
| Delete | ✅ | ❌ | ❌ | ✅ |
| Clone | ✅ | ✅ | ✅ | ✅ |

```python
@staticmethod
def check_edit_lock(quote: Quote):
    """Only DRAFT quotes are editable"""
    if quote.status != QuoteStatus.DRAFT.value:
        raise HTTPException(409, "Quote is read-only. Clone to edit.")
```

---

### 3. **Snapshot Creation on SENT**

**Kdy:** Při přechodu `DRAFT → SENT`

**Co obsahuje snapshot:**
```python
snapshot = {
    "quote_number": "85000001",
    "title": "Offer for CNC parts",
    "valid_until": "2026-02-28",

    # Partner data (může se změnit)
    "partner": {
        "partner_number": "70000001",
        "company_name": "ACME Corp",
        "ico": "12345678",
        "street": "Main St 123",
        "city": "Prague",
        # ... complete address
    },

    # Items (denormalizovaná data)
    "items": [
        {
            "part_number": "10000001",
            "part_name": "Bearing housing",
            "quantity": 100,
            "unit_price": 150.0,  # Z frozen batch
            "line_total": 15000.0,
            "notes": ""
        }
    ],

    # Totals
    "subtotal": 15000.0,
    "discount_percent": 10.0,
    "discount_amount": 1500.0,
    "tax_percent": 21.0,
    "tax_amount": 2835.0,
    "total": 16335.0,

    # Timestamps
    "created_at": "2026-01-15T10:00:00Z",
    "sent_at": "2026-01-20T14:30:00Z"
}
```

**Důvod:**
- ✅ Kompletní obchodní dokument (self-contained)
- ✅ Partner data zachována (pokud změní adresu, snapshot má původní)
- ✅ Ceny zamrzlé v okamžiku odeslání
- ✅ Použitelné pro PDF export

---

### 4. **Delete Protection for SENT/APPROVED Quotes**

**Pravidlo:** SENT a APPROVED nabídky NELZE smazat.

```python
@router.delete("/{quote_number}")
async def delete_quote(...):
    # ⛔ PROTECTION
    if quote.status in [QuoteStatus.SENT.value, QuoteStatus.APPROVED.value]:
        raise HTTPException(
            status_code=403,
            detail="Nelze smazat nabídku ve stavu 'sent/approved'. "
                   "Obsahuje právně závazný snapshot."
        )

    # ✅ Soft delete pro DRAFT a REJECTED
    quote.deleted_at = datetime.utcnow()
    quote.deleted_by = current_user.username
```

**Soft delete zachová:**
- ✅ `quote.snapshot_data` (JSON)
- ✅ Audit trail (`deleted_at`, `deleted_by`)
- ✅ Možnost obnovení (pokud omylem)

**Delete matrix:**

| Status | Lze smazat? | Snapshot zachován? | Důvod |
|--------|-------------|-------------------|-------|
| DRAFT | ✅ ANO | N/A (bez snapshotu) | Pracovní koncept |
| SENT | ❌ NE | — | Právní dokument |
| APPROVED | ❌ NE | — | Schválená nabídka |
| REJECTED | ✅ ANO | ✅ ANO (soft delete) | Zamítnutá nabídka |

---

## Implementation

### Backend Changes

**Files modified:**
1. `app/models/quote.py` - Removed `unit_price` from `QuoteItemUpdate`
2. `app/services/quote_service.py` - Block creation if no frozen batch (HTTP 400)
3. `app/routers/quote_items_router.py` - Remove price editing in update endpoint
4. `app/routers/quotes_router.py` - Delete protection for SENT/APPROVED

### Frontend Changes

**Files modified:**
1. `frontend/src/types/quote.ts` - Removed `unit_price` from types
2. `frontend/src/components/modules/quotes/QuoteDetailPanel.vue` - Removed price input field
3. Added info notice: "Cena se automaticky načte z nejnovější zmrazené kalkulace dílu"

### Tests Added

**Files modified:**
1. `tests/test_quotes.py`:
   - `test_sent_quote_cannot_be_deleted()`
   - `test_approved_quote_cannot_be_deleted()`
   - `test_draft_quote_can_be_deleted()`
   - `test_rejected_quote_can_be_deleted()`

---

## Consequences

### Positive

✅ **Legal Compliance:**
- Snapshot je kompletní právní dokument
- SENT/APPROVED quotes chráněné před smazáním
- Audit trail zachován navždy (soft delete)

✅ **Data Integrity:**
- Ceny pochází pouze z frozen batches (single source of truth)
- Nelze manuálně editovat ceny (eliminace chyb)
- Warning pokud part nemá frozen batch

✅ **Consistency:**
- Všechny nabídky používají stejný pricing mechanismus
- Dva snapshoty = dva různé účely:
  - **Frozen Batch snapshot** = interní kalkulace
  - **Quote snapshot** = obchodní dokument

### Negative

❌ **Flexibility:**
- Nelze rychle upravit cenu v nabídce (musí se změnit batch)
- Pokud part nemá frozen batch, nelze přidat do nabídky

❌ **Workflow:**
- Pro změnu ceny: unfreeze batch → změna → freeze → nový quote
- Nebo: clone quote → edit draft

### Neutral

🟡 **Disk Space:**
- Snapshot zabírá ~1-5KB per quote (JSON)
- Pro 1000 quotes/rok = ~5MB (zanedbatelné)

🟡 **Performance:**
- Frozen batch lookup: O(log n) s indexem na `status + deleted_at`
- Snapshot creation: <100ms (single JSON serialize)

---

## Alternatives Considered

### 1. **Editable Prices in Quotes**
**Pattern:** Povolit manuální override ceny v `QuoteItemUpdate`

**Rejected:**
- ❌ Riziko chyb (překlepy, nekonzistentní ceny)
- ❌ Ztráta audit trail (odkud cena pochází?)
- ❌ Není single source of truth

### 2. **No Snapshot (Live Data)**
**Pattern:** Quote.items odkazuje na Part/Batch bez snapshotu

**Rejected:**
- ❌ Pokud se Part smaže, quote ztratí data
- ❌ Pokud se změní cena, historické quotes ukazují novou cenu
- ❌ Právní problém (co bylo nabídnuto vs. co je teď)

### 3. **Allow Delete SENT Quotes (with Warning)**
**Pattern:** Povolit smazání SENT quotes s confirmation dialogem

**Rejected:**
- ❌ Riziko ztráty právních dokumentů
- ❌ Compliance problém (audit trail požaduje zachování)
- ❌ Pokud user chce "cleanup", soft delete stačí

---

## Migration Notes

### From v1.10 to v1.11

**Breaking Changes:**
- `QuoteItemCreate` nemá `unit_price` field (auto-load only)
- `QuoteItemUpdate` nemá `unit_price` field (read-only)
- DELETE `/quotes/{quote_number}` vrací HTTP 403 pro SENT/APPROVED

**Migration Steps:**
1. ✅ Žádná DB migrace nutná (schema kompatibilní)
2. ✅ Frontend: Remove price input fields z quote forms
3. ✅ Frontend: Handle HTTP 400 error (no frozen batch)
4. ✅ Frontend: Handle HTTP 403 error (cannot delete)

**Backward Compatibility:**
- ✅ Existující quotes zůstávají funkční
- ✅ Existující snapshoty zachovány
- ✅ Soft deleted quotes čitelné (admin SQL query)

---

## Future Enhancements

### Admin Interface (Optional)

```python
# View soft-deleted quotes
@router.get("/deleted", dependencies=[require_role(UserRole.ADMIN)])
async def get_deleted_quotes(...):
    query = select(Quote).where(Quote.deleted_at.is_not(None))
    # ... paginate, return

# Restore soft-deleted quote
@router.post("/{quote_number}/restore")
async def restore_quote(...):
    quote.deleted_at = None
    quote.deleted_by = None
```

### Cleanup Job (Optional)

```python
# Delete old DRAFT quotes (6+ months soft-deleted)
async def cleanup_old_draft_quotes(db: AsyncSession):
    cutoff = datetime.utcnow() - timedelta(days=180)

    # ONLY draft quotes (SENT/APPROVED protected)
    result = await db.execute(
        select(Quote).where(
            Quote.status == QuoteStatus.DRAFT.value,
            Quote.deleted_at < cutoff
        )
    )

    for quote in result.scalars():
        await db.delete(quote)  # Hard delete
```

**Note:** Cleanup není nutný! Soft deleted quotes zabírají minimální místo.

---

## Related Documents

- [ADR-012: Minimal Snapshot](012-minimal-snapshot.md) - Batch snapshot pattern
- [ADR VIS-001: Soft Delete](VIS-001-soft-delete-for-future-modules.md) - Soft delete policy
- [ADR-022: Batch Set Model](022-batch-set-model.md) - Frozen batches
- [app/models/quote.py](../../app/models/quote.py) - Quote model implementation

---

## Approval

**Implemented by:** Claude (AI Assistant) + User
**Date:** 2026-01-31
**Status:** ✅ Implemented & Tested

**Changes:**
- ✅ Backend: Frozen batch requirement enforced
- ✅ Backend: Delete protection implemented
- ✅ Frontend: Price editing removed
- ✅ Tests: 4 new tests added
- ✅ Documentation: This ADR created

---

## Summary

**Core Principles:**
1. **Frozen Batches Only** - Ceny pochází pouze z frozen batches
2. **Immutable After SENT** - Nabídky read-only po odeslání
3. **Protected Snapshots** - SENT/APPROVED nelze smazat
4. **Complete Snapshot** - Obsahuje partner + items + totals

**Benefits:**
- ✅ Právní compliance (audit trail)
- ✅ Data integrity (single source of truth)
- ✅ Consistency (stejný pricing process)

**Trade-offs:**
- ❌ Méně flexibility (nelze rychle měnit ceny)
- ✅ Ale: vyšší kvalita dat, nižší riziko chyb
