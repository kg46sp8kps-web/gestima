# KONTEXT - KALKULATOR3000

**Verze:** 9.1  
**Poslední aktualizace:** 2026-01-21  
**Účel:** Kontext aplikace, účel, technologie, historie a závislosti

---

## 🎯 ÚČEL APLIKACE

**KALKULATOR3000** je webová aplikace pro kalkulaci CNC obrábění kovových dílů. Systém umožňuje:

1. **Správa dílů** - vytváření a editace dílů s technologickými postupy
2. **Kalkulace časů** - automatický výpočet strojních časů pro různé operace
3. **Cenová kalkulace** - výpočet nákladů na materiál, strojní čas, seřízení
4. **Optimalizace dávek** - výběr optimálního stroje a režimu podle velikosti dávky
5. **AI Vision** - automatické rozpoznání operací z PDF výkresů (GPT-4o)

### Cílová skupina:
- **KOVO RYBKA** - výrobní firma specializující se na CNC obrábění
- Technologové - vytváření technologických postupů
- Kalkulanti - výpočet cen pro nabídky
- Vedení - přehled nákladů a optimalizace výroby

---

## 🏢 DOMÉNA A BUSINESS LOGIKA

### Typy operací:
- **Soustružení** - face, od_rough, od_finish, id_rough, id_finish, thread_od, thread_id, groove_*, parting
- **Vrtání** - center_drill, drill, drill_deep, ream, tap
- **Live tooling** - lt_drill, lt_tap, lt_flat, lt_slot, lt_polygon, lt_keyway
- **Frézování** - mill_face, mill_pocket, mill_slot, mill_contour, mill_3d
- **Broušení** - grind_od, grind_id, grind_face
- **Dokončovací** - hone, polish, deburr_manual

### Strojní park:
- **MASTURN32** - malý soustruh (700 Kč/hod)
- **SMARTURN160** - střední soustruh (1000 Kč/hod)
- **NLX2000** - velký soustruh (1300 Kč/hod)
- **NZX2000** - velký soustruh s podavačem (1500 Kč/hod)
- **MCV750** - frézka (800 Kč/hod)
- **DMU50** - 5osá frézka (1200 Kč/hod)

### Materiály:
- **Konstrukční ocel** - základní skupina
- **Nerezová ocel** - vyšší koeficienty
- **Hliník** - jiné řezné podmínky
- **Plasty** - speciální podmínky

### Řezné režimy:
- **LOW** - nízký výkon, nízké opotřebení nástroje
- **MID** - střední výkon (výchozí)
- **HIGH** - vysoký výkon, vyšší opotřebení

---

## 🛠️ TECHNOLOGIE

### Backend:
- **Python 3.x** - programovací jazyk
- **Flask 2.3+** - web framework
- **Pandas 2.0+** - práce s Excel soubory
- **OpenPyXL 3.1+** - čtení/zápis Excel
- **OpenAI API** - GPT-4o Vision pro analýzu výkresů
- **PyMuPDF** - PDF parsing

### Frontend:
- **Jinja2** - templating engine (server-side)
- **Vanilla JavaScript** - žádný framework
- **Bootstrap 5** - CSS framework (CDN)
- **Font Awesome** - ikony (CDN)
- **CSS moduly** - vlastní styly rozdělené do modulů

### Datové úložiště:
- **Excel soubory** - všechny data v `data/` adresáři
- **CSV kompatibilita** - možnost exportu/importu

### Deployment:
- **Lokální vývoj** - Flask development server
- **Produkce** - (není specifikováno, pravděpodobně WSGI server)

---

## 📚 HISTORIE A VÝVOJ

### Verze 9.1 (aktuální):
- **Zjednodušená architektura** - PART → OPERATION → FEATURE + BATCH
- **Odstraněny** MasterOperation, BatchOperation, BatchConfig
- **Zamykání hodnot** - možnost zamknout Vc/f/Ap a setup_time/operation_time
- **CSS opraveno** - importy modulů

### Verze 9.0:
- **Refaktoring** - zjednodušení datového modelu
- **Nové API** - REST endpointy
- **Frontend rewrite** - nové UI s tmavým tématem

### Verze 8.x (starší):
- **MasterOperation + BatchOperation** - složitější model
- **TPVVariant** - varianty technologických postupů
- **is_variable** - příznak variabilních operací

### Verze 7.x:
- **Feature Calculator** - kompletní přepis výpočtů
- **51 typů kroků** - podpora všech operací
- **Batch Optimizer** - automatická optimalizace

### Verze 5.x:
- **AI Vision** - integrace GPT-4o Vision
- **AI Process Builder** - automatické vytváření technologických postupů
- **Learning systém** - sběr skutečných časů

### Verze 2.x:
- **Základní funkcionalita** - správa dílů a operací
- **Excel databáze** - přechod na Excel místo SQL

---

## 🔗 ZÁVISLOSTI A EXTERNÍ SLUŽBY

### OpenAI API:
- **Účel:** Analýza PDF výkresů, rozpoznání operací
- **Model:** GPT-4o Vision
- **Konfigurace:** API klíč v `config.py` nebo `OPENAI_API_KEY` env variable
- **Cena:** cca $0.01-0.03 za jeden výkres
- **Endpoint:** `https://api.openai.com/v1/chat/completions`

### CDN závislosti:
- **Bootstrap 5** - CSS framework (CDN)
- **Font Awesome** - ikony (CDN)
- **Poznámka:** Aplikace vyžaduje internet pro načtení CSS/JS z CDN

---

## 📁 STRUKTURA PROJEKTU

```
uhy/
├── app.py                    # Flask aplikace (entry point)
├── config.py                 # Konfigurace (verze, API klíče)
├── requirements.txt          # Python závislosti
├── NAVOD_SPUSTENI.md         # Návod ke spuštění
│
├── core/                     # Business logika
│   ├── __init__.py
│   ├── db/                   # Databázová vrstva
│   │   ├── database.py       # Agregátor
│   │   ├── parts.py
│   │   ├── operations.py
│   │   ├── batches.py
│   │   └── features.py
│   ├── models/               # Datové modely
│   │   ├── part.py
│   │   ├── operation.py
│   │   ├── batch.py
│   │   ├── feature.py
│   │   └── enums.py
│   ├── feature_calculator.py # Výpočet časů
│   ├── cutting_conditions.py # Řezné podmínky
│   ├── price_calculator.py   # Cenová kalkulace
│   ├── batch_optimizer.py    # Optimalizace
│   ├── ai_vision.py          # AI Vision
│   └── ...
│
├── routes/                   # Routes a API
│   ├── __init__.py
│   ├── parts.py              # HTML views
│   └── api/                  # REST API
│       ├── parts.py
│       ├── operations.py
│       ├── features.py
│       └── batches.py
│
├── templates/                # Jinja2 šablony
│   ├── base.html
│   ├── index.html
│   └── parts/
│       ├── edit.html
│       └── partials/
│
├── static/                   # Statické soubory
│   ├── css/
│   ├── js/
│   └── img/
│
├── data/                     # Excel databáze
│   ├── parts.xlsx
│   ├── operations.xlsx
│   ├── batches.xlsx
│   ├── features.xlsx
│   └── ...
│
└── __zaloha knowledge/       # Dokumentace
    └── 2001/
        ├── 03_CURRENT_STATE.md
        └── 06_REFACTORING_PLAN.md
```

---

## 🔐 KONFIGURACE A NASTAVENÍ

### Konfigurační soubor (`config.py`):
```python
APP_VERSION = "5.3.3"  # Verze aplikace
OPENAI_API_KEY = "sk-..."  # OpenAI API klíč
DEFAULT_MARGIN = 0.25  # 25% marže
DEFAULT_EFFICIENCY = 0.85  # 85% efektivita
DEFAULT_SETUP_TIME = 30  # Seřizovací čas [min]
AI_MODEL = "gpt-4o"  # AI model
MACHINE_RATES = {...}  # Sazby strojů [Kč/hod]
```

### Environment variables:
- `OPENAI_API_KEY` - OpenAI API klíč (má přednost před config.py)
- `SECRET_KEY` - Flask secret key (vývoj: 'dev-key-change-in-prod')

### Data directory:
- `data/` - Excel soubory s daty
- Cesta: `core/db/base.py` → `DATA_DIR = Path(__file__).parent.parent.parent / "data"`

---

## 🎓 BUSINESS PRAVIDLA

### Výpočet strojního času:
1. **Otáčky:** `n = (1000 × Vc) / (π × D)`
2. **Strojní čas:** `t = (L / (n × f)) × 60` [sekundy]
3. **Počet průchodů:** `i = ceil(přídavek / Ap)`
4. **Celkový čas:** `total = t × i`

### Výpočet ceny:
1. **Materiál:** `hmotnost [kg] × cena/kg`
2. **Strojní čas:** `čas [hod] × sazba [Kč/hod]`
3. **Seřízení:** `setup_time [min] × sazba / 60 / dávka`
4. **Kooperace:** `cena + minimální cena za dávku`
5. **Celkem:** `materiál + strojní + seřízení + kooperace`

### Výběr stroje:
- **Malá série** (< 2h průběžný čas) → SMARTURN160
- **Série** (2-5h) → NLX2000
- **Velká série** (> 5h) → NZX2000 (s podavačem)

### Zamykání hodnot:
- Ruční změna Vc/f/Ap → automaticky zamkne (`*_locked = True`)
- Reset na 0/NULL/'' → odemkne a načte doporučenou hodnotu
- Zamčené hodnoty se nepřepočítávají při změně MODE

---

## 🚨 LIMITACE A OMEZENÍ

### Technické:
- **Excel databáze** - žádná transakčnost, pomalejší pro velké objemy
- **Single-threaded** - Flask development server (vývoj)
- **CDN závislost** - Bootstrap a Font Awesome vyžadují internet

### Funkční:
- **Chybí endpoint** - `/api/parts/{id}/all-batch-prices` (pro cenový ribbon)
- **Starý optimizer** - `batch_optimizer.py` používá starý model (v8.0)
- **AI Vision** - vyžaduje OpenAI API klíč a internet

### Datové:
- **Žádná validace** - Excel soubory se nevalidují při načtení
- **Žádné zálohování** - automatické zálohy nejsou implementovány
- **Žádná migrace** - změny schématu vyžadují ruční úpravu Excel

---

## 📖 DOKUMENTACE A ZDROJE

### Interní dokumentace:
- `ARCHITEKTURA.md` - struktura systému
- `AKTUALNI_STAV.md` - co funguje, co nefunguje
- `BUGY.md` - známé bugy a problémy
- `NAVOD_SPUSTENI.md` - návod ke spuštění

### Externí dokumentace:
- **Flask:** https://flask.palletsprojects.com/
- **Pandas:** https://pandas.pydata.org/
- **OpenAI API:** https://platform.openai.com/docs/

---

## 🔄 WORKFLOW A PROCESY

### Vytvoření nového dílu:
1. Uživatel vytvoří díl (`/parts/new`)
2. Vyplní základní info (číslo, název, materiál, polotovar)
3. Přidá operace (soustružení, frézování...)
4. Přidá kroky do operací (face, od_rough, drill...)
5. Systém automaticky vypočítá časy a ceny
6. Uživatel může upravit řezné podmínky (Vc/f/Ap)
7. Vytvoří dávky pro různé velikosti
8. Zobrazí cenový přehled

### AI Import výkresu:
1. Uživatel nahraje PDF výkres
2. AI Vision analyzuje výkres (GPT-4o)
3. Rozpozná operace, rozměry, tolerance
4. Uživatel zkontroluje a upraví výsledky
5. Uloží jako nový díl

### Optimalizace dávky:
1. Uživatel vybere velikost dávky
2. Batch Optimizer vybere optimální stroj a režim
3. Přepočítá řezné podmínky pro nový stroj
4. Zobrazí náklady na kus

---

*Verze 9.1 - Kompletní kontext aplikace*
