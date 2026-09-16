const API_BASE = "https://bindin.uz/api";
let activeLoaders = 0;

// Guard: every dashboard page requires an authenticated session.
if (!localStorage.getItem("token")) {
    window.location.href = "/auth";
}

function showLoader() {
    activeLoaders++;
    const el = document.getElementById("globalLoader");
    if (el) el.classList.remove("hidden");
}

function hideLoader() {
    activeLoaders = Math.max(0, activeLoaders - 1);
    if (activeLoaders === 0) {
        const el = document.getElementById("globalLoader");
        if (el) el.classList.add("hidden");
    }
}

function setButtonLoading(button, loadingText) {
    if (!button) return () => {};
    const originalHTML = button.innerHTML;
    const originalDisabled = button.disabled;
    button.disabled = true;
    button.innerHTML = `<span class="btn-spinner"></span>${loadingText ? `<span>${loadingText}</span>` : ''}`;
    return () => {
        button.innerHTML = originalHTML;
        button.disabled = originalDisabled;
    };
}

function showAlert(message, type = 'info', title = 'Tizim bildirishnomasi') {
    const titleEl = document.getElementById("govModalTitle");
    const body = document.getElementById("govModalBody");
    if (!titleEl || !body) return;
    titleEl.innerText = title;
    body.innerText = message;
    body.className = `gov-alert-body ${type}`;
    document.getElementById("govModal").classList.remove("hidden");
}

function closeGovAlert() {
    const el = document.getElementById("govModal");
    if (el) el.classList.add("hidden");
}

function emptyState(message) {
    return `<div class="empty-state">
        <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
        <p>${message}</p>
    </div>`;
}

function initials(a, b) {
    const first = (a || '').trim().charAt(0);
    const second = (b || '').trim().charAt(0);
    const combo = `${first}${second}`.toUpperCase();
    return combo || '--';
}

function formatUserFullName(usr) {
    if (!usr) return 'Mavjud emas';
    const parts = [usr.last_name, usr.first_name, usr.middle_name].filter(Boolean);
    return parts.length > 0 ? parts.join(' ') : (usr.username || 'Mavjud emas');
}

async function extractErrorMessage(res) {
    try {
        const data = await res.json();
        if (data.detail && Array.isArray(data.detail)) return data.detail.map(e => e.msg).join(', ');
        return data.detail || "Xatolik yuz berdi.";
    } catch {
        return "Noma'lum xatolik yuz berdi.";
    }
}

function logout() {
    localStorage.clear();
    window.location.href = "/";
}

async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem("token");
    const headers = { ...options.headers, "Authorization": `Bearer ${token}` };
    showLoader();
    try {
        const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        if (res.status === 401) {
            localStorage.clear();
            window.location.href = "/auth";
        }
        return res;
    } finally {
        hideLoader();
    }
}

function cardIconSvg() {
    return `<svg viewBox="0 0 24 24"><path d="M20 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V6c0-1.11-.89-2-2-2zm0 14H4v-6h16v6zm0-10H4V6h16v2z"/></svg>`;
}
function appIconSvg() {
    return `<svg viewBox="0 0 24 24"><path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/></svg>`;
}
function txIconSvg() {
    return `<svg viewBox="0 0 24 24"><path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/></svg>`;
}

// ---------- Shared navbar wiring ----------
function toggleMobileNav() {
    const panel = document.getElementById("mobileNavPanel");
    if (panel) panel.classList.toggle("open");
}

function initNavbar() {
    const role = localStorage.getItem("role");
    const roleBadge = document.getElementById("roleBadge");
    if (roleBadge) roleBadge.innerText = role === 'service' ? 'BIZNES' : 'FOYDALANUVCHI';

    // Cards are a user-only concept — services manage applications/transactions instead.
    document.querySelectorAll('[data-role="user-only"]').forEach(el => {
        el.classList.toggle('hidden', role !== 'user');
    });

    const path = window.location.pathname.replace(/\/$/, '') || '/dashboard';
    document.querySelectorAll('.topbar-nav a, .mobile-nav-panel a').forEach(link => {
        const linkPath = link.getAttribute('href').replace(/\/$/, '') || '/dashboard';
        link.classList.toggle('active', linkPath === path);
    });
}

async function loadNavProfile() {
    const role = localStorage.getItem("role");
    const endpoint = role === 'service' ? '/auth/me_service' : '/auth/me';
    const res = await apiFetch(endpoint);
    if (res.ok) {
        const profile = await res.json();
        window.__bindinProfile = profile;
        document.dispatchEvent(new CustomEvent('bindin:profile', { detail: profile }));
        return profile;
    }
    return null;
}

document.addEventListener('DOMContentLoaded', initNavbar);
