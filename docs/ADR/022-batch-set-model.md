# ADR-022: BatchSet Model (Sady cen)

**Status:** Přijato
**Date:** 2026-01-28
**Context:** Správa sad cenových dávek pro díly

---

## Kontext

**Problém:** Uživatel potřebuje vytvářet a spravovat **sady cenových dávek** (BatchSets) pro díly:
- Vytvořit sadu s více dávkami (1 ks, 10 ks, 50 ks...)
- Zmrazit celou sadu najednou (snapshot cen)
- Mít více sad pro jeden díl (historie cenování)
- Klonovat sady pro nové nabídky

**Aktuální stav (před ADR-022):**
- Batch.is_frozen = jednotlivé dávky zmrazitelné (ADR-012)
- Žádné seskupení dávek do sad
- Žádná timeline cenování

**Požadavky:**
1. Sady batches s auto-naming (timestamp)
2. Freeze celé sady najednou
3. Admin může mazat (soft delete + warning)
4. Nikdy auto-vytvářet sadu
5. Připraveno pro budoucí Workspace modul (ADR-023)

---

## Rozhodnutí

### 1. BatchSet Model

```python
class BatchSet(Base, AuditMixin):
    __tablename__ = "batch_sets"

    id = Column(Integer, primary_key=True, index=True)
    set_number = Column(String(8), unique=True, nullable=False, index=True)  # 35XXXXXX
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # Auto: "2026-01-28 14:35"
    status = Column(String(20), default="draft", nullable=False, index=True)  # draft | frozen

    # Freeze metadata
    frozen_at = Column(DateTime, nullable=True, index=True)
    frozen_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    part = relationship("Part", back_populates="batch_sets")
    batches = relationship("Batch", back_populates="batch_set", cascade="all, delete-orphan")
    frozen_by = relationship("User")
```

**Klíčová rozhodnutí:**
- `part_id` je **nullable** s `ondelete="SET NULL"` - historické sady zůstanou i po smazání Part
- `name` = timestamp formát `"2026-01-28 14:35"` (ISO sortable + čitelný)
- `status` = pouze `draft` nebo `frozen` (jednoduché)

### 2. Změna Batch modelu

```python
class Batch(Base, AuditMixin):
    # ... existing fields ...

    # Nový FK na BatchSet (nullable - legacy batches)
    batch_set_id = Column(Integer, ForeignKey("batch_sets.id", ondelete="CASCADE"), nullable=True, index=True)

    # Relationship
    batch_set = relationship("BatchSet", back_populates="batches")
```

**Poznámka:** Staré batches (batch_set_id=NULL) se mohou smazat - není potřeba migrace.

### 3. Auto-naming strategie

```python
def generate_batch_set_name() -> str:
    """Generuje jméno sady z aktuálního timestamp."""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M")  # "2026-01-28 14:35"
```

**Příklady:**
- `"2026-01-28 14:35"` - první sada
- `"2026-01-28 14:40"` - druhá sada (jiný čas)
- `"2026-01-29 09:00"` - další den

### 4. API Endpoints

```python
# app/routers/pricing_router.py

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

# Seznam sad pro díl
GET /api/pricing/part/{part_id}/batch-sets
Response: List[BatchSetResponse]

# Vytvoření nové sady (prázdná)
POST /api/pricing/batch-sets
Body: { part_id: int }
Response: BatchSetResponse

# Zmrazení celé sady
POST /api/pricing/batch-sets/{set_id}/freeze
Response: BatchSetResponse
Action: Všechny batches v sadě se zmrazí (is_frozen=True, snapshot_data)

# Smazání sady (soft delete)
DELETE /api/pricing/batch-sets/{set_id}
Response: 204 No Content
Action: Soft delete (deleted_at) - POUZE ADMIN

# Přidání batch do sady
POST /api/pricing/batch-sets/{set_id}/batches
Body: { quantity: int }
Response: BatchResponse

# Smazání batch ze sady
DELETE /api/pricing/batch-sets/{set_id}/batches/{batch_id}
Response: 204 No Content

# Přepočet cen sady (po změně technologie)
POST /api/pricing/batch-sets/{set_id}/recalculate
Response: BatchSetResponse with updated batches
```

### 5. Freeze Logic

```python
@router.post("/batch-sets/{set_id}/freeze")
async def freeze_batch_set(set_id: int, db: AsyncSession, current_user: User):
    """Zmrazí VŠECHNY batches v sadě atomicky."""
    batch_set = await db.get(BatchSet, set_id)

    if batch_set.status == "frozen":
        raise HTTPException(409, "Sada je již zmrazena")

    if len(batch_set.batches) == 0:
        raise HTTPException(400, "Nelze zmrazit prázdnou sadu")

    # Atomicky zmrazit všechny batches
    for batch in batch_set.batches:
        snapshot = await create_batch_snapshot(batch, current_user.username, db)
        batch.is_frozen = True
        batch.frozen_at = datetime.utcnow()
        batch.frozen_by_id = current_user.id
        batch.snapshot_data = snapshot
        batch.unit_price_frozen = batch.unit_cost
        batch.total_price_frozen = batch.total_cost

    # Označit sadu jako zmrazenou
    batch_set.status = "frozen"
    batch_set.frozen_at = datetime.utcnow()
    batch_set.frozen_by_id = current_user.id

    await db.commit()
    return batch_set
```

### 6. Delete Logic (Soft Delete + Warning)

```python
@router.delete("/batch-sets/{set_id}")
async def delete_batch_set(
    set_id: int,
    db: AsyncSession,
    current_user: User = Depends(require_role([UserRole.ADMIN]))  # POUZE ADMIN!
):
    """Soft delete sady - POUZE ADMIN."""
    batch_set = await db.get(BatchSet, set_id)

    if not batch_set:
        raise HTTPException(404, "Sada nenalezena")

    # Soft delete sady
    batch_set.deleted_at = datetime.utcnow()
    batch_set.deleted_by = current_user.username

    # Soft delete všech batches v sadě
    for batch in batch_set.batches:
        batch.deleted_at = datetime.utcnow()
        batch.deleted_by = current_user.username

    await db.commit()
    logger.info(f"Soft deleted batch set {set_id}", extra={"user": current_user.username})
```

**UI Warning (před smazáním):**
```
⚠️ Opravdu smazat sadu "{name}"?

Tato akce smaže sadu včetně všech {count} dávek.
Zmrazené sady zůstanou v historii (soft delete).

[Zrušit]  [Smazat]
```

---

## UI Design

### Right Panel - Sekce Ceny

```
┌─ RIGHT PANEL ─────────────────────────────────────────┐
│                                                        │
│ 💰 Ceny                                               │
│                                                        │
│ ┌─ Dropdown ─────────────────────────┐ [❄️] [🗑️] [+] │
│ │ 2026-01-28 14:35 ❄️ (3 dávky)     ▼│               │
│ │─────────────────────────────────────│               │
│ │ 2026-01-28 14:35 ❄️ (3 dávky)      │               │
│ │ 2026-01-15 09:20 ❄️ (4 dávky)      │               │
│ │ (žádná aktivní sada)               │               │
│ │─────────────────────────────────────│               │
│ │ + Nová sada                         │               │
│ └─────────────────────────────────────┘               │
│                                                        │
│ ┌─ Batch Table ───────────────────────────────────┐   │
│ │ ks    │ mat  │ koop │ tp   │ tj   │ cena  │     │   │
│ │ 1     │ 150  │ 0    │ 200  │ 150  │ 500   │ [✕] │   │
│ │ 10    │ 150  │ 0    │ 20   │ 150  │ 320   │ [✕] │   │
│ │ 50    │ 150  │ 0    │ 4    │ 150  │ 304   │ [✕] │   │
│ └──────────────────────────────────────────────────┘   │
│                                                        │
│ [Input: ks] [+ Přidat dávku]                          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Legenda tlačítek:**
- `❄️` = Zmrazit sadu (disabled když frozen nebo prázdná)
- `🗑️` = Smazat sadu (ADMIN only, s warning dialogem)
- `+` = Nová sada (prázdná)
- `✕` = Smazat batch (disabled když frozen)

### Default Selection Logic

```javascript
get selectedSet() {
    // 1. Pokud existuje draft sada → vyber ji
    const draft = this.batchSets.find(s => s.status === 'draft');
    if (draft) return draft;

    // 2. Jinak poslední frozen (ORDER BY frozen_at DESC)
    const frozen = this.batchSets
        .filter(s => s.status === 'frozen')
        .sort((a, b) => new Date(b.frozen_at) - new Date(a.frozen_at));
    if (frozen.length > 0) return frozen[0];

    // 3. Žádná sada → null (zobrazit "žádná sada")
    return null;
}
```

---

## Modularita (Připraveno pro Workspace - ADR-023)

### Princip: BatchSets jako nezávislý modul

```javascript
// app/static/js/modules/batch-sets.js

function batchSetsModule(config = {}) {
    return {
        // Module identity (pro Workspace systém)
        moduleType: 'batch-sets',
        moduleId: config.moduleId || crypto.randomUUID(),
        linkColor: config.linkColor || null,  // Pro budoucí Workspace linking

        // Props (vstupní data z parent/workspace)
        partId: config.partId || null,

        // State
        batchSets: [],
        selectedSetId: null,
        batches: [],
        loading: false,

        // Computed
        get selectedSet() {
            return this.batchSets.find(s => s.id === this.selectedSetId) || null;
        },

        get displayedBatches() {
            if (!this.selectedSet) return [];
            return this.batches.filter(b => b.batch_set_id === this.selectedSetId);
        },

        // Lifecycle
        async init() {
            if (this.partId) {
                await this.loadBatchSets();
            }

            // Listen pro změny z workspace (budoucnost)
            this.$watch('partId', async (newId) => {
                if (newId) await this.loadBatchSets();
            });
        },

        // API Methods
        async loadBatchSets() { /* ... */ },
        async createNewSet() { /* ... */ },
        async freezeSet() { /* ... */ },
        async deleteSet() { /* ... */ },
        async addBatch(quantity) { /* ... */ },
        async deleteBatch(batchId) { /* ... */ },
        async recalculatePrices() { /* ... */ },

        // Event emission (pro Workspace linking)
        emitChange(eventType, data) {
            if (this.linkColor) {
                this.$dispatch(`workspace:${this.linkColor}`, {
                    source: this.moduleId,
                    type: eventType,
                    data: data
                });
            }
        }
    };
}
```

### Použití v edit.html (TEĎ)

```html
<!-- Jednoduchá integrace bez Workspace -->
<div x-data="batchSetsModule({ partId: {{ part_id }} })">
    <!-- UI komponenty -->
</div>
```

### Použití v Workspace (BUDOUCNOST - ADR-023)

```html
<!-- Workspace container -->
<div x-data="workspaceController()">
    <!-- Modul propojený na červený link -->
    <div class="workspace-panel" x-data="batchSetsModule({
        partId: linkContext.red?.partId,
        linkColor: 'red',
        moduleId: 'pricing-panel-1'
    })">
        <!-- UI komponenty -->
    </div>
</div>
```

---

## Pydantic Schemas

```python
# app/models/batch_set.py

class BatchSetBase(BaseModel):
    name: str = Field(..., max_length=100)
    status: str = Field("draft", pattern="^(draft|frozen)$")


class BatchSetCreate(BaseModel):
    part_id: int = Field(..., gt=0)


class BatchSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_number: str
    part_id: Optional[int]
    name: str
    status: str
    frozen_at: Optional[datetime]
    frozen_by_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    version: int

    # Nested batches (optional, for detail view)
    batches: List[BatchResponse] = []

    @computed_field
    @property
    def batch_count(self) -> int:
        return len(self.batches)
```

---

## Migration

```python
"""Add BatchSet model

Revision ID: e7f8g9h0i1j2
"""

def upgrade():
    # 1. Vytvořit batch_sets tabulku
    op.create_table('batch_sets',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('set_number', sa.String(8), unique=True, nullable=False, index=True),
        sa.Column('part_id', sa.Integer, sa.ForeignKey('parts.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('status', sa.String(20), default='draft', nullable=False, index=True),
        sa.Column('frozen_at', sa.DateTime, nullable=True, index=True),
        sa.Column('frozen_by_id', sa.Integer, sa.ForeignKey('users.id'), nullable=True),
        # AuditMixin fields
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('created_by', sa.String(100)),
        sa.Column('updated_by', sa.String(100)),
        sa.Column('deleted_at', sa.DateTime, nullable=True, index=True),
        sa.Column('deleted_by', sa.String(100)),
        sa.Column('version', sa.Integer, default=1),
    )

    # 2. Přidat batch_set_id do batches (nullable)
    op.add_column('batches',
        sa.Column('batch_set_id', sa.Integer,
                  sa.ForeignKey('batch_sets.id', ondelete='CASCADE'),
                  nullable=True, index=True)
    )


def downgrade():
    op.drop_column('batches', 'batch_set_id')
    op.drop_table('batch_sets')
```

---

## Alternativy

### Option A: Rozšířit stávající Batch model (žádný BatchSet)

```python
# Přidat do Batch:
set_name = Column(String(100))  # Grouping by name
```

**Proč NE:**
- ❌ Žádná atomická operace freeze
- ❌ Duplicita dat (set_name na každém batch)
- ❌ Těžké queries (GROUP BY set_name)

### Option B: Quote model rovnou (VISION v2.0)

**Proč NE (zatím):**
- ❌ Overkill pro aktuální potřebu
- ❌ Vyžaduje Customer model
- ✅ BatchSet je **bridge** k Quote modulu

### Option C: UI-only grouping (žádný DB model)

**Proč NE:**
- ❌ Ztráta dat při refreshi
- ❌ Žádná persistence
- ❌ Žádný audit trail

---

## Důsledky

### Výhody
- ✅ Sady cen s timeline (historie)
- ✅ Atomické zmrazení celé sady
- ✅ Připraveno pro Workspace modul (ADR-023)
- ✅ Připraveno pro Quote modul (VISION v2.0)
- ✅ Modulární kód (oddělitelný)

### Nevýhody
- ❌ Nová tabulka (batch_sets)
- ❌ Složitější queries (JOIN)

### Rizika
- ⚠️ Legacy batches (batch_set_id=NULL) - řešení: mohou se smazat
- ⚠️ Part deletion - řešení: ondelete="SET NULL"

---

## Reference

- **ADR-012:** Minimal Snapshot Pattern (batch freeze logic)
- **ADR-023:** Workspace Module Architecture (budoucnost)
- **VISION.md:** Quote modul v2.0 (Q1 2026)

---

## Changelog

- 2026-01-28: Changed numbering from 40XXXXXX to 35XXXXXX (pricing domain grouping)
- 2026-01-28: Initial decision - BatchSet model pro sady cen
