const API_BASE = "/api";
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

// A transaction's receiver is always a service account — show its business
// name, not the (unused) personal name fields.
function formatServiceName(usr) {
    if (!usr) return 'Mavjud emas';
    if (usr.service_name && usr.service_name !== 'This is not a service account') return usr.service_name;
    return usr.username || 'Mavjud emas';
}

const FIELD_LABELS_UZ = {
    username: "Foydalanuvchi nomi",
    password: "Parol",
    password_confirm: "Parolni tasdiqlash",
    phone_number: "Telefon raqami",
    first_name: "Ism",
    last_name: "Familiya",
    middle_name: "Sharif",
    amount: "Summa",
    card_number: "Karta raqami",
    name: "Nomi",
    description: "Tavsif",
    pay_day: "To'lov kuni",
};

// Translates a single FastAPI/Pydantic validation message into Uzbek where we
// recognize the pattern; falls back to the raw message so nothing disappears.
function translateValidationMessage(msg) {
    if (/at least (\d+) character/i.test(msg)) {
        const n = msg.match(/at least (\d+) character/i)[1];
        return `Kamida ${n} ta belgidan iborat bo'lishi kerak`;
    }
    if (/at most (\d+) character/i.test(msg)) {
        const n = msg.match(/at most (\d+) character/i)[1];
        return `Ko'pi bilan ${n} ta belgidan iborat bo'lishi kerak`;
    }
    if (/field required/i.test(msg)) return "Bu maydon to'ldirilishi shart";
    if (/string should match pattern/i.test(msg)) return "Noto'g'ri formatda kiritildi";
    if (/value is not a valid/i.test(msg)) return "Noto'g'ri qiymat kiritildi";
    if (/input should be a valid/i.test(msg)) return "Noto'g'ri qiymat kiritildi";
    if (/greater than or equal to (\d+)/i.test(msg)) {
        const n = msg.match(/greater than or equal to (\d+)/i)[1];
        return `Kamida ${Number(n).toLocaleString('ru-RU')} bo'lishi kerak`;
    }
    return msg;
}

async function extractErrorMessage(res) {
    try {
        const data = await res.json();
        if (data.detail && Array.isArray(data.detail)) {
            return data.detail.map(e => {
                const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : null;
                const label = FIELD_LABELS_UZ[field];
                const message = translateValidationMessage(e.msg || '');
                return label ? `${label}: ${message}` : message;
            }).join('; ');
        }
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

// An application is "pending" once a customer has scanned/claimed it (payer set)
// but the first charge hasn't succeeded yet (is_active still false) and it
// hasn't been permanently closed (end_date still unset).
function appStatusLabel(a) {
    if (a.is_active) return 'Faol';
    if (a.payer && !a.end_date) return 'Kutilmoqda';
    return 'Nofaol';
}
function appStatusClass(a) {
    if (a.is_active) return 'active';
    if (a.payer && !a.end_date) return 'pending';
    return 'inactive';
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

const ROLE_BADGE_LABEL = { admin: 'ADMIN', service: 'BIZNES', user: 'FOYDALANUVCHI' };

function initNavbar() {
    const role = localStorage.getItem("role");
    const roleBadge = document.getElementById("roleBadge");
    if (roleBadge) roleBadge.innerText = ROLE_BADGE_LABEL[role] || 'FOYDALANUVCHI';

    // Nav items/sections can be restricted to one role via data-role="admin-only|service-only|user-only".
    document.querySelectorAll('[data-role]').forEach(el => {
        const required = el.getAttribute('data-role').replace('-only', '');
        el.classList.toggle('hidden', required !== role);
    });

    const path = window.location.pathname.replace(/\/$/, '') || '/dashboard';
    document.querySelectorAll('.topbar-nav a, .mobile-nav-panel a').forEach(link => {
        const linkPath = link.getAttribute('href').replace(/\/$/, '') || '/dashboard';
        link.classList.toggle('active', linkPath === path);
    });

    ensureSharedWidgets();
}

// ---------- Shared bell + profile-edit widgets ----------
// Injected once into every dashboard/admin page's topbar so we don't have to
// hand-edit the markup of every template that includes this script.
function ensureSharedWidgets() {
    const actions = document.querySelector('.topbar-actions');
    if (!actions || document.getElementById('notifBellBtn')) return;

    const bell = document.createElement('a');
    bell.href = '/notifications';
    bell.id = 'notifBellBtn';
    bell.className = 'icon-btn notif-bell';
    bell.title = 'Bildirishnomalar';
    bell.setAttribute('aria-label', 'Bildirishnomalar');
    bell.innerHTML = `<svg viewBox="0 0 24 24"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/></svg><span id="notifBellDot" class="notif-dot hidden"></span>`;

    const profileBtn = document.createElement('button');
    profileBtn.type = 'button';
    profileBtn.className = 'icon-btn';
    profileBtn.title = 'Profilni tahrirlash';
    profileBtn.setAttribute('aria-label', 'Profilni tahrirlash');
    profileBtn.onclick = openProfileEditModal;
    profileBtn.innerHTML = `<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>`;

    const roleBadge = actions.querySelector('#roleBadge');
    if (roleBadge) {
        roleBadge.insertAdjacentElement('afterend', profileBtn);
        roleBadge.insertAdjacentElement('afterend', bell);
    } else {
        actions.prepend(profileBtn);
        actions.prepend(bell);
    }

    ensureProfileEditModal();
    updateNotifBadge();
}

async function updateNotifBadge() {
    try {
        const res = await apiFetch('/notifications/unread-count');
        if (!res.ok) return;
        const data = await res.json();
        const dot = document.getElementById('notifBellDot');
        if (dot) dot.classList.toggle('hidden', !data.unread_count);
    } catch (e) {}
}

function ensureProfileEditModal() {
    if (document.getElementById('profileEditModal')) return;
    const modal = document.createElement('div');
    modal.id = 'profileEditModal';
    modal.className = 'modal hidden';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Profilni tahrirlash</h3>
            <div class="form-group">
                <label>Familiya</label>
                <input type="text" id="profileEditLastName" required>
            </div>
            <div class="form-group">
                <label>Ism</label>
                <input type="text" id="profileEditFirstName" required>
            </div>
            <div class="form-group">
                <label>Sharif</label>
                <input type="text" id="profileEditMiddleName" required>
            </div>
            <div class="form-group">
                <label>Telefon raqami</label>
                <input type="tel" id="profileEditPhone" placeholder="998941234567" required>
            </div>
            <button class="btn btn-primary btn-block" id="profileEditSubmitBtn" onclick="submitProfileEdit()">Saqlash</button>
            <button class="btn btn-outline btn-block" style="margin-top:0.6rem;" onclick="closeProfileEditModal()">Bekor qilish</button>
        </div>
    `;
    document.body.appendChild(modal);
}

async function openProfileEditModal() {
    ensureProfileEditModal();
    const profile = window.__bindinProfile || await loadNavProfile();
    if (profile) {
        document.getElementById('profileEditLastName').value = profile.last_name || '';
        document.getElementById('profileEditFirstName').value = profile.first_name || '';
        document.getElementById('profileEditMiddleName').value = profile.middle_name || '';
        document.getElementById('profileEditPhone').value = profile.phone_number || '';
    }
    document.getElementById('profileEditModal').classList.remove('hidden');
}

function closeProfileEditModal() {
    const el = document.getElementById('profileEditModal');
    if (el) el.classList.add('hidden');
}

async function submitProfileEdit() {
    const restore = setButtonLoading(document.getElementById('profileEditSubmitBtn'), 'Saqlanmoqda...');
    try {
        const payload = {
            last_name: document.getElementById('profileEditLastName').value.trim(),
            first_name: document.getElementById('profileEditFirstName').value.trim(),
            middle_name: document.getElementById('profileEditMiddleName').value.trim(),
            phone_number: document.getElementById('profileEditPhone').value.trim().replace(/\s+/g, ''),
        };
        const res = await apiFetch('/auth/me', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            closeProfileEditModal();
            showAlert("Profil yangilandi.", "success");
            await loadNavProfile();
            if (typeof initOverview === 'function') initOverview();
        } else {
            showAlert(await extractErrorMessage(res), "error");
        }
    } finally {
        restore();
    }
}

function requireRole(allowedRoles) {
    const role = localStorage.getItem("role");
    if (!allowedRoles.includes(role)) {
        window.location.href = role === 'admin' ? '/admin' : (role === 'service' ? '/dashboard' : '/dashboard');
    }
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

// ---------- Pagination ----------
// Renders Prev/Next controls for a PaginatedResponse ({items,total,page,page_size,total_pages,has_next,has_previous})
// and calls onPageChange(nextPage) when the viewer navigates.
function renderPagination(container, paginated, onPageChange) {
    if (!container) return;
    if (!paginated || paginated.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = `
        <div class="pagination">
            <button type="button" class="btn btn-secondary btn-sm" id="paginationPrev" ${paginated.has_previous ? '' : 'disabled'}>← Oldingi</button>
            <span class="pagination-info">${paginated.page} / ${paginated.total_pages} (jami ${paginated.total})</span>
            <button type="button" class="btn btn-secondary btn-sm" id="paginationNext" ${paginated.has_next ? '' : 'disabled'}>Keyingi →</button>
        </div>
    `;

    const prevBtn = container.querySelector('#paginationPrev');
    const nextBtn = container.querySelector('#paginationNext');
    if (prevBtn) prevBtn.addEventListener('click', () => onPageChange(paginated.page - 1));
    if (nextBtn) nextBtn.addEventListener('click', () => onPageChange(paginated.page + 1));
}

document.addEventListener('DOMContentLoaded', initNavbar);
