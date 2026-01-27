# Windows Deployment Scripts

**For:** Production deployment on Windows Server/Desktop

These scripts help you deploy GESTIMA on Windows in a production environment.

---

## 📁 Files

| Script | Purpose | When to use |
|--------|---------|-------------|
| `start_gestima.bat` | Start GESTIMA application | Autostart via Task Scheduler |
| `backup_gestima.bat` | Automated backup + external drive sync | Daily Task Scheduler job |
| `setup_firewall.ps1` | Windows Firewall configuration | 1× during initial setup |

---

## 🚀 Quick Setup Guide

### 1. Firewall Configuration (1× setup)

**Open PowerShell as Administrator:**
```powershell
cd C:\Gestima\scripts\windows
.\setup_firewall.ps1
```

**What it does:**
- Creates Windows Firewall rule for port 8000
- Allows inbound TCP connections from local network
- Enables access from other computers

**Verify:**
```powershell
# On another PC on the network
curl http://192.168.1.50:8000/health
```

---

### 2. Autostart Configuration (Task Scheduler)

**Copy startup script:**
```powershell
copy scripts\windows\start_gestima.bat C:\Gestima\
```

**Edit if needed:**
```batch
notepad C:\Gestima\start_gestima.bat
# Change paths if GESTIMA is not in C:\Gestima
```

**Create Task Scheduler task:**

1. Open Task Scheduler: `Win+R` → `taskschd.msc`
2. Actions → Create Basic Task
3. Name: `GESTIMA`
4. Trigger: `At startup`
5. Action: `Start a program`
   - Program: `C:\Gestima\start_gestima.bat`
   - Start in: `C:\Gestima`
6. Finish → Edit properties:
   - General:
     - Run whether user is logged on or not: ✅
     - Run with highest privileges: ✅
   - Conditions:
     - Start only if on AC power: ❌ (uncheck!)
   - Settings:
     - Allow task to be run on demand: ✅

**Test:**
```powershell
# Run task manually
schtasks /run /tn "GESTIMA"

# Verify
curl http://localhost:8000/health
```

---

### 3. Automated Daily Backup (Task Scheduler)

**Copy backup script:**
```powershell
copy scripts\windows\backup_gestima.bat C:\Gestima\
```

**Edit configuration:**
```batch
notepad C:\Gestima\backup_gestima.bat
```

**Required changes:**
```batch
REM Change these paths:
SET GESTIMA_DIR=C:\Gestima          # Your GESTIMA installation path
SET EXTERNAL_DRIVE=Z:\IT\GESTIMA_Backups  # Your external drive path
```

**Create Task Scheduler task:**

1. Task Scheduler → Create Basic Task
2. Name: `GESTIMA Backup`
3. Trigger: `Daily` → 2:00 AM
4. Action: `Start a program`
   - Program: `C:\Gestima\backup_gestima.bat`
   - Start in: `C:\Gestima`
5. Settings same as autostart task

**Test:**
```powershell
# Run backup manually
schtasks /run /tn "GESTIMA Backup"

# Check log
type C:\Gestima\backup_log.txt

# Verify backup created
dir C:\Gestima\backups

# Verify external drive sync (if configured)
dir Z:\IT\GESTIMA_Backups
```

---

## 🔧 Customization

### Change Port

**Default:** Port 8000

**To change:**

1. Edit `.env`:
   ```
   PORT=8080
   ```

2. Update firewall rule:
   ```powershell
   Remove-NetFirewallRule -DisplayName "GESTIMA"
   New-NetFirewallRule -DisplayName "GESTIMA" `
                       -Direction Inbound `
                       -LocalPort 8080 `
                       -Protocol TCP `
                       -Action Allow
   ```

3. Restart application

### Change Backup Time

**Default:** Daily at 2:00 AM

**To change:**

1. Task Scheduler → `GESTIMA Backup` → Properties
2. Triggers → Edit
3. Change time (e.g., 3:00 AM)
4. Save

### Change Backup Retention

**Default:** 30 days (local), 1 year (external drive)

**To change:**

Edit `backup_gestima.bat`:
```batch
REM Add retention cleanup before robocopy
forfiles /P "%GESTIMA_DIR%\backups" /M *.gz /D -30 /C "cmd /c del @path"
```

Change `-30` to desired days (e.g., `-60` for 60 days).

---

## 📊 Monitoring

### Check Application Status

```powershell
# Health check
curl http://localhost:8000/health

# Check if process is running
Get-Process -Name python | Where-Object {$_.Path -like "*Gestima*"}
```

### Check Backup Logs

```powershell
# View recent backup logs
type C:\Gestima\backup_log.txt

# Search for errors
findstr /I "ERROR" C:\Gestima\backup_log.txt
```

### Check Firewall Rule

```powershell
Get-NetFirewallRule -DisplayName "GESTIMA"
```

---

## 🐛 Troubleshooting

### Application won't start

**Check:**
1. Task Scheduler log: Task Scheduler → Task History
2. Python installed: `python --version`
3. Venv exists: `dir C:\Gestima\venv`
4. Port not in use: `netstat -ano | findstr 8000`

**Fix:**
```powershell
cd C:\Gestima
python gestima.py setup  # Reinstall venv
.\start_gestima.bat      # Test manual start
```

### Users can't connect from other PCs

**Check:**
1. Firewall rule: `Get-NetFirewallRule -DisplayName "GESTIMA"`
2. Static IP: `ipconfig` (should be 192.168.1.50)
3. Application running: `curl http://localhost:8000/health`

**Fix:**
```powershell
.\setup_firewall.ps1  # Recreate firewall rule
```

### Backup fails

**Check:**
1. Log file: `type C:\Gestima\backup_log.txt`
2. Disk space: `Get-PSDrive C`
3. External drive: `Test-Path Z:\`

**Fix:**
```powershell
# Free up disk space
# OR
# Change external drive path in backup_gestima.bat
```

---

## 📚 See Also

- [DEPLOYMENT.md](../../DEPLOYMENT.md) - Complete deployment guide
- [ADR-018](../../docs/ADR/018-deployment-strategy.md) - Deployment strategy architecture
- [README.md](../../README.md) - Project overview

---

**Questions?** Open an issue on GitHub or contact the team lead.
