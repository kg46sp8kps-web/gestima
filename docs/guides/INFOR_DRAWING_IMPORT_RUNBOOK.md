# Infor + Drawing Import Runbook

Datum: 2026-02-27

## 1) Aktualni importni toky

### A. Infor DB import (metadata + dokumenty)

- Manual admin import:
  - `/api/infor/import/*` (parts, routing, production, material_inputs)
  - `/api/infor/import/documents/*` (list -> preview -> execute)
- Automaticky sync:
  - `/api/infor/sync/*` + `InforSyncService`
  - kroky: `parts`, `materials`, `documents`, `operations`, `material_inputs`, `production`

Dokumenty z Inforu se importuji pres `InforDocumentImporter`:
- metadata: `list_documents()`
- parovani: `preview_import()`
- stazeni PDF: `download_document()`
- ulozeni: `file_service.store_from_bytes()` + `FileLink`

### B. Server import STEP/PDF (slozky dle artiklu)

- Admin panel: `/api/drawings/import/status|preview|execute`
- Service: `DrawingImportService`
- Import:
  - najde slozky
  - sparuje `folder_name -> Part.article_number`
  - importuje primary PDF + dalsi PDF + STEP
  - vytvori `FileRecord` + `FileLink`

Od 2026-02-27 umi tento import 2 rezimy:
- local path (legacy)
- SSH source bez mountu (nove)

## 2) Kriticke mezery (audit)

1. Parsovani drawing PDF bezi jen nad jednou stranou (`_pdf_to_base64_image`, page 0).
2. Neni deterministic parser PDF razitka (cislo vykresu/material) jako fallback mimo AI.
3. `InforDocumentImporter` matchuje dokument jen pres `article_number` tokeny v `DocumentName`.
4. STEP parser neni soucasti backend importu (STEP se uklada, ale neanalyzuje pri importu).
5. Bez telemetry metrik neni jednoduche merit kvalitu parovani/parsovani v case.

## 3) Presny navrh ciloveho rezimu

## Princip

- Infor DB import nech jako zdroj ERP dat.
- Server STEP/PDF import ber jako zdroj fyzickych souboru.
- V DEV i PROD pouzij stejny protokol: `ssh://`.
- Nepouzivej mount (`/Volumes`, SMB mapovani) jako zavislost.

## Konfigurace

V `.env`:

```env
DRAWINGS_SHARE_PATH=ssh://gestima@192.168.1.135:22/home/gestima/uploads/vykresy
```

Poznamka:
- local fallback stale funguje:
  - `DRAWINGS_SHARE_PATH=/absolutni/lokalni/cesta`

## Prerequisites (Mac dev + Linux server)

1. SSH key pro uzivatele, pod kterym bezi backend.
2. Passwordless auth (doporučeno `ed25519`).
3. Read pristup k remote slozce s vykresy.
4. Na hostu backendu dostupny `ssh` klient.

## Setup priklad

```bash
# 1) vygeneruj klic (pokud neni)
ssh-keygen -t ed25519 -C "gestima-drawing-import"

# 2) nahraj public key na server
ssh-copy-id gestima@192.168.1.135

# 3) over pristup
ssh gestima@192.168.1.135 'ls -la /home/gestima/uploads/vykresy | head'
```

## Otestovani po nasazeni

1. `GET /api/drawings/import/status` -> musi byt `is_accessible=true`.
2. `POST /api/drawings/import/preview` -> musi vratit slozky + match statistiky.
3. `POST /api/drawings/import/execute` na male sade.
4. Overit:
   - `FileRecord` pro PDF/STEP
   - `FileLink` (`drawing`, `step_model`)
   - `Part.file_id` nastavene na primary PDF

## 4) Doporuceni pro parser vykresu (next step)

1. Multi-page PDF analyza:
   - page 0 + strany s nejvyssi text density
   - nebo max 3 strany
2. Deterministic extraction fallback:
   - regex/OCR pro `drawing_number`, `revision`, `material norm`
3. Match quality telemetry:
   - logovat precision/recall labely z manual review v adminu
4. STEP post-import pipeline:
   - volitelne async zpracovani STEP po ulozeni (queue)

