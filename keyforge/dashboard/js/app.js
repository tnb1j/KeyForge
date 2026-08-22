/**
 * KeyForge Admin Dashboard Application Controller
 */

const API_BASE = '/api/v1';

const state = {
  token: localStorage.getItem('keyforge_token') || '',
  user: null,
  products: [],
  licenses: [],
  stats: null,
  activeView: 'overview',
};

// API Fetch Helper with Bearer Auth
async function api(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && endpoint !== '/auth/login') {
      logout();
      throw new Error('Session expired. Please log in again.');
    }

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `Request failed with status ${res.status}`);
    }
    return data;
  } catch (err) {
    console.error('API Error:', err);
    throw err;
  }
}

// Authentication
async function login(username, password) {
  try {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    state.token = data.access_token;
    state.user = data.user;
    localStorage.setItem('keyforge_token', state.token);
    hideModal('loginModal');
    updateUserPanel();
    loadDashboard();
  } catch (err) {
    alert(`Login failed: ${err.message}`);
  }
}

function logout() {
  state.token = '';
  state.user = null;
  localStorage.removeItem('keyforge_token');
  showModal('loginModal');
}

async function checkAuth() {
  if (!state.token) {
    showModal('loginModal');
    return false;
  }
  try {
    state.user = await api('/auth/me');
    updateUserPanel();
    return true;
  } catch {
    logout();
    return false;
  }
}

function updateUserPanel() {
  if (state.user) {
    document.getElementById('displayUsername').textContent = state.user.username;
    document.getElementById('displayRole').textContent = state.user.role;
  }
}

// Navigation
function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.classList.toggle('active', item.dataset.view === viewName);
  });
  document.querySelectorAll('.view-section').forEach((sec) => {
    sec.classList.toggle('active', sec.id === `view-${viewName}`);
  });

  const titles = {
    overview: 'System Overview & Metrics',
    products: 'Product Catalog & Profiles',
    licenses: 'License Lifecycle Manager',
    devices: 'Device Activations & Seats',
    keys: 'Cryptographic Key Vault',
    audit: 'Security Audit Trail',
    playground: 'Interactive License Playground',
  };
  document.getElementById('currentPageTitle').textContent = titles[viewName] || 'Dashboard';

  if (viewName === 'overview') loadOverview();
  else if (viewName === 'products') loadProducts();
  else if (viewName === 'licenses') loadLicenses();
  else if (viewName === 'devices') loadDevices();
  else if (viewName === 'keys') loadKeys();
  else if (viewName === 'audit') loadAudit();
}

// Modal Management
function showModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
}

function hideModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
}

// View: Overview
async function loadOverview() {
  try {
    const stats = await api('/stats');
    state.stats = stats;

    document.getElementById('metricTotalLicenses').textContent = stats.licenses.total;
    document.getElementById('metricActiveLicenses').textContent = stats.licenses.active;
    document.getElementById('metricExpiredLicenses').textContent = stats.licenses.expired;
    document.getElementById('metricRevokedLicenses').textContent = stats.licenses.revoked;
    document.getElementById('metricActiveDevices').textContent = stats.activations.active_devices;
    document.getElementById('metricTotalProducts').textContent = stats.products_count;

    const tbody = document.getElementById('recentEventsTableBody');
    tbody.innerHTML = '';
    stats.recent_audit_events.forEach((ev) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><span class="code-mono">${ev.event_type}</span></td>
        <td>${ev.actor_id}</td>
        <td>${ev.license_id || '-'}</td>
        <td>${ev.reason || '-'}</td>
        <td>${new Date(ev.timestamp).toLocaleString()}</td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error('Failed to load overview:', err);
  }
}

// View: Products
async function loadProducts() {
  try {
    const prods = await api('/products');
    state.products = prods;
    const tbody = document.getElementById('productsTableBody');
    tbody.innerHTML = '';

    prods.forEach((p) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><strong>${p.name}</strong></td>
        <td><span class="code-mono">${p.id}</span></td>
        <td>v${p.version}</td>
        <td><span class="code-mono">${p.active_key_id || 'None'}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="rotateKey('${p.id}')">Rotate Key</button>
        </td>
      `;
      tbody.appendChild(row);
    });

    // Update product selects in modals
    const prodSelect = document.getElementById('issueProductSelect');
    if (prodSelect) {
      prodSelect.innerHTML = prods
        .map((p) => `<option value="${p.id}">${p.name} (${p.id})</option>`)
        .join('');
    }
  } catch (err) {
    console.error('Failed to load products:', err);
  }
}

// View: Licenses
async function loadLicenses() {
  try {
    const search = document.getElementById('licenseSearchInput').value;
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await api(`/licenses${query}`);
    state.licenses = res.items;

    const tbody = document.getElementById('licensesTableBody');
    tbody.innerHTML = '';

    res.items.forEach((lic) => {
      const row = document.createElement('tr');
      const badgeClass = `badge-${lic.status}`;
      row.innerHTML = `
        <td><span class="code-mono">${lic.id}</span></td>
        <td><strong>${lic.license_key_masked}</strong></td>
        <td>${lic.product_id}</td>
        <td>${lic.customer_id}</td>
        <td><span class="badge ${badgeClass}">${lic.status}</span></td>
        <td>${lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : 'Lifetime'}</td>
        <td>${lic.active_devices_count}/${lic.max_devices}</td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="inspectLicense('${lic.id}')">Inspect</button>
          <button class="btn btn-secondary btn-sm" onclick="showRenewModal('${lic.id}')">Renew</button>
          ${
            lic.status === 'active'
              ? `<button class="btn btn-secondary btn-sm" onclick="suspendLicense('${lic.id}')">Suspend</button>`
              : lic.status === 'suspended'
              ? `<button class="btn btn-secondary btn-sm" onclick="reactivateLicense('${lic.id}')">Reactivate</button>`
              : ''
          }
          ${lic.status !== 'revoked' ? `<button class="btn btn-danger btn-sm" onclick="revokeLicense('${lic.id}')">Revoke</button>` : ''}
        </td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error('Failed to load licenses:', err);
  }
}

// View: Keys
async function loadKeys() {
  try {
    const keys = await api('/keys');
    const tbody = document.getElementById('keysTableBody');
    tbody.innerHTML = '';

    keys.forEach((k) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><span class="code-mono">${k.key_id}</span></td>
        <td>${k.product_id}</td>
        <td>v${k.version}</td>
        <td>${k.algorithm}</td>
        <td><span class="badge badge-${k.status === 'active' ? 'active' : 'suspended'}">${k.status}</span></td>
        <td><span class="code-mono">${k.fingerprint.substring(0, 16)}...</span></td>
        <td>${new Date(k.created_at).toLocaleString()}</td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error('Failed to load keys:', err);
  }
}

// View: Audit
async function loadAudit() {
  try {
    const res = await api('/audit?limit=100');
    const tbody = document.getElementById('auditTableBody');
    tbody.innerHTML = '';

    res.items.forEach((ev) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><span class="code-mono">${ev.event_type}</span></td>
        <td>${ev.actor_id} (${ev.actor_type})</td>
        <td>${ev.license_id || '-'}</td>
        <td>${ev.product_id || '-'}</td>
        <td>${ev.reason || '-'}</td>
        <td>${new Date(ev.timestamp).toLocaleString()}</td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error('Failed to load audit events:', err);
  }
}

// View: Devices
async function loadDevices() {
  // Lists active devices by querying licenses
  await loadLicenses();
}

// License Actions
async function issueSingleLicense() {
  const form = document.getElementById('issueLicenseForm');
  const body = {
    product_id: form.product_id.value,
    customer_id: form.customer_id.value,
    customer_email: form.customer_email.value || undefined,
    license_type: form.license_type.value,
    edition: form.edition.value,
    duration_days: parseInt(form.duration_days.value) || 365,
    max_devices: parseInt(form.max_devices.value) || 3,
  };

  try {
    const lic = await api('/licenses', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    hideModal('issueLicenseModal');
    form.reset();
    alert(`License Issued Successfully!\n\nKey: ${lic.license_key}\nLicense ID: ${lic.id}`);
    loadLicenses();
  } catch (err) {
    alert(`Failed to issue license: ${err.message}`);
  }
}

async function inspectLicense(id) {
  try {
    const lic = await api(`/licenses/${id}`);
    document.getElementById('inspectDetailsContent').textContent = JSON.stringify(lic, null, 2);
    showModal('inspectModal');
  } catch (err) {
    alert(`Failed to inspect license: ${err.message}`);
  }
}

async function suspendLicense(id) {
  if (!confirm('Are you sure you want to suspend this license?')) return;
  try {
    await api(`/licenses/${id}/suspend`, {
      method: 'POST',
      body: JSON.stringify({ reason: 'Admin suspended via dashboard' }),
    });
    loadLicenses();
  } catch (err) {
    alert(`Failed to suspend: ${err.message}`);
  }
}

async function reactivateLicense(id) {
  try {
    await api(`/licenses/${id}/reactivate`, {
      method: 'POST',
      body: JSON.stringify({ reason: 'Admin reactivated via dashboard' }),
    });
    loadLicenses();
  } catch (err) {
    alert(`Failed to reactivate: ${err.message}`);
  }
}

async function revokeLicense(id) {
  const reason = prompt('Enter reason for permanent revocation:');
  if (!reason) return;
  try {
    await api(`/licenses/${id}/revoke`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
    loadLicenses();
  } catch (err) {
    alert(`Failed to revoke: ${err.message}`);
  }
}

let activeRenewId = '';
function showRenewModal(id) {
  activeRenewId = id;
  showModal('renewModal');
}

async function submitRenew() {
  const days = parseInt(document.getElementById('renewDaysInput').value) || 365;
  try {
    await api(`/licenses/${activeRenewId}/renew`, {
      method: 'POST',
      body: JSON.stringify({ extend_days: days, reason: `Renewed for ${days} days` }),
    });
    hideModal('renewModal');
    loadLicenses();
  } catch (err) {
    alert(`Failed to renew: ${err.message}`);
  }
}

async function rotateKey(productId) {
  if (!confirm(`Are you sure you want to rotate signing key for product '${productId}'?`)) return;
  try {
    const res = await api(`/keys/${productId}/rotate`, { method: 'POST' });
    alert(`Key rotated successfully! New Key ID: ${res.new_key.key_id}`);
    loadProducts();
    loadKeys();
  } catch (err) {
    alert(`Failed to rotate key: ${err.message}`);
  }
}

// Playground Testing
async function runPlaygroundValidation() {
  const key = document.getElementById('playgroundKeyInput').value.trim();
  const prodId = document.getElementById('playgroundProductInput').value.trim();
  const clientVer = document.getElementById('playgroundVersionInput').value.trim();
  const term = document.getElementById('playgroundTerminal');

  if (!key) {
    term.textContent = 'Error: Please enter a license key or compact token.';
    return;
  }

  term.textContent = 'Validating license against KeyForge authority...\n';
  try {
    const res = await api('/licenses/validate', {
      method: 'POST',
      body: JSON.stringify({
        license_key: key,
        product_id: prodId || 'desktop-app',
        client_version: clientVer || '1.0.0',
      }),
    });
    term.textContent = `=== VALIDATION RESULT ===\n${JSON.stringify(res, null, 2)}`;
  } catch (err) {
    term.textContent = `=== VALIDATION ERROR ===\n${err.message}`;
  }
}

// Change Password
async function submitChangePassword() {
  const current_password = document.getElementById('currentPasswordInput').value;
  const new_password = document.getElementById('newPasswordInput').value;

  try {
    await api('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    });
    hideModal('changePasswordModal');
    document.getElementById('changePasswordForm').reset();
    alert('Password updated successfully! Please keep your new password in a safe place.');
  } catch (err) {
    alert(`Failed to update password: ${err.message}`);
  }
}

// Initialization
async function loadDashboard() {
  await loadOverview();
  await loadProducts();
}

window.addEventListener('DOMContentLoaded', async () => {
  // Navigation event bindings
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.addEventListener('click', () => switchView(item.dataset.view));
  });

  // Login form handler
  document.getElementById('loginForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const u = e.target.username.value;
    const p = e.target.password.value;
    login(u, p);
  });

  // Search input on licenses
  document.getElementById('licenseSearchInput')?.addEventListener('input', () => {
    loadLicenses();
  });

  const isAuthed = await checkAuth();
  if (isAuthed) {
    loadDashboard();
  }
});
