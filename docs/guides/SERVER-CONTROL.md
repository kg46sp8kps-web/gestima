# 🔧 GESTIMA - Server Control (Idiot-Proof Guide)

**Pro ty, co neví jak server zapnout/vypnout/restartovat.**

---

## 🔍 Zjistit jestli server běží

```bash
ps aux | grep -i "gestima\|uvicorn" | grep -v grep
```

**Výstup:**
- Vidíš něco → **Server BĚŽÍ** ✅
- Nic → **Server NEBĚŽÍ** ❌

**Alternativa (jednodušší):**
```bash
lsof -ti:8000
```

Pokud vidíš číslo (PID) → server běží na portu 8000.

---

## ✅ Zkontrolovat jestli server odpovídá

```bash
curl http://localhost:8000/health
```

**Výstup:**
- JSON s `{"status":"..."}` → **FUNGUJE** ✅
- `Connection refused` nebo chyba → **NEFUNGUJE** ❌

---

## ⏹️ Zastavit server

```bash
pkill -f "gestima.py run"
pkill -f "uvicorn app.gestima_app"
```

**Zkontrolovat že je mrtvý:**
```bash
ps aux | grep -i gestima | grep -v grep
```

Pokud nic → úspěšně zastaveno ✅

---

## ▶️ Nastartovat server

```bash
python gestima.py run > /tmp/gestima_server.log 2>&1 &
```

**Co to dělá:**
- `> /tmp/gestima_server.log` - logy do souboru
- `2>&1` - error output taky do logu
- `&` - běží na pozadí

**Zkontrolovat že běží:**
```bash
sleep 3 && curl http://localhost:8000/health
```

Pokud vidíš JSON → běží správně ✅

---

## 🔄 Restartovat server (kill + start)

**One-liner:**
```bash
pkill -f "gestima.py run" && pkill -f "uvicorn" && sleep 2 && python gestima.py run > /tmp/gestima_server.log 2>&1 &
```

**Po krůčcích (pokud one-liner selže):**
```bash
# 1. Zabít
pkill -f "gestima.py run"
pkill -f "uvicorn"

# 2. Počkat 2 sekundy
sleep 2

# 3. Ověřit že je mrtvý
ps aux | grep -i gestima | grep -v grep

# 4. Nastartovat znovu
python gestima.py run > /tmp/gestima_server.log 2>&1 &

# 5. Počkat a zkontrolovat health
sleep 3 && curl http://localhost:8000/health
```

---

## 📋 Sledovat logy v reálném čase

```bash
tail -f /tmp/gestima_server.log
```

Ukončit: `Ctrl+C`

**Zobrazit posledních 50 řádků:**
```bash
tail -50 /tmp/gestima_server.log
```

---

## 🆘 Troubleshooting

### Problém: Stránka se nenačítá v prohlížeči

**Postup:**

1️⃣ **Je server běží?**
```bash
ps aux | grep -i gestima | grep -v grep
```
Pokud NE → nastartuj server (viz výše)

2️⃣ **Odpovídá server?**
```bash
curl http://localhost:8000/health
```
Pokud NE → restart serveru

3️⃣ **Je DB inicializovaná?**
```bash
ls -lh data/gestima.db
```
Pokud vidíš `0B` (prázdná DB) → seed demo data:
```bash
echo "yes" | python gestima.py seed-demo
```

4️⃣ **Máš vytvořeného admina?**
```bash
sqlite3 data/gestima.db "SELECT username, role FROM users LIMIT 5;"
```
Pokud `no such table: users` → seed demo data (viz bod 3)

---

### Problém: Prázdná databáze (0 bytů)

**Řešení:**
```bash
echo "yes" | python gestima.py seed-demo
```

Vytvoří:
- ✅ Demo parts (3 kusy)
- ✅ Material catalog
- ✅ Demo admin: `demo` / `demo123`

**Potom RESTART serveru:**
```bash
pkill -f "gestima.py run" && pkill -f "uvicorn" && sleep 2 && python gestima.py run > /tmp/gestima_server.log 2>&1 &
```

---

### Problém: Port 8000 už je obsazený

**Zjistit co běží na portu 8000:**
```bash
lsof -ti:8000
```

**Zabít proces na portu 8000:**
```bash
kill -9 $(lsof -ti:8000)
```

**Nebo ručně:**
```bash
lsof -ti:8000  # Zjistit PID (např. 12345)
kill -9 12345   # Zabít proces
```

---

### Problém: Server spadl s chybou

**Přečti logy:**
```bash
tail -100 /tmp/gestima_server.log
```

**Hledej řádky:**
- `ERROR` - chyby aplikace
- `Traceback` - Python exception
- `CRITICAL` - kritická chyba

---

## 🎯 Quick Reference (nejpoužívanější příkazy)

| Co chci | Příkaz |
|---------|--------|
| **Zjistit jestli běží** | `lsof -ti:8000` |
| **Zkontrolovat health** | `curl http://localhost:8000/health` |
| **Zastavit** | `pkill -f "gestima.py run" && pkill -f "uvicorn"` |
| **Nastartovat** | `python gestima.py run > /tmp/gestima_server.log 2>&1 &` |
| **Restartovat** | `pkill -f "gestima.py run" && pkill -f "uvicorn" && sleep 2 && python gestima.py run > /tmp/gestima_server.log 2>&1 &` |
| **Sledovat logy** | `tail -f /tmp/gestima_server.log` |
| **Reset DB + seed** | `echo "yes" \| python gestima.py seed-demo` |

---

## 📝 Login Credentials

**Demo účet:**
- **Username:** `demo`
- **Password:** `demo123`
- **Role:** Admin

**URL:** http://localhost:8000

---

**Verze:** 1.0 (2026-01-29)
