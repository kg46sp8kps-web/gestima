# COMMANDS - Spouštění GESTIMA

## 🚀 Možnosti spuštění

### Možnost 1: Python Helper (DOPORUČENO)
```bash
python3 gestima.py run
```

Výhody:
- Bez manuálního aktivování venv
- Automaticky vrství cestu
- Funguje na všech OS (Windows, Mac, Linux)

### Možnost 2: Shell Script
```bash
./run.sh
```

### Možnost 3: Manuálně (bez helper)
```bash
source venv/bin/activate
uvicorn app.gestima_app:app --reload
```

---

## 📚 Všechny příkazy

### Setup (inicializace)
```bash
python3 gestima.py setup
```
- Vytvoří venv (pokud neexistuje)
- Instaluje dependencies z `requirements.txt`
- Upgrade pip

### Run (spuštění aplikace)
```bash
python3 gestima.py run
```
- Spustí FastAPI aplikaci na http://localhost:8000
- `--reload` = auto-restart při změně souborů
- Swagger API docs: http://localhost:8000/docs

### Test (spuštění testů)
```bash
# Všechny testy
python3 gestima.py test

# Specifický test
python3 gestima.py test -k test_time_calculation

# S verbose outputem
python3 gestima.py test -vv

# Pouze critical testy
python3 gestima.py test-critical
```

### Test-Critical (jen kritické testy)
```bash
python3 gestima.py test-critical
```
- Spustí testy označené `@pytest.mark.critical`
- Rychlejší (jenom nejdůležitější testy)

### Shell (Python REPL)
```bash
python3 gestima.py shell
```
- Interaktivní Python s venv aktivovaný
- Užitečné pro debugging

### Help
```bash
python3 gestima.py help
```
- Zobraz dostupné příkazy

---

## ⚡ Typický workflow vývoje

```bash
# Prvně: Setup (jen jednou)
python3 gestima.py setup

# Vývoj: V jednom terminálu
python3 gestima.py run

# Vývoj: V druhém terminálu (testy)
python3 gestima.py test-critical

# Během vývoje: Otevri aplikaci
open http://localhost:8000
```

---

## 🔍 Debug & Troubleshooting

### Venv není aktivován
```bash
source venv/bin/activate
which python  # Měl by být v venv/bin/
```

### Chybí dependencies
```bash
python3 gestima.py setup
# nebo
pip install -r requirements.txt
```

### Port 8000 je již používaný
```bash
# Najdi proces
lsof -i :8000

# Kill process
kill -9 <PID>

# nebo spusť na jiném portu
uvicorn app.gestima_app:app --port 8001
```

### Import error (modul nenalezen)
```bash
# Ujisti se, že venv je aktivovaný
python3 gestima.py shell
>>> import app  # Should work

# Pokud ne, zkus reinstall
pip install -r requirements.txt --force-reinstall
```

### Testy se nespustí
```bash
# Zkontroluj pytest instalaci
python3 gestima.py shell
>>> import pytest

# Pokud chybí, instaluj
pip install pytest pytest-asyncio
```

---

## 📊 API Endpoints

Jakmile je aplikace spuštěná (http://localhost:8000):

### Swagger UI (interaktivní docs)
```
http://localhost:8000/docs
```

### ReDoc (čitelnější docs)
```
http://localhost:8000/redoc
```

### Aplikace
```
http://localhost:8000/
http://localhost:8000/parts/
http://localhost:8000/parts/{id}/edit
```

---

## 🎯 Příklady

### Spustit aplikaci a otevřít v prohlížeči
```bash
python3 gestima.py run &
sleep 2
open http://localhost:8000
```

### Spustit testy s specifickým filtrem
```bash
python3 gestima.py test -k "pricing"
```

### Spustit testy v debug mode
```bash
python3 gestima.py test --pdb
```

### Instalovat nový package
```bash
source venv/bin/activate
pip install <package_name>

# nebo přímo
python3 gestima.py shell
>>> import subprocess
>>> subprocess.run(["pip", "install", "package_name"])
```

---

## 🔧 Konfigurování

### Environment variables (.env)
```bash
# .env soubor (vytvoř sám)
DEBUG=True
DATABASE_URL=sqlite+aiosqlite:///gestima.db
PORT=8000
```

Načítá se z: `app/config.py` (pydantic-settings)

---

## 📝 Checklist před commitem

```bash
# 1. Spustit testy
python3 gestima.py test-critical

# 2. Spustit app a ručně otestovat
python3 gestima.py run

# 3. Zkontrolovat kód (type hints)
python3 gestima.py shell
>>> from app.models import Part  # Should work

# 4. Git commit
git add .
git commit -m "..."
git push
```

---

## 🚀 Production (TODO)

```bash
# Production: bez --reload
uvicorn app.gestima_app:app --host 0.0.0.0 --port 8000

# s gunicorn (multiple workers)
pip install gunicorn
gunicorn app.gestima_app:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

**Aktualizace:** 2026-01-23
