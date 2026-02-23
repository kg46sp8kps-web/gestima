# ADR-044: Centrální File Manager

**Status:** Phase 1 + 2a DONE, Phase 2b-3 PENDING (2026-02-15)

## Context

~30 souborových touchpointů rozeseto přes 6 routerů, 2 služby a 3 modely. TimeVision matchuje soubory přes `pdf_filename` string (přejmenování = ztráta vazby), 2 různé cesty na disk, in-memory temp registry (restart = ztráta), flat adresář 105+ souborů, `/uploads/*` bez auth.

## Decision

**"Hloupý" File Manager** — pouze úložiště + registr, žádná business logika.
Business logika zůstává v příslušných routerech, které volají FileService pro fyzické operace.

## Key Files / Models

- `app/models/file_record.py` — `FileRecord` + `FileLink`
- `app/services/file_service.py` — `FileService` (5 core + 7 helper metod)
- `app/routers/files_router.py` — 9 endpointů `/api/files/`
- `app/schemas/file_record.py`
- `scripts/migrate_timevision_files.py` — idempotentní migrace

## Models

```python
class FileRecord(AuditMixin, Base):
    file_hash         = Column(String(64), index=True)       # SHA-256 (NOT unique)
    file_path         = Column(String(500), unique=True)     # Relativní: "parts/10900635/A.pdf"
    original_filename = Column(String(255))
    file_size         = Column(Integer)
    file_type         = Column(String(10), index=True)       # "pdf", "step", "nc"
    mime_type         = Column(String(100))
    status            = Column(String(20), default="active") # "temp"|"active"|"archived"

class FileLink(AuditMixin, Base):
    file_id     = Column(Integer, ForeignKey("file_records.id", ondelete="CASCADE"))
    entity_type = Column(String(50), index=True)    # "part", "timevision", "quote_item"
    entity_id   = Column(Integer, index=True)
    is_primary  = Column(Boolean, default=False)
    revision    = Column(String(2), nullable=True)  # "A", "B", "C"
    link_type   = Column(String(20), default="drawing")  # "drawing"|"step_model"|"nc_program"
```

Jeden soubor → více FileLinks (PDF je výkres dílu i zdroj pro TimeVision).

## FileService API (core)

```python
def store(file, directory, *, allowed_types) -> FileRecord
def get(file_id) -> FileRecord              # nebo 404
def link(file_id, entity_type, entity_id, *, is_primary, revision, link_type) -> FileLink
def unlink(file_id, entity_type, entity_id) -> None
def delete(file_id) -> None                 # soft delete, soubor na disku zůstává
```

## REST Endpoints

```
POST   /api/files/upload
GET    /api/files/{id}
GET    /api/files/{id}/preview              ← inline PDF, BEZ auth (pro iframe/pdf.js)
GET    /api/files/{id}/download             ← s auth
DELETE /api/files/{id}
POST   /api/files/{id}/link
DELETE /api/files/{id}/link/{entity_type}/{eid}
PUT    /api/files/{id}/primary/{entity_type}/{eid}
GET    /api/files?entity_type=X&entity_id=Y
```

## Directory Structure

```
uploads/
├── parts/{part_number}/     ← výkresy, STEP modely
├── quotes/{quote_number}/
├── loose/                   ← soubory bez vazby (TimeVision upload)
├── temp/                    ← dočasné (status="temp", auto-cleanup)
└── programs/{part_number}/  ← CNC programy (budoucnost)
```

## Implementation Phases

- **Phase 1 DONE:** FileRecord + FileLink modely, FileService, 9 endpointů, 37/37 testů
- **Phase 2a DONE:** TimeVision.file_id FK, migrace 68 PDF → FileRecord, 79 estimations linked
- **Phase 2b PENDING:** drawings_router refaktor, uploads_router, FileManagerModule.vue
- **Phase 3 PENDING:** Smazat Drawing model, DrawingService, step_router, StaticFiles mount

## Consequences

- Jeden centrální registr místo fragmentace v 6 routerech
- Polymorfní FileLink: přidání nové entity = nový řádek, BEZ schema změny
- Preview endpoint záměrně bez auth — iframe/pdf.js nemůže poslat Authorization header
- Fyzické soubory se v Phase 1-2 nepřesouvají — reorganizace adresářů je Phase 3 (volitelné)
- Phase 1 infrastruktura koexistuje se stávající (stará funguje, nová prázdná)

## Known Limitations

- Polymorfní FK (`entity_type` + `entity_id`) nemá DB-level constraint — validace v aplikaci
- Globální deduplikace (stejný hash = uložit jednou) zatím neimplementována
- TimeVision PDF preview: filename-based endpoint (pdf.js nemůže poslat auth header)
