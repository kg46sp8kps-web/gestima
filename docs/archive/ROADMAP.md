# ROADMAP - Plán vývoje KALKULATOR3000

**Verze:** 9.1 → 10.0  
**Poslední aktualizace:** 2026-01-21  
**Účel:** Dlouhodobý plán vývoje a prioritizace úloh

---

## 🎯 CÍLE

### Krátkodobé (1-2 týdny):
- ✅ Dokončit základní funkcionalitu v9.0
- ✅ Opravit kritické bugy (BUG-001 až BUG-003)
- ✅ Otestovat výpočty a zobrazení

### Střednědobé (1 měsíc):
- ⏳ Dokončit středně prioritní bugy (BUG-004 až BUG-007)
- ⏳ Refaktoring batch_optimizer.py na v9.0
- ⏳ Přidat validaci dat

### Dlouhodobé (2-3 měsíce):
- ⏳ AI Vision integrace a testování
- ⏳ Export do Excel/PDF
- ⏳ Learning systém (sběr skutečných časů)
- ⏳ Migrace na SQL databázi (volitelné)

---

## 📅 TIMELINE

### FÁZE 1: Dokončení základní funkcionality (Týden 1-2)

**Cíl:** Opravit kritické bugy a dokončit základní funkcionalitu

**Úlohy:**
- [x] Backend API - hotovo
- [x] Základní UI - hotovo
- [ ] **BUG-001:** Cenový ribbon (chybí endpoint)
- [ ] **BUG-002:** Zobrazení strojního času
- [ ] **BUG-003:** Test přepočtu MODE

**Kritéria dokončení:**
- Všechny kritické bugy opraveny
- Základní funkcionalita funguje
- Výpočty se zobrazují v UI

---

### FÁZE 2: Vylepšení UX (Týden 3-4)

**Cíl:** Vylepšit uživatelský zážitek a opravit středně prioritní bugy

**Úlohy:**
- [ ] **BUG-004:** Vizuální indikace zamykání
- [ ] **BUG-005:** Tvorba dávek
- [ ] **BUG-006:** Výběr stroje
- [ ] **BUG-007:** Přepočet při změně materiálu
- [ ] Toast notifikace (chyby, úspěchy)

**Kritéria dokončení:**
- Všechny středně prioritní bugy opraveny
- UX je intuitivní
- Uživatel vidí feedback na akce

---

### FÁZE 3: Optimalizace a refaktoring (Týden 5-6)

**Cíl:** Refaktoring starého kódu a optimalizace

**Úlohy:**
- [ ] Refaktoring `batch_optimizer.py` na v9.0 model
- [ ] Validace dat při vytváření/úpravě
- [ ] Optimalizace výpočtů (caching)
- [ ] Zlepšení error handlingu

**Kritéria dokončení:**
- Starý kód refaktorován
- Validace funguje
- Aplikace je rychlejší

---

### FÁZE 4: Rozšíření funkcionality (Týden 7-8)

**Cíl:** Přidat nové funkce

**Úlohy:**
- [ ] Export kalkulace do Excel
- [ ] Export kalkulace do PDF
- [ ] AI Vision testování a vylepšení
- [ ] Learning systém (základní)

**Kritéria dokončení:**
- Export funguje
- AI Vision je otestováno
- Learning systém sbírá data

---

### FÁZE 5: Pokročilé funkce (Týden 9-12)

**Cíl:** Pokročilé funkce a vylepšení

**Úlohy:**
- [ ] Learning systém (korekční faktory)
- [ ] G-kód parser
- [ ] Vizualizace dílu (SVG)
- [ ] Migrace na SQL (volitelné)

**Kritéria dokončení:**
- Learning systém funguje
- Vizualizace zobrazuje díl
- Systém je připraven na produkci

---

## 🔴 KRITICKÉ ÚLOHY (P1)

| ID | Úloha | Status | Deadline |
|----|-------|--------|----------|
| P1 | BUG-001: Cenový ribbon | ❌ | Týden 1 |
| P2 | BUG-002: Zobrazení času | ❌ | Týden 1 |
| P3 | BUG-003: Test MODE přepočtu | ⚠️ | Týden 1 |

---

## 🟡 DŮLEŽITÉ ÚLOHY (P2)

| ID | Úloha | Status | Deadline |
|----|-------|--------|----------|
| P4 | BUG-004: Vizuální zamykání | ⚠️ | Týden 2 |
| P5 | BUG-005: Tvorba dávek | ❌ | Týden 2 |
| P6 | BUG-006: Výběr stroje | ❌ | Týden 2 |
| P7 | BUG-007: Změna materiálu | ❌ | Týden 2 |

---

## 🟢 ROZŠÍŘENÍ (P3)

| ID | Úloha | Status | Deadline |
|----|-------|--------|----------|
| P8 | Refaktoring batch_optimizer | ⏳ | Týden 3 |
| P9 | Toast notifikace | ⏳ | Týden 3 |
| P10 | Validace dat | ⏳ | Týden 3 |
| P11 | Export do Excel | ⏳ | Týden 4 |
| P12 | AI Vision testování | ⏳ | Týden 4 |

---

## 📊 METRIKY ÚSPĚCHU

### Technické metriky:
- **Pokrytí funkcionalitou:** 100% základních funkcí
- **Počet bugů:** < 5 aktivních bugů
- **Výkon:** < 2s načtení stránky
- **Stabilita:** 0 kritických chyb

### Business metriky:
- **Použitelnost:** Technolog může vytvořit díl za < 10 minut
- **Přesnost:** Kalkulace časů ±10% od skutečnosti
- **Produktivita:** 50% rychlejší než manuální kalkulace

---

## 🚧 RIZIKA A MITIGACE

### Riziko 1: Starý kód (batch_optimizer.py)
- **Riziko:** Používá legacy modely, nefunguje s v9.0
- **Mitigace:** Refaktoring v FÁZI 3
- **Priorita:** Střední

### Riziko 2: Excel databáze
- **Riziko:** Pomalé pro velké objemy dat
- **Mitigace:** Migrace na SQL v FÁZI 5 (volitelné)
- **Priorita:** Nízká (aktuálně stačí)

### Riziko 3: AI Vision náklady
- **Riziko:** OpenAI API může být drahé
- **Mitigace:** Optimalizace promptů, caching
- **Priorita:** Střední

---

## 🔄 ITERACE A FEEDBACK

### Týdenní review:
- **Pondělí:** Plánování týdne
- **Středa:** Kontrola progresu
- **Pátek:** Review a plánování dalšího týdne

### Feedback loop:
1. **Implementace** - Cursor + Ladislav
2. **Testování** - Ladislav
3. **Feedback** - Ladislav → Cursor
4. **Oprava** - Cursor
5. **Dokončení** - Aktualizace dokumentace

---

## 📝 POZNÁMKY

### Změny v plánu:
- Plán je flexibilní, může se měnit podle priorit
- Nové bugy mají přednost před rozšířeními
- Feedback uživatelů může změnit prioritu

### Dokumentace:
- Po každé fázi aktualizovat `AKTUALNI_STAV.md`
- Po opravě bugu aktualizovat `BUGY.md`
- Po dokončení fáze aktualizovat tento `ROADMAP.md`

### TODO - Admin konzole:
- **Drilling koeficienty:** `_apply_drilling_coefficients()` v `cutting_conditions.py` - tabulka koeficientů pro různé průměry vrtáků
  - Aktuálně hardcoded: `[(3mm, k_vc=0.60, k_f=0.25), (6mm, 0.70, 0.40), ..., (40mm+, 0.85, 1.25)]`
  - **Účel:** Korekce Vc a f podle průměru vrtáku (malé vrtáky = nižší Vc)
  - **Implementovat:** DB tabulka `drilling_coefficients` + admin UI pro editaci
  - **Kdy:** Při implementaci administrace nástrojů a řezných podmínek

---

## ✅ CHECKLIST PRO KAŽDOU FÁZI

- [ ] Všechny úlohy dokončeny
- [ ] Všechny bugy opraveny
- [ ] Testování dokončeno
- [ ] Dokumentace aktualizována
- [ ] Feedback získán
- [ ] Další fáze naplánována

---

*Verze 1.0 - Dlouhodobý plán vývoje*
