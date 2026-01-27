@echo off
REM GESTIMA - Automated Backup Script for Production
REM
REM Usage:
REM   1. Copy this file to your GESTIMA installation folder (e.g., C:\Gestima\)
REM   2. Edit the paths below to match your installation
REM   3. Change the EXTERNAL_DRIVE path to your backup drive
REM   4. Configure Task Scheduler to run this script daily (e.g., 2:00 AM)
REM
REM Task Scheduler Setup:
REM   - Trigger: Daily at 2:00 AM
REM   - Action: Start a program
REM   - Program: C:\Gestima\backup_gestima.bat
REM   - Start in: C:\Gestima
REM   - Run whether user is logged on or not: YES
REM
REM See: DEPLOYMENT.md for complete setup guide

REM Configuration
SET GESTIMA_DIR=C:\Gestima
SET EXTERNAL_DRIVE=Z:\IT\GESTIMA_Backups
SET LOG_FILE=%GESTIMA_DIR%\backup_log.txt

REM Change to GESTIMA directory
cd /d %GESTIMA_DIR%

REM Log start time
echo. >> %LOG_FILE%
echo ===================================== >> %LOG_FILE%
echo Backup started: %DATE% %TIME% >> %LOG_FILE%
echo ===================================== >> %LOG_FILE%

REM Activate virtual environment
call venv\Scripts\activate

REM Create backup
echo Creating database backup... >> %LOG_FILE%
python gestima.py backup >> %LOG_FILE% 2>&1

if errorlevel 1 (
    echo ERROR: Backup creation failed! >> %LOG_FILE%
    exit /b 1
)

echo Backup created successfully >> %LOG_FILE%

REM Copy backup to external drive (if available)
if exist %EXTERNAL_DRIVE% (
    echo Copying backups to external drive... >> %LOG_FILE%
    robocopy %GESTIMA_DIR%\backups %EXTERNAL_DRIVE% /MIR /R:3 /W:5 /LOG+:%LOG_FILE%

    if errorlevel 8 (
        echo ERROR: External drive copy failed! >> %LOG_FILE%
        exit /b 1
    ) else (
        echo External drive sync successful >> %LOG_FILE%
    )
) else (
    echo WARNING: External drive not found at %EXTERNAL_DRIVE% >> %LOG_FILE%
    echo Backup saved locally only >> %LOG_FILE%
)

REM Log end time
echo Backup completed: %DATE% %TIME% >> %LOG_FILE%
echo. >> %LOG_FILE%

exit /b 0
