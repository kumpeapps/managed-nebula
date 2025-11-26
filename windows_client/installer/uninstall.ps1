# Managed Nebula Agent Uninstallation Script
# Run this script as Administrator
#
# Usage:
#   .\uninstall.ps1           # Keep configuration
#   .\uninstall.ps1 -Purge    # Remove everything including configuration

param(
    [switch]$Purge
)

$ErrorActionPreference = "Stop"

# Configuration
$ServiceName = "NebulaAgent"
$InstallDir = "$env:ProgramData\Nebula"
$BinDir = "$InstallDir\bin"

function Write-Banner {
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Cyan
    Write-Host "  Managed Nebula Agent Uninstaller" -ForegroundColor Cyan
    Write-Host "=======================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Banner

# Check for administrator privileges
if (-not (Test-Administrator)) {
    Write-Host "Error: This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

Write-Host "Uninstalling Managed Nebula Agent..." -ForegroundColor Yellow
Write-Host ""

# Step 1: Stop and remove service
Write-Host "Step 1: Stopping service..." -ForegroundColor Yellow
$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -eq "Running") {
        Stop-Service -Name $ServiceName -Force
        Start-Sleep -Seconds 2
        Write-Host "  Service stopped" -ForegroundColor Gray
    }
    
    Write-Host "  Removing service..." -ForegroundColor Gray
    & sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 1
    Write-Host "  Service removed" -ForegroundColor Gray
} else {
    Write-Host "  Service not found" -ForegroundColor Gray
}

# Step 2: Stop Nebula process
Write-Host ""
Write-Host "Step 2: Stopping Nebula process..." -ForegroundColor Yellow
$nebulaProcess = Get-Process -Name "nebula" -ErrorAction SilentlyContinue
if ($nebulaProcess) {
    Stop-Process -Name "nebula" -Force
    Write-Host "  Nebula process stopped" -ForegroundColor Gray
} else {
    Write-Host "  Nebula not running" -ForegroundColor Gray
}

# Step 3: Remove from PATH
Write-Host ""
Write-Host "Step 3: Cleaning up PATH..." -ForegroundColor Yellow
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($currentPath -like "*$BinDir*") {
    $newPath = ($currentPath -split ";") | Where-Object { $_ -ne $BinDir } | Join-String -Separator ";"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
    Write-Host "  Removed $BinDir from PATH" -ForegroundColor Gray
} else {
    Write-Host "  PATH already clean" -ForegroundColor Gray
}

# Step 4: Remove files
Write-Host ""
Write-Host "Step 4: Removing files..." -ForegroundColor Yellow

if ($Purge) {
    # Remove everything
    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
        Write-Host "  Removed $InstallDir (complete purge)" -ForegroundColor Gray
    } else {
        Write-Host "  Directory not found: $InstallDir" -ForegroundColor Gray
    }
    
    # Remove registry keys
    Write-Host ""
    Write-Host "Step 5: Cleaning registry..." -ForegroundColor Yellow
    $regPath = "HKLM:\SOFTWARE\ManagedNebula"
    if (Test-Path $regPath) {
        Remove-Item -Path $regPath -Recurse -Force
        Write-Host "  Removed registry key: $regPath" -ForegroundColor Gray
    } else {
        Write-Host "  Registry key not found" -ForegroundColor Gray
    }
} else {
    # Keep configuration
    if (Test-Path $BinDir) {
        Remove-Item -Path $BinDir -Recurse -Force
        Write-Host "  Removed binaries: $BinDir" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "  Configuration preserved at: $InstallDir" -ForegroundColor Yellow
    Write-Host "  Use -Purge flag to remove all data" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=======================================" -ForegroundColor Green
Write-Host "  Uninstallation Complete!" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green
Write-Host ""

if (-not $Purge -and (Test-Path $InstallDir)) {
    Write-Host "Note: Configuration and logs preserved at:" -ForegroundColor Yellow
    Write-Host "      $InstallDir" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To completely remove all data, run:" -ForegroundColor Yellow
    Write-Host "  .\uninstall.ps1 -Purge" -ForegroundColor Gray
    Write-Host ""
}
