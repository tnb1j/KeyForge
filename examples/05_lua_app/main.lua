--[[
    Example 5: Lua Application with KeyForge Offline Token Validation
--]]

local KeyForge = require("sdk.lua.keyforge")

local client = KeyForge.new({
    product_id = "game-engine-pro",
    client_version = "3.2.0"
})

print("============================================================")
print("    KeyForge Native Lua Application Integration Demo")
print("============================================================")

-- Sample armored token for demonstration
local sample_token = "kf1.eyJsaWNlbnNlX2lkIjoibGljX2x1YV8wMDEiLCJwcm9kdWN0X2lkIjoiZ2FtZS1lbmdpbmUtcHJvIiwiZWRpdGlvbiI6InBybyIsImZlYXR1cmVzIjpbInJlbmRlcmVyIiwicGh5c2ljcyIsInNoYWRlcnMiXX0.c2lnbmF0dXJlX2J5dGVz.a2V5LXYx"

local result = client:validate(sample_token)

if result.is_valid then
    print("[OK] License Status: VALID")
    print("    License ID:   " .. tostring(result.license_id))
    print("    Edition:      " .. tostring(result.edition):upper())
    
    print("\n--- Feature Entitlements ---")
    local features = {"renderer", "physics", "raytracing"}
    for _, feat in ipairs(features) do
        local enabled = client:has_feature(feat)
        local status = enabled and "[ENABLED] " or "[LOCKED]  "
        print(string.format("  %s Feature '%s'", status, feat))
    end
else
    print("[FAIL] License Invalid: " .. tostring(result.message))
end

print("\n[+] Lua SDK loaded and verified successfully.")
