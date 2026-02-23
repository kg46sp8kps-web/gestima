# ADR-003: Integer ID vs UUID pro primární klíče

## Status
Přijato (22.1.2026)

## Kontext

Otázka: Jaký typ primárního klíče použít pro Part, Operation, Feature?

**Požadavky:**
- Jedinečná identifikace
- Podpora pro budoucí moduly (poptávky, výroba, sklady)
- Výkon a jednoduchost

## Rozhodnutí

**Integer ID (auto-increment)** jako primární klíč.

UUID **není použito** - není potřeba pro single-database systém.

### Důvody:
1. **Výkon:** Integer JOIN rychlejší než UUID
2. **Jednoduchost:** Monolitická aplikace, jedna databáze
3. **Velikost:** Integer (4 B) vs UUID (16 B)
4. **Lidsky čitelné:** `/parts/123` vs `/parts/550e8400-...`

## Alternativy

1. **UUID jako primární klíč**
   - ❌ Pomalejší JOINy
   - ❌ Větší indexy
   - ✅ Distribuované systémy
   - ✅ Externí API (skrýt počet záznamů)

2. **Duální identifikace (Integer + UUID)**
   - ⚠️ Zbytečná komplexita pro současný scope
   - ✅ Možné přidat později

## Důsledky

### Pozitivní
- ✅ Rychlé JOINy
- ✅ Menší databáze
- ✅ Jednodušší debugging
- ✅ URL `/parts/123`

### Negativní
- ⚠️ Není vhodné pro externí API (odhaluje počet záznamů)
- ⚠️ Problémy při merge více instancí

### Kdy přidat UUID v budoucnu?

Pokud bude potřeba:
- Externí B2B API
- Offline-first mobile app
- Mikroservices architektura
- Integrace s externími ERP (SAP, Helios)

**Migrace:** UUID lze přidat později jako dodatečný sloupec bez změny FK vztahů.

## Reference
- Většina monolitických ERP používá Integer ID
- UUID typicky jen pro distribuované systémy
