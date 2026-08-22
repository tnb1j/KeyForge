@echo off
rem ==============================================================================
rem KeyForge Windows Batch Licensing Client Utility (.bat)
rem Provides automated license validation and activation for Windows scripts.
rem ==============================================================================

setlocal enabledelayedexpansion

set "ACTION=%~1"
set "SERVER_URL=%~2"
set "PRODUCT_ID=%~3"
set "LICENSE_KEY=%~4"

if "%ACTION%"=="" goto :usage
if "%SERVER_URL%"=="" goto :usage
if "%PRODUCT_ID%"=="" goto :usage
if "%LICENSE_KEY%"=="" goto :usage

rem Strip trailing slash from server URL
if "%SERVER_URL:~-1%"=="/" set "SERVER_URL=%SERVER_URL:~0,-1%"

rem Generate hardware identifier using PowerShell SHA-256
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($env:COMPUTERNAME + ':' + $env:PROCESSOR_IDENTIFIER)) | ForEach-Object { '{0:x2}' -f $_ }) -join ''"`) do (
    set "HW_ID=%%i"
)

if /i "%ACTION%"=="validate" goto :do_validate
if /i "%ACTION%"=="activate" goto :do_activate
goto :usage

:do_validate
echo [*] Validating KeyForge License for Product: %PRODUCT_ID%...
powershell -NoProfile -Command "$body = @{ license_key='%LICENSE_KEY%'; product_id='%PRODUCT_ID%'; installation_id='%HW_ID%'; client_version='1.0.0' } | ConvertTo-Json; try { $res = Invoke-RestMethod -Uri '%SERVER_URL%/api/v1/licenses/validate' -Method Post -ContentType 'application/json' -Body $body; if ($res.is_valid) { Write-Host '[OK] License VALID: Status=' $res.status 'Edition=' $res.edition -ForegroundColor Green; exit 0 } else { Write-Host '[FAIL] License INVALID:' $res.message -ForegroundColor Red; exit 1 } } catch { Write-Host '[ERROR] Server validation failed:' $_.Exception.Message -ForegroundColor Red; exit 2 }"
exit /b %ERRORLEVEL%

:do_activate
echo [*] Activating Device for License Key: %LICENSE_KEY%...
powershell -NoProfile -Command "$body = @{ license_key='%LICENSE_KEY%'; product_id='%PRODUCT_ID%'; installation_id='%HW_ID%'; device_fingerprint='%HW_ID%'; device_name=$env:COMPUTERNAME; platform='windows'; client_version='1.0.0' } | ConvertTo-Json; try { $res = Invoke-RestMethod -Uri '%SERVER_URL%/api/v1/licenses/activate' -Method Post -ContentType 'application/json' -Body $body; Write-Host '[OK] Device Activation Succeeded. Activation ID:' $res.activation_id -ForegroundColor Green; exit 0 } catch { Write-Host '[ERROR] Device Activation Failed:' $_.Exception.Message -ForegroundColor Red; exit 1 }"
exit /b %ERRORLEVEL%

:usage
echo ==============================================================================
echo KeyForge Windows Batch CLI Licensing Helper (.bat)
echo ==============================================================================
echo Usage:
echo   keyforge.bat validate ^<ServerUrl^> ^<ProductId^> ^<LicenseKey^>
echo   keyforge.bat activate ^<ServerUrl^> ^<ProductId^> ^<LicenseKey^>
echo.
echo Examples:
echo   keyforge.bat validate https://key-forge-lac.vercel.app desktop-app DSK-7K4M-9Q2X-8T6P
echo   keyforge.bat activate https://key-forge-lac.vercel.app desktop-app DSK-7K4M-9Q2X-8T6P
exit /b 1
