# GESTIMA Deployment Guide

**Verze:** 1.0
**Datum:** 2026-01-27
**Pro koho:** Vývojáři + IT administrátoři

---

## ⚡ Quick Links

**Already developing on Mac?** → Jump to [PRODUCTION-SETUP.md](PRODUCTION-SETUP.md) (30 min Windows checklist)

**Starting from zero?** → Continue reading (complete guide with Git setup, troubleshooting, FAQ)

---

## 📋 Obsah

1. [Přehled](#přehled)
2. [Prerequisites](#prerequisites)
3. [Git Setup (od nuly)](#git-setup-od-nuly)
4. [Dev Environment (Vývojářský laptop)](#dev-environment-vývojářský-laptop)
5. [Prod Environment (Firemní PC)](#prod-environment-firemní-pc)
6. [Denní Workflow](#denní-workflow)
7. [Deployment Workflow](#deployment-workflow)
8. [Backup & Restore](#backup--restore)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)

---

## Přehled

### Deployment Strategie

GESTIMA používá **Dev/Prod separation** s Git-based deploymentem:

```
┌─────────────────┐         ┌─────────────────┐
│  DEV (laptop)   │         │  PROD (firma)   │
│  localhost      │         │  192.168.1.50   │
│                 │         │                 │
│  gestima.db ────┼────X────┼──── gestima.db  │
│  (demo data)    │  NO     │  (real data)    │
│                 │  SYNC!  │                 │
└────────┬────────┘         └────────┬────────┘
         │                           │
         └────► Git Repo ◄───────────┘
              (GitHub/GitLab)
```

**Klíčové principy:**
- **Separate databases** - Dev i Prod mají vlastní `.db` soubor
- **Git pro kód** - Synchronizace kódu přes Git push/pull
- **Backup pro data** - Testování na real data přes backup/restore
- **Manuální deploy** - Deploy při fyzickém přístupu nebo Remote Desktop

**Proč takto?**
- SQLite = single-writer, nelze sdílet DB přes síť
- Bezpečnost = experimenty v dev neovlivní produkci
- Rychlost = dev běží lokálně, zero network latency

---

## Prerequisites

### Co potřebuješ

#### Pro Dev Environment (laptop):
- [ ] Python 3.9+ (ideálně 3.11)
- [ ] Git 2.30+
- [ ] GitHub/GitLab účet
- [ ] Terminal/PowerShell
- [ ] Text editor (VS Code doporučeno)

#### Pro Prod Environment (firma-PC):
- [ ] Python 3.9+
- [ ] Git 2.30+
- [ ] Windows 10/11 (nebo Linux/macOS)
- [ ] Statická IP adresa (např. 192.168.1.50)
- [ ] External disk pro backupy

### Instalace Python

#### Windows:
```powershell
# Stáhni z https://www.python.org/downloads/
# Při instalaci ZAŠKRTNI "Add Python to PATH"!

# Ověř instalaci
python --version
# Očekávaný výstup: Python 3.11.x
```

#### macOS:
```bash
# Homebrew
brew install python@3.11

# Ověř
python3 --version
```

#### Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
python3 --version
```

### Instalace Git

#### Windows:
```powershell
# Stáhni z https://git-scm.com/download/win
# Instaluj s defaultními nastaveními

# Ověř
git --version
# Očekávaný výstup: git version 2.43.x
```

#### macOS:
```bash
brew install git
git --version
```

#### Linux:
```bash
sudo apt install git
git --version
```

---

## Git Setup (od nuly)

### 1. Konfigurace Git (první použití)

```bash
# Nastav své jméno a email
git config --global user.name "Tvoje Jméno"
git config --global user.email "email@example.com"

# Ověř konfiguraci
git config --list
```

### 2. GitHub/GitLab účet

**GitHub (doporučeno):**
1. Jdi na https://github.com
2. Sign up (Free účet stačí)
3. Ověř email

### 3. SSH klíč (pro bezpečný přístup)

**Proč SSH?** Nemusíš zadávat heslo při každém `git push`.

```bash
# 1. Vygeneruj SSH klíč (pokud ještě nemáš)
ssh-keygen -t ed25519 -C "email@example.com"
# Stiskni Enter 3× (default cesta + žádné heslo)

# 2. Zkopíruj public key do schránky
# Windows (Git Bash):
cat ~/.ssh/id_ed25519.pub | clip

# macOS:
cat ~/.ssh/id_ed25519.pub | pbcopy

# Linux:
cat ~/.ssh/id_ed25519.pub | xclip -selection clipboard
```

**Přidej SSH klíč na GitHub:**
1. GitHub → Settings → SSH and GPG keys
2. "New SSH key"
3. Title: "Můj laptop"
4. Key: Ctrl+V (vložit klíč)
5. Add SSH key

**Test:**
```bash
ssh -T git@github.com
# Očekávaný výstup:
# Hi username! You've successfully authenticated...
```

### 4. Vytvoř Git Repository

**Na GitHub:**
1. GitHub → New repository
2. Name: `gestima`
3. Private: ✅ (DŮLEŽITÉ - ostrá data!)
4. Add README: ❌ (už máme)
5. Create repository

**Zkopíruj SSH URL:**
```
git@github.com:your-username/gestima.git
```

### 5. Push existujícího kódu na GitHub

```bash
# V GESTIMA složce
cd /path/to/gestima

# Inicializuj Git (pokud ještě není)
git init

# Přidej .gitignore (ignoruj DB a sensitive files)
cat > .gitignore << 'EOF'
# Database
*.db
*.db-shm
*.db-wal
gestima.db*

# Environment
.env
venv/
__pycache__/
*.pyc

# Backups
backups/
*.gz

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log
EOF

# Přidej soubory
git add .

# První commit
git commit -m "Initial commit"

# Připoj remote repository
git remote add origin git@github.com:your-username/gestima.git

# Push
git branch -M main
git push -u origin main
```

**Hotovo!** Kód je teď na GitHub.

---

## Dev Environment (Vývojářský laptop)

### 1. Clone Repository

```bash
# Clone z GitHub
cd ~/Projects  # nebo kde chceš
git clone git@github.com:your-username/gestima.git
cd gestima
```

### 2. Setup Dev Environment

```bash
# Setup (venv + dependencies)
python gestima.py setup

# Aktivuj venv (pokud ještě není)
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

### 3. Seed Demo Data

```bash
# Vytvoř demo databázi
python gestima.py seed-demo

# Co to udělá:
# - Init DB schema
# - Seed materials (MaterialGroup + MaterialItem)
# - Seed machines (5 demo strojů)
# - Seed 3 demo parts (DEMO-001, DEMO-002, DEMO-003)
# - Create demo admin user (username: demo, password: demo123)
```

### 4. První spuštění

```bash
# Spusť aplikaci
python gestima.py run

# Otevři prohlížeč
open http://localhost:8000

# Login:
# Username: demo
# Password: demo123
```

**Hotovo!** Dev environment běží. 🎉

### 5. Vytvoř vlastního admin usera

```bash
python gestima.py create-admin
# Username: tvoje_jmeno
# Password: *******
```

---

## Prod Environment (Firemní PC)

### 1. Příprava PC

#### A) Statická IP adresa

**Windows 10/11:**
```
Settings → Network & Internet → Ethernet/Wi-Fi
→ Properties → Edit IP assignment
→ Manual

IP address: 192.168.1.50
Subnet mask: 255.255.255.0
Gateway: 192.168.1.1
DNS: 192.168.1.1
```

**Ověř:**
```powershell
ipconfig
# Ověř že máš IP 192.168.1.50
```

#### B) Windows Firewall

```powershell
# Spusť PowerShell jako Administrator
# Přidej pravidlo pro port 8000
New-NetFirewallRule -DisplayName "GESTIMA" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Ověř
Get-NetFirewallRule -DisplayName "GESTIMA"
```

### 2. Clone Repository

```powershell
# V PowerShell
cd C:\
git clone git@github.com:your-username/gestima.git
cd gestima
```

### 3. Setup Prod Environment

```powershell
# Setup
python gestima.py setup

# Aktivuj venv
venv\Scripts\activate
```

### 4. Konfigurace .env

```powershell
# Vytvoř .env soubor
notepad .env
```

**Obsah `.env`:**
```bash
# Production config
DEBUG=false
SECRET_KEY=vygeneruj-nahodny-64-char-string-zde
SECURE_COOKIE=false  # HTTP v interní síti
DATABASE_URL=sqlite+aiosqlite:///gestima.db
PORT=8000
```

**Vygeneruj SECRET_KEY:**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Zkopíruj výstup do .env jako SECRET_KEY
```

### 5. Seed Production Data

```powershell
# Seed reference data (materiály, stroje)
python -m app.seed_materials
python scripts\seed_machines.py

# NESEDUJEŠ demo parts v produkci!
```

### 6. Vytvoř Admin Uživatele

```powershell
# Pro každého reálného uživatele
python gestima.py create-admin
# Username: jan_novak
# Password: ********

# Opakuj pro další usery (3×)
```

### 7. Test Manuálního Spuštění

```powershell
# Test run
python gestima.py run

# V jiném PC na síti otevři:
http://192.168.1.50:8000

# Login s vytvořeným účtem
```

**Funguje?** Pokračuj na autostart.

### 8. Autostart (Task Scheduler)

#### Vytvoř Batch Script

```powershell
# Vytvoř soubor
notepad C:\Gestima\start_gestima.bat
```

**Obsah `start_gestima.bat`:**
```batch
@echo off
cd /d C:\Gestima
call venv\Scripts\activate
python gestima.py run
pause
```

#### Konfigurace Task Scheduler

**Krok za krokem:**

1. **Otevři Task Scheduler**
   - Start → Task Scheduler

2. **Create Basic Task**
   - Name: `GESTIMA`
   - Description: `GESTIMA FastAPI Application`

3. **Trigger**
   - When: `At startup`

4. **Action**
   - Action: `Start a program`
   - Program: `C:\Gestima\start_gestima.bat`
   - Start in: `C:\Gestima`

5. **Finish** → Edit properties:
   - General tab:
     - Run whether user is logged on or not: ✅
     - Run with highest privileges: ✅
   - Conditions tab:
     - Start only if on AC power: ❌ (vypni)
   - Settings tab:
     - Allow task to be run on demand: ✅
     - If running task doesn't end, force stop: ❌

6. **Save** → Zadej heslo uživatele

**Test:**
```powershell
# Spusť task ručně
schtasks /run /tn "GESTIMA"

# Ověř že běží
curl http://localhost:8000/health
```

### 9. Automatický Denní Backup

#### Vytvoř Backup Script

```powershell
notepad C:\Gestima\backup_gestima.bat
```

**Obsah `backup_gestima.bat`:**
```batch
@echo off
cd /d C:\Gestima
call venv\Scripts\activate
python gestima.py backup

REM Zkopíruj na external drive (změň Z: na svůj disk)
if exist Z:\IT mkdir Z:\IT\GESTIMA_Backups
robocopy C:\Gestima\backups Z:\IT\GESTIMA_Backups /MIR /R:3 /W:5 /LOG+:C:\Gestima\backup_log.txt
```

#### Task Scheduler - Denní Backup

1. **Create Basic Task**
   - Name: `GESTIMA Backup`
   - Trigger: `Daily` → 2:00 AM
   - Action: `Start a program` → `C:\Gestima\backup_gestima.bat`

**Hotovo!** Produkce běží s automatickými backupy. 🎉

---

## Denní Workflow

### Developer (doma)

#### Práce na nové feature

```bash
cd ~/gestima

# 1. Pull nejnovější změny z main
git checkout main
git pull origin main

# 2. Vytvoř feature branch
git checkout -b feature/nova-funkce

# 3. Vyvíjej
# ...edituj kód...

# 4. Testuj
pytest
python gestima.py run  # Manuální test

# 5. Commit
git add .
git commit -m "feat: přidána nová funkce XYZ"

# 6. Push na GitHub
git push origin feature/nova-funkce
```

#### Code Review (GitHub)

1. **GitHub** → Pull Requests → New PR
2. Base: `main` ← Compare: `feature/nova-funkce`
3. Popis co změna dělá
4. Create Pull Request
5. **Review** (sám nebo kolega)
6. **Merge** → main branch

#### Cleanup

```bash
# Po merge na main
git checkout main
git pull origin main

# Smaž local feature branch
git branch -d feature/nova-funkce
```

---

## Deployment Workflow

### Kdy deployovat?

- Když jsou merged features v `main` branch
- Po důkladném otestování v dev
- Preferovaně v neaktivní době (ráno před příchodem users)

### Postup (v práci, fyzický přístup)

```powershell
# 1. Připoj se k firma-PC
# Remote Desktop nebo fyzicky

# 2. Jdi do GESTIMA složky
cd C:\Gestima

# 3. Pull nejnovější změny
git pull origin main

# 4. Restart aplikace
# Možnost A - Task Scheduler
schtasks /run /tn "GESTIMA"

# Možnost B - Manuální restart
# Najdi "GESTIMA" okno → Ctrl+C → Spusť start_gestima.bat

# 5. Ověř že běží
curl http://localhost:8000/health

# 6. Test v prohlížeči
# Jiný PC na síti: http://192.168.1.50:8000
```

### Hotfix Deploy (urgentní oprava)

```bash
# Dev (doma)
git checkout main
git checkout -b hotfix/kriticka-oprava
# ...fix...
git commit -m "fix: kritická oprava"
git push origin hotfix/kriticka-oprava

# GitHub: Fast merge (bez review pokud urgentní)

# Prod (zavolej kolegu v práci)
# Kolega spustí: git pull origin main + restart
```

---

## Backup & Restore

### Automatické Backupy (Produkce)

**Task Scheduler spouští denně 2:00 AM:**
```powershell
python gestima.py backup
```

**Backupy se ukládají:**
```
C:\Gestima\backups\gestima_backup_20260127_020000.db.gz
```

**Retention:**
- Local: 30 dnů (starší automaticky mažou)
- External drive: 1 rok

### Manuální Backup

```powershell
# Produkce
cd C:\Gestima
python gestima.py backup

# Výstup:
# ✅ Backup created: backups/gestima_backup_20260127_153045.db.gz
```

### Restore Backup (Dev - testování na real data)

```bash
# Dev (doma)
cd ~/gestima

# 1. Zkopíruj backup z produkce
# USB stick nebo network share
cp /mnt/usb/backups/gestima_backup_20260127.db.gz .

# 2. Restore
python gestima.py restore gestima_backup_20260127.db.gz

# Výstup:
# ✅ Restored: gestima.db

# 3. Spusť s reálnými daty
python gestima.py run

# 4. Po testování - reset na demo data
python gestima.py seed-demo
```

### Restore Backup (Produkce - rollback)

```powershell
# Produkce (pokud deploy pokazí)
cd C:\Gestima

# 1. Stop aplikaci
schtasks /end /tn "GESTIMA"

# 2. Restore poslední funkční backup
python gestima.py restore backups\gestima_backup_20260126_020000.db.gz

# 3. Rollback kód (pokud potřeba)
git checkout <previous-commit-hash>

# 4. Restart
schtasks /run /tn "GESTIMA"
```

---

## Troubleshooting

### Dev Environment

#### Problém: `git push` žádá heslo

**Příčina:** Používáš HTTPS místo SSH

**Fix:**
```bash
# Změň remote na SSH
git remote set-url origin git@github.com:your-username/gestima.git

# Ověř
git remote -v
# Mělo by být: git@github.com:... (NE https://)
```

#### Problém: `ImportError: No module named 'fastapi'`

**Příčina:** Venv není aktivovaný nebo dependencies chybí

**Fix:**
```bash
# Aktivuj venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstaluj dependencies
pip install -r requirements.txt
```

#### Problém: `Database is locked`

**Příčina:** Jiná instance běží

**Fix:**
```bash
# Najdi běžící Python procesy
ps aux | grep python  # macOS/Linux
tasklist | findstr python  # Windows

# Zabij proces
kill <PID>            # macOS/Linux
taskkill /PID <PID>   # Windows
```

### Prod Environment

#### Problém: Users se nemůžou připojit z jiných PC

**Možné příčiny:**

1. **Firewall blokuje port 8000**
   ```powershell
   # Ověř firewall pravidlo
   Get-NetFirewallRule -DisplayName "GESTIMA"

   # Přidej pokud chybí
   New-NetFirewallRule -DisplayName "GESTIMA" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```

2. **Aplikace neběží**
   ```powershell
   # Ověř
   curl http://localhost:8000/health

   # Spusť
   schtasks /run /tn "GESTIMA"
   ```

3. **Špatná IP adresa**
   ```powershell
   # Ověř IP
   ipconfig
   # Mělo by být: 192.168.1.50
   ```

#### Problém: Aplikace padá po restartu PC

**Příčina:** Task Scheduler task není správně nakonfigurovaný

**Fix:**
```
Task Scheduler → GESTIMA → Properties:
- General: "Run whether user is logged on or not" ✅
- Conditions: "Start only if on AC power" ❌
```

#### Problém: Backup selhal

**Možné příčiny:**

1. **Disk full**
   ```powershell
   # Ověř místo
   Get-PSDrive C
   ```

2. **External drive není připojený**
   ```powershell
   # Ověř drive Z:
   Test-Path Z:\
   ```

3. **Permissions**
   ```powershell
   # Ověř že user má write práva do backups/
   ```

---

## FAQ

### Q: Můžu mít více dev environments (laptop + desktop)?

**A: Ano!** Každý dev má vlastní `gestima.db`. Kód sync přes Git.

```bash
# Laptop
cd ~/gestima
git pull origin main

# Desktop
cd ~/gestima
git pull origin main

# Oba mají aktuální kód, vlastní DB
```

### Q: Jak sdílet DB mezi dev machines?

**A: Nesdílej!** Každý dev má vlastní demo DB. Pro testování na real data použij backup/restore.

### Q: Co když zapomenu pushnout změny před deployem?

**A:** Deploy pulluje z GitHub. Pokud jsi nepushnul, změny se nedeploynou.

```bash
# Před odchodem z domova
git push origin main

# V práci
git pull origin main  # Dostane tvé změny
```

### Q: Můžu deployovat z domova přes Remote Desktop?

**A: Ano!** Pokud máš RDP přístup k firma-PC:

```powershell
# Remote Desktop → firma-PC
mstsc /v:192.168.1.50

# Pak standardní deploy workflow
cd C:\Gestima
git pull origin main
schtasks /run /tn "GESTIMA"
```

### Q: Co když 2 developers deploynou současně?

**A:** Git merge conflict. Vyřešte merge před deployem:

```bash
# Developer 2
git pull origin main
# CONFLICT! Vyřeš merge
git add .
git commit -m "merge: resolve conflict"
git push origin main
```

### Q: Jak často backupovat?

**A:** Denně je standard. Pokud high-activity (>100 changes/day), zvyš frekvenci:

```powershell
# Task Scheduler: 2× denně (2:00 + 14:00)
```

### Q: Můžu použít Dropbox/Google Drive pro backupy?

**A: Ano,** ale **NIKDY** pro live DB! Jen pro backup kopie:

```powershell
# Po backupu
robocopy C:\Gestima\backups "C:\Users\User\Dropbox\GESTIMA_Backups" /MIR
```

### Q: Co když ztratím všechny backupy?

**A: Ouch!** Proto:
- Local backupy (30 dnů)
- External drive (1 rok)
- Cloud backup (optional)

**3-2-1 rule:**
- 3 kopie dat
- 2 různé media (local + external)
- 1 offsite (cloud)

### Q: Kdy přejít na PostgreSQL?

**A:** Zvážit PostgreSQL pokud:
- >10 concurrent users
- Real-time MES v4.0 (Q3 2026)
- Full-text search requirements

**Pro <10 users: SQLite stačí!**

---

## Další Kroky

**Po úspěšném deploymentu:**

1. ✅ **Monitoring**
   - Pravidelně kontroluj health check: `http://192.168.1.50:8000/health`
   - Ověřuj backupy: `dir C:\Gestima\backups`

2. ✅ **User Training**
   - Vytvoř admin účty pro users
   - Školení základních workflow (vytvoření part, batch, operace)

3. ✅ **Dokumentace**
   - Přečti [CLAUDE.md](CLAUDE.md) - AI development pravidla
   - Přečti [STATUS.md](../status/STATUS.md) - Aktuální stav projektu

4. ✅ **Next Features**
   - Viz [NEXT-STEPS.md](docs/NEXT-STEPS.md) - Plánované features

---

## Reference

- [ADR-018](docs/ADR/018-deployment-strategy.md) - Architektonické rozhodnutí deployment
- [ADR-007](docs/ADR/007-https-caddy.md) - HTTPS pro public deployment
- [STATUS.md](../status/STATUS.md) - Stav projektu
- [CLAUDE.md](CLAUDE.md) - AI development pravidla
- [Git Documentation](https://git-scm.com/doc) - Oficiální Git docs

---

**Questions?** Otevři issue na GitHub nebo kontaktuj team lead.

**Hodně štěstí!** 🚀
