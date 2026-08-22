<#
.SYNOPSIS
    Example 3: Windows PowerShell Enterprise Automation Tool with KeyForge Integration.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModulePath = Join-Path $ScriptDir "..\..\sdk\powershell\KeyForge.psm1"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "    KeyForge Enterprise Windows Automation Tool Integration" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Import the KeyForge PowerShell Client Module
Import-Module $ModulePath -Force

$HardwareId = Get-KeyForgeHardwareId
Write-Host "[+] Local Privacy-Preserving Hardware ID: $HardwareId" -ForegroundColor Green

Write-Host "`nUsage demonstration with local or remote KeyForge Server:" -ForegroundColor Yellow
Write-Host "  # 1. Perform Device Activation:"
Write-Host "  Invoke-KeyForgeActivation -ServerUrl 'http://127.0.0.1:8000' -ProductId 'desktop-app' -LicenseKey 'DSK-XXXX-XXXX-XXXX'"
Write-Host "`n  # 2. Perform Online Validation Check:"
Write-Host "  Test-KeyForgeLicense -ServerUrl 'http://127.0.0.1:8000' -ProductId 'desktop-app' -LicenseKey 'DSK-XXXX-XXXX-XXXX'"

Write-Host "`n[OK] PowerShell Client Module initialized successfully." -ForegroundColor Green
