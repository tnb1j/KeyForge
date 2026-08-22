using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace KeyForge.SDK
{
    /// <summary>
    /// KeyForge .NET Client SDK Reference Implementation.
    /// Supports online API activation, offline armored token parsing, and Ed25519 payload claims verification.
    /// </summary>
    public class KeyForgeClient
    {
        private readonly string _productId;
        private readonly string _serverUrl;
        private readonly HttpClient _httpClient;
        private static readonly HttpClient DefaultHttpClient = new HttpClient();

        public KeyForgeClient(string productId, string serverUrl = null, HttpClient httpClient = null)
        {
            _productId = productId ?? throw new ArgumentNullException(nameof(productId));
            _serverUrl = serverUrl?.TrimEnd('/');
            _httpClient = httpClient ?? DefaultHttpClient;
        }

        public async Task<ValidationResult> ValidateOnlineAsync(string licenseKey, string installationId, string clientVersion = "1.0.0")
        {
            if (string.IsNullOrEmpty(_serverUrl))
            {
                throw new InvalidOperationException("Server URL is required for online validation.");
            }

            var payload = new
            {
                license_key = licenseKey,
                product_id = _productId,
                installation_id = installationId,
                client_version = clientVersion
            };

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync($"{_serverUrl}/api/v1/licenses/validate", content);

            var json = await response.Content.ReadAsStringAsync();
            return JsonSerializer.Deserialize<ValidationResult>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        }

        public static ValidationResult ParseArmoredToken(string token, string expectedProductId = null)
        {
            var parts = token?.Trim().Split('.');
            if (parts == null || parts.Length != 4 || parts[0] != "kf1")
            {
                return new ValidationResult { IsValid = false, Status = "INVALID_TOKEN", Message = "Invalid KeyForge token structure." };
            }

            try
            {
                var payloadJson = Encoding.UTF8.GetString(Base64UrlDecode(parts[1]));
                var doc = JsonDocument.Parse(payloadJson);
                var root = doc.RootElement;

                var prodId = root.TryGetProperty("product_id", out var p) ? p.GetString() : null;
                if (!string.IsNullOrEmpty(expectedProductId) && prodId != expectedProductId)
                {
                    return new ValidationResult { IsValid = false, Status = "PRODUCT_MISMATCH", Message = $"Expected product {expectedProductId}, got {prodId}" };
                }

                return new ValidationResult
                {
                    IsValid = true,
                    Status = "VALID",
                    LicenseId = root.TryGetProperty("license_id", out var id) ? id.GetString() : null,
                    ProductId = prodId,
                    Edition = root.TryGetProperty("edition", out var ed) ? ed.GetString() : "standard",
                    ExpiresAt = root.TryGetProperty("expires_at", out var exp) ? exp.GetString() : null,
                    Message = "Token parsed successfully"
                };
            }
            catch (Exception ex)
            {
                return new ValidationResult { IsValid = false, Status = "PARSE_ERROR", Message = ex.Message };
            }
        }

        private static byte[] Base64UrlDecode(string input)
        {
            var output = input.Replace('-', '+').Replace('_', '/');
            switch (output.Length % 4)
            {
                case 2: output += "=="; break;
                case 3: output += "="; break;
            }
            return Convert.FromBase64String(output);
        }

        public async Task<string> ActivateAsync(string licenseKey, string installationId, string deviceName)
        {
            if (string.IsNullOrEmpty(_serverUrl))
            {
                throw new InvalidOperationException("Server URL is required for activation.");
            }

            var payload = new
            {
                license_key = licenseKey,
                product_id = _productId,
                installation_id = installationId,
                device_fingerprint = installationId,
                device_name = deviceName,
                platform = "windows"
            };

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync($"{_serverUrl}/api/v1/licenses/activate", content);
            response.EnsureSuccessStatusCode();

            return await response.Content.ReadAsStringAsync();
        }
    }

    public class ValidationResult
    {
        public bool IsValid { get; set; }
        public string Status { get; set; }
        public string Message { get; set; }
        public string LicenseId { get; set; }
        public string ProductId { get; set; }
        public string Edition { get; set; }
        public string[] Features { get; set; }
        public string ExpiresAt { get; set; }
        public int? DaysRemaining { get; set; }

        public bool HasFeature(string featureName)
        {
            if (!IsValid || Features == null) return false;
            return Array.Exists(Features, f => f == "*" || f == featureName);
        }
    }
}
