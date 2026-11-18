/*
 * FinancialApp: utilidades compartidas por todas las páginas de la app.
 * Sesión, peticiones autenticadas, formato de dinero, escape de HTML,
 * contador de pendientes y preferencias del dispositivo.
 */

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password', '/reset-password', '/terms'];

// La sesión vive en localStorage ("mantener la sesión iniciada") o en sessionStorage (se cierra con el navegador)
function sessionStore() {
    return localStorage.getItem('financial_token') ? localStorage : sessionStorage;
}
let token = sessionStore().getItem('financial_token');
const user = JSON.parse(sessionStore().getItem('financial_user') || '{}');

function saveSession(newToken, newUser, remember) {
    clearSession();
    const store = remember ? localStorage : sessionStorage;
    store.setItem('financial_token', newToken);
    if (newUser) store.setItem('financial_user', JSON.stringify(newUser));
}

/** Reemplaza el token de la sesión actual (p. ej. tras cambiar la contraseña). */
function replaceToken(newToken) {
    sessionStore().setItem('financial_token', newToken);
    token = newToken;
}

function saveUser(newUser) {
    sessionStore().setItem('financial_user', JSON.stringify(newUser));
    Object.assign(user, newUser);
    document.querySelectorAll('[data-user-name]').forEach(el => { el.textContent = newUser.full_name; });
}

function clearSession() {
    ['financial_token', 'financial_user'].forEach(k => { localStorage.removeItem(k); sessionStorage.removeItem(k); });
}

if (!PUBLIC_PATHS.includes(window.location.pathname) && !token) {
    window.location.replace('/login');
}

function logout() {
    clearSession();
    window.location.href = '/login';
}

/** Valida un formulario con los mensajes de cada campo; marca errores y aciertos. */
function validateFields(form) {
    let ok = true;
    form.querySelectorAll('input, select, textarea').forEach(el => {
        if (!el.willValidate || el.type === 'hidden') return;
        const valid = el.checkValidity();
        el.classList.toggle('is-invalid', !valid);
        el.classList.toggle('is-valid', valid && el.type !== 'checkbox' && el.type !== 'password' && el.value !== '');
        if (!valid && ok) { el.focus(); ok = false; }
    });
    return ok;
}

// Quita la marca de error en cuanto el usuario corrige el campo
document.addEventListener('input', (e) => {
    if (e.target.classList?.contains('is-invalid') && e.target.checkValidity()) e.target.classList.remove('is-invalid');
});

/** Estado de carga de un botón: deshabilitado con texto y rueda. */
function setLoading(btn, loading, text) {
    if (!btn) return;
    if (loading) {
        btn.dataset.label = btn.dataset.label || btn.innerHTML;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>${esc(text || 'Guardando…')}`;
        btn.disabled = true;
        btn.setAttribute('aria-busy', 'true');
    } else {
        if (btn.dataset.label) btn.innerHTML = btn.dataset.label;
        btn.disabled = false;
        btn.removeAttribute('aria-busy');
    }
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
    if (getPrefs().dateFormat === 'numeric') return `${String(d).padStart(2, '0')}/${String(m).padStart(2, '0')}/${y}`;
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

/** Hora local (Ecuador) de un datetime ISO de la API: "14:32" */
function fmtTime(isoDateTime) {
    if (!isoDateTime) return '';
    const d = new Date(isoDateTime);
    return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Guayaquil' });
}

/** "Hoy", "Ayer" o la fecha corta, para agrupar movimientos */
function dayLabel(iso) {
    const today = new Date();
    const fmt = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    if (iso === fmt(today)) return 'Hoy';
    if (iso === fmt(yesterday)) return 'Ayer';
    return fmtDate(iso);
}

/**
 * Anillas de cuenta: franja proporcional (una banda por cuenta con la tinta de su banco)
 * y su leyenda. Al pasar sobre una cuenta su banda se ilumina y las demás se atenúan.
 * items: [{ label, sub, value, color }]
 */
function renderBands(stripEl, legendEl, items) {
    const total = items.reduce((s, x) => s + Math.max(0, x.value), 0);
    const list = items.filter(x => x.value > 0);
    if (!total || !list.length) {
        stripEl.innerHTML = '';
        legendEl.innerHTML = '<li class="text-muted">Agrega una cuenta para ver cómo se reparte tu dinero.</li>';
        return;
    }
    stripEl.innerHTML = list.map((x, i) =>
        `<li data-band="${i}" data-key="${esc(x.key ?? x.label)}" style="--share:${x.value / total};--band:${esc(x.color)}" title="${esc(x.label)} · ${money(x.value)}"></li>`).join('');
    legendEl.innerHTML = list.map((x, i) => `
        <li data-band="${i}" data-key="${esc(x.key ?? x.label)}" tabindex="0" style="--band:${esc(x.color)}">
            <span class="sw"></span><span><strong>${esc(x.label)}</strong>
            <span class="amt">${x.sub ? `${esc(x.sub)} · ` : ''}<span class="text-nowrap">${money(x.value)} · ${pct(x.value / total * 100)}</span></span></span>
        </li>`).join('');
    const focus = (i) => {
        [stripEl, legendEl].forEach(el => {
            el.classList.toggle('is-focus', i !== null);
            el.querySelectorAll('[data-band]').forEach(n => n.classList.toggle('is-on', n.dataset.band === String(i)));
        });
    };
    [stripEl, legendEl].forEach(el => {
        el.onmouseover = e => { const n = e.target.closest('[data-band]'); if (n) focus(n.dataset.band); };
        el.onfocusin = e => { const n = e.target.closest('[data-band]'); if (n) focus(n.dataset.band); };
        el.onmouseleave = () => focus(null);
        el.onfocusout = () => focus(null);
    });
    // Otras filas de la página (cuentas, registro) iluminan su banda con data-band-key
    const byKey = key => stripEl.querySelector(`[data-key="${CSS.escape(String(key))}"]`)?.dataset.band ?? null;
    document.querySelectorAll('[data-band-key]').forEach(row => {
        row.addEventListener('mouseenter', () => focus(byKey(row.dataset.bandKey)));
        row.addEventListener('mouseleave', () => focus(null));
    });
}

/**
 * Muestra una cifra como dígitos; si cambió desde la última visita (clave en localStorage),
 * los dígitos que cambiaron se actualizan uno a uno.
 */
function renderFigure(el, value, storageKey) {
    const text = money(value);
    const previous = storageKey ? localStorage.getItem(storageKey) : null;
    const i = text.lastIndexOf(',');
    const chars = [...text.slice(0, i)];
    const prevChars = previous ? [...previous.slice(0, previous.lastIndexOf(','))] : chars;
    const offset = prevChars.length - chars.length;
    let flipIndex = 0;
    el.innerHTML = chars.map((c, k) => {
        const changed = previous && previous !== text && prevChars[k + offset] !== c;
        const delay = changed ? `style="animation-delay:${(flipIndex++) * 60}ms"` : '';
        return `<span class="digit${changed ? ' is-flip' : ''}" ${delay}>${esc(c)}</span>`;
    }).join('') + `<small>${esc(text.slice(i))}</small>`;
    if (storageKey) localStorage.setItem(storageKey, text);
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
    applyPreferences();
    refreshPendingBadge();
}

// Preferencias guardadas en este dispositivo (Perfil ➝ Preferencias)
function getPrefs() {
    try { return JSON.parse(localStorage.getItem('financial_prefs') || '{}'); } catch (e) { return {}; }
}
function applyPreferences() {
    const prefs = getPrefs();
    const root = document.documentElement;
    if (prefs.theme === 'light' || prefs.theme === 'dark') root.dataset.theme = prefs.theme;
    else delete root.dataset.theme;
    root.classList.toggle('hide-amounts', Boolean(prefs.hideAmounts));
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
