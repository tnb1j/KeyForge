# KeyForge Client Integration Guide

KeyForge provides production-ready, native client SDKs and scripts for **Python, Node.js, PowerShell, Windows Batch, Lua, C# (.NET), and Go**.

---

## 1. Python Integration (`sdk/python/`)

```python
from keyforge_client import KeyForgeClient, FileLicenseStorage

PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAPaOoxqKAmcniEt/tbnnq2lhXXCU0pGbsSF7Qu+ynIsA=
-----END PUBLIC KEY-----"""

client = KeyForgeClient(
    product_id="photostudio",
    public_key=PUBLIC_KEY_PEM,
    server_url="https://key-forge-lac.vercel.app",
    storage=FileLicenseStorage(),
    client_version="1.0.0",
)

# 1. Activate device online
if not client.is_valid():
    license_key = input("Enter License Key: ")
    client.activate(license_key)

# 2. Check offline validity and feature entitlements
if client.is_valid():
    print(f"Licensed to edition: {client.get_edition()}")
    if client.has_feature("raw_export"):
        enable_raw_export()
```

---

## 2. Node.js / TypeScript Integration (`sdk/nodejs/`)

```javascript
const { KeyForgeNodeClient } = require('./sdk/nodejs');

const client = new KeyForgeNodeClient({
  productId: 'cloud-analytics-api',
  publicKey: '3da3a8c6a28099c9e212dfed6e79eada58575c2534a466ec485ed0bbeca722c0',
});

async function verifyRequest(token) {
  const result = await client.validate(token);
  if (result.is_valid) {
    console.log(`Access granted to customer: ${result.customer_id}`);
    if (client.hasFeature('advanced_export')) {
      // Execute feature logic
    }
  } else {
    console.error(`Validation failed: ${result.message}`);
  }
}
```

---

## 3. Windows PowerShell Integration (`sdk/powershell/`)

```powershell
Import-Module .\sdk\powershell\KeyForge.psm1 -Force

# 1. Activate Device Online
Invoke-KeyForgeActivation -ServerUrl "https://key-forge-lac.vercel.app" `
    -ProductId "desktop-app" `
    -LicenseKey "DSK-7K4M-9Q2X-8T6P"

# 2. Verify Online or Offline Token
$status = Test-KeyForgeLicense -ServerUrl "https://key-forge-lac.vercel.app" `
    -ProductId "desktop-app" `
    -LicenseKeyOrToken "DSK-7K4M-9Q2X-8T6P"

if ($status.is_valid) {
    Write-Host "[OK] License Active (Edition: $($status.edition))" -ForegroundColor Green
}
```

---

## 4. Windows Batch Integration (`sdk/batch/`)

Gate Windows command scripts and installers with a single call:

```bat
@echo off
set "SERVER_URL=https://key-forge-lac.vercel.app"
set "PRODUCT_ID=desktop-app"
set /p "KEY=Enter License Key: "

call .\sdk\batch\keyforge.bat validate %SERVER_URL% %PRODUCT_ID% %KEY%
if %ERRORLEVEL% neq 0 (
    echo [ERROR] License validation failed. Aborting.
    exit /b 1
)

echo [SUCCESS] Access granted! Proceeding with installer...
```

---

## 5. Lua Integration (`sdk/lua/`)

```lua
local KeyForge = require("sdk.lua.keyforge")

local client = KeyForge.new({
    product_id = "game-engine-pro",
    server_url = "https://key-forge-lac.vercel.app"
})

local result = client:validate("kf1.eyJsaWNlbnNlX2lkIjoibGljXzAxfQ.sig.key")
if result.is_valid and client:has_feature("renderer") then
    print("Game engine graphics layer initialized.")
end
```

---

## 6. C# / .NET Integration (`sdk/csharp/`)

```csharp
using KeyForge.SDK;

var client = new KeyForgeClient("desktop-app", "https://key-forge-lac.vercel.app");

// Online validation
var result = await client.ValidateOnlineAsync("DSK-7K4M-9Q2X-8T6P", "machine_hw_id_101");
if (result.IsValid && result.HasFeature("pro_filters"))
{
    Console.WriteLine($"License active until {result.ExpiresAt}");
}
```

---

## 7. Go Integration (`sdk/golang/`)

```go
package main

import (
    "fmt"
    "keyforge"
)

func main() {
    client := keyforge.NewClient("analytics-agent", "https://key-forge-lac.vercel.app", nil)
    result, err := client.ValidateOnline("DSK-7K4M-9Q2X-8T6P", "hw_id_go_node_01")
    if err == nil && result.IsValid {
        fmt.Printf("Access granted for edition: %s\n", result.Edition)
    }
}
```
