/**
 * KeyForge Enterprise Admin Dashboard Application Controller
 * High-performance, zero-emoji, SVG-driven controller with Toast & Batch Generation
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

// Toast Notifications
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>`,
  };

  toast.innerHTML = `
    ${icons[type] || icons.info}
    <span>${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => toast.classList.add('show'), 10);

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

// Copy to Clipboard with Toast
async function copyToClipboard(text, label = 'Copied') {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`${label} copied to clipboard!`, 'success');
  } catch {
    const el = document.createElement('textarea');
    el.value = text;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showToast(`${label} copied to clipboard!`, 'success');
  }
}

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
      throw new Error('Session expired. Please sign in again.');
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
    showToast(`Welcome back, ${data.user.username}`, 'success');
  } catch (err) {
    showToast(err.message || 'Authentication failed', 'error');
  }
}

function logout() {
  state.token = '';
  state.user = null;
  localStorage.removeItem('keyforge_token');
  showModal('loginModal');
  showToast('Signed out successfully', 'info');
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
    const u = state.user.username || 'Admin';
    document.getElementById('displayUsername').textContent = u;
    document.getElementById('displayRole').textContent = state.user.role || 'SUPER_ADMIN';
    const avatar = document.getElementById('avatarLetter');
    if (avatar) avatar.textContent = u.charAt(0).toUpperCase();
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
    overview: { title: 'System Overview', sub: 'Real-time metrics, license activity, and authority status' },
    products: { title: 'Product Catalog & Profiles', sub: 'Declarative product policies and active signing keys' },
    licenses: { title: 'License Lifecycle Manager', sub: 'Issued keys, seat allocations, expiration, and status control' },
    keys: { title: 'Cryptographic Key Vault', sub: 'Ed25519 asymmetric verification keys and rotation schedules' },
    audit: { title: 'Security Audit Trail', sub: 'Immutable, structured event log of administrative actions' },
    playground: { title: 'Interactive Playground', sub: 'Sandbox verification and negative tamper testing' },
  };

  const current = titles[viewName] || { title: 'Dashboard', sub: '' };
  document.getElementById('currentPageTitle').textContent = current.title;
  document.getElementById('currentPageSubtitle').textContent = current.sub;

  if (viewName === 'overview') loadOverview();
  else if (viewName === 'products') loadProducts();
  else if (viewName === 'licenses') loadLicenses();
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

    if (!stats.recent_audit_events || stats.recent_audit_events.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No security events recorded yet.</p></div></td></tr>`;
      return;
    }

    stats.recent_audit_events.forEach((ev) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><span class="code-mono">${ev.event_type}</span></td>
        <td>${ev.actor_id}</td>
        <td>${ev.license_id ? `<span class="code-mono code-copyable" onclick="copyToClipboard('${ev.license_id}')">${ev.license_id}</span>` : '-'}</td>
        <td>${ev.reason || '-'}</td>
        <td style="color: var(--text-dim); font-size: 12px;">${new Date(ev.timestamp).toLocaleString()}</td>
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

    if (prods.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No products registered yet.</p></div></td></tr>`;
      return;
    }

    prods.forEach((p) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><strong>${p.name}</strong></td>
        <td><span class="code-mono">${p.id}</span></td>
        <td><span class="badge badge-active">v${p.version}</span></td>
        <td><span class="code-mono">${p.active_key_id || 'None'}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="rotateKey('${p.id}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px; height:13px;"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Rotate Key
          </button>
        </td>
      `;
      tbody.appendChild(row);
    });

    // Populate dropdowns in modals
    const issueSelect = document.getElementById('issueProductSelect');
    const batchSelect = document.getElementById('batchProductSelect');
    const optionsHtml = prods.map((p) => `<option value="${p.id}">${p.name} (${p.id})</option>`).join('');
    if (issueSelect) issueSelect.innerHTML = optionsHtml;
    if (batchSelect) batchSelect.innerHTML = optionsHtml;
  } catch (err) {
    console.error('Failed to load products:', err);
  }
}

// View: Licenses
async function loadLicenses() {
  try {
    const search = document.getElementById('licenseSearchInput')?.value || '';
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await api(`/licenses${query}`);
    state.licenses = res.items;

    const tbody = document.getElementById('licensesTableBody');
    tbody.innerHTML = '';

    if (res.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><p>No licenses match your query.</p></div></td></tr>`;
      return;
    }

    res.items.forEach((lic) => {
      const row = document.createElement('tr');
      const badgeClass = `badge-${lic.status}`;
      row.innerHTML = `
        <td><span class="code-mono">${lic.id}</span></td>
        <td>
          <span class="code-mono code-copyable" title="Click to copy masked key" onclick="copyToClipboard('${lic.license_key_masked}', 'License Key')">
            ${lic.license_key_masked}
          </span>
        </td>
        <td>${lic.product_id}</td>
        <td>${lic.customer_id}</td>
        <td>
          <span class="badge ${badgeClass}">
            <span class="badge-dot"></span>
            ${lic.status}
          </span>
        </td>
        <td>${lic.expires_at ? new Date(lic.expires_at).toLocaleDateString() : '<span style="color:var(--text-dim)">Perpetual</span>'}</td>
        <td><strong>${lic.active_devices_count}</strong> / ${lic.max_devices}</td>
        <td>
          <div class="btn-group">
            <button class="btn btn-secondary btn-sm" onclick="inspectLicense('${lic.id}')" title="Inspect Claims">Inspect</button>
            <button class="btn btn-secondary btn-sm" onclick="showRenewModal('${lic.id}')" title="Renew / Extend">Renew</button>
            ${
              lic.status === 'active'
                ? `<button class="btn btn-secondary btn-sm" onclick="suspendLicense('${lic.id}')">Suspend</button>`
                : lic.status === 'suspended'
                ? `<button class="btn btn-secondary btn-sm" onclick="reactivateLicense('${lic.id}')">Reactivate</button>`
                : ''
            }
            ${lic.status !== 'revoked' ? `<button class="btn btn-danger btn-sm" onclick="revokeLicense('${lic.id}')">Revoke</button>` : ''}
          </div>
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

    if (keys.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>No verification keys found in vault.</p></div></td></tr>`;
      return;
    }

    keys.forEach((k) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><span class="code-mono">${k.key_id}</span></td>
        <td>${k.product_id}</td>
        <td><span class="badge badge-active">v${k.version}</span></td>
        <td><span class="code-mono">${k.algorithm}</span></td>
        <td>
          <span class="badge ${k.status === 'active' ? 'badge-active' : 'badge-suspended'}">
            <span class="badge-dot"></span>
            ${k.status}
          </span>
        </td>
        <td>
          <span class="code-mono code-copyable" title="Click to copy full fingerprint" onclick="copyToClipboard('${k.fingerprint}', 'Fingerprint')">
            ${k.fingerprint.substring(0, 16)}...
          </span>
        </td>
        <td style="color: var(--text-dim); font-size: 12px;">${new Date(k.created_at).toLocaleString()}</td>
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

    if (res.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>No audit trail records found.</p></div></td></tr>`;
      return;
    }

    res.items.forEach((ev) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td><span class="code-mono">${ev.event_type}</span></td>
        <td>${ev.actor_id} <span style="color:var(--text-dim)">(${ev.actor_type})</span></td>
        <td>${ev.license_id ? `<span class="code-mono code-copyable" onclick="copyToClipboard('${ev.license_id}')">${ev.license_id}</span>` : '-'}</td>
        <td>${ev.product_id || '-'}</td>
        <td>${ev.reason || '-'}</td>
        <td style="color: var(--text-dim); font-size: 12px;">${new Date(ev.timestamp).toLocaleString()}</td>
      `;
      tbody.appendChild(row);
    });
  } catch (err) {
    console.error('Failed to load audit events:', err);
  }
}

// Actions: Issue Single License
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
    showToast(`License issued: ${lic.license_key}`, 'success');
    loadLicenses();
    loadOverview();
  } catch (err) {
    showToast(`Failed to issue license: ${err.message}`, 'error');
  }
}

// Actions: Batch Issue Licenses
async function issueBatchLicenses() {
  const form = document.getElementById('batchIssueForm');
  const prodId = form.product_id.value;
  const count = parseInt(form.count.value) || 10;
  const prefix = form.customer_prefix.value || 'bulk';
  const type = form.license_type.value;
  const edition = form.edition.value;

  const items = [];
  for (let i = 1; i <= count; i++) {
    items.push({
      product_id: prodId,
      customer_id: `${prefix}_${String(i).padStart(3, '0')}`,
      license_type: type,
      edition: edition,
      duration_days: 365,
      max_devices: 3,
    });
  }

  try {
    const res = await api('/licenses/batch', {
      method: 'POST',
      body: JSON.stringify({ items }),
    });
    hideModal('batchIssueModal');
    showToast(`Generated ${res.count} licenses successfully!`, 'success');
    loadLicenses();
    loadOverview();

    // Auto-download batch as JSON file
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(res.licenses, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `keyforge_batch_${prodId}_${Date.now()}.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
  } catch (err) {
    showToast(`Batch generation failed: ${err.message}`, 'error');
  }
}

async function inspectLicense(id) {
  try {
    const lic = await api(`/licenses/${id}`);
    document.getElementById('inspectDetailsContent').textContent = JSON.stringify(lic, null, 2);
    showModal('inspectModal');
  } catch (err) {
    showToast(`Failed to inspect license: ${err.message}`, 'error');
  }
}

async function suspendLicense(id) {
  if (!confirm('Are you sure you want to suspend this license?')) return;
  try {
    await api(`/licenses/${id}/suspend`, {
      method: 'POST',
      body: JSON.stringify({ reason: 'Administrator suspended via console' }),
    });
    showToast('License suspended', 'info');
    loadLicenses();
  } catch (err) {
    showToast(`Failed to suspend: ${err.message}`, 'error');
  }
}

async function reactivateLicense(id) {
  try {
    await api(`/licenses/${id}/reactivate`, {
      method: 'POST',
      body: JSON.stringify({ reason: 'Administrator reactivated via console' }),
    });
    showToast('License reactivated', 'success');
    loadLicenses();
  } catch (err) {
    showToast(`Failed to reactivate: ${err.message}`, 'error');
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
    showToast('License permanently revoked', 'error');
    loadLicenses();
    loadOverview();
  } catch (err) {
    showToast(`Failed to revoke: ${err.message}`, 'error');
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
    showToast(`License renewed for ${days} days`, 'success');
    loadLicenses();
  } catch (err) {
    showToast(`Failed to renew: ${err.message}`, 'error');
  }
}

async function rotateKey(productId) {
  if (!confirm(`Are you sure you want to rotate signing key for product '${productId}'?`)) return;
  try {
    const res = await api(`/keys/${productId}/rotate`, { method: 'POST' });
    showToast(`Key rotated: ${res.new_key.key_id}`, 'success');
    loadProducts();
    loadKeys();
  } catch (err) {
    showToast(`Failed to rotate key: ${err.message}`, 'error');
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

  term.textContent = 'Executing cryptographic validation against KeyForge authority...\n';
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
    showToast('Password updated successfully!', 'success');
  } catch (err) {
    showToast(`Failed to update password: ${err.message}`, 'error');
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

  // Search input on licenses (debounced)
  let searchTimeout;
  document.getElementById('licenseSearchInput')?.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadLicenses, 200);
  });

  // Global Escape key to dismiss modals
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay.active').forEach((m) => {
        if (m.id !== 'loginModal') m.classList.remove('active');
      });
    }
  });

  const isAuthed = await checkAuth();
  if (isAuthed) {
    loadDashboard();
  }
});
