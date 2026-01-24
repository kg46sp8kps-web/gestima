# ADR-002: Snapshot Pattern pro obchodní dokumenty

## Status
Přijato (22.1.2026)

## Kontext

Problém: Nabídky a zakázky musí mít **stabilní kalkulace** i po změně master dat.

**Příklad:**
- Leden: Nabídka 1500 Kč (materiál 11523)
- Únor: Změna materiálu na 42CrMo4
- Problém: Nabídka z ledna ukazuje novou cenu 2200 Kč ❌

## Rozhodnutí

**Snapshot Pattern** - při vytvoření dokumentu zmrazit kompletní stav do JSON.

### Implementace:
```python
class Quotation(Base):
    part_id = Column(Integer, ForeignKey("parts.id"))  # Živá vazba
    quotation_data = Column(JSON)  # Snapshot (~5 KB)
```

### Kdy snapshoty:
- ✅ Nabídky
- ✅ Výrobní zakázky
- ✅ Faktury
- ❌ Rozpracovaná kalkulace (live data)

## Alternativy

1. **Rekonstrukce z Audit Logu**
   - ❌ Tisíce SQL dotazů
   - ❌ Pomalé
   - ❌ Složité (historické ceny materiálů, strojů...)

2. **Denormalizované sloupce**
   - ⚠️ Funguje, ale inflexibilní
   - ⚠️ Desítky sloupců

3. **Event Sourcing**
   - ❌ Příliš komplexní pro tento use-case

## Důsledky

### Pozitivní
- ✅ Rychlé čtení (jeden SELECT)
- ✅ Stabilita dokumentů
- ✅ Audit compliance
- ✅ Možnost porovnání (snapshot vs aktuální stav)

### Negativní
- ⚠️ Redundance dat (~5 KB na dokument)
- ⚠️ Růst databáze: ~2.5 MB/rok pro 500 nabídek

### Vztah k Audit Logu
- **Audit Log:** Kdo co kdy změnil (delta)
- **Snapshot:** Jak dokument vypadal (kompletní stav)
- **Kombinace:** Audit log pro master data + Snapshot pro dokumenty

## Reference
- SAP: "Document Header" snapshot
- HELIOS: "Dokument Snapshot" tabulky
- Standardní ERP přístup
