# Managed Nebula Agent Installation Script
# Run this script as Administrator
#
# Usage:
#   .\install.ps1
#   .\install.ps1 -Token "your-client-token" -ServerUrl "https://server:8080"
#   .\install.ps1 -Uninstall

param(
    [string]$Token,
    [string]$ServerUrl = "http://localhost:8080",
    [int]$PollIntervalHours = 24,
    [switch]$Uninstall,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Configuration
$ServiceName = "NebulaAgent"
$DisplayName = "Managed Nebula Agent"
$Description = "Managed Nebula VPN Agent - Polls server for configuration and manages the local Nebula daemon"
$InstallDir = "$env:ProgramData\Nebula"
$BinDir = "$InstallDir\bin"
$LogDir = "$InstallDir\logs"
$ConfigFile = "$InstallDir\agent.ini"

function Write-Banner {
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Cyan
    Write-Host "  Managed Nebula Agent Installer" -ForegroundColor Cyan
    Write-Host "=======================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Stop-ExistingService {
    Write-Host "Checking for existing service..." -ForegroundColor Yellow
    
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        if ($service.Status -eq "Running") {
            Write-Host "Stopping existing service..." -ForegroundColor Yellow
            Stop-Service -Name $ServiceName -Force
            Start-Sleep -Seconds 2
        }
    }
}

function Install-NebulaAgent {
    Write-Banner
    
    # Check for administrator privileges
    if (-not (Test-Administrator)) {
        Write-Host "Error: This script must be run as Administrator" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Installing Managed Nebula Agent..." -ForegroundColor Green
    Write-Host ""
    
    # Get script directory
    $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    
    # Stop existing service
    Stop-ExistingService
    
    # Create directories
    Write-Host "Step 1: Creating directories..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Write-Host "  Created: $InstallDir" -ForegroundColor Gray
    Write-Host "  Created: $BinDir" -ForegroundColor Gray
    Write-Host "  Created: $LogDir" -ForegroundColor Gray
    
    # Copy binaries
    Write-Host ""
    Write-Host "Step 2: Copying binaries..." -ForegroundColor Yellow
    
    $filesToCopy = @(
        "NebulaAgent.exe",
        "NebulaAgentService.exe",
        "nebula.exe",
        "nebula-cert.exe"
    )
    
    foreach ($file in $filesToCopy) {
        $sourcePath = Join-Path $ScriptDir $file
        if (Test-Path $sourcePath) {
            Copy-Item $sourcePath $BinDir -Force
            Write-Host "  Copied: $file" -ForegroundColor Gray
        } else {
            Write-Host "  Warning: $file not found" -ForegroundColor Yellow
        }
    }
    
    # Create configuration file
    Write-Host ""
    Write-Host "Step 3: Creating configuration..." -ForegroundColor Yellow
    
    if (-not (Test-Path $ConfigFile) -or $Force) {
        $configContent = @"
# Managed Nebula Agent Configuration
[agent]
server_url = $ServerUrl
poll_interval_hours = $PollIntervalHours
log_level = INFO
auto_start_nebula = true
"@
        
        if ($Token) {
            $configContent += "`nclient_token = $Token"
        }
        
        $configContent | Out-File -FilePath $ConfigFile -Encoding utf8
        Write-Host "  Created: $ConfigFile" -ForegroundColor Gray
    } else {
        Write-Host "  Configuration file already exists, skipping..." -ForegroundColor Gray
    }
    
    # Set permissions
    Write-Host ""
    Write-Host "Step 4: Setting permissions..." -ForegroundColor Yellow
    
    # Restrict access to SYSTEM and Administrators
    $acl = Get-Acl $InstallDir
    $acl.SetAccessRuleProtection($true, $false)
    
    $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "SYSTEM", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $adminRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "Administrators", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    
    $acl.AddAccessRule($systemRule)
    $acl.AddAccessRule($adminRule)
    Set-Acl -Path $InstallDir -AclObject $acl
    
    Write-Host "  Permissions set on $InstallDir" -ForegroundColor Gray
    
    # Install Windows Service
    Write-Host ""
    Write-Host "Step 5: Installing Windows Service..." -ForegroundColor Yellow
    
    $serviceBinaryPath = Join-Path $BinDir "NebulaAgentService.exe"
    
    # Remove existing service if present
    $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Host "  Removing existing service..." -ForegroundColor Gray
        & sc.exe delete $ServiceName | Out-Null
        Start-Sleep -Seconds 2
    }
    
    # Create new service
    New-Service -Name $ServiceName `
                -BinaryPathName $serviceBinaryPath `
                -DisplayName $DisplayName `
                -Description $Description `
                -StartupType Automatic | Out-Null
    
    Write-Host "  Service '$ServiceName' installed" -ForegroundColor Gray
    
    # Add PATH entry
    Write-Host ""
    Write-Host "Step 6: Updating PATH..." -ForegroundColor Yellow
    
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ($currentPath -notlike "*$BinDir*") {
        [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$BinDir", "Machine")
        Write-Host "  Added $BinDir to system PATH" -ForegroundColor Gray
    } else {
        Write-Host "  PATH already contains $BinDir" -ForegroundColor Gray
    }
    
    # Start service
    Write-Host ""
    Write-Host "Step 7: Starting service..." -ForegroundColor Yellow
    
    if ($Token) {
        Start-Service -Name $ServiceName
        Write-Host "  Service started" -ForegroundColor Gray
    } else {
        Write-Host "  Service not started (no token provided)" -ForegroundColor Yellow
        Write-Host "  Configure $ConfigFile with your client token, then run:" -ForegroundColor Yellow
        Write-Host "    Start-Service $ServiceName" -ForegroundColor Gray
    }
    
    # Summary
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installation Directory: $InstallDir" -ForegroundColor White
    Write-Host "Configuration File:     $ConfigFile" -ForegroundColor White
    Write-Host "Log Directory:          $LogDir" -ForegroundColor White
    Write-Host ""
    Write-Host "Service Commands:" -ForegroundColor White
    Write-Host "  Start-Service $ServiceName" -ForegroundColor Gray
    Write-Host "  Stop-Service $ServiceName" -ForegroundColor Gray
    Write-Host "  Get-Service $ServiceName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Agent Commands:" -ForegroundColor White
    Write-Host "  NebulaAgent.exe --status" -ForegroundColor Gray
    Write-Host "  NebulaAgent.exe --once" -ForegroundColor Gray
    Write-Host "  NebulaAgent.exe --version" -ForegroundColor Gray
    Write-Host ""
    
    if (-not $Token) {
        Write-Host "IMPORTANT: Configure your client token in $ConfigFile" -ForegroundColor Yellow
        Write-Host "           Then start the service with: Start-Service $ServiceName" -ForegroundColor Yellow
        Write-Host ""
    }
}

function Uninstall-NebulaAgent {
    Write-Banner
    
    # Check for administrator privileges
    if (-not (Test-Administrator)) {
        Write-Host "Error: This script must be run as Administrator" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Uninstalling Managed Nebula Agent..." -ForegroundColor Yellow
    Write-Host ""
    
    # Stop and remove service
    Write-Host "Step 1: Removing service..." -ForegroundColor Yellow
    Stop-ExistingService
    
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        & sc.exe delete $ServiceName | Out-Null
        Write-Host "  Service removed" -ForegroundColor Gray
    } else {
        Write-Host "  Service not found" -ForegroundColor Gray
    }
    
    # Stop Nebula process
    Write-Host ""
    Write-Host "Step 2: Stopping Nebula..." -ForegroundColor Yellow
    Get-Process -Name "nebula" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "  Done" -ForegroundColor Gray
    
    # Remove from PATH
    Write-Host ""
    Write-Host "Step 3: Updating PATH..." -ForegroundColor Yellow
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    $newPath = ($currentPath -split ";") | Where-Object { $_ -ne $BinDir } | Join-String -Separator ";"
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
    Write-Host "  Removed $BinDir from PATH" -ForegroundColor Gray
    
    # Remove files
    Write-Host ""
    Write-Host "Step 4: Removing files..." -ForegroundColor Yellow
    
    if ($Force) {
        # Remove everything
        if (Test-Path $InstallDir) {
            Remove-Item -Path $InstallDir -Recurse -Force
            Write-Host "  Removed $InstallDir (including configuration)" -ForegroundColor Gray
        }
    } else {
        # Keep configuration, remove binaries
        if (Test-Path $BinDir) {
            Remove-Item -Path $BinDir -Recurse -Force
            Write-Host "  Removed $BinDir" -ForegroundColor Gray
        }
        Write-Host "  Configuration preserved at $ConfigFile" -ForegroundColor Gray
        Write-Host "  Use -Force to remove configuration as well" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host "  Uninstallation Complete!" -ForegroundColor Green
    Write-Host "=======================================" -ForegroundColor Green
    Write-Host ""
}

# Main
if ($Uninstall) {
    Uninstall-NebulaAgent
} else {
    Install-NebulaAgent
}
