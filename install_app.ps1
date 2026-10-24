# AIS-140 Simulator - Native Windows Application Installer & System Registrar
# Installs to %LocalAppData%\Programs\AIS140-Simulator
# Registers Desktop shortcut, Start Menu shortcut, and Windows "Open with" protocol associations.
param(
    [switch]$Uninstall
)

$AppName = "AIS-140 Simulator"
$ExeName = "AIS140-Simulator-Portable.exe"
$InstallDir = "$env:LOCALAPPDATA\Programs\AIS140-Simulator"
$StartMenuDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
$DesktopDir = [Environment]::GetFolderPath("Desktop")

if ($Uninstall) {
    Write-Host "Uninstalling $AppName..." -ForegroundColor Yellow
    Remove-Item -Path "$DesktopDir\$AppName.lnk" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$StartMenuDir\$AppName.lnk" -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "HKCU:\Software\Classes\Applications\$ExeName" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AIS140Simulator" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$InstallDir" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Uninstallation complete!" -ForegroundColor Green
    exit 0
}

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Installing $AppName to Windows..." -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Create install directory
if (-not (Test-Path "$InstallDir")) {
    New-Item -ItemType Directory -Path "$InstallDir" -Force | Out-Null
}

# 2. Copy application executable
$SourceExe = "$PSScriptRoot\dist\$ExeName"
if (-not (Test-Path "$SourceExe")) {
    $SourceExe = "$PSScriptRoot\$ExeName"
}

if (Test-Path "$SourceExe") {
    Copy-Item -Path "$SourceExe" -Destination "$InstallDir\$ExeName" -Force
} else {
    Write-Host "[ERROR] Could not find $ExeName in dist or root!" -ForegroundColor Red
    exit 1
}

# 3. Create Windows Shortcuts (Start Menu + Desktop)
$WshShell = New-Object -ComObject WScript.Shell

# Desktop shortcut
$ShortcutDesktop = $WshShell.CreateShortcut("$DesktopDir\$AppName.lnk")
$ShortcutDesktop.TargetPath = "$InstallDir\$ExeName"
$ShortcutDesktop.WorkingDirectory = "$InstallDir"
$ShortcutDesktop.Description = "AIS-140 VLTD Telematics Client Simulator"
$ShortcutDesktop.Save()

# Start Menu shortcut
$ShortcutStart = $WshShell.CreateShortcut("$StartMenuDir\$AppName.lnk")
$ShortcutStart.TargetPath = "$InstallDir\$ExeName"
$ShortcutStart.WorkingDirectory = "$InstallDir"
$ShortcutStart.Description = "AIS-140 VLTD Telematics Client Simulator"
$ShortcutStart.Save()

# 4. Register in Windows Registry (Open with / Geo protocol / Add-Remove programs)
$AppRegKey = "HKCU:\Software\Classes\Applications\$ExeName\shell\open\command"
New-Item -Path "$AppRegKey" -Force | Out-Null
Set-ItemProperty -Path "$AppRegKey" -Name "(Default)" -Value """$InstallDir\$ExeName"" ""%1"""

# Register in Windows Add/Remove Programs (Installed Apps)
$UninstallRegKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AIS140Simulator"
New-Item -Path "$UninstallRegKey" -Force | Out-Null
Set-ItemProperty -Path "$UninstallRegKey" -Name "DisplayName" -Value "$AppName"
Set-ItemProperty -Path "$UninstallRegKey" -Name "DisplayVersion" -Value "2.0.0"
Set-ItemProperty -Path "$UninstallRegKey" -Name "Publisher" -Value "AIS140 Telematics"
Set-ItemProperty -Path "$UninstallRegKey" -Name "InstallLocation" -Value "$InstallDir"
Set-ItemProperty -Path "$UninstallRegKey" -Name "UninstallString" -Value "powershell.exe -ExecutionPolicy Bypass -File `"$PSScriptRoot\install_app.ps1`" -Uninstall"

Write-Host "`n[SUCCESS] $AppName successfully installed!" -ForegroundColor Green
Write-Host "  Installed Location: $InstallDir"
Write-Host "  Desktop Shortcut:   $DesktopDir\$AppName.lnk"
Write-Host "  Start Menu Entry:   $StartMenuDir\$AppName.lnk"
Write-Host "  Registered for:     Windows Open with & Location links"
