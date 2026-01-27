# GESTIMA - Windows Firewall Setup Script
#
# Usage:
#   1. Open PowerShell as Administrator
#   2. cd C:\Gestima\scripts\windows
#   3. .\setup_firewall.ps1
#
# What it does:
#   - Creates Windows Firewall rule to allow inbound TCP connections on port 8000
#   - Enables access from other computers on the local network
#
# See: DEPLOYMENT.md for complete setup guide

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  GESTIMA - Firewall Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# Check if rule already exists
$existingRule = Get-NetFirewallRule -DisplayName "GESTIMA" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "Firewall rule 'GESTIMA' already exists." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Do you want to recreate it? (y/n): " -NoNewline -ForegroundColor Yellow
    $response = Read-Host

    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Removing existing rule..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName "GESTIMA"
        Write-Host "Existing rule removed." -ForegroundColor Green
    } else {
        Write-Host "Keeping existing rule. Exiting." -ForegroundColor Yellow
        exit 0
    }
}

# Create firewall rule
Write-Host "Creating firewall rule for GESTIMA (port 8000)..." -ForegroundColor Cyan

try {
    New-NetFirewallRule -DisplayName "GESTIMA" `
                        -Direction Inbound `
                        -LocalPort 8000 `
                        -Protocol TCP `
                        -Action Allow `
                        -Profile Domain,Private `
                        -Description "Allow inbound TCP connections to GESTIMA application on port 8000" | Out-Null

    Write-Host ""
    Write-Host "SUCCESS: Firewall rule created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Rule details:" -ForegroundColor Cyan
    Write-Host "  Name:      GESTIMA" -ForegroundColor White
    Write-Host "  Direction: Inbound" -ForegroundColor White
    Write-Host "  Port:      8000 (TCP)" -ForegroundColor White
    Write-Host "  Action:    Allow" -ForegroundColor White
    Write-Host "  Profile:   Domain, Private" -ForegroundColor White
    Write-Host ""
    Write-Host "Other computers on your network can now access:" -ForegroundColor Green
    Write-Host "  http://192.168.1.50:8000" -ForegroundColor White
    Write-Host ""
    Write-Host "Note: Make sure your PC has a static IP address (192.168.1.50)" -ForegroundColor Yellow
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create firewall rule!" -ForegroundColor Red
    Write-Host "Error details: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Verify rule was created
Write-Host "Verifying firewall rule..." -ForegroundColor Cyan
$rule = Get-NetFirewallRule -DisplayName "GESTIMA" -ErrorAction SilentlyContinue

if ($rule) {
    Write-Host "Verification: OK" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Verification: FAILED" -ForegroundColor Red
    Write-Host "Rule may not be active. Check Windows Firewall settings." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
