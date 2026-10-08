/**
 * Moliya (Kalkulator) — Frontend Application Engine
 * Asynchronous pure vanilla JS with live REST API integration
 */

const API_BASE = '/api/v1';

// ==========================================
// IKONKALAR — emoji o'rniga o'zimiz chizgan SVG belgilar
// (24x24, currentColor, stroke asosida)
// ==========================================

const ICONS = {
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  logout:   '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
  receipt:  '<path d="M6 2h12v20l-3-2-3 2-3-2-3 2z"/><path d="M9 7h6M9 11h6M9 15h4"/>',
  chart:    '<path d="M3 3v18h18"/><path d="M7 16v-4M12 16V8M17 16v-7"/>',
  wallet:   '<rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 10h18M16 14h2"/>',
  ledger:   '<path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20V2H6.5A2.5 2.5 0 0 0 4 4.5z"/><path d="M4 17.5h16"/>',
  members:  '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20v-1a4.5 4.5 0 0 1 4.5-4.5h4a4.5 4.5 0 0 1 4.5 4.5v1"/><circle cx="17" cy="9" r="2.5"/><path d="M17.5 14.6A4 4 0 0 1 21.5 18.5V20"/>',
  expense:  '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 10v4M18 10v4"/>',
  income:   '<path d="M22 7l-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  transfer: '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
  card:     '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
  trash:    '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>',
  check:    '<circle cx="12" cy="12" r="10"/><path d="M8 12.5l2.5 2.5L16 9.5"/>',
  warning:  '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  person:   '<circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/>',
  tag:      '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L2 12V2h10l8.6 8.6a2 2 0 0 1 0 2.8z"/><circle cx="7" cy="7" r="1.5"/>',
  pin:      '<path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/>',
  note:     '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  folder:   '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  up:       '<path d="M12 19V5M5 12l7-7 7 7"/>',
  down:     '<path d="M12 5v14M19 12l-7 7-7-7"/>',
  clock:    '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  plus:     '<path d="M12 5v14M5 12h14"/>',
  incomeArrow:  '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>',
  expenseArrow: '<line x1="7" y1="7" x2="17" y2="17"/><polyline points="17 7 17 17 7 17"/>',
};

function icon(name) {
  const body = ICONS[name];
  return body ? `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${body}</svg>` : '';
}

// HTML ichidagi <span data-icon="..."></span> belgilarini SVG bilan to'ldiradi
function hydrateIcons(root = document) {
  root.querySelectorAll('[data-icon]').forEach(el => {
    el.innerHTML = icon(el.dataset.icon);
  });
}
hydrateIcons();

// ==========================================
// CSRF HIMOYASI — Django xavfsizligi
// ==========================================

/**
 * Django tomonidan o'rnatilgan 'csrftoken' cookie'sini o'qib olish.
 * Bu token barcha POST/PUT/PATCH/DELETE so'rovlarga qo'shilishi shart.
 */
function getCsrfToken() {
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    cookie = cookie.trim();
    if (cookie.startsWith('csrftoken=')) {
      return decodeURIComponent(cookie.substring('csrftoken='.length));
    }
  }
  return '';
}

/**
 * Global fetch() ni intercept qilib, barcha mutatsiya so'rovlariga
 * (POST, PUT, PATCH, DELETE) avtomatik X-CSRFToken header qo'shadi.
 * GET va HEAD so'rovlarga tegmaydi.
 */
const _originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  if (method !== 'GET' && method !== 'HEAD') {
    options.headers = {
      ...(options.headers || {}),
      'X-CSRFToken': getCsrfToken(),
    };
  }
  const response = await _originalFetch.call(window, url, options);
  if (response.status === 401 && typeof url === 'string' && !url.includes('/auth/')) {
    checkAuth();
  }
  return response;
};

// Global state
let state = {
  summary: {},
  wallets: [],
  members: [],
  incomeCategories: [],
  expenseCategories: [],
  expenses: [],
  incomes: [],
  transfers: [],
  debts: [],
  activeTab: 'all',
  currentUser: null,
  currentUserId: null,
  txOffset: 0,
  txLimit: 15,
  hasMoreTx: false,
};

// Utilities
function formatMoney(amount, currency = 'UZS') {
  if (amount === undefined || amount === null) return '0 ' + currency;
  return new Intl.NumberFormat('uz-UZ').format(amount) + ' ' + currency;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('uz-UZ', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// Ilovaning o'z tasdiqlash oynasi (brauzerning standart oynasi o'rniga). true / false bilan hal bo'ladigan Promise qaytaradi
let _confirmResolver = null;

function showConfirm({ title = 'Tasdiqlang', message = '', confirmText = 'Ha', cancelText = "Yo'q", danger = true } = {}) {
  return new Promise(resolve => {
    if (_confirmResolver) _confirmResolver(false);
    _confirmResolver = resolve;

    document.getElementById('confirmTitle').textContent = title;
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmIcon').innerHTML = icon(danger ? 'warning' : 'check');
    document.getElementById('confirmIcon').classList.toggle('danger', danger);
    const okBtn = document.getElementById('btnConfirmOk');
    okBtn.textContent = confirmText;
    okBtn.className = danger ? 'btn btn-rose' : 'btn btn-primary';
    document.getElementById('btnConfirmCancel').textContent = cancelText;

    openModal('modalConfirm');
    document.getElementById('btnConfirmCancel').focus();
  });
}

function _resolveConfirm(value) {
  closeModal('modalConfirm');
  const resolve = _confirmResolver;
  _confirmResolver = null;
  if (resolve) resolve(value);
}

document.getElementById('btnConfirmOk')?.addEventListener('click', () => _resolveConfirm(true));
document.getElementById('btnConfirmCancel')?.addEventListener('click', () => _resolveConfirm(false));
document.getElementById('modalConfirm')?.addEventListener('click', (e) => {
  if (e.target.id === 'modalConfirm') _resolveConfirm(false);
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && document.getElementById('modalConfirm')?.classList.contains('active')) _resolveConfirm(false);
});

// O'chirishdan oldin ikki marta so'raydi: avval amalga xos tasdiq, keyin "rostan ham?" tasdig'i
async function confirmDelete(firstMessage) {
  const first = await showConfirm({
    title: "O'chirilsinmi?",
    message: firstMessage,
    confirmText: "Ha, o'chirish",
    cancelText: "Yo'q",
  });
  if (!first) return false;
  return showConfirm({
    title: "Rostan ham o'chirmoqchimisiz?",
    message: "Bu amalni ortga qaytarib bo'lmaydi.",
    confirmText: "Ha, o'chirilsin",
    cancelText: "Yo'q, qoldirish",
  });
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? icon('check') : icon('warning')}</span>
    <div>${message}</div>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function getCurrentDateTimeLocal() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

// Balance hide/show toggle (fintech-style privacy)
const BALANCE_HIDDEN_KEY = 'moliyaBalanceHidden';
function applyBalanceVisibility() {
  const hidden = localStorage.getItem(BALANCE_HIDDEN_KEY) === '1';
  const sumEl = document.getElementById('heroBalanceSum');
  const btn = document.getElementById('btnToggleBalance');
  if (!sumEl || !btn) return;
  sumEl.classList.toggle('balance-hidden', hidden);
  const eyeShow = btn.querySelector('.eye-show');
  const eyeHide = btn.querySelector('.eye-hide');
  if (eyeShow && eyeHide) {
    eyeShow.style.display = hidden ? 'none' : 'block';
    eyeHide.style.display = hidden ? 'block' : 'none';
  }
  btn.title = hidden ? "Balansni ko'rsatish" : 'Balansni yashirish';
}
document.getElementById('btnToggleBalance')?.addEventListener('click', () => {
  const hidden = localStorage.getItem(BALANCE_HIDDEN_KEY) === '1';
  localStorage.setItem(BALANCE_HIDDEN_KEY, hidden ? '0' : '1');
  applyBalanceVisibility();
});
applyBalanceVisibility();

// ==========================================
// YORUG' / QORONG'U REJIM (Light / Dark theme)
// ==========================================
const THEME_KEY = 'moliyaTheme';

function applyThemeIcon(theme) {
  const btn = document.getElementById('btnThemeToggle');
  if (!btn) return;
  const sun = btn.querySelector('.theme-ico-sun');
  const moon = btn.querySelector('.theme-ico-moon');
  if (sun && moon) {
    sun.style.display = theme === 'dark' ? 'none' : 'block';
    moon.style.display = theme === 'dark' ? 'block' : 'none';
  }
  btn.title = theme === 'dark' ? "Yorug' rejimga o'tish" : "Qorong'u rejimga o'tish";
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  applyThemeIcon(theme);
}

document.getElementById('btnThemeToggle')?.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  setTheme(current === 'dark' ? 'light' : 'dark');
});

applyThemeIcon(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');

// Modal open/close helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.add('active');
    if (id === 'modalExpense') {
      const expDate = document.getElementById('expenseDate');
      if (expDate && !expDate.value) expDate.value = getCurrentDateTimeLocal();
    }
    if (id === 'modalIncome') {
      const incDate = document.getElementById('incomeDate');
      if (incDate && !incDate.value) incDate.value = getCurrentDateTimeLocal();
    }
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('active');
}

// Close modal when clicking outside
window.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-backdrop')) {
    e.target.classList.remove('active');
  }
});

// ==========================================
// CUSTOM SELECT — native <select> ni to'liq stillangan
// (tema ranglariga mos) dropdown bilan almashtiradi.
// ==========================================

function enhanceCustomSelect(select) {
  if (select.dataset.csEnhanced) return;
  select.dataset.csEnhanced = '1';

  const wrapper = document.createElement('div');
  wrapper.className = 'custom-select-wrapper';
  select.parentNode.insertBefore(wrapper, select);
  wrapper.appendChild(select);

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'custom-select-trigger';
  trigger.innerHTML = '<span></span>';
  wrapper.appendChild(trigger);

  const panel = document.createElement('div');
  panel.className = 'custom-select-panel';
  document.body.appendChild(panel);

  const labelSpan = trigger.querySelector('span');

  function labelHtml(opt) {
    if (!opt) return '';
    const plus = opt.value === '__custom__' ? icon('plus') + ' ' : '';
    return plus + escapeHtml(opt.textContent);
  }

  function sync() {
    const opt = select.options[select.selectedIndex];
    labelSpan.innerHTML = labelHtml(opt);
    trigger.classList.toggle('placeholder', !select.value);
    trigger.classList.toggle('disabled', select.disabled);
  }

  function buildPanel() {
    panel.innerHTML = '';
    Array.from(select.options).forEach((opt) => {
      const item = document.createElement('div');
      item.className = 'custom-select-option';
      item.innerHTML = labelHtml(opt);
      if (opt.disabled) {
        item.classList.add('disabled');
      } else {
        if (opt.value === select.value) item.classList.add('selected');
        item.addEventListener('click', () => {
          select.value = opt.value;
          select.dispatchEvent(new Event('change', { bubbles: true }));
          sync();
          close();
        });
      }
      panel.appendChild(item);
    });
  }

  function position() {
    const r = trigger.getBoundingClientRect();
    const spaceBelow = window.innerHeight - r.bottom - 12;
    panel.style.left = r.left + 'px';
    panel.style.width = r.width + 'px';
    panel.style.maxHeight = Math.max(120, Math.min(260, spaceBelow)) + 'px';
    panel.style.top = (r.bottom + 6) + 'px';
  }

  function open() {
    if (select.disabled) return;
    document.querySelectorAll('.custom-select-panel.open').forEach(p => {
      if (p !== panel) p.classList.remove('open');
    });
    buildPanel();
    position();
    panel.classList.add('open');
    wrapper.classList.add('open');
  }

  function close() {
    panel.classList.remove('open');
    wrapper.classList.remove('open');
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.classList.contains('open') ? close() : open();
  });

  window.addEventListener('scroll', () => {
    if (panel.classList.contains('open')) position();
  }, true);
  window.addEventListener('resize', () => {
    if (panel.classList.contains('open')) close();
  });

  // select.innerHTML qayta to'ldirilganda (API dan kategoriya/hamyon kelganda)
  // trigger'dagi matnni avtomatik yangilaydi.
  new MutationObserver(sync).observe(select, { childList: true });

  select._csSync = sync;
  sync();
}

function enhanceAllSelects(root = document) {
  root.querySelectorAll('select.form-control').forEach(enhanceCustomSelect);
}

document.addEventListener('click', () => {
  document.querySelectorAll('.custom-select-panel.open').forEach(p => p.classList.remove('open'));
  document.querySelectorAll('.custom-select-wrapper.open').forEach(w => w.classList.remove('open'));
});

// form.reset() select'ning value'sini DOM mutatsiyasiz o'zgartiradi —
// shu sabab trigger matnini qo'lda qayta sinxronlaymiz.
const _nativeFormReset = HTMLFormElement.prototype.reset;
HTMLFormElement.prototype.reset = function () {
  _nativeFormReset.call(this);
  this.querySelectorAll('select.form-control').forEach(s => s._csSync && s._csSync());
};

enhanceAllSelects();

// ==========================================
// DATA FETCHING
// ==========================================

async function fetchSummary() {
  try {
    const res = await fetch(`${API_BASE}/wallets/summary/`);
    if (res.ok) {
      state.summary = await res.json();
      renderSummary();
    }
  } catch (err) {
    console.error('Error fetching summary:', err);
  }
}

async function fetchWallets() {
  try {
    const res = await fetch(`${API_BASE}/wallets/`);
    if (res.ok) {
      const data = await res.json();
      state.wallets = data.results || data;
      renderWallets();
      populateWalletDropdowns();
    }
  } catch (err) {
    console.error('Error fetching wallets:', err);
  }
}

async function fetchMembers() {
  try {
    const res = await fetch(`${API_BASE}/members/`);
    if (res.ok) {
      const data = await res.json();
      state.members = data.results || data;
      renderMembers();
      populateExpenseMemberDropdown();
    }
  } catch (err) {
    console.error('Error fetching members:', err);
  }
}

async function fetchCategories() {
  try {
    const [incRes, expRes] = await Promise.all([
      fetch(`${API_BASE}/categories/`),
      fetch(`${API_BASE}/expense-categories/`)
    ]);
    if (incRes.ok) {
      const d = await incRes.json();
      state.incomeCategories = d.results || d;
      populateIncomeCategoryDropdown();
    }
    if (expRes.ok) {
      const d = await expRes.json();
      state.expenseCategories = d.results || d;
      populateExpenseCategoryDropdown();
    }
  } catch (err) {
    console.error('Error fetching categories:', err);
  }
}

async function fetchTransactions(isLoadMore = false) {
  try {
    if (!isLoadMore) {
      state.txOffset = 0;
    }
    const limit = state.txLimit;
    const offset = state.txOffset;

    const [expRes, incRes, trRes] = await Promise.all([
      fetch(`${API_BASE}/expenses/?limit=${limit}&offset=${offset}`),
      fetch(`${API_BASE}/incomes/?limit=${limit}&offset=${offset}`),
      fetch(`${API_BASE}/transfers/?limit=${limit}&offset=${offset}`)
    ]);

    let expNext = false, incNext = false, trNext = false;

    if (expRes.ok) {
      const d = await expRes.json();
      const items = d.results || d;
      expNext = !!d.next;
      state.expenses = isLoadMore ? [...state.expenses, ...items] : items;
    }
    if (incRes.ok) {
      const d = await incRes.json();
      const items = d.results || d;
      incNext = !!d.next;
      state.incomes = isLoadMore ? [...state.incomes, ...items] : items;
    }
    if (trRes.ok) {
      const d = await trRes.json();
      const items = d.results || d;
      trNext = !!d.next;
      state.transfers = isLoadMore ? [...state.transfers, ...items] : items;
    }

    state.hasMoreTx = expNext || incNext || trNext;
    state.txOffset += limit;

    const loadMoreBtn = document.getElementById('btnLoadMoreTx');
    if (loadMoreBtn) {
      loadMoreBtn.style.display = state.hasMoreTx ? 'block' : 'none';
    }

    renderTransactions();
  } catch (err) {
    console.error('Error fetching transactions:', err);
  }
}

async function fetchDebts() {
  try {
    const res = await fetch(`${API_BASE}/debts/`);
    if (res.ok) {
      const d = await res.json();
      state.debts = d.results || d;
      renderDebts();
      // Qarzlar tarixi sahifasi ochiq bo'lsa, u ham yangilansin
      if (document.getElementById('statsDebtsSection')?.style.display === '') renderDebtsPage();
    }
  } catch (err) {
    console.error('Error fetching debts:', err);
  }
}

async function refreshAll() {
  await Promise.all([
    fetchSummary(),
    fetchWallets(),
    fetchMembers(),
    fetchCategories(),
    fetchTransactions(),
    fetchDebts()
  ]);
}

// ==========================================
// RENDERING FUNCTIONS
// ==========================================

function formatNumber(amount) {
  if (amount === undefined || amount === null) return '0';
  return new Intl.NumberFormat('uz-UZ').format(amount).replace(/,/g, ' ');
}

function renderSummary() {
  const s = state.summary || {};
  const totalBalanceEl = document.getElementById('statTotalBalance');
  if (totalBalanceEl) totalBalanceEl.textContent = formatNumber(s.total_wallets_balance || 0);

  const incEl = document.getElementById('statMonthlyIncome');
  if (incEl) incEl.textContent = formatNumber(s.monthly_income || 0);

  const expEl = document.getElementById('statMonthlyExpense');
  if (expEl) expEl.textContent = formatNumber(s.monthly_expense || 0);

  renderWeeklyExpenseChart(s.weekly_expenses || []);
}

// ==========================================
// XABARLAR (navbar qo'ng'irog'i)
// ==========================================
// Faqat muhim ogohlantirishlar: muddati o'tgan yoki yaqinlashgan qarzlar.
// Ular qarzlar ro'yxatidan jonli hisoblanadi, qarz to'langach o'zi yo'qoladi.

function _debtDaysLeft(d) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return Math.round((new Date(d.due_date + 'T00:00:00') - today) / 86400000);
}

function getDebtAlerts() {
  return (state.debts || [])
    .filter(d => !d.is_settled && d.due_date)
    .map(d => ({ d, urgency: _debtUrgency(d), days: _debtDaysLeft(d) }))
    .filter(x => x.urgency === 'overdue' || x.urgency === 'soon')
    .sort((a, b) => a.days - b.days);
}

function renderNotifications() {
  const badge = document.getElementById('notifBadge');
  const list = document.getElementById('notifList');
  if (!badge || !list) return;

  const alerts = getDebtAlerts();

  if (alerts.length === 0) {
    badge.style.display = 'none';
  } else {
    badge.textContent = alerts.length > 99 ? '99+' : alerts.length;
    badge.style.display = '';
    badge.style.background = alerts.some(a => a.urgency === 'overdue') ? 'var(--rose)' : 'var(--amber)';
  }

  list.innerHTML = alerts.length ? alerts.map(({ d, urgency, days }) => {
    const when = urgency === 'overdue'
      ? `muddati ${Math.abs(days)} kun oldin o'tgan (${d.due_date})`
      : (days === 0 ? 'muddati bugun tugaydi' : `muddatiga ${days} kun qoldi (${d.due_date})`);
    const kind = d.debt_type === 'give' ? 'Sizga qaytarishi kerak' : 'Siz qaytarishingiz kerak';
    return `
      <button type="button" class="notif-item clickable" data-notif-debt="1">
        <span class="notif-dot ${urgency}"></span>
        <span class="notif-body">
          <div class="notif-text"><b>${escapeHtml(d.person_name)}</b> - qarz ${when}</div>
          <div class="notif-time">${kind} · qoldiq ${formatNumber(d.remaining_summa)} UZS</div>
        </span>
      </button>`;
  }).join('') : `<div class="notif-empty">Hozircha xabarlar yo'q</div>`;
}

function _setNotifPanel(open) {
  const panel = document.getElementById('notifPanel');
  const btn = document.getElementById('btnNotif');
  if (!panel || !btn) return;
  panel.hidden = !open;
  btn.setAttribute('aria-expanded', String(open));
  if (open) renderNotifications();
}

document.getElementById('btnNotif')?.addEventListener('click', (e) => {
  e.stopPropagation();
  _setNotifPanel(document.getElementById('notifPanel').hidden);
});
document.getElementById('notifList')?.addEventListener('click', (e) => {
  if (e.target.closest('[data-notif-debt]')) {
    _setNotifPanel(false);
    openDebtsPage();
  }
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('#notifWrap')) _setNotifPanel(false);
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') _setNotifPanel(false);
});

const WEEKDAY_FULL_NAMES = { Du: 'Dushanba', Se: 'Seshanba', Ch: 'Chorshanba', Pa: 'Payshanba', Ju: 'Juma', Sh: 'Shanba', Ya: 'Yakshanba' };

function renderWeeklyExpenseChart(weeklyData = []) {
  const container = document.getElementById('weeklyExpenseChart');
  if (!container) return;

  const total = weeklyData.reduce((sum, d) => sum + (d.expense || 0), 0);
  if (!weeklyData.length || total === 0) {
    container.innerHTML = `<div class="weekly-rank-empty">Ma'lumotlar mavjud emas</div>`;
    return;
  }

  const maxVal = Math.max(...weeklyData.map(d => d.expense), 1);
  const sorted = [...weeklyData].sort((a, b) => b.expense - a.expense);

  container.innerHTML = sorted.map(d => {
    const pct = d.expense > 0 ? Math.max((d.expense / maxVal) * 100, 4) : 0;
    const valueLabel = d.expense >= 1000000
      ? (d.expense / 1000000).toFixed(1).replace(/\.0$/, '') + ' mln'
      : d.expense >= 1000
      ? Math.round(d.expense / 1000) + ' ming'
      : formatNumber(d.expense);
    const fullName = WEEKDAY_FULL_NAMES[d.label] || d.label;
    const clickable = d.expense > 0;
    return `
      <div class="weekly-rank-row${d.is_max ? ' is-max' : ''}${clickable ? ' is-clickable' : ''}"${clickable ? ` onclick="event.stopPropagation(); openWeekdayTxFilter('${d.label}','${fullName}')"` : ''}>
        <span class="weekly-rank-day">${fullName}</span>
        <div class="weekly-rank-track"><div class="weekly-rank-fill" style="width: ${pct}%;"></div></div>
        <span class="weekly-rank-value">${valueLabel}</span>
      </div>
    `;
  }).join('');
}

function renderWallets() {
  const container = document.getElementById('walletsList');
  if (!container) return;

  if (state.wallets.length === 0) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Hamyon mavjud emas</p>`;
    return;
  }

  container.innerHTML = state.wallets.map(w => `
    <div class="wallet-compact-card">
      <div>
        <div style="font-weight: 500; font-size: 0.95rem; color: var(--text-main);">${icon('card')} ${escapeHtml(w.name)}</div>
        <div style="font-size: 0.75rem; color: var(--text-subtle);">${w.currency}</div>
      </div>
      <div style="display: flex; align-items: center; gap: 10px;">
        <div style="font-weight: 600; font-size: 1.05rem; color: var(--text-main);">
          ${formatNumber(w.summa)} <span style="font-size: 0.8rem; color: var(--text-muted);">${w.currency}</span>
        </div>
        ${state.wallets.length > 1 ? `
          <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.72rem; opacity: 0.6;" title="Hamyonni o'chirish" onclick="deleteWallet(${w.id})">${icon('trash')}</button>
        ` : ''}
      </div>
    </div>
  `).join('');
}

function renderMembers() {
  const container = document.getElementById('membersList');
  if (!container) return;

  if (state.members.length === 0) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">A'zo qo'shilmagan — harajat qilganda "Kimga?" savoli ko'rinmaydi</p>`;
    return;
  }

  container.innerHTML = state.members.map(m => `
    <div class="member-compact-card is-clickable" data-member-id="${m.id}" data-member-name="${escapeHtml(m.name)}" title="${escapeHtml(m.name)}ga sarflangan harajatlarni ko'rish">
      <div style="font-weight: 500; font-size: 0.95rem; color: var(--text-main);">${memberIcon(m.kind)} ${escapeHtml(m.name)}</div>
      <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.72rem; opacity: 0.6;" title="A'zoni o'chirish" onclick="event.stopPropagation(); deleteMember(${m.id})">${icon('trash')}</button>
    </div>
  `).join('');
}

// A'zo turi bo'yicha icon: bitta odam yoki butun oila
function memberIcon(kind) {
  return icon(kind === 'family' ? 'members' : 'person');
}

function populateExpenseMemberDropdown() {
  const el = document.getElementById('expenseMemberSelect');
  if (!el) return;
  const currentVal = el.value;
  const toOption = m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`;
  const people = state.members.filter(m => m.kind !== 'family');
  const families = state.members.filter(m => m.kind === 'family');
  const options = ['<option value="">-- O\'zim uchun --</option>'];
  if (people.length && families.length) {
    options.push(`<optgroup label="Odamlar">${people.map(toOption).join('')}</optgroup>`);
    options.push(`<optgroup label="Oilalar">${families.map(toOption).join('')}</optgroup>`);
  } else {
    options.push(...state.members.map(toOption));
  }
  el.innerHTML = options.join('');
  if (currentVal && Array.from(el.options).some(o => o.value === currentVal)) {
    el.value = currentVal;
  }

  const group = document.getElementById('expenseMemberGroup');
  if (group) group.style.display = state.members.length > 0 ? '' : 'none';
}

// Raw item lookup for detail drawer
const _txDetailMap = {};

// Build sorted list from state
function _buildTxList(filter = 'all') {
  let list = [];

  if (filter === 'all' || filter === 'expenses') {
    state.expenses.forEach(e => {
      const key = `expense_${e.id}`;
      _txDetailMap[key] = e;
      list.push({ type: 'expense', key, id: e.id, title: e.category_name || 'Harajat', amount: e.summa, wallet: e.wallet_name || 'Hamyon', date: e.date, icon: 'expenseArrow' });
    });
  }
  if (filter === 'all' || filter === 'incomes') {
    state.incomes.forEach(i => {
      const key = `income_${i.id}`;
      _txDetailMap[key] = i;
      list.push({ type: 'income', key, id: i.id, title: i.category_name || 'Daromad', amount: i.summa, wallet: i.wallet_name || 'Hamyon', date: i.date, icon: 'incomeArrow' });
    });
  }
  if (filter === 'all' || filter === 'transfers') {
    state.transfers.forEach(t => {
      const key = `transfer_${t.id}`;
      _txDetailMap[key] = t;
      list.push({ type: 'transfer', key, id: t.id, title: `O'tkazma`, amount: t.summa, wallet: `${t.from_wallet_name} → ${t.to_wallet_name}`, date: t.date, icon: 'transfer' });
    });
  }
  list.sort((a, b) => new Date(b.date) - new Date(a.date));
  return list;
}

function _txItemHtml(item) {
  const sign = item.type === 'income' ? '+' : item.type === 'transfer' ? '' : '-';
  return `
    <div class="tx-compact-item" onclick="openTxDetail('${item.key}','${item.type}',${item.id})">
      <div class="tx-icon-badge ${item.type}">${icon(item.icon)}</div>
      <div class="tx-compact-body">
        <div class="tx-compact-name">${escapeHtml(item.title)}</div>
        <div class="tx-compact-sub">${formatDate(item.date)} · ${escapeHtml(item.wallet)}</div>
      </div>
      <div class="tx-compact-amount ${item.type}">${sign}${formatNumber(item.amount)}</div>
    </div>`;
}

// ── Kun / A'zo bo'yicha filtrlangan operatsiyalar oynasi ──────────
function openWeekdayTxFilter(weekdayCode, weekdayFullName) {
  _loadTxFilterModal({
    title: `${weekdayFullName} kuni`,
    url: `${API_BASE}/expenses/?weekday=${weekdayCode}&limit=200`,
    emptyText: `${weekdayFullName} kuni harajat topilmadi`
  });
}

function openMemberTxFilter(memberId, memberName) {
  _loadTxFilterModal({
    title: memberName,
    url: `${API_BASE}/expenses/?member=${memberId}&limit=200`,
    emptyText: `${memberName} uchun harajat topilmadi`
  });
}

async function _loadTxFilterModal({ title, url, emptyText }) {
  const titleEl = document.getElementById('txFilterTitle');
  const summaryEl = document.getElementById('txFilterSummary');
  const listEl = document.getElementById('txFilterList');

  if (titleEl) titleEl.innerHTML = `<span>${icon('receipt')}</span> ${escapeHtml(title)}`;
  if (summaryEl) summaryEl.innerHTML = '';
  if (listEl) listEl.innerHTML = `<div style="text-align:center;padding:20px 0;color:var(--text-subtle);font-size:0.85rem;">Yuklanmoqda...</div>`;
  openModal('modalTxFilter');

  let items = [];
  try {
    const res = await fetch(url);
    if (res.ok) {
      const d = await res.json();
      items = d.results || d;
    }
  } catch (e) {
    console.error('Tx filter fetch error:', e);
  }

  if (items.length === 0) {
    if (listEl) listEl.innerHTML = `<div style="text-align:center;padding:20px 0;color:var(--text-subtle);font-size:0.85rem;">${escapeHtml(emptyText)}</div>`;
    return;
  }

  const total = items.reduce((sum, e) => sum + Number(e.summa || 0), 0);
  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="tx-filter-total-label">Jami sarflangan</div>
      <div class="tx-filter-total-value">${formatNumber(total)} UZS</div>
    `;
  }

  const txItems = items
    .map(e => {
      const key = `expense_${e.id}`;
      _txDetailMap[key] = e;
      return { type: 'expense', key, id: e.id, title: e.category_name || 'Harajat', amount: e.summa, wallet: e.wallet_name || 'Hamyon', date: e.date, icon: 'expenseArrow' };
    })
    .sort((a, b) => new Date(b.date) - new Date(a.date));

  if (listEl) listEl.innerHTML = txItems.map(_txItemHtml).join('');
}

document.addEventListener('click', e => {
  const card = e.target.closest('.member-compact-card');
  if (!card) return;
  openMemberTxFilter(Number(card.dataset.memberId), card.dataset.memberName);
});

// ── Dashboard preview: last 3 items ──────────────────────────
function renderTransactions() {
  const container = document.getElementById('txPreviewList');
  if (!container) return;

  // Populate detail map for all types (needed for drawer)
  _buildTxList('all');

  const list = _buildTxList('all').slice(0, 3);

  if (list.length === 0) {
    container.innerHTML = `<div style="text-align:center;padding:18px 0;color:var(--text-subtle);font-size:0.85rem;">Hozircha operatsiyalar yo'q</div>`;
    return;
  }
  container.innerHTML = list.map(_txItemHtml).join('');
}


// ==========================================
// OYLIK STATISTIKA SAHIFASI
// ==========================================

// Joriy ko'rinayotgan oy/yil
let _statsYear  = new Date().getFullYear();
let _statsMonth = new Date().getMonth() + 1;  // 1-indexed
let _txPageFilter = 'all';
let _statsData = null;  // oxirgi kelgan stats

const UZ_MONTHS = [
  'Yanvar','Fevral','Mart','Aprel','May','Iyun',
  'Iyul','Avgust','Sentabr','Oktabr','Noyabr','Dekabr'
];

// Navbar bo'limlari uchun sarlavhalar
const TX_FILTER_TITLES = {
  all: 'Barcha Operatsiyalar',
  incomes: 'Barcha Kirimlar',
  expenses: 'Barcha Chiqimlar',
  transfers: "Barcha O'tkazmalar",
};

function openTxPage(mode = 'transactions', filter = 'all') {
  _txPageFilter = filter;
  _statsYear  = new Date().getFullYear();
  _statsMonth = new Date().getMonth() + 1;

  // Tab holati tanlangan filtrga moslanadi
  document.querySelectorAll('#txPageTabs .tx-page-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.filter === filter)
  );

  const isStats = mode === 'stats';
  document.getElementById('statsOverviewSection').style.display = isStats ? '' : 'none';
  document.getElementById('statsOperationsSection').style.display = isStats ? 'none' : '';
  document.getElementById('statsDebtsSection').style.display = 'none';
  document.getElementById('txPageTitleText').textContent = isStats ? 'Oylik Statistika' : (TX_FILTER_TITLES[filter] || TX_FILTER_TITLES.all);
  document.getElementById('txPageTitleIcon').innerHTML = icon(isStats ? 'chart' : 'receipt');

  document.getElementById('txPageOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  _loadMonthlyStats();
}

// ── Qarzlar tarixi sahifasi (to'langan + to'lanmagan) ──────────
let _debtPageFilter = 'all';

function openDebtsPage() {
  _debtPageFilter = 'all';
  document.querySelectorAll('#debtPageTabs .tx-page-tab').forEach(btn =>
    btn.classList.toggle('active', btn.dataset.debtFilter === 'all')
  );

  document.getElementById('statsOverviewSection').style.display = 'none';
  document.getElementById('statsOperationsSection').style.display = 'none';
  document.getElementById('statsDebtsSection').style.display = '';
  document.getElementById('txPageTitleText').textContent = 'Qarzlar Tarixi';
  document.getElementById('txPageTitleIcon').innerHTML = icon('ledger');
  document.getElementById('txPageMonth').textContent = 'Barcha davr';

  document.getElementById('txPageOverlay').classList.add('open');
  document.body.style.overflow = 'hidden';
  renderDebtsPage();
}

function renderDebtsPage() {
  renderDebtStatRow();
  renderDebtPageList();
}

function renderDebtStatRow() {
  const row = document.getElementById('debtStatRow');
  if (!row) return;

  const open = state.debts.filter(d => !d.is_settled);
  const toReceive = open.filter(d => d.debt_type === 'give').reduce((s, d) => s + (d.remaining_summa || 0), 0);
  const toPay     = open.filter(d => d.debt_type === 'take').reduce((s, d) => s + (d.remaining_summa || 0), 0);
  const settled   = state.debts.filter(d => d.is_settled).length;

  row.innerHTML = `
    <div class="debt-stat-box">
      <span class="debt-stat-label">Menga qaytarishadi</span>
      <span class="debt-stat-value" style="color:var(--emerald);">${formatNumber(toReceive)} UZS</span>
    </div>
    <div class="debt-stat-box">
      <span class="debt-stat-label">Men qaytaraman</span>
      <span class="debt-stat-value" style="color:var(--amber);">${formatNumber(toPay)} UZS</span>
    </div>
    <div class="debt-stat-box">
      <span class="debt-stat-label">Yopilgan qarzlar</span>
      <span class="debt-stat-value">${settled} ta</span>
    </div>
  `;
}

function renderDebtPageList() {
  const container = document.getElementById('debtPageList');
  if (!container) return;

  let list = state.debts;
  if (_debtPageFilter === 'open') list = list.filter(d => !d.is_settled);
  else if (_debtPageFilter === 'settled') list = list.filter(d => d.is_settled);

  if (list.length === 0) {
    container.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">Bu filtr bo'yicha qarzlar yo'q</div>`;
    return;
  }

  // To'lanmaganlar shoshilinchligi bo'yicha, yopilganlar oxirida
  const sorted = [...list].sort((a, b) => {
    if (a.is_settled !== b.is_settled) return a.is_settled ? 1 : -1;
    return DEBT_URGENCY_RANK[_debtUrgency(a)] - DEBT_URGENCY_RANK[_debtUrgency(b)];
  });

  container.innerHTML = sorted.map(d => {
    const isGive = d.debt_type === 'give';
    const typeLabel = isGive ? 'Berdim' : 'Oldim';
    const typeColor = isGive ? 'var(--emerald)' : 'var(--amber)';
    const paidPercent = d.summa > 0 ? Math.min(100, Math.round((d.paid_summa || 0) / d.summa * 100)) : 0;

    return `
      <div class="debt-history-row ${d.is_settled ? 'settled' : ''}">
        <div class="debt-history-main">
          <div class="debt-history-name">
            ${escapeHtml(d.person_name)}
            <span class="debt-history-type" style="color:${typeColor};">${typeLabel}</span>
            ${d.is_settled ? `<span class="debt-history-type" style="color:var(--emerald);">Yopilgan</span>` : ''}
          </div>
          <div class="debt-history-meta">
            ${formatNumber(d.paid_summa || 0)} / ${formatNumber(d.summa)} UZS ${_debtDueBadge(d)}
          </div>
          <div class="stats-progress-track" style="margin-top:6px;">
            <div class="stats-progress-fill" style="width:${Math.max(2, paidPercent)}%;background:${d.is_settled ? 'var(--emerald)' : 'linear-gradient(90deg,#3b82f6,#60a5fa)'};"></div>
          </div>
        </div>
        <div class="debt-history-actions">
          ${!d.is_settled ? `
            <span class="debt-history-remaining">${formatNumber(d.remaining_summa)} UZS</span>
            <button class="btn btn-subtle btn-xs" onclick="openRepayModal(${d.id})">To'lash</button>
          ` : `<span style="font-size:0.75rem;color:var(--emerald);">${icon('check')}</span>`}
        </div>
      </div>
    `;
  }).join('');
}

// Qarzlar tarixi filtr tablari
document.getElementById('debtPageTabs')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.tx-page-tab');
  if (!btn) return;
  _debtPageFilter = btn.dataset.debtFilter;
  document.querySelectorAll('#debtPageTabs .tx-page-tab').forEach(b => b.classList.toggle('active', b === btn));
  renderDebtPageList();
});

function closeTxPage() {
  document.getElementById('txPageOverlay').classList.remove('open');
  document.body.style.overflow = '';
}

function _updateMonthNavLabel() {
  const el = document.getElementById('monthNavLabel');
  if (el) el.textContent = `${UZ_MONTHS[_statsMonth - 1]} ${_statsYear}`;
  const sub = document.getElementById('txPageMonth');
  if (sub) sub.textContent = `${UZ_MONTHS[_statsMonth - 1]} ${_statsYear}`;
}

async function _loadMonthlyStats() {
  _updateMonthNavLabel();

  try {
    const res = await fetch(`${API_BASE}/stats/monthly/?year=${_statsYear}&month=${_statsMonth}`);
    if (!res.ok) { throw new Error('stats fetch failed'); }
    _statsData = await res.json();
  } catch (e) {
    console.error('Monthly stats error:', e);
    _statsData = null;
  }

  renderMonthlyTrendChart((_statsData && _statsData.daily_trend) || []);
  _renderStatsCategoryList('expense');
  _renderStatsCategoryList('income');
  renderTxPageList();
}

// ── Oylik chiziqli diagramma (Kirim/Chiqim trendi) ────────────

// Catmull-Rom nuqtalar orqali silliq egri chiziq (Bezier) yo'li quradi
function _smoothPath(points) {
  if (points.length < 2) return '';
  if (points.length === 2) return `M${points[0][0]},${points[0][1]} L${points[1][0]},${points[1][1]}`;
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const cp1x = p1[0] + (p2[0] - p0[0]) / 6;
    const cp1y = p1[1] + (p2[1] - p0[1]) / 6;
    const cp2x = p2[0] - (p3[0] - p1[0]) / 6;
    const cp2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C${cp1x},${cp1y} ${cp2x},${cp2y} ${p2[0]},${p2[1]}`;
  }
  return d;
}

function renderMonthlyTrendChart(dailyTrend) {
  const wrapper = document.getElementById('monthlyTrendChart');
  if (!wrapper) return;

  const total = dailyTrend.reduce((sum, d) => sum + (d.income || 0) + (d.expense || 0), 0);
  if (!dailyTrend.length || total === 0) {
    wrapper.innerHTML = `<div class="weekly-rank-empty">Bu oy uchun ma'lumot yo'q</div>`;
    return;
  }

  const width = 600, height = 170;
  const pL = 4, pR = 4, pT = 16, pB = 22;
  const chartW = width - pL - pR;
  const chartH = height - pT - pB;
  const n = dailyTrend.length;

  const incomes = dailyTrend.map(d => d.income || 0);
  const expenses = dailyTrend.map(d => d.expense || 0);
  const maxVal = Math.max(...incomes, ...expenses, 1);

  const xFor = (i) => pL + (n > 1 ? (i / (n - 1)) * chartW : chartW / 2);
  const yFor = (val) => pT + chartH - (val / maxVal) * chartH;
  const baseY = yFor(0);

  const labelStep = Math.ceil(n / 6);
  let xLabelsSvg = '';
  dailyTrend.forEach((d, i) => {
    if (i % labelStep === 0 || i === n - 1) {
      xLabelsSvg += `<text x="${xFor(i)}" y="${height - 6}" class="trend-axis-label" text-anchor="middle">${d.day}</text>`;
    }
  });

  const incPath = _smoothPath(incomes.map((v, i) => [xFor(i), yFor(v)]));
  const expPath = _smoothPath(expenses.map((v, i) => [xFor(i), yFor(v)]));
  const incAreaPath = `${incPath} L${xFor(n - 1)},${baseY} L${xFor(0)},${baseY} Z`;

  wrapper.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" class="trend-chart-svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id="trendIncomeGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" class="trend-grad-stop-start" />
          <stop offset="100%" class="trend-grad-stop-end" />
        </linearGradient>
      </defs>
      <line x1="${pL}" y1="${baseY}" x2="${width - pR}" y2="${baseY}" class="trend-zero-line" />
      ${xLabelsSvg}
      <path d="${incAreaPath}" fill="url(#trendIncomeGrad)" />
      <path d="${expPath}" class="trend-line expense" />
      <path d="${incPath}" class="trend-line income" />
    </svg>
  `;
}

// ── Kategoriya ro'yxati ─────────────────────────────────────────
function _renderStatsCategoryList(type) {
  const isExp   = type === 'expense';
  const listId  = isExp ? 'statsCatExpList' : 'statsCatIncList';
  const totalId = isExp ? 'statsCatExpTotal' : 'statsCatIncTotal';
  const container = document.getElementById(listId);
  const totalEl   = document.getElementById(totalId);
  if (!container) return;

  const cats  = (_statsData && (isExp ? _statsData.category_expenses : _statsData.category_incomes)) || [];
  const total = (_statsData && (isExp ? _statsData.total_expense : _statsData.total_income)) || 0;

  if (totalEl) totalEl.textContent = formatNumber(total) + ' UZS';

  if (cats.length === 0) {
    container.innerHTML = `<div style="color:var(--text-subtle);font-size:0.82rem;padding:8px 0;">Ma'lumot yo'q</div>`;
    return;
  }

  const GRAD = isExp
    ? ['linear-gradient(90deg,#f43f5e,#fb7185)', 'linear-gradient(90deg,#f59e0b,#fbbf24)',
       'linear-gradient(90deg,#8b5cf6,#a78bfa)', 'linear-gradient(90deg,#06b6d4,#22d3ee)', 'linear-gradient(90deg,#ec4899,#f472b6)']
    : ['linear-gradient(90deg,#10b981,#34d399)', 'linear-gradient(90deg,#3b82f6,#60a5fa)',
       'linear-gradient(90deg,#06b6d4,#22d3ee)', 'linear-gradient(90deg,#8b5cf6,#a78bfa)', 'linear-gradient(90deg,#f59e0b,#fbbf24)'];

  container.innerHTML = cats.map((c, i) => `
    <div class="stats-cat-row">
      <div class="stats-cat-header">
        <span class="stats-cat-name">${escapeHtml(c.name)}</span>
        <span class="stats-cat-meta">${formatNumber(c.total)} UZS <span class="stats-cat-percent">(${c.percent}%)</span></span>
      </div>
      <div class="stats-progress-track">
        <div class="stats-progress-fill" style="width:${Math.max(2, c.percent)}%;background:${GRAD[i % GRAD.length]};"></div>
      </div>
    </div>
  `).join('');
}

// ── 6. Operatsiyalar ro'yxati ──────────────────────────────────────
function renderTxPageList() {
  const container = document.getElementById('txPageList');
  if (!container) return;

  const list = _buildTxList(_txPageFilter);

  if (list.length === 0) {
    container.innerHTML = `<div style="text-align:center;padding:30px 0;color:var(--text-subtle);font-size:0.88rem;">Bu filtr bo'yicha operatsiyalar yo'q</div>`;
    return;
  }

  // Group by date
  const groups = {};
  list.forEach(item => {
    const d = new Date(item.date);
    const today     = new Date();
    const yesterday = new Date(today); yesterday.setDate(today.getDate() - 1);
    let label;
    if (d.toDateString() === today.toDateString())     label = 'Bugun';
    else if (d.toDateString() === yesterday.toDateString()) label = 'Kecha';
    else label = d.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long' });
    if (!groups[label]) groups[label] = [];
    groups[label].push(item);
  });

  let html = '';
  for (const [label, items] of Object.entries(groups)) {
    html += `<div class="tx-date-group">${label}</div>`;
    html += items.map(_txItemHtml).join('');
  }
  container.innerHTML = html;
}

// Oy navigatsiyasi
document.getElementById('btnPrevMonth')?.addEventListener('click', () => {
  _statsMonth--;
  if (_statsMonth < 1) { _statsMonth = 12; _statsYear--; }
  _loadMonthlyStats();
});

document.getElementById('btnNextMonth')?.addEventListener('click', () => {
  const now = new Date();
  if (_statsYear === now.getFullYear() && _statsMonth >= now.getMonth() + 1) return; // Kelajakka o'tma
  _statsMonth++;
  if (_statsMonth > 12) { _statsMonth = 1; _statsYear++; }
  _loadMonthlyStats();
});

// Tab switching inside tx page
document.addEventListener('click', e => {
  const tab = e.target.closest('.tx-page-tab');
  if (!tab) return;
  _txPageFilter = tab.dataset.filter;
  document.querySelectorAll('.tx-page-tab').forEach(b => b.classList.remove('active'));
  tab.classList.add('active');
  renderTxPageList();
});





function openTxDetail(key, type, id) {
  const raw = _txDetailMap[key];
  if (!raw) return;

  const typeLabels = { expense: 'Harajat', income: 'Daromad', transfer: "O'tkazma" };
  const icons      = { expense: 'expense', income: 'income', transfer: 'transfer' };
  const sign       = type === 'income' ? '+' : type === 'transfer' ? '' : '-';

  // Header
  const badge = document.getElementById('detailTypeBadge');
  badge.textContent = typeLabels[type] || type;
  badge.className = `detail-type-badge ${type}`;

  const titleEl = document.getElementById('detailTitle');
  if (type === 'expense')  titleEl.textContent = raw.category_name || 'Harajat';
  if (type === 'income')   titleEl.textContent = raw.category_name || 'Daromad';
  if (type === 'transfer') titleEl.textContent = `${raw.from_wallet_name} → ${raw.to_wallet_name}`;

  // Amount
  const amtEl = document.getElementById('detailAmountBig');
  amtEl.textContent = sign + formatNumber(raw.summa);
  amtEl.className = `detail-amount-big ${type}`;

  // Rows
  const rows = [];

  const addRow = (icon, label, val) => {
    if (val === undefined || val === null || val === '' || val === false) return;
    rows.push(`
      <div class="detail-row">
        <span class="detail-row-icon">${icon}</span>
        <span class="detail-row-label">${label}</span>
        <span class="detail-row-val">${escapeHtml(String(val))}</span>
      </div>
    `);
  };

  const fullDate = raw.date ? new Date(raw.date).toLocaleString('uz-UZ', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit'
  }) : '';

  if (type === 'expense') {
    addRow(icon('tag'), 'Kategoriya', raw.category_name);
    addRow(icon('wallet'), 'Hamyon', raw.wallet_name);
    addRow(memberIcon(raw.member_kind), 'Kimga', raw.member_name);
    addRow(icon('note'), 'Izoh', raw.description);
    addRow(icon('calendar'), 'Sana', fullDate);
  } else if (type === 'income') {
    addRow(icon('folder'), 'Manba', raw.category_name);
    addRow(icon('wallet'), 'Hamyon', raw.wallet_name);
    addRow(icon('note'), 'Izoh', raw.description);
    addRow(icon('calendar'), 'Sana', fullDate);
  } else if (type === 'transfer') {
    addRow(icon('up'), 'Chiqdi', raw.from_wallet_name);
    addRow(icon('down'), 'Tushdi', raw.to_wallet_name);
    addRow(icon('note'), 'Izoh', raw.description);
    addRow(icon('calendar'), 'Sana', fullDate);
  }

  if (raw.created_at) {
    const created = new Date(raw.created_at).toLocaleString('uz-UZ', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
    addRow(icon('clock'), 'Qo\'shildi', created);
  }

  document.getElementById('detailRows').innerHTML = rows.join('') ||
    '<p style="color:var(--text-subtle); font-size:0.83rem;">Qo\'shimcha ma\'lumot yo\'q</p>';

  // Delete button
  const delBtn = document.getElementById('detailDeleteBtn');
  delBtn.onclick = () => {
    closeTxDetail();
    deleteTransaction(type, id);
  };

  // Show backdrop
  document.getElementById('txDetailBackdrop').classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeTxDetail(event) {
  if (event && event.target !== document.getElementById('txDetailBackdrop')) return;
  document.getElementById('txDetailBackdrop').classList.remove('active');
  document.body.style.overflow = '';
}


// Backenddagi DEBT_DUE_SOON_DAYS bilan mos bo'lishi kerak (views.py)
const DEBT_DUE_SOON_DAYS = 3;
const DEBT_URGENCY_RANK = { overdue: 0, soon: 1, normal: 2, none: 3 };

function _debtUrgency(d) {
  if (d.is_settled || !d.due_date) return 'none';
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const due = new Date(d.due_date + 'T00:00:00');
  const diffDays = Math.round((due - today) / 86400000);
  if (diffDays < 0) return 'overdue';
  if (diffDays <= DEBT_DUE_SOON_DAYS) return 'soon';
  return 'normal';
}

function _debtDueBadge(d) {
  if (!d.due_date) return '';
  const urgency = _debtUrgency(d);
  const label = urgency === 'overdue' ? `Muddati o'tgan: ${d.due_date}` : `Muddat: ${d.due_date}`;
  return `· <span class="debt-due-badge debt-due-${urgency}">${label}</span>`;
}

function renderDebts() {
  renderNotifications();
  const container = document.getElementById('debtsList');
  if (!container) return;

  if (state.debts.length === 0) {
    container.innerHTML = `<p style="color: var(--text-subtle); font-size: 0.85rem; padding: 6px 0;">Qarzlar mavjud emas</p>`;
    return;
  }

  const sorted = [...state.debts].sort((a, b) => DEBT_URGENCY_RANK[_debtUrgency(a)] - DEBT_URGENCY_RANK[_debtUrgency(b)]);

  container.innerHTML = sorted.map(d => {
    const isGive = d.debt_type === 'give';
    const typeLabel = isGive ? 'Berdim' : 'Oldim';
    const typeColor = isGive ? 'var(--emerald)' : 'var(--amber)';

    return `
      <div class="debt-compact-card">
        <div>
          <div style="font-weight: 500; font-size: 0.92rem; color: var(--text-main);">
            ${escapeHtml(d.person_name)}
            <span style="font-size: 0.72rem; padding: 2px 6px; border-radius: 6px; background: var(--bg-sunken); color: ${typeColor}; margin-left: 6px;">${typeLabel}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--text-subtle); margin-top: 2px;">
            Qoldiq: <b style="color:var(--text-main);">${formatNumber(d.remaining_summa)} UZS</b> ${_debtDueBadge(d)}
          </div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          ${!d.is_settled ? `
            <button class="btn btn-subtle btn-xs" onclick="openRepayModal(${d.id})">To'lash</button>
          ` : `<span style="font-size: 0.75rem; color: var(--emerald);">Yopildi ${icon('check')}</span>`}
          <button class="btn-icon" style="width: 24px; height: 24px; font-size: 0.75rem;" title="O'chirish" onclick="deleteDebt(${d.id})">${icon('trash')}</button>
        </div>
      </div>
    `;
  }).join('');
}

// ==========================================
// DROPDOWN POPULATORS
// ==========================================

function populateWalletDropdowns() {
  const dropdownIds = [
    'expenseWalletSelect',
    'incomeWalletSelect',
    'transferFromWallet',
    'transferToWallet',
    'debtWalletSelect',
    'repayWalletSelect'
  ];

  dropdownIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;

    const currentVal = el.value;
    let optionsHtml = '';

    if (id === 'debtWalletSelect') {
      optionsHtml += '<option value="">-- Hamyonsiz (Qo\'lma-qo\'l / Naqd) --</option>';
    }

    optionsHtml += state.wallets.map(w => `
      <option value="${w.id}">${escapeHtml(w.name)} (${formatMoney(w.summa, w.currency)})</option>
    `).join('');

    el.innerHTML = optionsHtml;

    if (currentVal && Array.from(el.options).some(o => o.value === currentVal)) {
      el.value = currentVal;
    } else if (id === 'transferToWallet' && state.wallets.length > 1) {
      el.value = state.wallets[1].id;
    }
  });

  updateSingleWalletFieldVisibility();
  updateTransferButtonVisibility();
}

// Hamyon bitta bo'lsa, "Qaysi hamyondan/ga?" savolini yashiramiz — tanlov qilib
// o'tirishning hojati yo'q, yagona hamyon avtomatik tanlanadi.
function updateSingleWalletFieldVisibility() {
  const singleWallet = state.wallets.length === 1;
  [
    { groupId: 'expenseWalletGroup', selectId: 'expenseWalletSelect' },
    { groupId: 'incomeWalletGroup', selectId: 'incomeWalletSelect' },
  ].forEach(({ groupId, selectId }) => {
    const group = document.getElementById(groupId);
    const select = document.getElementById(selectId);
    if (!group || !select) return;
    group.style.display = singleWallet ? 'none' : '';
    select.required = !singleWallet;
    if (singleWallet && state.wallets[0]) {
      select.value = String(state.wallets[0].id);
    }
  });
}

// Kamida 2 ta hamyon bo'lmasa, "O'tkazma" tezkor tugmasi ma'nosiz bo'ladi
// (qaysidan va qaysiga ko'chirish kerakligini tanlashning iloji yo'q).
function updateTransferButtonVisibility() {
  const btn = document.getElementById('btnOpenTransferModal');
  const grid = document.querySelector('.action-grid-row');
  if (!btn || !grid) return;
  const hasEnoughWallets = state.wallets.length >= 2;
  btn.style.display = hasEnoughWallets ? '' : 'none';
  grid.classList.toggle('cols-3', !hasEnoughWallets);
}

function populateExpenseCategoryDropdown() {
  const el = document.getElementById('expenseCategorySelect');
  if (!el) return;
  const options = [
    '<option value="" disabled selected>-- Harajat toifasini tanlang --</option>',
    ...state.expenseCategories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`),
    '<option value="__custom__">Boshqa (o\'zingiz yozing...)</option>'
  ];
  el.innerHTML = options.join('');
}

function populateIncomeCategoryDropdown() {
  const el = document.getElementById('incomeCategorySelect');
  if (!el) return;
  const options = [
    '<option value="" disabled selected>-- Daromad manbayini tanlang --</option>',
    ...state.incomeCategories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`),
    '<option value="__custom__">Boshqa (o\'zingiz yozing...)</option>'
  ];
  el.innerHTML = options.join('');
}

// Custom category change listeners
document.getElementById('incomeCategorySelect')?.addEventListener('change', (e) => {
  const group = document.getElementById('incomeCustomCategoryGroup');
  const input = document.getElementById('incomeCustomCategory');
  if (e.target.value === '__custom__') {
    group.style.display = 'block';
    input.required = true;
    input.focus();
  } else {
    group.style.display = 'none';
    input.required = false;
    input.value = '';
  }
});

document.getElementById('expenseCategorySelect')?.addEventListener('change', (e) => {
  const group = document.getElementById('expenseCustomCategoryGroup');
  const input = document.getElementById('expenseCustomCategory');
  if (e.target.value === '__custom__') {
    group.style.display = 'block';
    input.required = true;
    input.focus();
  } else {
    group.style.display = 'none';
    input.required = false;
    input.value = '';
  }
});

// ==========================================
// FORM SUBMISSIONS & ERROR HANDLING
// ==========================================

// Error extraction helper
function extractErrorMessage(err, fallback = 'Xatolik yuz berdi') {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  if (err.error) return Array.isArray(err.error) ? err.error[0] : err.error;
  if (err.detail) return Array.isArray(err.detail) ? err.detail[0] : err.detail;
  if (err.summa) return Array.isArray(err.summa) ? err.summa[0] : err.summa;
  if (err.wallet) return Array.isArray(err.wallet) ? err.wallet[0] : err.wallet;
  if (err.to_wallet) return Array.isArray(err.to_wallet) ? err.to_wallet[0] : err.to_wallet;
  if (err.from_wallet) return Array.isArray(err.from_wallet) ? err.from_wallet[0] : err.from_wallet;
  if (err.name) return Array.isArray(err.name) ? err.name[0] : err.name;
  const firstKey = Object.keys(err)[0];
  if (firstKey) {
    const val = err[firstKey];
    return Array.isArray(val) ? val[0] : String(val);
  }
  return fallback;
}

// 1. Add Expense
document.getElementById('formAddExpense')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  let categoryId = document.getElementById('expenseCategorySelect').value;

  if (!categoryId) {
    showToast('Iltimos, harajat toifasini tanlang', 'error');
    return;
  }

  // Agar yangi kategoriya yozilgan bo'lsa
  if (categoryId === '__custom__') {
    const customName = document.getElementById('expenseCustomCategory').value.trim();
    if (!customName) {
      showToast('Iltimos, harajat toifasi nomini yozing', 'error');
      return;
    }

    try {
      const catRes = await fetch(`${API_BASE}/expense-categories/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: customName })
      });
      if (catRes.ok) {
        const catData = await catRes.json();
        categoryId = catData.id;
        await fetchCategories();
      } else {
        const errData = await catRes.json().catch(() => ({}));
        showToast(extractErrorMessage(errData, 'Kategoriya yaratishda xatolik'), 'error');
        return;
      }
    } catch (err) {
      showToast('Tarmoq xatosi', 'error');
      return;
    }
  }

  const payload = {
    summa: parseInt(document.getElementById('expenseSumma').value),
    wallet: parseInt(document.getElementById('expenseWalletSelect').value),
    category: parseInt(categoryId),
    description: document.getElementById('expenseDescription').value.trim(),
  };

  const memberVal = document.getElementById('expenseMemberSelect')?.value;
  if (memberVal) {
    payload.member = parseInt(memberVal);
  }

  const expDateVal = document.getElementById('expenseDate')?.value;
  if (expDateVal) {
    payload.date = new Date(expDateVal).toISOString();
  }

  try {
    const res = await fetch(`${API_BASE}/expenses/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Harajat muvaffaqiyatli saqlandi!');
      closeModal('modalExpense');
      e.target.reset();
      document.getElementById('expenseCustomCategoryGroup').style.display = 'none';
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Harajat saqlashda xatolik'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// 2. Add Income
document.getElementById('formAddIncome')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  let categoryId = document.getElementById('incomeCategorySelect').value;

  if (!categoryId) {
    showToast('Iltimos, daromad manbayini tanlang', 'error');
    return;
  }

  // Agar yangi manba yozilgan bo'lsa
  if (categoryId === '__custom__') {
    const customName = document.getElementById('incomeCustomCategory').value.trim();
    if (!customName) {
      showToast('Iltimos, daromad manbayi nomini yozing', 'error');
      return;
    }

    try {
      const catRes = await fetch(`${API_BASE}/categories/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: customName })
      });
      if (catRes.ok) {
        const catData = await catRes.json();
        categoryId = catData.id;
        await fetchCategories();
      } else {
        const errData = await catRes.json();
        showToast(errData.name || 'Manba yaratishda xatolik', 'error');
        return;
      }
    } catch (err) {
      showToast('Tarmoq xatosi', 'error');
      return;
    }
  }

  const payload = {
    summa: parseInt(document.getElementById('incomeSumma').value),
    wallet: parseInt(document.getElementById('incomeWalletSelect').value),
    category: parseInt(categoryId),
    description: document.getElementById('incomeDescription').value.trim(),
  };

  const incDateVal = document.getElementById('incomeDate')?.value;
  if (incDateVal) {
    payload.date = new Date(incDateVal).toISOString();
  }

  try {
    const res = await fetch(`${API_BASE}/incomes/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Daromad muvaffaqiyatli saqlandi!');
      closeModal('modalIncome');
      e.target.reset();
      document.getElementById('incomeCustomCategoryGroup').style.display = 'none';
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Daromad saqlashda xatolik'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// 3. Add Transfer
document.getElementById('formAddTransfer')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const fromW = parseInt(document.getElementById('transferFromWallet').value);
  const toW = parseInt(document.getElementById('transferToWallet').value);
  const summa = parseInt(document.getElementById('transferSumma').value);

  if (fromW === toW) {
    showToast('Bir xil hamyonlar o\'rtasida o\'tkazma qilib bo\'lmaydi', 'error');
    return;
  }

  const payload = {
    from_wallet: fromW,
    to_wallet: toW,
    summa: summa,
    description: document.getElementById('transferDescription').value.trim(),
    user: state.currentUserId
  };

  try {
    const res = await fetch(`${API_BASE}/transfers/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('O\'tkazma muvaffaqiyatli amalga oshirildi!');
      closeModal('modalTransfer');
      e.target.reset();
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'O\'tkazmada xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// 4. Add Debt
document.getElementById('formAddDebt')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const walletVal = document.getElementById('debtWalletSelect').value;
  const payload = {
    person_name: document.getElementById('debtPersonName').value.trim(),
    debt_type: document.getElementById('debtTypeSelect').value,
    summa: parseInt(document.getElementById('debtSumma').value),
    due_date: document.getElementById('debtDueDate').value || null,
    wallet: walletVal ? parseInt(walletVal) : null,
    description: document.getElementById('debtDescription').value.trim(),
    user: state.currentUserId
  };

  try {
    const res = await fetch(`${API_BASE}/debts/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Qarz daftarga yozildi!');
      closeModal('modalDebt');
      e.target.reset();
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Qarz kiritishda xatolik'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// 5. Add Wallet
document.getElementById('formAddWallet')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById('walletName').value.trim(),
    summa: parseInt(document.getElementById('walletInitialSumma').value) || 0,
    currency: document.getElementById('walletCurrency').value.trim() || 'UZS',
    user: state.currentUserId
  };

  try {
    const res = await fetch(`${API_BASE}/wallets/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Yangi hamyon qo\'shildi!');
      closeModal('modalWallet');
      e.target.reset();
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Hamyon yaratishda xatolik'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// 6. Add Member
document.getElementById('formAddMember')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    name: document.getElementById('memberName').value.trim(),
    kind: document.getElementById('memberKind')?.value || 'person',
  };

  try {
    const res = await fetch(`${API_BASE}/members/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Yangi a\'zo qo\'shildi!');
      closeModal('modalMember');
      e.target.reset();
      await fetchMembers();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'A\'zo qo\'shishda xatolik'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// 7. Repay Debt
let activeRepayDebtId = null;
function openRepayModal(debtId) {
  const debt = state.debts.find(d => d.id === debtId);
  if (!debt) return;
  activeRepayDebtId = debtId;
  document.getElementById('repayPersonName').textContent = debt.person_name;
  document.getElementById('repayRemaining').textContent = formatMoney(debt.remaining_summa);
  document.getElementById('repayAmount').max = debt.remaining_summa;
  document.getElementById('repayAmount').value = debt.remaining_summa;
  openModal('modalRepayDebt');
}

document.getElementById('formRepayDebt')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!activeRepayDebtId) return;

  const payload = {
    amount: parseInt(document.getElementById('repayAmount').value),
    wallet: parseInt(document.getElementById('repayWalletSelect').value)
  };

  try {
    const res = await fetch(`${API_BASE}/debts/${activeRepayDebtId}/repay/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      showToast('Qarz to\'landi va hamyon yangilandi!');
      closeModal('modalRepayDebt');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Qarzni to\'lashda xatolik'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// ==========================================
// DELETE HANDLERS
// ==========================================

async function deleteTransaction(type, id) {
  if (!(await confirmDelete('Ushbu amaliyotni bekor qilib o\'chirishni xohlaysizmi? Hamyon balansi qaytariladi.'))) {
    return;
  }

  let endpoint = 'expenses';
  if (type === 'income') endpoint = 'incomes';
  if (type === 'transfer') endpoint = 'transfers';

  try {
    const res = await fetch(`${API_BASE}/${endpoint}/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('Amaliyot o\'chirildi va balans qaytarildi');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'O\'chirishda xatolik yuz berdi (hamyonda balans yetarli bo\'lmasligi mumkin)'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
}

async function deleteDebt(id) {
  if (!(await confirmDelete('Qarz yozuvini o\'chirishni xohlaysizmi?'))) return;

  try {
    const res = await fetch(`${API_BASE}/debts/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('Qarz o\'chirildi');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Qarzni o\'chirishda xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
}

async function deleteWallet(id) {
  if (!(await confirmDelete('Hamyonni o\'chirishni xohlaysizmi? Oldingi barcha amaliyotlar arxivlanadi.'))) return;

  try {
    const res = await fetch(`${API_BASE}/wallets/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('Hamyon muvaffaqiyatli o\'chirildi');
      refreshAll();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'Hamyonni o\'chirishda xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
}

async function deleteMember(id) {
  if (!(await confirmDelete('A\'zoni o\'chirishni xohlaysizmi?'))) return;

  try {
    const res = await fetch(`${API_BASE}/members/${id}/`, {
      method: 'DELETE'
    });

    if (res.ok || res.status === 204) {
      showToast('A\'zo o\'chirildi');
      await fetchMembers();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(extractErrorMessage(err, 'A\'zoni o\'chirishda xatolik yuz berdi'), 'error');
    }
  } catch (error) {
    showToast('Tarmoq xatosi', 'error');
  }
}

// Tab switcher for transactions
document.querySelectorAll('#txTabs .pill-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    document.querySelectorAll('#txTabs .pill-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.activeTab = btn.dataset.tab;
    renderTransactions();
  });
});

// Helper
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Load more transactions
document.getElementById('btnLoadMoreTx')?.addEventListener('click', () => {
  fetchTransactions(true);
});

// ==========================================
// AUTHENTICATION ENGINE
// ==========================================

async function checkAuth() {
  const authSection = document.getElementById('authSection');
  const mainApp = document.getElementById('mainApp');
  const userProfileNav = document.getElementById('userProfileNav');

  try {
    const res = await fetch(`${API_BASE}/auth/me/`);
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated) {
        state.currentUser = data.user;
        state.currentUserId = data.user.id;
        try { localStorage.removeItem(`moliyaNotifs:${data.user.id}`); } catch (e) { /* e'tiborsiz */ }

        // Show main app, hide auth screen
        if (authSection) authSection.style.display = 'none';
        if (mainApp) mainApp.style.display = 'block';
        if (userProfileNav) userProfileNav.style.display = 'flex';
        const navSections = document.getElementById('navSections');
        if (navSections) navSections.style.display = 'flex';
        queueBrandSync();
        const notifWrap = document.getElementById('notifWrap');
        if (notifWrap) notifWrap.style.display = 'block';
        renderUserNav();

        refreshAll();
        return true;
      }
    }
  } catch (err) {
    console.error('Auth check error:', err);
  }

  // Not authenticated: Show login screen, hide main app
  state.currentUser = null;
  state.currentUserId = null;
  _setNotifPanel(false);

  if (authSection) authSection.style.display = 'flex';
  if (mainApp) mainApp.style.display = 'none';
  if (userProfileNav) userProfileNav.style.display = 'none';
  const navSectionsEl = document.getElementById('navSections');
  if (navSectionsEl) navSectionsEl.style.display = 'none';
  queueBrandSync();
  const notifWrapEl = document.getElementById('notifWrap');
  if (notifWrapEl) notifWrapEl.style.display = 'none';

  state.summary = {};
  state.wallets = [];
  state.expenses = [];
  state.incomes = [];
  state.transfers = [];
  state.debts = [];
  renderSummary();
  renderWallets();
  renderTransactions();
  renderDebts();

  return false;
}

// Auth Tabs Switcher
document.getElementById('authTabLogin')?.addEventListener('click', () => {
  document.getElementById('authTabLogin').classList.add('active');
  document.getElementById('authTabRegister').classList.remove('active');
  document.getElementById('formLoginMain').style.display = 'flex';
  document.getElementById('formRegisterMain').style.display = 'none';
  const title = document.getElementById('authScreenTitle');
  if (title) title.textContent = 'Moliya Tizimiga Kirish';
});

document.getElementById('authTabRegister')?.addEventListener('click', () => {
  document.getElementById('authTabRegister').classList.add('active');
  document.getElementById('authTabLogin').classList.remove('active');
  document.getElementById('formLoginMain').style.display = 'none';
  document.getElementById('formRegisterMain').style.display = 'flex';
  const title = document.getElementById('authScreenTitle');
  if (title) title.textContent = 'Yangi Hisob Ochish';
});

// ==========================================
// PAROLNI UNUTDIM — emailga kod yuborish va yangi parol o'rnatish
// ==========================================

let forgotStep = 1;

function setForgotStep(step) {
  forgotStep = step;
  const isCodeStep = step === 2;
  document.getElementById('forgotStep2').hidden = !isCodeStep;
  document.getElementById('btnForgotResend').hidden = !isCodeStep;
  document.getElementById('forgotUsername').readOnly = isCodeStep;
  document.getElementById('btnForgotSubmit').textContent = isCodeStep ? 'Parolni yangilash' : 'Kod yuborish';
  document.getElementById('forgotIntro').textContent = isCodeStep
    ? "Emailingizga 6 xonali kod yuborildi (spam papkasini ham tekshiring). Kod 15 daqiqa amal qiladi."
    : "Foydalanuvchi nomingiz yoki emailingizni kiriting — akkauntga ulangan emailga 6 xonali tiklash kodi yuboramiz.";
}

function showForgotPassword(show) {
  const loginForm = document.getElementById('formLoginMain');
  const forgotForm = document.getElementById('formForgotPassword');
  const tabs = document.querySelector('.auth-tabs');
  const title = document.getElementById('authScreenTitle');

  loginForm.style.display = show ? 'none' : 'flex';
  forgotForm.style.display = show ? 'flex' : 'none';
  if (tabs) tabs.style.display = show ? 'none' : '';
  if (title) title.textContent = show ? 'Parolni Tiklash' : 'Moliya Tizimiga Kirish';

  if (show) {
    forgotForm.reset();
    document.getElementById('forgotUsername').value = document.getElementById('loginUsername').value.trim();
    setForgotStep(1);
    document.getElementById('forgotUsername').focus();
  }
}

async function requestResetCode() {
  const username = document.getElementById('forgotUsername').value.trim();
  if (!username) {
    showToast('Foydalanuvchi nomi yoki emailni kiriting', 'error');
    return false;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/password-reset/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(data.message || 'Kod yuborildi');
      return true;
    }
    showToast(extractErrorMessage(data, 'Kod yuborishda xatolik'), 'error');
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
  return false;
}

document.getElementById('btnForgotPassword')?.addEventListener('click', () => showForgotPassword(true));
document.getElementById('btnForgotBack')?.addEventListener('click', () => showForgotPassword(false));

document.getElementById('btnForgotResend')?.addEventListener('click', async () => {
  if (await requestResetCode()) document.getElementById('forgotCode').value = '';
});

document.getElementById('forgotCode')?.addEventListener('input', (e) => {
  e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
});

document.getElementById('formForgotPassword')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const submitBtn = document.getElementById('btnForgotSubmit');
  submitBtn.disabled = true;

  try {
    if (forgotStep === 1) {
      if (await requestResetCode()) {
        setForgotStep(2);
        document.getElementById('forgotCode').focus();
      }
      return;
    }

    const username = document.getElementById('forgotUsername').value.trim();
    // Kod ko'chirib qo'yilganda probel/defis qo'shilib qolishi mumkin — faqat raqamlarni olamiz
    const code = document.getElementById('forgotCode').value.replace(/\D/g, '');
    const newPassword = document.getElementById('forgotNewPassword').value;
    const newPassword2 = document.getElementById('forgotNewPassword2').value;

    if (code.length !== 6) {
      showToast(`Kod 6 xonali bo'lishi kerak — siz ${code.length} ta raqam kiritdingiz`, 'error');
      return;
    }
    if (newPassword.length < 8) {
      showToast("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak", 'error');
      return;
    }
    if (newPassword !== newPassword2) {
      showToast('Yangi parollar bir-biriga mos kelmadi', 'error');
      return;
    }

    const res = await fetch(`${API_BASE}/auth/password-reset/confirm/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, code, new_password: newPassword })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast(data.message || 'Parol yangilandi');
      showForgotPassword(false);
      document.getElementById('loginUsername').value = username;
      document.getElementById('loginPassword').value = '';
      document.getElementById('loginPassword').focus();
    } else {
      showToast(extractErrorMessage(data, 'Parolni tiklashda xatolik'), 'error');
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  } finally {
    submitBtn.disabled = false;
  }
});

// Login Form Submit (Main Auth Screen)
document.getElementById('formLoginMain')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const usernameInput = document.getElementById('loginUsername');
  const passwordInput = document.getElementById('loginPassword');

  const payload = {
    username: usernameInput.value.trim(),
    password: passwordInput.value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      showToast(`Xush kelibsiz, ${data.user.name || data.user.username}!`);
      e.target.reset();
      await checkAuth();
    } else {
      showToast(data.error || 'Login yoki parol noto\'g\'ri', 'error');
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// Register Form Submit (Main Auth Screen)
document.getElementById('formRegisterMain')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    username: document.getElementById('regUsername').value.trim(),
    password: document.getElementById('regPassword').value.trim(),
    first_name: document.getElementById('regFirstName').value.trim(),
    phone: document.getElementById('regPhone').value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      showToast(`Ro'yxatdan muvaffaqiyatli o'tdingiz, ${data.user.name || data.user.username}!`);
      e.target.reset();
      await checkAuth();
    } else {
      showToast(data.error || 'Ro\'yxatdan o\'tishda xatolik yuz berdi', 'error');
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// ==========================================
// SOZLAMALAR — profil va parolni o'zgartirish
// ==========================================

function renderUserNav() {
  const user = state.currentUser;
  if (!user) return;
  const display = user.name || user.username;
  const userName = document.getElementById('userName');
  const userAvatar = document.getElementById('userAvatar');
  if (userName) userName.textContent = display;
  if (userAvatar) userAvatar.textContent = display[0].toUpperCase();
}

function switchSettingsTab(tab) {
  document.querySelectorAll('.settings-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.settingsTab === tab);
  });
  document.querySelectorAll('[data-settings-panel]').forEach(panel => {
    panel.hidden = panel.dataset.settingsPanel !== tab;
  });
}

function openSettings() {
  const user = state.currentUser;
  if (!user) return;
  document.getElementById('settingsFirstName').value = user.first_name || '';
  document.getElementById('settingsLastName').value = user.last_name || '';
  document.getElementById('settingsUsername').value = user.username || '';
  document.getElementById('settingsEmail').value = user.email || '';
  document.getElementById('settingsPhone').value = user.phone || '';
  document.getElementById('formSettingsPassword').reset();
  switchSettingsTab('profile');
  openModal('modalSettings');
}

document.getElementById('btnOpenSettings')?.addEventListener('click', openSettings);

document.querySelectorAll('.settings-tab').forEach(btn => {
  btn.addEventListener('click', () => switchSettingsTab(btn.dataset.settingsTab));
});

document.getElementById('formSettingsProfile')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const payload = {
    first_name: document.getElementById('settingsFirstName').value.trim(),
    last_name: document.getElementById('settingsLastName').value.trim(),
    username: document.getElementById('settingsUsername').value.trim(),
    email: document.getElementById('settingsEmail').value.trim(),
    phone: document.getElementById('settingsPhone').value.trim(),
  };

  try {
    const res = await fetch(`${API_BASE}/auth/profile/`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      state.currentUser = data.user;
      renderUserNav();
      showToast("Profil ma'lumotlari saqlandi");
      closeModal('modalSettings');
    } else {
      showToast(extractErrorMessage(data, 'Profilni saqlashda xatolik'), 'error');
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
});

document.getElementById('formSettingsPassword')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const oldPassword = document.getElementById('settingsOldPassword').value;
  const newPassword = document.getElementById('settingsNewPassword').value;
  const newPassword2 = document.getElementById('settingsNewPassword2').value;

  if (newPassword !== newPassword2) {
    showToast('Yangi parollar bir-biriga mos kelmadi', 'error');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/auth/change-password/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      showToast("Parol o'zgartirildi");
      e.target.reset();
      closeModal('modalSettings');
    } else {
      showToast(extractErrorMessage(data, "Parolni o'zgartirishda xatolik"), 'error');
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// Logout Button
document.getElementById('btnLogout')?.addEventListener('click', async () => {
  const sure = await showConfirm({
    title: 'Tizimdan chiqish',
    message: 'Tizimdan chiqishni xohlaysizmi?',
    confirmText: 'Ha, chiqish',
    cancelText: "Yo'q",
    danger: false,
  });
  if (!sure) return;
  try {
    const res = await fetch(`${API_BASE}/auth/logout/`, {
      method: 'POST'
    });
    if (res.ok) {
      closeModal('modalSettings');
      showToast('Tizimdan muvaffaqiyatli chiqildi');
      checkAuth();
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// Akkauntni o'chirish: tugma alohida tasdiqlash oynasini ochadi (parol so'raydi)
document.getElementById('btnDeleteAccount')?.addEventListener('click', () => {
  document.getElementById('formDeleteAccount').reset();
  openModal('modalDeleteAccount');
  document.getElementById('deleteAccountPassword').focus();
});

document.getElementById('formDeleteAccount')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const password = document.getElementById('deleteAccountPassword').value;
  const sure = await showConfirm({
    title: "Rostan ham o'chirmoqchimisiz?",
    message: "Akkauntingiz o'chiriladi va unga qayta kira olmaysiz. Bu amalni ortga qaytarib bo'lmaydi.",
    confirmText: "Ha, akkauntni o'chirish",
    cancelText: "Yo'q, qoldirish",
  });
  if (!sure) return;

  try {
    const res = await fetch(`${API_BASE}/auth/delete-account/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) {
      e.target.reset();
      closeModal('modalDeleteAccount');
      closeModal('modalSettings');
      showToast("Akkaunt o'chirildi");
      checkAuth();
    } else {
      showToast(extractErrorMessage(data, "Akkauntni o'chirishda xatolik"), 'error');
    }
  } catch (err) {
    showToast('Tarmoq xatosi', 'error');
  }
});

// Password Visibility Toggle (Show / Hide)
document.querySelectorAll('.toggle-password-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const targetId = btn.getAttribute('data-target');
    const input = document.getElementById(targetId);
    if (!input) return;

    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';

    const eyeShow = btn.querySelector('.eye-show');
    const eyeHide = btn.querySelector('.eye-hide');
    if (eyeShow && eyeHide) {
      eyeShow.style.display = isPassword ? 'none' : 'block';
      eyeHide.style.display = isPassword ? 'block' : 'none';
    }
    btn.title = isPassword ? "Parolni yashirish" : "Parolni ko'rsatish";
  });
});

// Initial boot
document.addEventListener('DOMContentLoaded', () => {
  fetchCategories();
  checkAuth();
});




// Navbar doim ko'rinib turadi: ro'yxat sahifalari (overlay) uning ostidan boshlanishi uchun balandligini kuzatib boramiz
function syncNavbarHeight() {
  const nav = document.querySelector('.navbar');
  if (nav) document.documentElement.style.setProperty('--navbar-h', nav.getBoundingClientRect().height + 'px');
}
syncNavbarHeight();
const _navEl = document.querySelector('.navbar');
if (_navEl && 'ResizeObserver' in window) new ResizeObserver(syncNavbarHeight).observe(_navEl);
else window.addEventListener('resize', syncNavbarHeight);

// "Moliya" ovali "Kirim" tugmasi bilan bir xil enda bo'lishi uchun enini unga moslab turamiz.
// Tor ekranda (tugmalar faqat ikonka) moslash o'chadi va brend o'z eniga qaytadi.
let _brandSyncQueued = false;
function syncBrandWidth() {
  _brandSyncQueued = false;
  const brand = document.querySelector('.navbar .brand');
  const link = document.querySelector('.navbar .nav-section-link');
  if (!brand || !link) return;
  const label = link.querySelector('.nav-section-label');
  const iconOnly = !label || getComputedStyle(label).display === 'none';
  if (iconOnly || link.offsetParent === null) {
    brand.style.width = '';
    return;
  }
  const target = Math.round(link.getBoundingClientRect().width);
  if (Math.abs(target - brand.offsetWidth) >= 1) brand.style.width = target + 'px';
}
function queueBrandSync() {
  if (_brandSyncQueued) return;
  _brandSyncQueued = true;
  setTimeout(syncBrandWidth, 0);
}
if ('ResizeObserver' in window) {
  const ro = new ResizeObserver(queueBrandSync);
  ro.observe(document.querySelector('.navbar'));
  const firstLink = document.querySelector('.navbar .nav-section-link');
  if (firstLink) ro.observe(firstLink);
}
window.addEventListener('resize', queueBrandSync);
queueBrandSync();
