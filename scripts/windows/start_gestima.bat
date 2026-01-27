@echo off
REM GESTIMA - Startup Script for Production
REM
REM Usage:
REM   1. Copy this file to your GESTIMA installation folder (e.g., C:\Gestima\)
REM   2. Edit the paths below to match your installation
REM   3. Configure Task Scheduler to run this script at startup
REM
REM Task Scheduler Setup:
REM   - Action: Start a program
REM   - Program: C:\Gestima\start_gestima.bat
REM   - Start in: C:\Gestima
REM   - Run whether user is logged on or not: YES
REM   - Run with highest privileges: YES
REM
REM See: DEPLOYMENT.md for complete setup guide

REM Change to GESTIMA directory
cd /d C:\Gestima

REM Activate virtual environment
call venv\Scripts\activate

REM Start GESTIMA application
echo.
echo ========================================
echo   GESTIMA - Production Server
echo ========================================
echo.
echo Starting application...
echo URL: http://192.168.1.50:8000
echo.
echo Press Ctrl+C to stop
echo.

python gestima.py run

REM Pause on error (for debugging when run manually)
if errorlevel 1 pause
