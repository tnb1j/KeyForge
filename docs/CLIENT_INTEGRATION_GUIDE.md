# KeyForge Client Integration Guide

## 1. Python Integration

Install or bundle `keyforge_client`:

```python
from keyforge_client import KeyForgeClient, FileLicenseStorage

PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAPaOoxqKAmcniEt/tbnnq2lhXXCU0pGbsSF7Qu+ynIsA=
-----END PUBLIC KEY-----"""

client = KeyForgeClient(
    product_id="photostudio",
    public_key=PUBLIC_KEY_PEM,
    server_url="https://licensing.yourcompany.com",
    storage=FileLicenseStorage(),
)

# Check license validity
if client.is_valid():
    print(f"Licensed to edition: {client.get_edition()}")
    if client.has_feature("raw_export"):
        enable_raw_export()
else:
    # Prompt for license activation
    license_key = input("Enter License Key: ")
    client.activate(license_key)
```

---

## 2. Node.js / TypeScript Integration

```javascript
const { KeyForgeNodeClient } = require('@keyforge/client');

const client = new KeyForgeNodeClient({
  productId: 'cloud-analytics-api',
  publicKey: '3da3a8c6a28099c9e212dfed6e79eada58575c2534a466ec485ed0bbeca722c0',
});

async function verifyRequest(token) {
  const result = await client.validate(token);
  if (result.is_valid) {
    console.log(`Access granted to ${result.customer_id}`);
  } else {
    console.error(`Validation failed: ${result.message}`);
  }
}
```

---

## 3. Windows PowerShell Integration

```powershell
Import-Module .\KeyForge.psm1

# Activate license
$act = Invoke-KeyForgeActivation -ServerUrl "https://licensing.yourcompany.com" `
    -ProductId "desktop-app" `
    -LicenseKey "DSK-7K4M-9Q2X-8T6P"

# Verify license
$status = Test-KeyForgeLicense -ServerUrl "https://licensing.yourcompany.com" `
    -ProductId "desktop-app" `
    -LicenseKey "DSK-7K4M-9Q2X-8T6P"

if ($status.is_valid) {
    Write-Host "License Valid!" -ForegroundColor Green
}
```
