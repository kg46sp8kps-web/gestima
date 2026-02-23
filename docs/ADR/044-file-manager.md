# ADR-044: Centrální File Manager [PARTIAL — fáze 1+2a hotová, 2b-3 pending]
> Archive: docs/ADR/archive/044-file-manager.md — Claude může požádat o přečtení

## Rozhodnutí
Centrální "hloupý" FileManager — jen storage + registr, business logika zůstává v routerech které volají FileService.

## Pattern
- `app/services/file_service.py` — FileService (fyzické operace)
- `app/models/file_record.py` — FileRecord + FileLink modely
- `app/routers/` — business logika v příslušných routerech

## Nesmíš
- vkládat business logiku do FileService
- přistupovat k filesystému mimo FileService
- přeskočit FileLink při napojení souboru na entitu
