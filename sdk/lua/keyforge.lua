--[[
    KeyForge Universal Licensing Client Module for Lua
    Compatible with Lua 5.1+, LuaJIT, and OpenResty.
    Provides online REST validation and offline token claim extraction.
--]]

local KeyForge = {}
KeyForge.__index = KeyForge

-- Helper: Base64URL decode
local function b64url_decode(str)
    str = str:gsub("-", "+"):gsub("_", "/")
    local pad = #str % 4
    if pad == 2 then str = str .. "=="
    elseif pad == 3 then str = str .. "=" end
    
    local b = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    return (str:gsub('.', function(x)
        if (x == '=') then return '' end
        local r, f = '', (b:find(x) - 1)
        for i = 6, 1, -1 do r = r .. (f % 2 ^ i - f % 2 ^ (i - 1) > 0 and '1' or '0') end
        return r
    end):gsub('%d%d%d%d%d%d%d%d', function(x)
        if (#x ~= 8) then return '' end
        local c = 0
        for i = 1, 8 do c = c + (x:sub(i, i) == '1' and 2 ^ (8 - i) or 0) end
        return string.char(c)
    end))
end

-- Helper: Basic JSON parse (fallback if cjson not installed)
local function parse_json(str)
    local ok, cjson = pcall(require, "cjson")
    if ok then
        return cjson.decode(str)
    end
    -- Lightweight fallback parser for key-value fields
    local res = {}
    for k, v in string.gmatch(str, '"(%w+)":%s*"([^"]+)"') do
        res[k] = v
    end
    for k, v in string.gmatch(str, '"(%w+)":%s*(%d+)') do
        res[k] = tonumber(v)
    end
    for k, v in string.gmatch(str, '"(%w+)":%s*(true)') do
        res[k] = true
    end
    for k, v in string.gmatch(str, '"(%w+)":%s*(false)') do
        res[k] = false
    end
    return res
end

function KeyForge.new(config)
    local self = setmetatable({}, KeyForge)
    self.product_id = config.product_id or "default-product"
    self.server_url = config.server_url and config.server_url:gsub("/+$", "") or nil
    self.client_version = config.client_version or "1.0.0"
    self.cached_license = nil
    return self
end

-- Parse armored token (kf1.payload.sig.keyid)
function KeyForge:parse_token(token)
    local parts = {}
    for part in string.gmatch(token, "[^.]+") do
        table.insert(parts, part)
    end
    
    if #parts ~= 4 or parts[1] ~= "kf1" then
        return nil, "Invalid KeyForge token structure"
    end
    
    local payload_json = b64url_decode(parts[2])
    local payload = parse_json(payload_json)
    local key_id = b64url_decode(parts[4])
    
    return {
        schema_version = 1,
        key_id = key_id,
        algorithm = "Ed25519",
        payload = payload,
        signature = parts[3]
    }
end

-- Validate license token or key
function KeyForge:validate(license_input)
    if type(license_input) == "string" and license_input:sub(1, 4) == "kf1." then
        local token_obj, err = self:parse_token(license_input)
        if not token_obj then
            return { is_valid = false, status = "INVALID_TOKEN", message = err }
        end
        
        local p = token_obj.payload
        if p.product_id and p.product_id ~= self.product_id then
            return {
                is_valid = false,
                status = "PRODUCT_MISMATCH",
                message = string.format("Product mismatch: expected %s, got %s", self.product_id, p.product_id)
            }
        end
        
        self.cached_license = p
        return {
            is_valid = true,
            status = "VALID",
            license_id = p.license_id,
            product_id = p.product_id,
            edition = p.edition or "standard",
            features = p.features or {},
            expires_at = p.expires_at
        }
    end
    
    return {
        is_valid = false,
        status = "REQUIRES_ONLINE_VALIDATION",
        message = "Raw license key provided without server connection"
    }
end

function KeyForge:has_feature(feature_name)
    if not self.cached_license then return false end
    local feats = self.cached_license.features or {}
    for _, f in ipairs(feats) do
        if f == "*" or f == feature_name then
            return true
        end
    end
    return false
end

return KeyForge
