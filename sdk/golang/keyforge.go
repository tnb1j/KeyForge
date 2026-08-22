// Package keyforge provides client SDK capabilities for Go applications.
package keyforge

import (
	"bytes"
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
)

// Client handles online and offline license validation for Go applications.
type Client struct {
	ProductID     string
	PublicKey     ed25519.PublicKey
	ServerURL     string
	ClientVersion string
	HTTPClient    *http.Client
}

// NewClient initializes a KeyForge client instance.
func NewClient(productID string, serverURL string, pubKey ed25519.PublicKey) *Client {
	return &Client{
		ProductID:     productID,
		PublicKey:     pubKey,
		ServerURL:     strings.TrimRight(serverURL, "/"),
		ClientVersion: "1.0.0",
		HTTPClient:    &http.Client{Timeout: 10 * time.Second},
	}
}

// LicensePayload represents the claims embedded in a license.
type LicensePayload struct {
	SchemaVersion int                    `json:"schema_version"`
	LicenseID     string                 `json:"license_id"`
	LicenseKey    string                 `json:"license_key"`
	ProductID     string                 `json:"product_id"`
	LicenseType   string                 `json:"license_type"`
	Edition       string                 `json:"edition"`
	CustomerID    string                 `json:"customer_id"`
	Features      []string               `json:"features"`
	ExpiresAt     string                 `json:"expires_at"`
	MaxDevices    int                    `json:"max_devices"`
	Metadata      map[string]interface{} `json:"metadata"`
}

// ParsedToken represents an unpacked armored token.
type ParsedToken struct {
	SchemaVersion int
	KeyID         string
	Algorithm     string
	Payload       LicensePayload
	Signature     []byte
}

// ValidationResult represents the output of a validation check.
type ValidationResult struct {
	IsValid       bool     `json:"is_valid"`
	Status        string   `json:"status"`
	Message       string   `json:"message"`
	LicenseID     string   `json:"license_id"`
	ProductID     string   `json:"product_id"`
	Edition       string   `json:"edition"`
	Features      []string `json:"features"`
	ExpiresAt     string   `json:"expires_at"`
	DaysRemaining *int     `json:"days_remaining"`
}

// HasFeature returns true if the license entitles the caller to the named feature.
func (v *ValidationResult) HasFeature(featureName string) bool {
	if !v.IsValid {
		return false
	}
	for _, f := range v.Features {
		if f == "*" || f == featureName {
			return true
		}
	}
	return false
}

// ParseArmoredToken parses a kf1.payload.sig.keyid string.
func ParseArmoredToken(token string) (*ParsedToken, error) {
	parts := strings.Split(strings.TrimSpace(token), ".")
	if len(parts) != 4 || parts[0] != "kf1" {
		return nil, errors.New("invalid KeyForge armored token structure")
	}

	payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, fmt.Errorf("failed to decode payload: %w", err)
	}

	var payload LicensePayload
	if err := json.Unmarshal(payloadBytes, &payload); err != nil {
		return nil, fmt.Errorf("failed to parse payload JSON: %w", err)
	}

	sigBytes, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return nil, fmt.Errorf("failed to decode signature: %w", err)
	}

	keyIDBytes, err := base64.RawURLEncoding.DecodeString(parts[3])
	if err != nil {
		return nil, fmt.Errorf("failed to decode key ID: %w", err)
	}

	return &ParsedToken{
		SchemaVersion: 1,
		KeyID:         string(keyIDBytes),
		Algorithm:     "Ed25519",
		Payload:       payload,
		Signature:     sigBytes,
	}, nil
}

// ValidateOnline queries the KeyForge REST endpoint.
func (c *Client) ValidateOnline(licenseKey, installationID string) (*ValidationResult, error) {
	if c.ServerURL == "" {
		return nil, errors.New("server URL required for online validation")
	}

	payload := map[string]string{
		"license_key":     licenseKey,
		"product_id":      c.ProductID,
		"installation_id": installationID,
		"client_version":  c.ClientVersion,
	}
	body, _ := json.Marshal(payload)

	resp, err := c.HTTPClient.Post(fmt.Sprintf("%s/api/v1/licenses/validate", c.ServerURL), "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result ValidationResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result, nil
}
