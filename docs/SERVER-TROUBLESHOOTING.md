# Server Troubleshooting Guide

## Default Admin Credentials

**Username:** `admin`
**Password:** `asdfghjkl`

Po prvním setupu nebo smazání DB, admin je vždy vytvořen s těmito credentials.

---

## Problém: Server nereaguje / nejede

### Rychlá diagnostika (30 sekund)

```bash
# 1. Běží vůbec?
ps aux | grep gestima | grep -v grep

# 2. Port 8000 obsazený?
lsof -i :8000

# 3. Health check
curl http://localhost:8000/health
```

---

## Řešení podle symptomů

### ✅ Server BĚŽÍ, ale nereaguje

**Symptomy:**
- `ps aux | grep gestima` vrací proces
- `curl http://localhost:8000/health` timeout nebo 500

**Řešení:**
```bash
# 1. Najdi PID procesu
ps aux | grep gestima | grep -v grep
# Výstup: lofas  43825  0.0  0.1  ...

# 2. Zabij proces
kill <PID>    # např. kill 43825

# 3. Restart
python3 gestima.py run
```

**Kdy to použít:**
- Server "zamrzl"
- Po změně kódu které --reload nezachytil
- Divné 500 chyby

---

### ❌ Server NEBĚŽÍ

**Symptomy:**
- `ps aux | grep gestima` nic nevrací
- `curl http://localhost:8000/health` → "Connection refused"

**Řešení:**
```bash
# Spustit na popředí (vidíš logy)
python3 gestima.py run

# NEBO na pozadí
nohup python3 gestima.py run > gestima_server.log 2>&1 &

# Sledovat logy
tail -f gestima_server.log
```

---

### 🔧 Pokročilé: Problém s portem 8000

**Symptomy:**
- Chyba "Address already in use"
- `lsof -i :8000` ukazuje jiný proces

**Řešení:**
```bash
# 1. Zjisti co drží port
lsof -i :8000

# 2. Zabij ten proces
kill <PID>

# 3. Restart GESTIMA
python3 gestima.py run
```

---

## Alpine.js / UI nefunguje

**Symptomy:**
- Login page načtená, ale tlačítko "Přihlašování..." zamrzlé
- RSS zprávy se nenačítají (spinner točí donekonečna)
- Console: `Uncaught EvalError: 'unsafe-eval' is not allowed`

**Root cause:**
- Alpine.js VYŽADUJE `'unsafe-eval'` v CSP (Content Security Policy)
- Používá `new AsyncFunction()` pro reaktivitu

**Fix:**
```python
# app/gestima_app.py - CSP headers
"script-src 'self' 'unsafe-inline' 'unsafe-eval'"  # ✅ Správně
"script-src 'self' 'unsafe-inline'"                 # ❌ Alpine.js nefunguje
```

**Ověření:**
```bash
# Test CSP headers
curl -I http://localhost:8000 | grep -i content-security

# Mělo by vrátit:
# content-security-policy: ... script-src 'self' 'unsafe-inline' 'unsafe-eval' ...
```

---

## Běžné chyby a fixes

### Import Error / Module Not Found

**Chyba:**
```
ModuleNotFoundError: No module named 'uvicorn'
```

**Fix:**
```bash
# 1. Zkontroluj Python verzi
python3 --version  # Musí být 3.9+

# 2. Reinstaluj závislosti
pip3 install -r requirements.txt

# 3. Restart
python3 gestima.py run
```

---

### Database Locked

**Chyba:**
```
sqlite3.OperationalError: database is locked
```

**Fix:**
```bash
# 1. Zastav všechny procesy
pkill -f gestima

# 2. Smaž lock soubory
rm -f gestima.db-shm gestima.db-wal

# 3. Restart
python3 gestima.py run
```

---

### Port Permission Denied

**Chyba:**
```
OSError: [Errno 13] Permission denied
```

**Fix:**
```bash
# Použij port > 1024 (nepotřebuje sudo)
# V app/gestima_app.py změň port na 8000 (default je OK)

# NEBO spusť s sudo (nedoporučeno)
sudo python3 gestima.py run  # ❌ Avoid this
```

---

## Checklist před eskalací

Pokud nic nefunguje, projdi tohle:

- [ ] `python3 --version` → Je 3.9+?
- [ ] `pip3 list | grep fastapi` → Je nainstalované?
- [ ] `ls -lh gestima.db` → Existuje databáze?
- [ ] `tail -50 gestima_server.log` → Co říkají logy?
- [ ] `curl http://localhost:8000/health` → Co vrací?
- [ ] `git status` → Nejsou uncommited změny které rozbily kód?

---

## Pomocné příkazy

```bash
# Kompletní restart (hard reset)
pkill -f gestima && sleep 2 && python3 gestima.py run

# Sledovat logy v real-time
tail -f gestima_server.log

# Testovat jestli server odpovídá
watch -n 2 'curl -s http://localhost:8000/health | jq .'

# Najít všechny Python procesy
ps aux | grep python

# Uvolnit port 8000 násilím
lsof -ti :8000 | xargs kill -9
```

---

## Offline Mode (Vendor Files)

**GESTIMA běží 100% OFFLINE!**

JavaScript knihovny jsou **lokální**:
- `app/static/js/vendor/alpine.min.js` (43 KB)
- `app/static/js/vendor/htmx.min.js` (48 KB)

**Pokud chybí:**
```bash
# Stáhnout znovu
curl -L https://unpkg.com/alpinejs@3.13.5/dist/cdn.min.js \
  -o app/static/js/vendor/alpine.min.js

curl -L https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js \
  -o app/static/js/vendor/htmx.min.js
```

**Důležité:** CSP NEPOVOLUJE externí CDN! Vše musí být lokální.

---

## Prevence

**Best practices:**
1. Vždy používej `python3 gestima.py run` (ne přímý uvicorn)
2. Sleduj logy během vývoje (`tail -f`)
3. Restart po větších změnách v kódu
4. Backup před experimentováním (`python3 gestima.py backup`)
5. Po smazání DB spusť `python3 gestima.py create-admin` (vytvoří admin/asdfghjkl)

---

**Poslední update:** 2026-01-28
**GESTIMA verze:** 1.5.1
