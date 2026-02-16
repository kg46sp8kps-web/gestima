# ADR-044: Centrální File Manager

**Status:** Accepted (Phase 1 backend DONE, Phase 2-3 pending)
**Date:** 2026-02-15
**Author:** AI + User

## Context

Gestima má **~30 touchpointů** souborových operací rozesetých přes 6 routerů, 2 služby a 3 modely. Soubory se ukládají, servírují a mažou na 5 různých místech různými způsoby:

### Současné problémy

| # | Problém | Dopad |
|---|---------|-------|
| 1 | **TimeVision matchuje soubory přes `pdf_filename` string** | Přejmenování = ztráta vazby, žádná referenční integrita |
| 2 | **2 různé cesty**: `uploads/drawings/` vs `drawings/` | Nekonzistentní, soubory se "ztrácí" |
| 3 | **STEP soubory bez DB evidence** | `step_router.py` servíruje z disku, žádný audit trail |
| 4 | **Temp registry v paměti** (`Dict[str, str]`) | Restart serveru = orphaned soubory |
| 5 | **Flat adresář** (105+ souborů v jedné složce) | Neškáluje pro 1000+ souborů |
| 6 | **`/uploads/*` bez autentizace** (StaticFiles mount) | Bezpečnostní díra |
| 7 | **Žádný centrální registr** | Každý router si evidenci řeší sám |

### Současná architektura (fragmentovaná)

```
Drawing model        → part_id FK, file_path, file_hash, is_primary
TimeVisionEstimation → pdf_filename (string!), pdf_path (string!)
Part.drawing_path    → deprecated string field
step_router          → čte přímo z disku, žádná DB
uploads_router       → in-memory dict pro temp soubory
```

## Decision

### Princip: "Hloupý" File Manager

File Manager je **POUZE úložiště + registr**. Neobsahuje žádnou business logiku.

```
✅ File Manager DĚLÁ:        ❌ File Manager NEDĚLÁ:
  Uloží soubor na disk         Nerozhoduje o business workflow
  Validuje typ (magic bytes)   Neřeší TimeVision/Parts logiku
  Vytvoří DB záznam            Nerozhoduje o primary drawing
  Vrátí URL pro zobrazení      Neřídí vazby mezi entitami
  Smaže / archivuje soubor     Neví co je "nabídka" nebo "díl"
  Detekuje orphany             Neposílá notifikace
```

Business logika ZŮSTÁVÁ v příslušných routerech/services. Ty volají File Manager pro fyzické operace.

---

### 1. Nový model: `FileRecord`

**Tabulka:** `file_records`

```python
class FileRecord(AuditMixin, Base):
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)

    # Identita souboru
    file_hash = Column(String(64), nullable=False, index=True)       # SHA-256
    file_path = Column(String(500), nullable=False, unique=True)     # Relativní: "parts/10900635/rev_A.pdf"
    original_filename = Column(String(255), nullable=False)          # Původní název od uživatele
    file_size = Column(Integer, nullable=False)                      # Bytes

    # Typ souboru
    file_type = Column(String(10), nullable=False, index=True)       # "pdf", "step", "nc", "xlsx"
    mime_type = Column(String(100), nullable=False)                  # "application/pdf"

    # Stav
    status = Column(String(20), default="active", nullable=False, index=True)  # "temp", "active", "archived"

    # AuditMixin provides: created_at, updated_at, created_by, updated_by, deleted_at, deleted_by, version
```

**Klíčová rozhodnutí:**
- `file_path` je **unique** — jeden fyzický soubor = jeden záznam
- `file_hash` NENÍ unique — stejný obsah může být uložen vícekrát (jiné entity)
- `status="temp"` nahrazuje in-memory dict pro dočasné soubory
- **Žádné `entity_type`/`entity_id` přímo v modelu** — vazby jdou přes `FileLink`

---

### 2. Vazební model: `FileLink`

**Tabulka:** `file_links`

```python
class FileLink(AuditMixin, Base):
    __tablename__ = "file_links"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_records.id", ondelete="CASCADE"), nullable=False, index=True)

    # Polymorfní vazba
    entity_type = Column(String(50), nullable=False, index=True)     # "part", "quote_item", "timevision"
    entity_id = Column(Integer, nullable=False, index=True)          # FK na konkrétní entitu

    # Metadata vazby (business logika patří SEM, ne do FileRecord)
    is_primary = Column(Boolean, default=False, nullable=False)
    revision = Column(String(2), nullable=True)                      # "A", "B", "C"
    link_type = Column(String(20), default="drawing", nullable=False) # "drawing", "step_model", "nc_program"

    __table_args__ = (
        # Unikátní: jeden soubor může být k entitě připojen jen jednou
        Index("ix_file_links_entity", "entity_type", "entity_id"),
        UniqueConstraint("file_id", "entity_type", "entity_id", name="uq_file_link"),
    )
```

**Proč separátní tabulka (ne sloupce v FileRecord):**
- Jeden soubor → více vazeb (PDF je výkres dílu A ZÁROVEŇ zdroj pro TimeVision estimation)
- Přidání nové entity = nový řádek v `file_links`, BEZ změny schema
- `is_primary` a `revision` patří k VAZBĚ (ne k souboru) — stejný PDF může být rev_A u dílu X a rev_B u dílu Y

---

### 3. Adresářová struktura

```
uploads/
├── parts/                          # Výkresy vázané na díly
│   └── {part_number}/              # Složka per díl
│       ├── {part_number}_A.pdf     # Revision A
│       ├── {part_number}_B.pdf     # Revision B
│       └── {part_number}_A.step    # 3D model
├── quotes/                         # Soubory z poptávek
│   └── {quote_number}/             # Složka per nabídka
│       └── uploaded.pdf
├── loose/                          # Soubory bez vazby (TimeVision, importy)
│   └── {original_filename}.pdf
├── temp/                           # Dočasné (auto-cleanup, status="temp" v DB)
│   └── {uuid}.pdf
└── programs/                       # Budoucnost: CNC programy
    └── {part_number}/
        └── {program_name}.nc
```

**Pravidla:**
- Podsložky per `entity` — škáluje na tisíce souborů
- `loose/` pro soubory bez entity vazby (TimeVision scanning)
- `temp/` s DB evidencí (přežije restart serveru!)

---

### 4. FileService — API (5 core metod)

```python
class FileService:
    """Centrální file service. Hloupý — jen ukládá a vrací."""

    def store(
        self,
        file: UploadFile,
        directory: str,              # "parts/10900635" nebo "loose"
        *,
        allowed_types: list[str] = ["pdf", "step"],
    ) -> FileRecord:
        """Validuj, ulož na disk, vytvoř DB záznam. Vrať FileRecord."""

    def get(self, file_id: int) -> FileRecord:
        """Vrať FileRecord nebo 404."""

    def link(
        self,
        file_id: int,
        entity_type: str,
        entity_id: int,
        *,
        is_primary: bool = False,
        revision: str | None = None,
        link_type: str = "drawing",
    ) -> FileLink:
        """Propoj soubor s entitou. Vrať FileLink."""

    def unlink(self, file_id: int, entity_type: str, entity_id: int) -> None:
        """Odpoj soubor od entity (soft delete FileLink)."""

    def delete(self, file_id: int) -> None:
        """Soft delete FileRecord + všechny FileLinks. Soubor na disku ZŮSTÁVÁ."""
```

**Pomocné metody:**
```python
    def get_files_for_entity(self, entity_type: str, entity_id: int) -> list[FileRecord]:
        """Všechny soubory entity (přes FileLink JOIN)."""

    def get_primary(self, entity_type: str, entity_id: int, link_type: str = "drawing") -> FileRecord | None:
        """Primární soubor entity daného typu."""

    def set_primary(self, file_id: int, entity_type: str, entity_id: int) -> None:
        """Nastav jako primary (unset ostatní stejného entity+link_type)."""

    def cleanup_temp(self, max_age_hours: int = 24) -> int:
        """Smaž temp soubory starší než N hodin. Vrať počet smazaných."""

    def find_orphans(self) -> list[FileRecord]:
        """Soubory bez žádného FileLink (kromě temp)."""

    def serve_file(self, file_id: int) -> FileResponse:
        """Vrať FileResponse pro download/preview. Kontroluje existence na disku."""
```

---

### 5. REST API endpointy

**Router:** `/api/files/`

```
POST   /api/files/upload                         ← Upload souboru (vrátí FileRecord)
GET    /api/files/{id}                            ← Metadata souboru
GET    /api/files/{id}/preview                    ← Náhled PDF (inline, bez auth — pro iframe/pdf.js)
GET    /api/files/{id}/download                   ← Stáhni/zobraz soubor (FileResponse, s auth)
DELETE /api/files/{id}                            ← Soft delete

POST   /api/files/{id}/link                       ← Propoj s entitou
DELETE /api/files/{id}/link/{entity_type}/{eid}   ← Odpoj od entity
PUT    /api/files/{id}/primary/{entity_type}/{eid} ← Nastav jako primary

GET    /api/files?entity_type=part&entity_id=123  ← Soubory entity
GET    /api/files/orphans                          ← Osiřelé soubory (admin)
```

---

### 6. Jak to volají stávající moduly (příklady)

#### Parts — upload výkresu k dílu

```python
# drawings_router.py (REFAKTOROVANÝ)
@router.post("/parts/{pn}/drawings")
async def upload_drawing(pn: str, file: UploadFile, db: Session):
    part = get_part_or_404(pn, db)

    # 1. File Manager uloží (hloupý — neví co je "díl")
    record = file_service.store(file, directory=f"parts/{pn}")

    # 2. Business logika: propoj s dílem
    link = file_service.link(
        file_id=record.id,
        entity_type="part",
        entity_id=part.id,
        revision=next_revision(part),        # Business logika
        is_primary=not part.has_primary(),    # Business logika
    )

    return DrawingResponse.from_record(record, link)
```

#### TimeVision — upload PDF pro AI estimaci

```python
# time_vision_router.py (REFAKTOROVANÝ)
@router.post("/time-vision/upload")
async def upload_for_estimation(file: UploadFile, db: Session):
    # 1. File Manager uloží (hloupý — neví co je "estimation")
    record = file_service.store(file, directory="loose")

    # 2. Business logika: vytvoř estimation
    estimation = TimeVisionEstimation(file_id=record.id, ...)
    db.add(estimation)

    return estimation
```

#### TimeVision — propojení s dílem (NOVÁ funkce!)

```python
# Uživatel v UI klikne "Link to Part"
@router.post("/time-vision/{estimation_id}/link-part")
async def link_to_part(estimation_id: int, part_id: int, db: Session):
    estimation = get_estimation_or_404(estimation_id, db)

    # Přidej vazbu: soubor → díl (soubor zůstává kde je)
    file_service.link(
        file_id=estimation.file_id,
        entity_type="part",
        entity_id=part_id,
        link_type="drawing",
    )
```

#### Quote — odkaz na existující soubor (ŽÁDNÝ nový upload)

```python
# quotes_router.py — jen link, soubor už existuje u dílu
@router.post("/quotes/{qid}/items/{item_id}/attach")
async def attach_drawing(qid: int, item_id: int, file_id: int, db: Session):
    # File Manager jen přidá vazbu
    file_service.link(file_id, "quote_item", item_id)
```

#### Budoucnost — CNC program

```python
# Nový cnc_router.py — File Manager se NEMĚNÍ
@router.post("/operations/{op_id}/programs")
async def upload_nc_program(op_id: int, file: UploadFile, db: Session):
    operation = get_operation_or_404(op_id, db)
    part = operation.part

    record = file_service.store(
        file,
        directory=f"programs/{part.part_number}",
        allowed_types=["nc", "gcode"],          # Rozšíření typů
    )
    file_service.link(record.id, "operation", op_id, link_type="nc_program")
```

---

### 7. Frontend: FileManagerModule.vue

**Floating window** v Gestima workspace systému (Split-pane pattern dle ADR-026):

```
┌─ FileManagerModule.vue ─────────────────────────────────────┐
│ LEFT: FileTreePanel.vue        │ RIGHT: FilePreviewPanel.vue│
│ ┌────────────────────────────┐ │ ┌────────────────────────┐ │
│ │ 🔍 Search...               │ │ │                        │ │
│ │ ── Filters ──              │ │ │   [PDF/STEP Preview]   │ │
│ │ [PDF] [STEP] [All]         │ │ │                        │ │
│ │ [Orphans] [Temp]           │ │ │   Metadata:            │ │
│ │                            │ │ │   Název: výkres_v3.pdf │ │
│ │ 📁 parts/ (234 files)      │ │ │   Typ: PDF, 2.1 MB    │ │
│ │   📁 10900635/ (3)         │ │ │   Hash: abc123...      │ │
│ │     📄 rev_A.pdf ★         │ │ │   Nahráno: 2026-02-15  │ │
│ │     📄 rev_B.pdf           │ │ │                        │ │
│ │     📐 model.step          │ │ │   ── Vazby ──          │ │
│ │   📁 0044976/ (1)          │ │ │   🔗 Part 10900635 ★   │ │
│ │ 📁 loose/ (12 files)       │ │ │   🔗 TV Estimation #42 │ │
│ │   📄 JR_810665.pdf         │ │ │   🔗 Quote #Q-0001     │ │
│ │ 📁 temp/ (2 files, 3h)     │ │ │                        │ │
│ │                            │ │ │   [Link to Part...]    │ │
│ │ ── Drag & Drop ──          │ │ │   [Download]           │ │
│ │ [📎 Drop files here]       │ │ │   [Archive]  [Delete]  │ │
│ └────────────────────────────┘ │ └────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Priority:**
- P1: Browse souborů s tree view (read-only)
- P1: Preview PDF/STEP
- P1: Metadata + vazby
- P2: Drag & drop upload
- P2: Link to Part (propojení loose → part)
- P3: Orphan management (admin)
- P3: Batch operace

---

### 8. Migrace dat

#### Krok 1: Vytvoř nové tabulky
```sql
CREATE TABLE file_records (...);
CREATE TABLE file_links (...);
```

#### Krok 2: Migruj existující Drawing záznamy
```python
for drawing in db.query(Drawing).all():
    record = FileRecord(
        file_hash=drawing.file_hash,
        file_path=drawing.file_path,        # Zachovej existující cestu!
        original_filename=drawing.filename,
        file_size=drawing.file_size,
        file_type=drawing.file_type,
        mime_type="application/pdf" if drawing.file_type == "pdf" else "application/step",
        status="active",
    )
    link = FileLink(
        file_id=record.id,
        entity_type="part",
        entity_id=drawing.part_id,
        is_primary=drawing.is_primary,
        revision=drawing.revision,
        link_type="drawing" if drawing.file_type == "pdf" else "step_model",
    )
```

#### Krok 3: Migruj TimeVision odkazy
```python
for estimation in db.query(TimeVisionEstimation).all():
    # Najdi nebo vytvoř FileRecord pro tento PDF
    record = find_or_create_file_record(estimation.pdf_path, estimation.pdf_filename)
    estimation.file_id = record.id          # Nový FK sloupec
```

#### Krok 4: Legacy kompatibilita
```python
# Part.drawing_path → computed property přes FileLink
@property
def drawing_path(self):
    primary = file_service.get_primary("part", self.id, "drawing")
    return primary.file_path if primary else None
```

**DŮLEŽITÉ:** Fyzické soubory se NEPŘESOUVAJÍ v první fázi! Cesty v DB zůstávají. Reorganizace adresářů je volitelný krok 2.

---

### 9. Co se smaže / deprecatuje

| Stávající | Akce | Kdy |
|-----------|------|-----|
| `Drawing` model | Zachovat jako view/proxy → přesměrovat na FileRecord+FileLink | Phase 2 |
| `Drawing` model | Smazat | Phase 3 (po ověření) |
| `Part.drawing_path` sloupec | Computed property z FileLink | Phase 2 |
| `Part.drawing_path` sloupec | DROP column | Phase 3 |
| `TimeVisionEstimation.pdf_filename` | Nahradit `file_id` FK | Phase 2 |
| `TimeVisionEstimation.pdf_path` | Smazat (redundantní s FileRecord.file_path) | Phase 2 |
| `uploads_router.py` temp dict | Nahradit `FileRecord(status="temp")` | Phase 2 |
| `step_router.py` | Nahradit `/api/files/{id}/download` | Phase 2 |
| `StaticFiles("/uploads")` mount | Nahradit `/api/files/{id}/download` (s auth!) | Phase 2 |

---

## Implementační fáze

### Phase 1: Backend základ ✅ DONE (2026-02-15)
- [x] `FileRecord` + `FileLink` modely → `app/models/file_record.py`
- [x] Alembic migrace → `file_records` + `file_links` tabulky vytvořeny
- [x] `FileService` (5 core + 7 helper metod) → `app/services/file_service.py` (809 LOC)
- [x] `/api/files/` router (9 endpointů) → `app/routers/files_router.py` (608 LOC)
- [x] Pydantic schemas → `app/schemas/file_record.py` (167 LOC)
- [x] Testy → 37/37 passed (`test_file_record.py`, `test_file_service.py`, `test_files_router.py`)
- [ ] ~~Migrace dat z Drawing → FileRecord~~ (odloženo na Phase 2)
- [ ] ~~`TimeVisionEstimation.file_id` FK~~ (odloženo na Phase 2)
- [ ] ~~Temp files v DB místo in-memory dict~~ (odloženo na Phase 2)

**DŮLEŽITÉ:** Phase 1 vytvořila novou infrastrukturu VEDLE stávající.
Stávající moduly (drawings_router, time_vision_router, parts_router) jsou NEDOTČENÉ.
Obě soustavy koexistují — stará funguje v produkci, nová je připravena ale prázdná.

### Phase 2a: TimeVision → FileManager ✅ DONE (2026-02-15)
- [x] `TimeVisionEstimation.file_id` FK sloupec → alembic migrace `y8z9a0b1c2d3`
- [x] Migrace dat: 68 PDF → FileRecord, 79/79 estimations linked, 73 active FileLinks
- [x] Migrační script: `scripts/migrate_timevision_files.py` (idempotentní, UPSERT)
- [x] FileLink cleanup: max 2 per file (1× time_v1 + 1× features_v2), jen newest estimation
- [x] Refaktor `time_vision_router.py` → `file_id` preferován, filename fallback
- [x] `ProcessRequest` schema: `file_id` + `filename` (backward compat)
- [x] UPSERT logika: file_id match preferován nad filename match
- [x] `list_drawings()` vrací `file_id` z FileRecord
- [x] Frontend: typy, API, store, komponenty — vše podporuje file_id
- [x] V1/V2 konzistence zachována (68 time_v1 + 11 features_v2 = 79 linked)
- [x] Nový endpoint `GET /api/files/{id}/preview` — bez auth, jen PDF, Content-Disposition: inline
- [x] `FilePreviewPanel.vue` používá preview endpoint (iframe + `#view=Fit`)
- [x] `TimeVisionPdfPreview.vue` používá filename-based endpoint (pdf.js nemůže poslat auth)
- [x] `file_service.serve_file()` → `content_disposition_type="inline"`

### Phase 2b: Ostatní moduly (PENDING)
- [ ] Migrace dat: `Drawing` záznamy → `FileRecord` + `FileLink` (migrační script)
- [ ] Refaktor `drawings_router.py` → volá `file_service` místo `DrawingService`
- [ ] Refaktor `uploads_router.py` → temp files přes `FileRecord(status="temp")`
- [ ] `FileManagerModule.vue` (floating window)
- [ ] `FileTreePanel.vue` + `FilePreviewPanel.vue`
- [ ] Refaktor `DrawingsManagementModal.vue` → volá `/api/files/`
- [ ] `PartDrawingWindow.vue` → file_id místo part_number

### Phase 3: Cleanup (PENDING — až po ověření Phase 2)
- [ ] Smazat `Drawing` model
- [ ] Smazat `DrawingService`
- [ ] Smazat `Part.drawing_path` sloupec
- [ ] Smazat `step_router.py`
- [ ] Odstranit `StaticFiles("/uploads")` mount
- [ ] Reorganizace adresářů na disku (volitelné)

## Known Limitations

1. **Fyzické soubory se nepřesouvají** v Phase 1 — reorganizace je Phase 3
2. **Polymorfní FK** (`entity_type` + `entity_id`) nemá DB-level foreign key constraint — validace v aplikační vrstvě
3. **Globální deduplikace** (stejný hash = uložit jen jednou) zatím neimplementována — může přijít později
4. **Preview endpoint bez auth** — `GET /api/files/{id}/preview` nemá auth dependency (iframe/pdf.js nemůže poslat Authorization header). Omezeno na PDF soubory. Download endpoint (`/download`) vyžaduje auth.
5. **TimeVision PDF preview** — používá filename-based endpoint (`/api/time-vision/drawings/{filename}/pdf`, bez auth) protože pdf.js (`pdfjsLib.getDocument`) posílá XHR bez Authorization headeru

## Alternativy (zamítnuté)

1. **"Chytrý" File Manager** — FM řídí business logiku per entity_type → neudržitelný, nekonečné if/else
2. **S3/MinIO** — overkill pro on-premise SQLite deployment, přidat později pokud potřeba
3. **Nechat jak je** — fragmentace se bude zhoršovat s každým novým modulem
