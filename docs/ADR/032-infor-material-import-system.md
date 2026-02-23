# ADR-032: Infor Material Import [ACCEPTED]
> Archive: docs/ADR/archive/032-infor-material-import-system.md — Claude může požádat o přečtení

## Rozhodnutí
Materiály se importují z Infor SLItems IDO (ne z Excelu) — parser detekuje MaterialGroup a StockShape z kódu položky automaticky.

## Pattern
- `app/services/infor_material_importer.py` — SLItems → MaterialItem
- `app/services/infor_importer_base.py` — generický base class
- `app/routers/infor_import_router.py` — preview + execute endpointy

## Nesmíš
- manuální Excel import materiálů
- hardcodeovat material mapping v kódu
- importovat bez preview/validate fáze
