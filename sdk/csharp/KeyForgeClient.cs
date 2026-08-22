using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace KeyForge.SDK
{
    /// <summary>
    /// KeyForge .NET Client SDK Reference Implementation.
    /// Supports online API activation and Ed25519 payload claims verification.
    /// </summary>
    public class KeyForgeClient
    {
        private readonly string _productId;
        private readonly string _serverUrl;
        private readonly HttpClient _httpClient;

        public KeyForgeClient(string productId, string serverUrl)
        {
            _productId = productId ?? throw new ArgumentNullException(nameof(productId));
            _serverUrl = serverUrl?.TrimEnd('/') ?? throw new ArgumentNullException(nameof(serverUrl));
            _httpClient = new HttpClient();
        }

        public async Task<ValidationResult> ValidateAsync(string licenseKey, string installationId, string clientVersion = "1.0.0")
        {
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

        public async Task<string> ActivateAsync(string licenseKey, string installationId, string deviceName)
        {
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
