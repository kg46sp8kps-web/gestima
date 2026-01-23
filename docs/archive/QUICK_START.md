# 🚀 QUICK START

## Setup (1x na začátku)
```bash
python3 gestima.py setup
```

## Spuštění aplikace
```bash
python3 gestima.py run
```
Otevři: http://localhost:8000

## Spuštění testů
```bash
python3 gestima.py test-critical
```

---

## 📋 Co je připraveno

### Dokumentace
- ✅ [ARCHITECTURE.md](ARCHITECTURE.md) - Architektura projektu
- ✅ [DB_ARCHITECTURE.md](DB_ARCHITECTURE.md) - Struktura databáze
- ✅ [FUTURE_STEPS.md](FUTURE_STEPS.md) - Bugy a úkoly (P1, P2, P3)
- ✅ [CLAUDE.md](CLAUDE.md) - **Pravidla pro AI asistenta**
- ✅ [COMMANDS.md](COMMANDS.md) - Všechny dostupné příkazy

### Skripty
- ✅ `python3 gestima.py run` - Spuštění aplikace
- ✅ `python3 gestima.py test` - Spuštění testů
- ✅ `python3 gestima.py setup` - Setup venv
- ✅ `./run.sh` - Shell script pro spuštění
- ✅ `./test.sh` - Shell script pro testy

### Aplikace
- ✅ FastAPI + SQLAlchemy
- ✅ 400+ řádků business logiky (time_calculator, price_calculator...)
- ✅ 8+ testovacích souborů
- ✅ Jinja2 + HTMX + Alpine.js frontend
- ✅ SQLite databáze s WAL mode

---

## 📊 Aktuální stav

### ✅ Funguje
```
Aplikace běží na http://localhost:8000
14 z 14 critical testů prochází ✓
Databáze je inicializovaná ✓
```

### 🔴 TODO (Priority Order)

**Týden 1 (P1 - Kritické):**
1. BUG-002: Zobrazení strojního času
2. BUG-003: Přepočet MODE (LOW/MID/HIGH)
3. BUG-001: Cenový ribbon

**Týden 2 (P2 - Důležité):**
4. BUG-006: Výběr stroje
5. BUG-007: Přepočet při změně materiálu
6. BUG-004: Vizuální indikace zamykání
7. BUG-005: Tvorba dávek

---

## 🎯 Workflows

### Vývoj (Workflw 1)
```bash
# Terminal 1: Spuštění aplikace
python3 gestima.py run

# Terminal 2: Testy
python3 gestima.py test-critical

# Browser: Otestuj manuálně
open http://localhost:8000
```

### Before Commit
```bash
# 1. Spusť testy
python3 gestima.py test-critical

# 2. Spusť app a otestuj manuálně
python3 gestima.py run

# 3. Commit
git add .
git commit -m "..."
```

---

## 🔗 Důležité linky

### API Docs (když je app spuštěná)
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Dokumentace
- [CLAUDE.md](CLAUDE.md) ← Čti PŘED implementací
- [LESSONS.md](docs/LESSONS.md) ← Neudělej stejné chyby
- [FUTURE_STEPS.md](FUTURE_STEPS.md) ← Co dělat

### Zdrojový kód
- Backend logika: [app/services/](app/services/)
- Databázové modely: [app/models/](app/models/)
- API routery: [app/routers/](app/routers/)
- Frontend: [app/templates/](app/templates/) + [app/static/](app/static/)

---

## 🚨 Troubleshooting

### App se nespustí
```bash
# Zkontroluj dependencies
python3 gestima.py setup

# Zkontroluj port (pokud je zablokaný)
lsof -i :8000
```

### Test selhává
```bash
# Reinstall dependencies
python3 gestima.py setup

# Run specific test
python3 gestima.py test -k "test_pricing"
```

### venv je rozbitý
```bash
# Smaž venv
rm -rf venv

# Vytvořit nový
python3 gestima.py setup
```

---

## 📚 Pro novou AI session

```
1. Přečti CLAUDE.md (pravidla)
2. Přečti FUTURE_STEPS.md (co dělat)
3. Přečti LESSONS.md (neudělej chyby)
4. Spusť: python3 gestima.py run
5. Implementuj bugfix
6. Testuj: python3 gestima.py test-critical
7. Commit: git commit -m "..."
```

---

**Status:** 🟢 Ready
**Last Update:** 2026-01-23
**Version:** 1.0.0
