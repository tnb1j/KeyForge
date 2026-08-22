@echo off
rem Example 4: Enterprise Windows Batch Installer with KeyForge Gate
setlocal

echo ============================================================
echo   Enterprise Windows Tool Installer with KeyForge Gate
echo ============================================================

set "SERVER_URL=https://key-forge-lac.vercel.app"
set "PRODUCT_ID=desktop-app"

set /p "USER_KEY=Enter your KeyForge License Key: "
if "%USER_KEY%"=="" (
    echo [ERROR] License key cannot be blank.
    exit /b 1
)

echo.
echo [*] Verifying license with KeyForge Authority...
call ..\..\sdk\batch\keyforge.bat validate %SERVER_URL% %PRODUCT_ID% %USER_KEY%

if %ERRORLEVEL% neq 0 (
    echo [ERROR] License validation failed. Aborting installation.
    exit /b 1
)

echo.
echo [SUCCESS] Verification passed! Proceeding with software setup...
echo [+] Extracting application binaries...
echo [+] Registering COM components...
echo [+] Installation completed successfully!
pause
