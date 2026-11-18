/*
 * FinancialApp: utilidades compartidas por todas las páginas de la app.
 * Sesión, peticiones autenticadas, formato de dinero, escape de HTML,
 * contador de pendientes y perfil de usuario.
 */

const PUBLIC_PATHS = ['/login', '/register'];
const token = localStorage.getItem('financial_token');
const user = JSON.parse(localStorage.getItem('financial_user') || '{}');

if (!PUBLIC_PATHS.includes(window.location.pathname) && !token) {
    window.location.replace('/login');
}

function logout() {
    localStorage.removeItem('financial_token');
    localStorage.removeItem('financial_user');
    window.location.href = '/login';
}

/** fetch con el token del usuario; si la sesión expiró vuelve al login. */
async function authFetch(url, options = {}) {
    options.headers = { ...options.headers, 'Authorization': `Bearer ${token}` };
    const res = await fetch(url, options);
    if (res.status === 401) {
        logout();
        throw new Error('Tu sesión expiró. Vuelve a iniciar sesión.');
    }
    return res;
}

/** Mensaje legible de un error de la API (FastAPI devuelve texto o lista de errores). */
function apiError(data, fallback = 'No se pudo completar la acción.') {
    if (!data || !data.detail) return fallback;
    return Array.isArray(data.detail) ? data.detail.map(d => d.msg).join('; ') : data.detail;
}

const moneyFormat = new Intl.NumberFormat('es-EC', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** 1234.5 -> "$1.234,50"; con sign=true agrega + o − */
function money(value, { sign = false } = {}) {
    const n = Number(value) || 0;
    const prefix = sign ? (n > 0 ? '+' : n < 0 ? '−' : '') : (n < 0 ? '−' : '');
    return `${prefix}$${moneyFormat.format(Math.abs(n))}`;
}

const MONTHS_SHORT = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** "2026-11-05" -> "5 nov" (año actual) o "5 nov 2025" (otro año) */
function fmtDate(iso) {
    if (!iso) return '';
    const [y, m, d] = String(iso).slice(0, 10).split('-').map(Number);
    if (!y || !m || !d) return String(iso);
    return `${d} ${MONTHS_SHORT[m - 1]}${y === new Date().getFullYear() ? '' : ` ${y}`}`;
}

/** 4.5 -> "4,50" para mostrar en un campo de monto */
function amountInput(value) {
    return value === null || value === undefined || value === '' ? '' : Number(value).toFixed(2).replace('.', ',');
}

/** "1.234,50" | "4,5" | "4.50" -> "1234.50" (texto listo para la API) o '' si no es válido */
function parseAmountInput(text) {
    let t = String(text || '').trim().replace(/[^\d.,]/g, '');
    if (t.includes(',')) t = t.replace(/\./g, '').replace(',', '.');
    const n = Number(t);
    return t && Number.isFinite(n) && n > 0 ? n.toFixed(2) : '';
}

/** 84 -> "84%", 10.5 -> "10,5%" */
function pct(value) {
    const n = Number(value) || 0;
    return Math.abs(n - Math.round(n)) < 0.05 ? `${Math.round(n)}%` : `${n.toFixed(1).replace('.', ',')}%`;
}

/** Escapa texto externo antes de insertarlo como HTML. */
function esc(value) {
    const div = document.createElement('div');
    div.textContent = value ?? '';
    return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/** Muestra un aviso en el contenedor #globalAlert de la página. */
function showAlert(type, message, timeout = 4500) {
    const box = document.getElementById('globalAlert');
    if (!box) return;
    box.className = `alert alert-${type}`;
    box.textContent = message;
    if (timeout) setTimeout(() => { box.className = 'alert d-none'; }, timeout);
}

/** Alterna la visibilidad de un campo de contraseña. */
function bindPasswordToggle(buttonId, inputId) {
    const btn = document.getElementById(buttonId);
    const input = document.getElementById(inputId);
    if (!btn || !input) return;
    btn.addEventListener('click', () => {
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        btn.querySelector('i').className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
        btn.setAttribute('aria-label', show ? 'Ocultar contraseña' : 'Mostrar contraseña');
    });
}

/** Actualiza los contadores de pagos pendientes del iPhone en la navegación. */
async function refreshPendingBadge() {
    if (!token) return;
    try {
        const res = await authFetch('/api/v1/pending/count');
        if (!res.ok) return;
        const { pending } = await res.json();
        document.querySelectorAll('[data-pending-count]').forEach(el => {
            el.textContent = pending;
            el.hidden = pending === 0;
        });
    } catch (e) { /* sin conexión: no se muestra nada */ }
}

// -----------------------------------------------------------------------------
// Shell de la app: usuario, salir, perfil
// -----------------------------------------------------------------------------
function initShell() {
    document.querySelectorAll('[data-user-name]').forEach(el => { el.textContent = user.full_name || 'Usuario'; });
    document.querySelectorAll('[data-action="logout"]').forEach(el => el.addEventListener('click', logout));
    document.querySelectorAll('[data-action="profile"]').forEach(el => el.addEventListener('click', openProfile));

    const form = document.getElementById('profileForm');
    if (form) {
        bindPasswordToggle('toggleProfilePwd', 'profileNewPassword');
        form.addEventListener('submit', saveProfile);
    }
    refreshPendingBadge();
}

function openProfile() {
    const modal = document.getElementById('profileModal');
    if (!modal) return;
    document.getElementById('profileAlert').className = 'alert d-none';
    document.getElementById('profileFullName').value = user.full_name || '';
    document.getElementById('profileEmail').value = user.email || '';
    document.getElementById('profileCurrency').value = user.currency_preference || 'USD';
    document.getElementById('profileNewPassword').value = '';
    document.getElementById('profileCurrentPassword').value = '';
    document.getElementById('profileConfirmPassword').value = '';
    bootstrap.Modal.getOrCreateInstance(modal).show();
}

async function saveProfile(event) {
    event.preventDefault();
    const alertBox = document.getElementById('profileAlert');
    const btn = event.submitter;
    const newPwd = document.getElementById('profileNewPassword').value;
    if (newPwd && newPwd !== document.getElementById('profileConfirmPassword').value) {
        alertBox.className = 'alert alert-danger';
        alertBox.textContent = 'Las contraseñas no coinciden.';
        return;
    }
    const payload = {
        full_name: document.getElementById('profileFullName').value.trim(),
        currency_preference: document.getElementById('profileCurrency').value,
    };
    if (newPwd) {
        const current = document.getElementById('profileCurrentPassword').value;
        if (!current) {
            alertBox.className = 'alert alert-danger';
            alertBox.textContent = 'Escribe tu contraseña actual para cambiarla.';
            return;
        }
        payload.password = newPwd;
        payload.current_password = current;
    }

    btn.disabled = true;
    try {
        const res = await authFetch('/api/v1/auth/me', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(apiError(data, 'No se pudo actualizar el perfil.'));
        localStorage.setItem('financial_user', JSON.stringify(data));
        Object.assign(user, data);
        document.querySelectorAll('[data-user-name]').forEach(el => { el.textContent = data.full_name; });
        alertBox.className = 'alert alert-success';
        alertBox.textContent = 'Perfil actualizado.';
        setTimeout(() => bootstrap.Modal.getInstance(document.getElementById('profileModal'))?.hide(), 900);
    } catch (err) {
        alertBox.className = 'alert alert-danger';
        alertBox.textContent = err.message;
    } finally {
        btn.disabled = false;
    }
}

/**
 * Zona de borrado dentro de un diálogo: "Eliminar…" muestra la confirmación,
 * y solo "Sí, eliminar" ejecuta onConfirm. Se reinicia cada vez que se usa.
 */
function setupDangerZone(zone, onConfirm) {
    zone.classList.remove('is-confirming');
    zone.querySelector('[data-danger="ask"]').onclick = () => zone.classList.add('is-confirming');
    zone.querySelector('[data-danger="cancel"]').onclick = () => zone.classList.remove('is-confirming');
    zone.querySelector('[data-danger="confirm"]').onclick = async (e) => {
        e.target.disabled = true;
        try { await onConfirm(); } finally { e.target.disabled = false; zone.classList.remove('is-confirming'); }
    };
}

document.addEventListener('DOMContentLoaded', initShell);
