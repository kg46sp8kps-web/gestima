# ADR-048: Orphan detekce — rozšíření o soft-deleted díly

**Status:** DONE (2026-02-20)
**Date:** 2026-02-20
**Decision:** Rozšírena orphan detekce souborů o možnost zahrnout soubory jejichž FileLinky vedou VÝHRADNĚ na soft-deleted díly

---

## Kontext

FileManager (ADR-044) měl `find_orphans()` která hledala soubory bez aktivního FileLinku.
Ale při soft delete Part modelu (`deleted_at NOT NULL`):
- FileLink zůstane v DB (FK není cascaded)
- Soubor se tedy nezobrazí jako orphan
- Přestože díl ve skutečnosti neexistuje v UI

Příklad: Smazal jsem Part #18045, ale soubor `parts/18045/drawing.pdf` zůstal označený jako linked → orphan detection ho nevidí.

---

## Rozhodnutí

### 1. Nový parametr `find_orphans(include_linked_to_deleted=False)`

```python
def find_orphans(self, include_linked_to_deleted: bool = False) -> list[FileRecord]:
```

- **`False` (default):** Originální chování — soubory bez jakéhokoliv aktivního FileLinku
- **`True`:** Zahrnuje i soubory jejichž FileLinky vedou VÝHRADNĚ na soft-deleted Part (`part.deleted_at IS NOT NULL`)

Implementace: **dvoustupňový dotaz** kvůli SQLAlchemy limitaci:

```python
# Krok 1: raw SQL vrátí active part IDs
active_part_ids = db.session.execute(
    text("SELECT DISTINCT entity_id FROM file_links WHERE entity_type='part' AND deleted_at IS NULL")
).scalars()
active_part_ids_set = set(active_part_ids)

# Krok 2: Python set místo SQL
orphans = session.query(FileRecord)
    .filter(FileRecord.status == "active")
    .filter(~FileRecord.id.in_([...linked non-deleted...]))
    .options(selectinload(FileRecord.links))
    .all()
```

**Důvod dvoustupňového přístupu:** SQLAlchemy `notin_(text(...))` negeneruje závorky → `NOT IN text(...) AND ...` → syntax error. Řešení: raw query → Python set → `.notin_()` s listou.

### 2. Obohacení entity names

V orphans endpointu přidán call `_enrich_link_entity_names(orphans)`:

```python
def _enrich_link_entity_names(file_records: list[FileRecord]) -> None:
    """Přidá entity_name do FileLink.entity_data (part.name apod.)"""
    # Funguje i pro soft-deleted díly — Part query bez filtru vrací všechny
```

Bez toho: `entity_name=null` → UI zobrazuje `part #18045` místo `TEST` → špatná UX.

### 3. Router pořadí — critical bug fix

**Problém:** FastAPI matchuje routes v **pořadí registrace**. Měl jsem:
```python
@router.get("/{file_id}")          # Řešen TŘETÍ
@router.get("/orphans")            # Řešen PRVNÍ (souhlasí se 2.reg)
```

Výsledek: Request `GET /api/files/orphans` → FastAPI vidí `/{file_id}` DŘÍV → matchuje `file_id="orphans"` → `int()` konverze → **422 Unprocessable Entity**.

**Řešení:** Obě spec. routes MUSÍ být PŘED generic:
```python
@router.get("/orphans")            # ← NEJDŘÍV (spec. routes)
@router.get("/orphans/bulk")       # ← DRUHÉ
@router.get("/{file_id}")          # ← NAKONEC (generic)
```

### 4. Selectinload() — async greenlet bug fix

**Problém bez `.selectinload(FileRecord.links)`:**
```python
orphans = session.query(FileRecord).filter(...).all()
for orphan in orphans:
    names = [link.entity_name for link in orphan.links]  # ← lazy load mimo greenlet!
```

Výsledek: `MissingGreenlet: greenlet_spawn has not been called` → **500 Internal Server Error**.

**Řešení:** Eager load v query:
```python
.options(selectinload(FileRecord.links))
```

---

## Backend Implementation

**Soubor:** `app/services/file_service.py`

```python
def find_orphans(self, include_linked_to_deleted: bool = False) -> list[FileRecord]:
    """
    Najde orphan soubory.
    
    include_linked_to_deleted=True:
      Zahrnuje i soubory jejichž FileLinky vedou VÝHRADNĚ na soft-deleted díly.
    """
    # Krok 1: Najdi všechny IDs части, ke kterým existuje aktivní FileLink
    if include_linked_to_deleted:
        # Raw SQL pro active FileLinks na parts
        active_part_ids = self.db_session.execute(
            text("""
                SELECT DISTINCT entity_id 
                FROM file_links 
                WHERE entity_type = 'part' AND deleted_at IS NULL
            """)
        ).scalars().all()
        active_part_ids_set = set(active_part_ids) if active_part_ids else set()
    else:
        # Originální: všechny FileLinks (včetně deleted)
        all_linked = self.db_session.query(FileLink).all()
        active_part_ids_set = {fl.entity_id for fl in all_linked if fl.entity_type == 'part'}
    
    # Krok 2: Najdi orphan FileRecords
    query = self.db_session.query(FileRecord)\
        .filter(FileRecord.status == "active")\
        .filter(~FileRecord.id.in_([...all linked IDs...]))\
        .options(selectinload(FileRecord.links))
    
    return query.all()
```

**Soubor:** `app/routers/files_router.py`

```python
# ← NEJDŘÍV (specific routes)
@router.get("/orphans")
def get_orphans(include_linked_to_deleted: bool = False) -> list[FileRecordSchema]:
    orphans = file_service.find_orphans(include_linked_to_deleted)
    file_service._enrich_link_entity_names(orphans)  # Přidej part.name apod.
    return [FileRecordSchema.from_orm(o) for o in orphans]

@router.post("/orphans/bulk")
def delete_orphans_bulk(file_ids: list[int]) -> dict:
    """Smaž multiple orphans najednou (soft delete)"""
    for file_id in file_ids:
        file_service.delete(file_id)
    return {"deleted": len(file_ids)}

# ← NAKONEC (generic route)
@router.get("/{file_id}")
def get_file(file_id: int) -> FileRecordSchema:
    ...
```

---

## Frontend Implementation

**Soubor:** `frontend/src/api/files.ts`

```typescript
export async function getOrphans(
  includeLinkedToDeleted: boolean = false
): Promise<FileRecord[]> {
  const response = await client.get('/files/orphans', {
    params: { include_linked_to_deleted: includeLinkedToDeleted }
  });
  return response.data;
}

export async function deleteOrphansBulk(fileIds: number[]): Promise<void> {
  await client.post('/files/orphans/bulk', { file_ids: fileIds });
}
```

**Soubor:** `frontend/src/stores/files.ts`

```typescript
export const useFilesStore = defineStore('files', {
  state: () => ({
    orphans: [] as FileRecord[],
    includeDeletedParts: false
  }),

  actions: {
    async fetchOrphans() {
      this.orphans = await getOrphans(this.includeDeletedParts);
    },

    async deleteOrphansBulk(fileIds: number[]) {
      await deleteOrphansBulk(fileIds);
      await this.fetchOrphans();  // Refresh
    }
  }
});
```

**Soubor:** `frontend/src/components/modules/files/FileListPanel.vue`

```vue
<template>
  <div class="orphan-toolbar">
    <label>
      <input 
        v-model="includeDeletedParts" 
        type="checkbox"
      />
      Zahrnout soubory smazaných dílů
    </label>
    
    <button 
      @click="refreshOrphans"
      :disabled="orphans.length === 0"
    >
      Obnovit seznam
    </button>
    
    <button 
      @click="deleteSelected"
      :disabled="selectedFileIds.length === 0"
    >
      Smazat {{selectedFileIds.length}} souborů
    </button>
  </div>
  
  <div class="orphan-list">
    <div v-for="file in orphans" :key="file.id" class="file-item">
      <input 
        v-model="selectedFileIds" 
        :value="file.id" 
        type="checkbox"
      />
      {{ file.original_filename }}
      <span class="file-size">({{ formatBytes(file.file_size) }})</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const filesStore = useFilesStore();
const selectedFileIds = ref<number[]>([]);
const includeDeletedParts = ref(false);

const orphans = computed(() => filesStore.orphans);

const refreshOrphans = async () => {
  await filesStore.fetchOrphans();
  selectedFileIds.value = [];
};

const deleteSelected = async () => {
  await filesStore.deleteOrphansBulk(selectedFileIds.value);
  selectedFileIds.value = [];
};

onMounted(() => {
  refreshOrphans();
});
</script>
```

---

## Testing

```bash
# Backend test
pytest tests/test_file_service.py::test_find_orphans_with_soft_deleted -v

# Manual test
curl http://localhost:8000/api/files/orphans?include_linked_to_deleted=true
```

---

## Consequences

1. **Orphan detection nyní vidí všechny opravdu "mrtvé" soubory** — včetně těch z deleted parts
2. **UI checkbox umožňuje uživateli filtrovat** — chce smazat jen soubory bez references?
3. **Žádný DB schema change** — pouze nový SQL dotaz + parametr
4. **Backward compatible** — default `False` = původní chování

---

## Limitations

- Orphan detekce vidí POUZE soft-deleted Parts (`deleted_at IS NOT NULL`), ne hard-deleted
- Bulk delete je asynchronní — timeout na 1000+ souborů možný
- Non-part FileLinks ignorovány — fokus na Part model

---

## Files Changed

| Soubor | Změna |
|--------|-------|
| `app/services/file_service.py` | `find_orphans(include_linked_to_deleted)` |
| `app/routers/files_router.py` | `/orphans` + `/orphans/bulk` PŘED `/{file_id}`, enrich call |
| `frontend/src/api/files.ts` | `getOrphans()`, `deleteOrphansBulk()` |
| `frontend/src/stores/files.ts` | `fetchOrphans()`, `deleteOrphansBulk()` actions |
| `frontend/src/components/modules/files/FileListPanel.vue` | Orphan toolbar + checkbox |
