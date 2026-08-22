<#
.SYNOPSIS
    KeyForge Universal Licensing Client Module for Windows & PowerShell.

.DESCRIPTION
    Provides automated license verification, hardware identity hashing, and API activation
    for enterprise Windows automation scripts, installers, and PowerShell applications.
#>

function Get-KeyForgeHardwareId {
    [CmdletBinding()]
    param()
    
    $sysInfo = "$($env:COMPUTERNAME):$($env:PROCESSOR_IDENTIFIER):$($env:OS)"
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($sysInfo)
    $hashBytes = $hasher.ComputeHash($bytes)
    return -join ($hashBytes | ForEach-Object { "{0:x2}" -f $_ })
}

function Test-KeyForgeLicense {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServerUrl,
        
        [Parameter(Mandatory=$true)]
        [string]$ProductId,
        
        [Parameter(Mandatory=$true)]
        [string]$LicenseKey,
        
        [string]$ClientVersion = "1.0.0"
    )
    
    $hwId = Get-KeyForgeHardwareId
    $body = @{
        license_key = $LicenseKey
        product_id = $ProductId
        installation_id = $hwId
        client_version = $ClientVersion
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$($ServerUrl.TrimEnd('/'))/api/v1/licenses/validate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body
        return $response
    } catch {
        Write-Error "KeyForge License Validation Failed: $_"
        return @{
            is_valid = $false
            status = "SERVER_UNAVAILABLE"
            message = $_.Exception.Message
        }
    }
}

function Invoke-KeyForgeActivation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$ServerUrl,
        
        [Parameter(Mandatory=$true)]
        [string]$ProductId,
        
        [Parameter(Mandatory=$true)]
        [string]$LicenseKey,
        
        [string]$DeviceName = $env:COMPUTERNAME,
        [string]$ClientVersion = "1.0.0"
    )
    
    $hwId = Get-KeyForgeHardwareId
    $body = @{
        license_key = $LicenseKey
        product_id = $ProductId
        installation_id = $hwId
        device_fingerprint = $hwId
        device_name = $DeviceName
        platform = "windows"
        client_version = $ClientVersion
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri "$($ServerUrl.TrimEnd('/'))/api/v1/licenses/activate" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body
        return $response
    } catch {
        Write-Error "KeyForge Activation Failed: $_"
        throw
    }
}

Export-ModuleMember -Function Get-KeyForgeHardwareId, Test-KeyForgeLicense, Invoke-KeyForgeActivation
