# ADR-034: Infor Item Code Parsing [ACCEPTED]
> Archive: docs/ADR/archive/034-infor-item-code-parsing-patterns.md — Claude může požádat o přečtení

## Rozhodnutí
Infor item kódy jsou strukturované (materiál + tvar + rozměry + povrch) a parsují se regex patterny — ne AI, ne manuálně.

## Pattern
- `app/services/infor_material_importer.py` — regex patterns pro kódy jako "1.4301-KR-D20-P"

## Nesmíš
- parsovat Infor kódy pomocí AI
- parsovat ad-hoc string splits bez struktury
- ignorovat strukturu kódu při importu
