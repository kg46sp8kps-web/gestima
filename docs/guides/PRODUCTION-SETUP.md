# GESTIMA - Production Setup (Windows PC)

**Situace:** Už vyvíjíš na Mac, potřebuješ nahodit produkci na Windows PC v firemní síti.

**Čas:** ~30 minut

---

## 📋 Co potřebuješ

- [ ] Windows PC (běží pořád)
- [ ] Python 3.9+ nainstalovaný
- [ ] Git nainstalovaný
- [ ] Přístup k Git repo (GitHub/GitLab)

---

## 🚀 Setup (krok za krokem)

### 1. Nainstaluj Python (pokud nemáš)

**Stáhni:** https://www.python.org/downloads/

**Při instalaci:** ✅ **Zaškrtni "Add Python to PATH"!**

**Ověř:**
```powershell
python --version
# Mělo by být: Python 3.9 nebo vyšší
```

### 2. Nainstaluj Git (pokud nemáš)

**Stáhni:** https://git-scm.com/download/win

**Ověř:**
```powershell
git --version
```

### 3. Nastav Git (pokud ještě nemáš)

```powershell
git config --global user.name "Tvoje Jméno"
git config --global user.email "email@example.com"
```

### 4. SSH klíč pro GitHub (pokud nemáš)

**Vygeneruj klíč:**
```powershell
ssh-keygen -t ed25519 -C "email@example.com"
# Stiskni Enter 3× (default vše)
```

**Zkopíruj public key:**
```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub
# Zkopíruj výstup (Ctrl+C)
```

**Přidej na GitHub:**
1. GitHub → Settings → SSH and GPG keys
2. "New SSH key"
3. Vlož klíč → Add

**Test:**
```powershell
ssh -T git@github.com
# Mělo by být: "Hi username! You've successfully authenticated..."
```

### 5. Clone Repository

```powershell
# V PowerShell
cd C:\
git clone git@github.com:your-org/gestima.git
cd gestima
```

### 6. Setup Python Environment

```powershell
# Vytvoř venv + nainstaluj dependencies
python gestima.py setup
```

### 7. Vytvoř .env soubor

```powershell
notepad .env
```

**Vlož do .env:**
```bash
DEBUG=false
SECRET_KEY=vygeneruj-nahodny-64-char-string-zde
SECURE_COOKIE=false
DATABASE_URL=sqlite+aiosqlite:///gestima.db
PORT=8000
```

**Vygeneruj SECRET_KEY:**
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
# Zkopíruj výstup a vlož do .env jako SECRET_KEY
```

### 8. Seed Reference Data (materiály, stroje)

```powershell
# Aktivuj venv (pokud ještě není)
venv\Scripts\activate

# Seed materials
python -m app.seed_materials

# Seed machines
python scripts\seed_machines.py
```

### 9. Vytvoř Admin Uživatele

```powershell
python gestima.py create-admin
# Username: tvoje_jmeno
# Password: ********

# Opakuj pro další usery (3× celkem)
```

### 10. Test Manuálního Spuštění

```powershell
python gestima.py run
```

**V jiném PC na síti otevři:**
```
http://192.168.1.50:8000
```

**Nefunguje?** Pokračuj krokem 11 (firewall).

### 11. Firewall Rule

**PowerShell jako Administrator:**
```powershell
cd C:\Gestima\scripts\windows
.\setup_firewall.ps1
```

**Test znovu:**
```
http://192.168.1.50:8000
```

### 12. Statická IP (pokud nemáš)

**Windows 10/11:**
```
Settings → Network → Properties → Edit IP
→ Manual

IP: 192.168.1.50
Subnet: 255.255.255.0
Gateway: 192.168.1.1
DNS: 192.168.1.1
```

**Ověř:**
```powershell
ipconfig
# IP address should be: 192.168.1.50
```

### 13. Autostart (Task Scheduler)

**1. Zkopíruj script:**
```powershell
copy scripts\windows\start_gestima.bat C:\Gestima\
```

**2. Otevři Task Scheduler:**
```
Win+R → taskschd.msc
```

**3. Create Basic Task:**
- Name: `GESTIMA`
- Trigger: `At startup`
- Action: `Start a program`
  - Program: `C:\Gestima\start_gestima.bat`
  - Start in: `C:\Gestima`

**4. Edit Properties:**
- General:
  - Run whether user is logged on or not: ✅
  - Run with highest privileges: ✅
- Conditions:
  - Start only if on AC power: ❌ (vypni!)

**5. Test:**
```powershell
schtasks /run /tn "GESTIMA"
```

### 14. Daily Backup (Task Scheduler)

**1. Zkopíruj script:**
```powershell
copy scripts\windows\backup_gestima.bat C:\Gestima\
```

**2. Edit backup script:**
```powershell
notepad backup_gestima.bat
```

**Změň cestu k external drive:**
```batch
SET EXTERNAL_DRIVE=Z:\IT\GESTIMA_Backups
```

**3. Create Task Scheduler:**
- Name: `GESTIMA Backup`
- Trigger: `Daily` → 2:00 AM
- Action: `C:\Gestima\backup_gestima.bat`

**4. Test:**
```powershell
schtasks /run /tn "GESTIMA Backup"
type backup_log.txt
```

---

## ✅ Hotovo!

**Produkce běží na:**
```
http://192.168.1.50:8000
```

**Users se připojí:**
```
1. Otevřou prohlížeč
2. Zadají: http://192.168.1.50:8000
3. Login s účtem co jsi vytvořil v kroku 9
```

---

## 🔄 Deploy Update (když jsi v práci)

```powershell
cd C:\Gestima
python gestima.py deploy
```

**Restartuj aplikaci:**
```powershell
schtasks /run /tn "GESTIMA"
```

---

## 🐛 Troubleshooting

### Users se nemůžou připojit

**Check:**
```powershell
# 1. Aplikace běží?
curl http://localhost:8000/health

# 2. Firewall pravidlo?
Get-NetFirewallRule -DisplayName "GESTIMA"

# 3. Správná IP?
ipconfig
# Mělo by být: 192.168.1.50
```

**Fix:**
```powershell
# Recreate firewall rule
cd scripts\windows
.\setup_firewall.ps1
```

### Aplikace neběží po restartu PC

**Check:**
```powershell
# Task Scheduler properties
# General: "Run whether user is logged on or not" = YES
# Conditions: "Start only if on AC power" = NO
```

### Backup selhal

**Check:**
```powershell
# Log
type backup_log.txt

# Disk space
Get-PSDrive C

# External drive připojený?
Test-Path Z:\
```

---

## 📞 Další Help?

**Kompletní guide:** [DEPLOYMENT.md](DEPLOYMENT.md)

**Quick commands:**
```bash
python gestima.py help          # All commands
python gestima.py backup        # Manual backup
python gestima.py create-admin  # New user
```

---

**Questions?** Ask team lead nebo otevři issue na GitHub.
