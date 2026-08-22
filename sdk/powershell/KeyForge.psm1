<#
.SYNOPSIS
    KeyForge Universal Licensing Client Module for Windows & PowerShell.

.DESCRIPTION
    Provides automated online license validation, device activation, and offline armored token
    parsing for enterprise Windows automation scripts, installers, and PowerShell applications.
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

function ConvertFrom-KeyForgeBase64Url {
    param([string]$InputString)
    $padded = $InputString.Replace('-', '+').Replace('_', '/')
    switch ($padded.Length % 4) {
        2 { $padded += "==" }
        3 { $padded += "=" }
    }
    $bytes = [System.Convert]::FromBase64String($padded)
    return [System.Text.Encoding]::UTF8.GetString($bytes)
}

function ConvertFrom-KeyForgeToken {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)]
        [string]$Token
    )
    
    $parts = $Token.Trim().Split('.')
    if ($parts.Length -ne 4 -or $parts[0] -ne "kf1") {
        throw "Invalid KeyForge armored token format."
    }
    
    $payloadJson = ConvertFrom-KeyForgeBase64Url -InputString $parts[1]
    $payload = $payloadJson | ConvertFrom-Json
    $keyId = ConvertFrom-KeyForgeBase64Url -InputString $parts[3]
    
    return [PSCustomObject]@{
        schema_version = 1
        key_id = $keyId
        algorithm = "Ed25519"
        payload = $payload
        signature = $parts[2]
    }
}

function Test-KeyForgeLicense {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$false)]
        [string]$ServerUrl,
        
        [Parameter(Mandatory=$true)]
        [string]$ProductId,
        
        [Parameter(Mandatory=$true)]
        [string]$LicenseKeyOrToken,
        
        [string]$ClientVersion = "1.0.0"
    )
    
    # Check if this is an armored token for offline parsing
    if ($LicenseKeyOrToken.StartsWith("kf1.")) {
        try {
            $parsed = ConvertFrom-KeyForgeToken -Token $LicenseKeyOrToken
            $p = $parsed.payload
            
            if ($p.product_id -and $p.product_id -ne $ProductId) {
                return [PSCustomObject]@{
                    is_valid = $false
                    status = "PRODUCT_MISMATCH"
                    message = "Product mismatch: expected $ProductId, got $($p.product_id)"
                }
            }
            
            return [PSCustomObject]@{
                is_valid = $true
                status = "VALID"
                license_id = $p.license_id
                product_id = $p.product_id
                edition = $p.edition
                features = $p.features
                expires_at = $p.expires_at
                message = "Offline token parsed successfully"
            }
        } catch {
            return [PSCustomObject]@{
                is_valid = $false
                status = "INVALID_TOKEN"
                message = $_.Exception.Message
            }
        }
    }
    
    if (-not $ServerUrl) {
        return [PSCustomObject]@{
            is_valid = $false
            status = "SERVER_REQUIRED"
            message = "Server URL is required to validate raw license keys."
        }
    }
    
    $hwId = Get-KeyForgeHardwareId
    $body = @{
        license_key = $LicenseKeyOrToken
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
        return [PSCustomObject]@{
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

Export-ModuleMember -Function Get-KeyForgeHardwareId, ConvertFrom-KeyForgeToken, Test-KeyForgeLicense, Invoke-KeyForgeActivation
