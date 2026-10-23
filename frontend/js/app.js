/**
 * BidScouter v2 — Dashboard JavaScript
 * Features: bid table, kanban tracker, charts with labels, link health, CPO reminders
 */

const API = '';
let allBids = [];
let currentPage = 'dashboard';
let sortBy = 'deadline', sortDir = 'asc';
let pageNum = 0, pageSize = 30;
let appPageNum = 0, appPageSize = 30;
let charts = {};
let settingsData = {};
let statusMeta = [];
let _debounceTimer = null;

// ── STATUS CONFIG ────────────────────────────────────────────────────────────
const STATUS_CONFIG = {
  not_applied:      { label: 'Not Applied',      icon: '○', color: '#94a3b8', desc: 'Haven\'t taken any action yet' },
  doc_purchased:    { label: 'Doc Purchased',     icon: '📄', color: '#3b82f6', desc: 'Bid document purchased' },
  cpo_delivered:    { label: 'CPO Delivered',     icon: '🏦', color: '#f59e0b', desc: 'CPO/security delivered to procurer' },
  applied:          { label: 'Applied',           icon: '📬', color: '#34a853', desc: 'Bid formally submitted' },
  sample_delivered: { label: 'Sample Delivered',  icon: '📦', color: '#0097a7', desc: 'Product sample delivered' },
  secured:          { label: 'Secured ✅',        icon: '🏆', color: '#16a34a', desc: 'Bid won! Congratulations!' },
  failed:           { label: 'Failed ❌',          icon: '✖', color: '#ea4335', desc: 'Bid lost. Collect CPO if applicable.' },
  cancelled:        { label: 'Cancelled 🚫',      icon: '⊘', color: '#7c3aed', desc: 'Bid cancelled by procurer. Collect CPO.' },
};

// ── INIT ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  Chart.register(ChartDataLabels);
  updateClock();
  setInterval(updateClock, 1000);
  setupNavigation();
  setupTableSorting();
  await loadSettings();
  await populateSiteFilter();
  await showPage('dashboard');
  setInterval(() => { loadStats(); if (currentPage === 'dashboard') loadDashboard(); }, 90000);
});

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleString('en-ET', { year:'numeric', month:'short', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false });
}

// ── NAVIGATION ───────────────────────────────────────────────────────────────
function setupNavigation() {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', e => { e.preventDefault(); showPage(el.dataset.page); });
  });
}

async function showPage(name) {
  currentPage = name;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const pageEl = document.getElementById(`page-${name}`);
  if (pageEl) pageEl.classList.add('active');
  const navEl = document.querySelector(`[data-page="${name}"]`);
  if (navEl) navEl.classList.add('active');
  document.getElementById('page-title').textContent = {
    dashboard: 'Dashboard', table: 'All Bids', tracker: 'My Applications',
    charts: 'Charts & Analytics', settings: 'Settings',
  }[name] || name;
  document.getElementById('sidebar').classList.remove('open');
  // Load page data
  if (name === 'dashboard')  { await loadStats(); await loadDashboard(); }
  if (name === 'table')      { await loadTable(); }
  if (name === 'tracker')    { await loadTracker(); }
  if (name === 'charts')     { await loadStats(); await loadCharts(); }
  if (name === 'settings')   { await loadSettings(); await loadCrawlLogs(); }
}

function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); }

// ── STATS ─────────────────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const data = await api('/api/bids/stats/summary');
    set('stat-total',  data.total);
    set('stat-active', data.active);
    set('stat-new',    data.new_today);
    set('stat-urgent', data.upcoming_30h);
    set('stat-dead',   data.dead_links || 0);
    set('stat-cpo',    data.cpo_refund_pending || 0);

    const unread = data.unread || 0;
    set('bell-count', unread);
    set('cpo-count', data.cpo_refund_pending || 0);
    document.getElementById('new-badge').classList.toggle('show', unread > 0);
    document.getElementById('new-badge').textContent = unread;

    if (currentPage === 'dashboard') {
      renderMiniCategoryChart(data.by_category || []);
      renderMiniPipelineChart(data.by_status || []);
    }
    if (currentPage === 'charts') {
      renderCategoryDonut(data.by_category || []);
      renderSiteBar(data.by_site || []);
      renderPipelineFull(data.by_status || []);
    }
    return data;
  } catch (e) { console.error('Stats error', e); return {}; }
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
async function loadDashboard() {
  const [urgent, recent, timeline] = await Promise.all([
    api('/api/bids?sort_by=deadline&sort_dir=asc&days=1&limit=8').catch(() => []),
    api('/api/bids?sort_by=created_at&sort_dir=desc&limit=8').catch(() => []),
    api('/api/bids?sort_by=deadline&sort_dir=asc&days=14&limit=200').catch(() => []),
  ]);
  renderMiniList('urgent-list', urgent, true);
  renderMiniList('recent-list', recent, false);
  renderTimelineChart(timeline);
  await loadCPOPending();
}

function renderMiniList(elId, bids, showDeadline) {
  const el = document.getElementById(elId);
  if (!bids.length) { el.innerHTML = '<p class="empty-msg">None found.</p>'; return; }
  el.innerHTML = bids.map(b => `
    <div class="mini-row" onclick="openBidDetail('${b.id}')">
      <span class="dot ${b.is_new ? 'dot-new' : 'dot-read'}"></span>
      <span class="mr-title">${esc(b.title)}</span>
      <span class="mr-co">${esc(b.company || '—')}</span>
      ${b.category ? `<span class="mini-tag" style="background:#e8f0fe;color:#1a73e8">${esc(b.category)}</span>` : ''}
      ${showDeadline ? `<span class="mr-dl">⏰ ${fmtDeadlineShort(b.deadline)}</span>` : ''}
    </div>
  `).join('');
}

async function loadCPOPending() {
  try {
    const bids = await api('/api/bids/cpo/pending-refunds');
    const el = document.getElementById('cpo-list');
    const alertEl = document.getElementById('cpo-alert');
    const alertList = document.getElementById('cpo-alert-list');
    if (!bids.length) {
      el.innerHTML = '<p class="empty-msg">No CPO refunds pending 👍</p>';
      if (alertEl) alertEl.style.display = 'none';
      return;
    }
    const rows = bids.map(b => `
      <div class="mini-row" onclick="openStatusModal('${b.id}')">
        <span>💰</span>
        <span class="mr-title">${esc(b.title)}</span>
        <span class="mr-co">${esc(b.company || '—')}</span>
        <span class="mini-tag" style="background:#fce4ec;color:#880e4f">${esc(b.bid_security_type)} ${b.bid_security_amount ? fmtMoney(b.bid_security_amount) : ''}</span>
        <span class="mini-tag app-badge app-${b.application_status}">${STATUS_CONFIG[b.application_status]?.icon} ${STATUS_CONFIG[b.application_status]?.label || b.application_status}</span>
      </div>
    `).join('');
    el.innerHTML = rows;
    if (alertEl && alertList) {
      alertEl.style.display = 'block';
      alertList.innerHTML = bids.map(b => `
        <div class="cpo-row">
          <strong>${esc(b.title.substring(0,60))}</strong>
          <span>— ${esc(b.bid_security_type)} ${b.bid_security_amount ? fmtMoney(b.bid_security_amount) : ''}</span>
          <button class="act-btn" onclick="markCPOCollected('${b.id}')">✓ Collected</button>
        </div>
      `).join('');
    }
  } catch (e) {}
}

async function markCPOCollected(bidId) {
  await api(`/api/bids/${bidId}/application`, 'PATCH', { cpo_refund_collected: true });
  showToast('CPO marked as collected.', 'success');
  loadDashboard();
  loadStats();
}

// ── TABLE ─────────────────────────────────────────────────────────────────────
function setupTableSorting() {
  document.querySelectorAll('.bids-tbl th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.sort;
      if (sortBy === col) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
      else { sortBy = col; sortDir = 'asc'; }
      document.querySelectorAll('.bids-tbl th').forEach(h => h.classList.remove('sort-asc','sort-desc'));
      th.classList.add(sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
      loadTable();
    });
  });
}

async function loadTable() {
  const params = new URLSearchParams({
    search:        document.getElementById('filter-search').value,
    category:      document.getElementById('filter-category').value,
    site:          document.getElementById('filter-site').value,
    app_status:    document.getElementById('filter-appstatus').value,
    days:          document.getElementById('filter-days').value,
    show_expired:  document.getElementById('filter-expired').checked,
    hide_dead_links: document.getElementById('filter-hide-dead').checked,
    sort_by: sortBy, sort_dir: sortDir, limit: 1000,
  });
  try {
    allBids = await api(`/api/bids?${params}`);
    renderTable();
  } catch (e) { console.error(e); }
}

function changePageSize(val) {
  pageSize = val === 'all' ? 999999 : parseInt(val, 10);
  pageNum = 0;
  renderTable();
}

function renderTable() {
  const isAll = pageSize >= 999999;
  const numPageSize = isAll ? Math.max(1, allBids.length) : pageSize;
  const maxPage = Math.max(0, Math.ceil(allBids.length / numPageSize) - 1);
  if (pageNum > maxPage) pageNum = maxPage;

  const start = isAll ? 0 : pageNum * numPageSize;
  const slice = isAll ? allBids : allBids.slice(start, start + numPageSize);
  const tbody = document.getElementById('bids-tbody');
  const empty = document.getElementById('table-empty');

  if (!allBids.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    renderPaginationControls({
      containerId: 'pagination',
      counterId: 'table-count',
      totalItems: 0,
      currentPage: 0,
      pageSize: pageSize,
      onPageChange: 'goPage',
      unitName: 'bids',
    });
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = slice.map(b => {
    const sc = STATUS_CONFIG[b.application_status] || STATUS_CONFIG.not_applied;
    const dlClass = deadlineClass(b.deadline);
    const linkHtml = linkBadge(b);
    const rowClass = [
      b.is_new ? 'row-new' : '',
      b.link_status === 'dead' ? 'row-dead' : '',
      b.application_status === 'secured' ? 'row-secured' : '',
      b.application_status === 'failed' ? 'row-failed' : '',
      b.application_status === 'cancelled' ? 'row-cancelled' : '',
    ].filter(Boolean).join(' ');

    return `<tr class="${rowClass}">
      <td>
        <span class="app-badge app-${b.application_status}" style="cursor:pointer" onclick="openStatusModal('${b.id}')" title="Click to update stage">
          ${sc.icon} ${sc.label}
        </span>
        ${(b.application_status === 'failed' || b.application_status === 'cancelled') && !b.cpo_refund_collected && b.bid_security_type?.toLowerCase().includes('cpo') ?
          '<br><span style="font-size:11px;font-weight:700;color:#dc2626;display:inline-block;margin-top:4px">💰 Collect CPO</span>' : ''}
      </td>
      <td>
        <div style="display:flex;align-items:flex-start;gap:6px">
          <span class="dot ${b.is_new ? 'dot-new' : 'dot-read'}" title="${b.is_new ? 'New' : 'Read'}" style="margin-top:5px;flex-shrink:0"></span>
          <div>
            <span class="cell-wrap">${esc(b.title)}</span>
            ${b.bid_number ? `<small style="color:#64748b;font-weight:600;display:block;margin-top:2px">Ref: ${esc(b.bid_number)}</small>` : ''}
            <button class="doc-pill-btn ${(b.prepared_docs_count && b.prepared_docs_count >= (b.required_docs_count || 11)) ? 'all-ready' : (b.prepared_docs_count > 0 ? 'partial-ready' : '')}" onclick="openDocsModal('${b.id}')" title="View required documents for this bid">
              📋 ${b.prepared_docs_count || 0}/${b.required_docs_count || 11} Docs
            </button>
          </div>
        </div>
      </td>
      <td><span class="cell-clip" title="${esc(b.company)}">${esc(b.company || '—')}</span></td>
      <td><span class="mini-tag" style="background:#e8f0fe;color:#1a73e8;font-size:11px">${esc(b.category)}</span></td>
      <td class="${dlClass}"><strong>${fmtDeadline(b.deadline)}</strong></td>
      <td>${b.registration_fee ? fmtMoney(b.registration_fee, b.registration_fee_currency) : '<span style="color:#ccc">—</span>'}</td>
      <td>${b.bid_security_type ? `<span class="sec-badge ${secClass(b.bid_security_type)}">${esc(b.bid_security_type)}</span>` : '<span style="color:#ccc">—</span>'}</td>
      <td style="font-weight:700;color:#0f172a">${b.bid_security_amount ? fmtMoney(b.bid_security_amount, b.bid_security_currency) : '<span style="color:#ccc">—</span>'}</td>
      <td><span class="cell-clip" title="${esc(b.location)}">${esc(b.location || '—')}</span></td>
      <td>
        ${b.contact_phone ? `<span style="display:block;font-size:11px;margin-bottom:2px">📞 ${esc(b.contact_phone)}</span>` : ''}
        ${b.contact_email ? `<a href="mailto:${esc(b.contact_email)}" style="font-size:11px;word-break:break-all">✉ ${esc(b.contact_email)}</a>` : ''}
        ${!b.contact_phone && !b.contact_email ? '<span style="color:#ccc">—</span>' : ''}
      </td>
      <td>${linkHtml}</td>
      <td>
        <div style="display:flex;gap:4px">
          <button class="act-btn" onclick="openDocsModal('${b.id}')" title="Document Requirements Checklist">📋</button>
          <button class="act-btn" onclick="openBidDetail('${b.id}')" title="View details">👁</button>
          <button class="act-btn del" onclick="deleteBid('${b.id}',this)" title="Delete">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');

  renderPaginationControls({
    containerId: 'pagination',
    counterId: 'table-count',
    totalItems: allBids.length,
    currentPage: pageNum,
    pageSize: pageSize,
    onPageChange: 'goPage',
    unitName: 'bids',
  });
}

function linkBadge(b) {
  if (!b.source_url) return '<span style="color:#ccc">—</span>';
  const linkText = {
    valid: '🟢 Valid', dead: '🔴 Dead', redirect: '🟡 Redirect',
    timeout: '⚫ Timeout', unknown: '⚪ Unchecked',
  }[b.link_status] || '⚪ Unchecked';
  const cls = `link-${b.link_status || 'unknown'}`;
  const icon = b.link_status === 'dead' ? '' :
    `<a href="${esc(b.source_url)}" target="_blank" rel="noopener" class="act-btn" title="Open link">🔗</a>`;
  return `<span class="${cls}" style="display:block;font-size:10px">${linkText}</span>${icon}`;
}

function renderPaginationControls({ containerId, counterId, totalItems, currentPage, pageSize, onPageChange, unitName = 'items' }) {
  const container = document.getElementById(containerId);
  const counter = document.getElementById(counterId);
  if (!container) return;

  const isAll = pageSize >= 999999 || pageSize === 'all';
  const effectiveSize = isAll ? (totalItems || 1) : parseInt(pageSize, 10);
  const totalPages = isAll || totalItems === 0 ? 1 : Math.ceil(totalItems / effectiveSize);

  // Summary Counter
  if (counter) {
    if (totalItems === 0) {
      counter.textContent = `0 ${unitName}`;
    } else if (isAll || totalPages === 1) {
      counter.innerHTML = `Showing all <strong>${totalItems}</strong> ${unitName} <span style="color:#16a34a;font-weight:600">(Full List)</span>`;
    } else {
      const start = currentPage * effectiveSize + 1;
      const end = Math.min((currentPage + 1) * effectiveSize, totalItems);
      counter.innerHTML = `Showing <strong>${start}–${end}</strong> of <strong>${totalItems}</strong> ${unitName} (Page ${currentPage + 1} of ${totalPages})`;
    }
  }

  // If only 1 page, no pagination buttons needed
  if (totalPages <= 1) {
    container.innerHTML = '';
    return;
  }

  let html = '';
  const prevDisabled = currentPage === 0 ? 'disabled' : '';
  const nextDisabled = currentPage >= totalPages - 1 ? 'disabled' : '';

  // First & Prev buttons
  html += `<button class="pg-btn pg-nav ${prevDisabled}" onclick="${onPageChange}(0)" ${prevDisabled} title="First Page">« First</button>`;
  html += `<button class="pg-btn pg-nav ${prevDisabled}" onclick="${onPageChange}(${currentPage - 1})" ${prevDisabled} title="Previous Page">‹ Prev</button>`;

  // Dynamic window of page numbers
  let startP = Math.max(0, currentPage - 2);
  let endP = Math.min(totalPages - 1, currentPage + 2);

  if (startP > 0) {
    html += `<button class="pg-btn" onclick="${onPageChange}(0)">1</button>`;
    if (startP > 1) html += `<span class="pg-ellipsis">…</span>`;
  }

  for (let i = startP; i <= endP; i++) {
    html += `<button class="pg-btn ${i === currentPage ? 'active' : ''}" onclick="${onPageChange}(${i})">${i + 1}</button>`;
  }

  if (endP < totalPages - 1) {
    if (endP < totalPages - 2) html += `<span class="pg-ellipsis">…</span>`;
    html += `<button class="pg-btn" onclick="${onPageChange}(${totalPages - 1})">${totalPages}</button>`;
  }

  // Next & Last buttons
  html += `<button class="pg-btn pg-nav ${nextDisabled}" onclick="${onPageChange}(${currentPage + 1})" ${nextDisabled} title="Next Page">Next ›</button>`;
  html += `<button class="pg-btn pg-nav ${nextDisabled}" onclick="${onPageChange}(${totalPages - 1})" ${nextDisabled} title="Last Page">Last »</button>`;

  container.innerHTML = html;
}

function goPage(n) {
  pageNum = Math.max(0, n);
  renderTable();
  document.getElementById('bids-table')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── TRACKER / KANBAN & APPLICATION TABLE ─────────────────────────────────────
let currentTrackerView = 'both'; // 'cards', 'table', 'both'
let appTrackerBids = [];

function setTrackerView(mode) {
  currentTrackerView = mode;
  document.querySelectorAll('.view-toggle-group .toggle-btn').forEach(b => b.classList.remove('active'));
  const activeBtn = document.getElementById(`btn-view-${mode}`);
  if (activeBtn) activeBtn.classList.add('active');

  const cardsContainer = document.getElementById('tracker-cards-container');
  const tableContainer = document.getElementById('tracker-table-container');

  if (mode === 'cards') {
    cardsContainer.style.display = 'block';
    tableContainer.style.display = 'none';
  } else if (mode === 'table') {
    cardsContainer.style.display = 'none';
    tableContainer.style.display = 'block';
  } else {
    cardsContainer.style.display = 'block';
    tableContainer.style.display = 'block';
  }
}

async function loadTracker() {
  appTrackerBids = await api('/api/bids?sort_by=application_status&limit=1000&show_expired=true').catch(() => []);
  
  // Render KPI Summary Chips
  renderTrackerKPIs(appTrackerBids);

  // Render Kanban Cards
  renderKanbanBoard(appTrackerBids);

  // Render Applications Table
  renderAppTable();

  // Apply current view setting
  setTrackerView(currentTrackerView);

  // Load CPO alerts
  await loadCPOPending();
}

function renderTrackerKPIs(bids) {
  const kpiBar = document.getElementById('tracker-kpi-bar');
  if (!kpiBar) return;

  const total = bids.length;
  const inProgress = bids.filter(b => ['doc_purchased', 'cpo_delivered', 'applied', 'sample_delivered'].includes(b.application_status)).length;
  const secured = bids.filter(b => b.application_status === 'secured').length;
  const failed = bids.filter(b => b.application_status === 'failed').length;
  const cancelled = bids.filter(b => b.application_status === 'cancelled').length;
  const cpoPending = bids.filter(b => ['failed', 'cancelled'].includes(b.application_status) && !b.cpo_refund_collected && b.bid_security_type?.toLowerCase().includes('cpo')).length;

  kpiBar.innerHTML = `
    <div class="tracker-chip" onclick="filterAppTableStage('')">
      <span style="font-size:20px">🗂</span>
      <div><div class="chip-num">${total}</div><div class="chip-label">Total Applications</div></div>
    </div>
    <div class="tracker-chip" onclick="filterAppTableStage('active')">
      <span style="font-size:20px">⏳</span>
      <div><div class="chip-num" style="color:#1d4ed8">${inProgress}</div><div class="chip-label">In Progress</div></div>
    </div>
    <div class="tracker-chip" onclick="filterAppTableStage('secured')">
      <span style="font-size:20px">🏆</span>
      <div><div class="chip-num" style="color:#15803d">${secured}</div><div class="chip-label">Secured / Won</div></div>
    </div>
    <div class="tracker-chip" onclick="filterAppTableStage('failed')">
      <span style="font-size:20px">✖</span>
      <div><div class="chip-num" style="color:#b91c1c">${failed + cancelled}</div><div class="chip-label">Failed / Cancelled</div></div>
    </div>
    <div class="tracker-chip" onclick="filterAppTableStage('cpo_pending')" style="background:#fffbeb;border-color:#fde047">
      <span style="font-size:20px">💰</span>
      <div><div class="chip-num" style="color:#b45309">${cpoPending}</div><div class="chip-label" style="color:#92400e">CPO to Collect</div></div>
    </div>
  `;
}

function filterAppTableStage(stage) {
  const sel = document.getElementById('app-table-filter-stage');
  if (sel) {
    sel.value = stage;
    renderAppTable();
    // If table container is hidden, switch view so user sees the table
    if (currentTrackerView === 'cards') setTrackerView('both');
    document.getElementById('tracker-table-container')?.scrollIntoView({ behavior: 'smooth' });
  }
}

function renderKanbanBoard(bids) {
  const board = document.getElementById('kanban-board');
  if (!board) return;

  const grouped = {};
  Object.keys(STATUS_CONFIG).forEach(s => grouped[s] = []);
  bids.forEach(b => {
    const s = b.application_status || 'not_applied';
    if (!grouped[s]) grouped[s] = [];
    grouped[s].push(b);
  });

  board.innerHTML = Object.entries(STATUS_CONFIG).map(([key, cfg]) => {
    const items = grouped[key] || [];
    const cards = items.length === 0
      ? '<div style="text-align:center;padding:20px;color:#94a3b8;font-size:12px;font-style:italic">No bids in this stage</div>'
      : items.map(b => {
        const isCpoPending = ['failed', 'cancelled'].includes(b.application_status) && !b.cpo_refund_collected && b.bid_security_type?.toLowerCase().includes('cpo');
        return `
        <div class="kanban-card" onclick="openStatusModal('${b.id}')">
          <div class="kc-title">${esc(b.title)}</div>
          <div class="kc-co">${esc(b.company || '—')}</div>
          ${b.category ? `<span class="mini-tag" style="background:#e8f0fe;color:#1a73e8">${esc(b.category)}</span>` : ''}
          ${isCpoPending ? `<span class="mini-tag" style="background:#fee2e2;color:#dc2626;margin-left:4px">💰 Collect CPO</span>` : ''}
          <div class="kc-meta-row">
            <span class="kc-dl">${b.deadline ? `⏰ ${fmtDeadlineShort(b.deadline)}` : 'No deadline'}</span>
            <span class="kc-amt">${b.bid_security_amount ? fmtMoney(b.bid_security_amount, b.bid_security_currency) : '—'}</span>
          </div>
          ${b.application_notes ? `<div class="kc-notes">"${esc(b.application_notes)}"</div>` : ''}
          <button class="kc-act-btn" onclick="event.stopPropagation();openStatusModal('${b.id}')">✏️ Change Stage</button>
        </div>`;
      }).join('');

    return `<div class="kanban-col">
      <div class="kanban-col-header kc-${key}" style="border-bottom-color:${cfg.color}">
        <span>${cfg.icon} ${cfg.label}</span>
        <span class="kanban-count">${items.length}</span>
      </div>
      <div class="kanban-col-body">${cards}</div>
    </div>`;
  }).join('');
}

function getPipelineProgress(status) {
  switch (status) {
    case 'doc_purchased':
      return { step: '1/5 Doc Purchased', pct: 20, color: '#3b82f6' };
    case 'cpo_delivered':
      return { step: '2/5 CPO Delivered', pct: 40, color: '#f59e0b' };
    case 'applied':
      return { step: '3/5 Formally Applied', pct: 65, color: '#10b981' };
    case 'sample_delivered':
      return { step: '4/5 Sample Delivered', pct: 85, color: '#00838f' };
    case 'secured':
      return { step: '5/5 Won / Secured 🏆', pct: 100, color: '#16a34a' };
    case 'failed':
      return { step: '5/5 Concluded (Lost) ❌', pct: 100, color: '#dc2626' };
    case 'cancelled':
      return { step: '5/5 Tender Cancelled 🚫', pct: 100, color: '#7c3aed' };
    default:
      return { step: '0/5 Not Started', pct: 5, color: '#94a3b8' };
  }
}

function changeAppPageSize(val) {
  appPageSize = val === 'all' ? 999999 : parseInt(val, 10);
  appPageNum = 0;
  renderAppTable();
}

function goAppPage(n) {
  appPageNum = Math.max(0, n);
  renderAppTable();
  document.getElementById('app-status-tbl')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function renderAppTable() {
  const tbody = document.getElementById('app-table-tbody');
  const empty = document.getElementById('app-table-empty');
  if (!tbody) return;

  const search = (document.getElementById('app-table-search')?.value || '').toLowerCase().trim();
  const filterStage = document.getElementById('app-table-filter-stage')?.value || '';

  let filtered = appTrackerBids.filter(b => {
    // Stage filtering
    if (filterStage === 'active') {
      if (!['doc_purchased', 'cpo_delivered', 'applied', 'sample_delivered'].includes(b.application_status)) return false;
    } else if (filterStage === 'cpo_pending') {
      const isCpo = ['failed', 'cancelled'].includes(b.application_status) && !b.cpo_refund_collected && b.bid_security_type?.toLowerCase().includes('cpo');
      if (!isCpo) return false;
    } else if (filterStage && b.application_status !== filterStage) {
      return false;
    }

    // Text search
    if (search) {
      const str = `${b.title} ${b.company} ${b.category} ${b.bid_number} ${b.application_notes} ${b.location}`.toLowerCase();
      if (!str.includes(search)) return false;
    }
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    renderPaginationControls({
      containerId: 'app-table-pagination',
      counterId: 'app-table-count',
      totalItems: 0,
      currentPage: 0,
      pageSize: appPageSize,
      onPageChange: 'goAppPage',
      unitName: 'applications',
    });
    return;
  }
  empty.style.display = 'none';

  const isAll = appPageSize >= 999999;
  const numSize = isAll ? Math.max(1, filtered.length) : appPageSize;
  const maxPage = Math.max(0, Math.ceil(filtered.length / numSize) - 1);
  if (appPageNum > maxPage) appPageNum = maxPage;

  const start = isAll ? 0 : appPageNum * numSize;
  const slice = isAll ? filtered : filtered.slice(start, start + numSize);

  tbody.innerHTML = slice.map(b => {
    const sc = STATUS_CONFIG[b.application_status] || STATUS_CONFIG.not_applied;
    const prog = getPipelineProgress(b.application_status);
    const isCpoPending = ['failed', 'cancelled'].includes(b.application_status) && !b.cpo_refund_collected && b.bid_security_type?.toLowerCase().includes('cpo');
    const isCpoCollected = ['failed', 'cancelled'].includes(b.application_status) && b.cpo_refund_collected && b.bid_security_type?.toLowerCase().includes('cpo');

    let cpoRecoveryHtml = '—';
    if (isCpoPending) {
      cpoRecoveryHtml = `
        <span class="sec-badge" style="background:#fee2e2;color:#b91c1c;display:block;margin-bottom:4px;font-weight:700">⚠️ Collect CPO</span>
        <button class="act-btn" onclick="markCPOCollected('${b.id}')" title="Mark as collected">✓ Collected</button>
      `;
    } else if (isCpoCollected) {
      cpoRecoveryHtml = `<span class="sec-badge" style="background:#dcfce7;color:#15803d;font-weight:700">✓ CPO Collected</span>`;
    }

    return `
      <tr>
        <td>
          <span class="app-badge app-${b.application_status}" style="cursor:pointer" onclick="openStatusModal('${b.id}')" title="Click to change stage">
            ${sc.icon} ${sc.label}
          </span>
        </td>
        <td>
          <span class="cell-wrap" style="color:var(--text);font-weight:600">${esc(b.title)}</span>
          ${b.bid_number ? `<span style="font-size:11px;color:#64748b;font-weight:600;display:block;margin-top:2px">Ref: ${esc(b.bid_number)}</span>` : ''}
          <button class="doc-pill-btn ${(b.prepared_docs_count && b.prepared_docs_count >= (b.required_docs_count || 11)) ? 'all-ready' : (b.prepared_docs_count > 0 ? 'partial-ready' : '')}" onclick="openDocsModal('${b.id}')" title="View and check off required documents">
            📋 ${b.prepared_docs_count || 0}/${b.required_docs_count || 11} Docs Ready
          </button>
        </td>
        <td><span class="cell-clip" title="${esc(b.company)}">${esc(b.company || '—')}</span></td>
        <td><span class="mini-tag" style="background:#e8f0fe;color:#1a73e8;font-size:11px">${esc(b.category)}</span></td>
        <td>
          <div class="pipeline-progress-bar">
            <div class="prog-track">
              <div class="prog-fill" style="width:${prog.pct}%;background:${prog.color}"></div>
            </div>
            <span class="prog-step-text" style="color:${prog.color}">${prog.step}</span>
          </div>
        </td>
        <td class="${deadlineClass(b.deadline)}">
          <strong>${fmtDeadline(b.deadline)}</strong>
        </td>
        <td>
          <strong style="color:#0f172a">${b.bid_security_amount ? fmtMoney(b.bid_security_amount, b.bid_security_currency) : '—'}</strong>
          ${b.bid_security_type ? `<br><small style="color:#64748b;font-weight:600">${esc(b.bid_security_type)}</small>` : ''}
        </td>
        <td>${cpoRecoveryHtml}</td>
        <td>
          <span style="font-size:12px;color:#334155;display:block;line-height:1.4">
            ${b.application_notes ? `"${esc(b.application_notes)}"` : '<span style="color:#94a3b8;font-style:italic">No notes recorded</span>'}
          </span>
        </td>
        <td>
          <div style="display:flex;gap:4px">
            <button class="act-btn" onclick="openDocsModal('${b.id}')" title="Document Checklist">📋 Docs</button>
            <button class="act-btn" onclick="openStatusModal('${b.id}')" title="Update Status">📝 Stage</button>
            <button class="act-btn" onclick="openBidDetail('${b.id}')" title="View Full Details">👁</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  renderPaginationControls({
    containerId: 'app-table-pagination',
    counterId: 'app-table-count',
    totalItems: filtered.length,
    currentPage: appPageNum,
    pageSize: appPageSize,
    onPageChange: 'goAppPage',
    unitName: 'applications',
  });
}

// ── STATUS MODAL ─────────────────────────────────────────────────────────────
let _statusBidId = null;

async function openStatusModal(bidId) {
  _statusBidId = bidId;
  const bid = await api(`/api/bids/${bidId}`).catch(() => null);
  if (!bid) return;

  const modal = document.getElementById('status-modal');
  const content = document.getElementById('status-modal-content');

  const pipeline = Object.entries(STATUS_CONFIG).map(([key, cfg]) => `
    <div class="status-option ${bid.application_status === key ? 'current' : ''}"
         onclick="selectStatus('${key}')" id="so-${key}">
      <span class="so-icon">${cfg.icon}</span>
      <div>
        <div class="so-label">${cfg.label}</div>
        <div class="so-desc">${cfg.desc}</div>
      </div>
    </div>
  `).join('');

  const showCpoCollect = ['failed','cancelled'].includes(bid.application_status) &&
    bid.bid_security_type?.toLowerCase().includes('cpo');

  content.innerHTML = `
    <div style="font-size:12px;color:#888;margin-bottom:12px">${esc(bid.title.substring(0,80))}</div>
    <div class="status-pipeline">${pipeline}</div>
    <div class="modal-notes">
      <label>Notes</label>
      <textarea id="status-notes" rows="3" placeholder="Add notes about this bid…">${esc(bid.application_notes || '')}</textarea>
    </div>
    ${showCpoCollect ? `
    <div class="modal-collect-row">
      <input type="checkbox" id="cpo-collected" ${bid.cpo_refund_collected ? 'checked' : ''}/>
      <label for="cpo-collected">CPO / Bid Security refund collected</label>
    </div>` : ''}
    <div style="display:flex;gap:8px;margin-top:14px">
      <button class="btn-primary" onclick="saveStatus()">💾 Save</button>
      <button class="btn-secondary" onclick="closeStatusModal()">Cancel</button>
    </div>
  `;

  modal.style.display = 'flex';
  modal.classList.add('open');
}

function selectStatus(key) {
  document.querySelectorAll('.status-option').forEach(el => el.classList.remove('current'));
  const el = document.getElementById(`so-${key}`);
  if (el) el.classList.add('current');
}

async function saveStatus() {
  if (!_statusBidId) return;
  const current = document.querySelector('.status-option.current');
  const status = current ? current.id.replace('so-','') : null;
  const notes = document.getElementById('status-notes')?.value || '';
  const cpoEl = document.getElementById('cpo-collected');
  const payload = { application_notes: notes };
  if (status) payload.application_status = status;
  if (cpoEl) payload.cpo_refund_collected = cpoEl.checked;

  await api(`/api/bids/${_statusBidId}/application`, 'PATCH', payload);
  closeStatusModal();
  showToast('Status updated!', 'success');
  if (currentPage === 'table')   loadTable();
  if (currentPage === 'tracker') loadTracker();
  if (currentPage === 'dashboard') { loadStats(); loadDashboard(); }
}

function closeStatusModal() {
  const m = document.getElementById('status-modal');
  m.style.display = 'none'; m.classList.remove('open');
}
function closeStatusModalOverlay(e) {
  if (e.target === document.getElementById('status-modal')) closeStatusModal();
}

// ── BID DETAIL MODAL ─────────────────────────────────────────────────────────
async function openBidDetail(id) {
  try {
    const b = await api(`/api/bids/${id}`);
    const sc = STATUS_CONFIG[b.application_status] || STATUS_CONFIG.not_applied;
    const modal = document.getElementById('bid-modal');
    const content = document.getElementById('modal-content');

    content.innerHTML = `
      <div class="modal-title">${esc(b.title)}</div>
      <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
        <span class="app-badge app-${b.application_status}">${sc.icon} ${sc.label}</span>
        ${b.category ? `<span class="mini-tag" style="background:#e8f0fe;color:#1a73e8">${esc(b.category)}</span>` : ''}
        <span class="link-${b.link_status || 'unknown'}" style="font-size:12px">
          ${b.link_status === 'valid' ? '🟢' : b.link_status === 'dead' ? '🔴 DEAD LINK' : '⚪'} ${b.link_status || 'unchecked'}
        </span>
      </div>
      <div class="modal-grid">
        <div><div class="mf-label">Company / Org</div><div class="mf-value">${esc(b.company || '—')}</div></div>
        <div><div class="mf-label">Bid / Tender No.</div><div class="mf-value">${esc(b.bid_number || '—')}</div></div>
        <div><div class="mf-label">Deadline</div>
             <div class="mf-value ${deadlineClass(b.deadline)}" style="font-size:15px;font-weight:700">${fmtDeadline(b.deadline)}</div></div>
        <div><div class="mf-label">Posted Date</div><div class="mf-value">${b.posted_date ? fmtDate(b.posted_date) : '—'}</div></div>
        <div><div class="mf-label">Where to Apply / Buy Doc</div><div class="mf-value">${esc(b.location || '—')}</div></div>
        <div><div class="mf-label">Registration / Doc Fee</div>
             <div class="mf-value">${b.registration_fee ? fmtMoney(b.registration_fee, b.registration_fee_currency) : '—'}</div></div>
        <div><div class="mf-label">Bid Security Type</div>
             <div class="mf-value">${b.bid_security_type ? `<span class="sec-badge ${secClass(b.bid_security_type)}">${esc(b.bid_security_type)}</span>` : '—'}</div></div>
        <div><div class="mf-label">Bid Security Amount</div>
             <div class="mf-value" style="font-size:16px;font-weight:700;color:#ea4335">${b.bid_security_amount ? fmtMoney(b.bid_security_amount, b.bid_security_currency) : '—'}</div></div>
        <div><div class="mf-label">Contact Name</div><div class="mf-value">${esc(b.contact_name || '—')}</div></div>
        <div><div class="mf-label">Contact Phone</div>
             <div class="mf-value">${b.contact_phone ? `<a href="tel:${esc(b.contact_phone)}">${esc(b.contact_phone)}</a>` : '—'}</div></div>
        <div style="grid-column:span 2">
          <div class="mf-label">Contact Email</div>
          <div class="mf-value">${b.contact_email ? `<a href="mailto:${esc(b.contact_email)}">${esc(b.contact_email)}</a>` : '—'}</div>
        </div>
        <div style="grid-column:span 2">
          <div class="mf-label">Source Link</div>
          <div class="mf-value">
            ${b.source_url ? `<a href="${esc(b.source_url)}" target="_blank" rel="noopener" class="btn-export" style="font-size:12px">🔗 Open Original Posting</a>` : '—'}
            <span style="margin-left:8px;font-size:12px;color:#888">${esc(b.source_site)}</span>
            ${b.link_status === 'dead' ? '<span style="margin-left:6px;color:#ea4335;font-size:12px">⚠ Link may be dead</span>' : ''}
          </div>
        </div>
      </div>
      ${b.application_notes ? `<div style="background:#f8fafc;border-radius:8px;padding:12px;margin-bottom:12px;font-size:12px"><strong>📝 Notes:</strong> ${esc(b.application_notes)}</div>` : ''}
      
      <!-- Document Requirements Summary Card -->
      <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:8px;padding:12px 14px;margin-bottom:14px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px">
          <strong style="color:#0369a1;font-size:13.5px">📋 Required Documents Checklist (${b.prepared_docs_count || 0}/${b.required_docs_count || 11} Ready)</strong>
          <button class="btn-primary" style="font-size:11.5px;padding:4px 10px;background:#0284c7;border-color:#0284c7" onclick="openDocsModal('${b.id}')">
            Open Full Checklist ➔
          </button>
        </div>
        <div style="font-size:12px;color:#334155;line-height:1.45">
          <strong>Mandatory:</strong> CPO (${b.bid_security_amount ? fmtMoney(b.bid_security_amount, b.bid_security_currency) : 'As per doc'}) • Physical Garment Sample (${fmtDeadline(b.deadline)}) • Renewed Trade License 2017 E.C. • Tax Clearance (MoR) • VAT & TIN • PPAA Supplier Registration • Signed Technical Compliance Matrix.
        </div>
      </div>

      <div style="display:flex;gap:8px;margin-top:4px">
        <button class="btn-primary" onclick="closeModal();openStatusModal('${b.id}')">📝 Update Status</button>
        <button class="btn-secondary" onclick="closeModal()">Close</button>
      </div>
      <details style="margin-top:14px">
        <summary style="cursor:pointer;font-size:12px;color:#888">Raw Extracted Text</summary>
        <pre style="font-size:11px;margin-top:8px;white-space:pre-wrap;background:#f8fafc;padding:10px;border-radius:8px;max-height:180px;overflow-y:auto">${esc(b.raw_text || '')}</pre>
      </details>
    `;

    modal.style.display = 'flex'; modal.classList.add('open');
    if (b.is_new) { await api(`/api/bids/${id}/mark_read`, 'POST'); loadStats(); }
  } catch (e) { showToast('Failed to load bid', 'error'); }
}

function closeModal() {
  const m = document.getElementById('bid-modal');
  m.style.display = 'none'; m.classList.remove('open');
}
function closeModalOverlay(e) {
  if (e.target === document.getElementById('bid-modal')) closeModal();
}

// ── REQUIRED BID DOCUMENTS MODAL ─────────────────────────────────────────────
let currentDocsBidId = null;
let currentDocsData = null;

async function openDocsModal(bidId) {
  try {
    currentDocsBidId = bidId;
    const data = await api(`/api/bids/${bidId}/documents`);
    currentDocsData = data;
    renderDocsModalContent(data);
    const modal = document.getElementById('docs-modal');
    modal.style.display = 'flex';
    modal.classList.add('open');
  } catch (err) {
    showToast('Failed to load document requirements', 'error');
  }
}

function closeDocsModal() {
  const m = document.getElementById('docs-modal');
  if (m) {
    m.style.display = 'none';
    m.classList.remove('open');
  }
}

function closeDocsModalOverlay(e) {
  if (e.target === document.getElementById('docs-modal')) {
    closeDocsModal();
  }
}

async function toggleDocItem(docId, isChecked) {
  if (!currentDocsData || !currentDocsBidId) return;
  const currentPrepared = currentDocsData.documents.filter(d => d.is_prepared).map(d => d.id);
  let updated;
  if (isChecked) {
    updated = Array.from(new Set([...currentPrepared, docId]));
  } else {
    updated = currentPrepared.filter(id => id !== docId);
  }

  try {
    const res = await api(`/api/bids/${currentDocsBidId}/documents`, 'POST', {
      prepared_document_ids: updated
    });
    currentDocsData.documents = res.documents;
    currentDocsData.prepared_docs = res.prepared_docs;
    currentDocsData.progress_percent = res.progress_percent;
    renderDocsModalContent(currentDocsData);

    // Sync with table cache
    const targetBid = allBids.find(b => b.id === currentDocsBidId);
    if (targetBid) {
      targetBid.prepared_docs_count = res.prepared_docs;
      targetBid.prepared_documents = JSON.stringify(updated);
      if (typeof renderTable === 'function') renderTable();
      if (typeof renderAppTable === 'function') renderAppTable();
    }
    showToast(`Saved: ${res.prepared_docs}/${res.total_docs} documents ready`, 'success');
  } catch (err) {
    console.error('Error saving document status:', err);
    showToast('Failed to save document status', 'error');
  }
}

function renderDocsModalContent(data) {
  const content = document.getElementById('docs-modal-content');
  if (!content) return;

  // Group by category
  const categories = [
    { key: 'legal_statutory', icon: '🏛️', label: 'Legal & Statutory Compliance' },
    { key: 'financial_security', icon: '💳', label: 'Financial Securities & Bid Fees' },
    { key: 'technical_sample', icon: '🧵', label: 'Technical Specifications & Samples' },
    { key: 'submission_forms', icon: '✍️', label: 'Forms & Declarations' },
  ];

  let groupsHtml = '';
  categories.forEach(cat => {
    const catDocs = data.documents.filter(d => d.category === cat.key);
    if (!catDocs.length) return;

    const cardsHtml = catDocs.map(d => `
      <div class="doc-card ${d.is_prepared ? 'prepared' : ''}">
        <div class="doc-card-top">
          <input type="checkbox"
                 id="cb-${d.id}"
                 class="doc-card-cb"
                 ${d.is_prepared ? 'checked' : ''}
                 onchange="toggleDocItem('${d.id}', this.checked)"
                 title="Mark as prepared"
          />
          <div class="doc-card-content">
            <div class="doc-card-header">
              <label for="cb-${d.id}" style="cursor:pointer;margin:0">
                <span class="doc-card-title">${esc(d.title)}</span>
                ${d.title_am ? `<span class="doc-card-title-am">/ ${esc(d.title_am)}</span>` : ''}
              </label>
              <span class="${d.mandatory ? 'doc-badge-mandatory' : 'doc-badge-optional'}">
                ${d.mandatory ? 'Mandatory' : 'Conditional / Optional'}
              </span>
            </div>
            <div class="doc-card-desc">${esc(d.description)}</div>
            ${d.tips ? `<div class="doc-tip-box"><span>💡</span> <span><strong>Factory Tip:</strong> ${esc(d.tips)}</span></div>` : ''}
          </div>
        </div>
      </div>
    `).join('');

    groupsHtml += `
      <div class="docs-category-group">
        <div class="docs-category-title">${cat.icon} ${cat.label}</div>
        <div class="docs-list">${cardsHtml}</div>
      </div>
    `;
  });

  content.innerHTML = `
    <div class="docs-modal-header">
      <div class="docs-modal-title">
        <span>📋 Required Bid Documents</span>
      </div>
      <div class="docs-modal-subtitle">
        <strong>${esc(data.title)}</strong>
        ${data.bid_number ? `<span>• Ref: <code>${esc(data.bid_number)}</code></span>` : ''}
        <span>• 🏢 ${esc(data.company || 'Procuring Entity')}</span>
        <span>• ⏳ Deadline: <strong>${fmtDeadline(data.deadline)}</strong></span>
      </div>
    </div>

    <div class="docs-progress-card">
      <div class="docs-progress-meta">
        <span>Submission Readiness: <strong>${data.prepared_docs} of ${data.total_docs} Documents Ready</strong></span>
        <span style="color:#059669;font-weight:700">${data.progress_percent}%</span>
      </div>
      <div class="docs-progress-bar">
        <div class="docs-progress-fill" style="width:${data.progress_percent}%;background:${data.progress_percent === 100 ? '#10b981' : (data.progress_percent >= 50 ? '#0284c7' : '#f59e0b')}"></div>
      </div>
    </div>

    <div style="max-height:55vh;overflow-y:auto;padding-right:4px">
      ${groupsHtml}
    </div>

    <div class="docs-modal-actions">
      <div style="display:flex;gap:8px">
        <button class="btn-secondary" onclick="printDocsChecklist()" title="Print submission document checklist">🖨️ Print Checklist</button>
        ${data.source_url ? `<a href="${esc(data.source_url)}" target="_blank" rel="noopener" class="btn-export" style="font-size:12px;display:inline-flex;align-items:center;gap:4px">🔗 Open Tender Portal</a>` : ''}
      </div>
      <button class="btn-primary" onclick="closeDocsModal()">Done / Close</button>
    </div>
  `;
}

function printDocsChecklist() {
  if (!currentDocsData) return;
  const d = currentDocsData;
  const win = window.open('', '_blank');
  const itemsHtml = d.documents.map(item => `
    <tr style="border-bottom:1px solid #ddd">
      <td style="padding:8px;text-align:center;font-size:16px;width:30px">${item.is_prepared ? '☑' : '☐'}</td>
      <td style="padding:8px">
        <strong>${esc(item.title)}</strong> <span style="color:#666">(${esc(item.title_am || '')})</span>
        <span style="font-size:11px;margin-left:8px;padding:2px 6px;border-radius:3px;background:${item.mandatory ? '#fee2e2;color:#991b1b' : '#f1f5f9;color:#475569'}">
          ${item.mandatory ? 'MANDATORY' : 'OPTIONAL'}
        </span>
        <div style="font-size:12px;color:#333;margin-top:4px">${esc(item.description)}</div>
        ${item.tips ? `<div style="font-size:11px;color:#854d0e;margin-top:2px">💡 Tip: ${esc(item.tips)}</div>` : ''}
      </td>
    </tr>
  `).join('');

  win.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Bid Document Submission Checklist — ${esc(d.bid_number || d.title)}</title>
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 24px; color: #1e293b; }
        h1 { font-size: 20px; margin-bottom: 4px; color: #1e3a8a; }
        .meta { font-size: 13px; color: #475569; margin-bottom: 16px; line-height: 1.5; }
        table { width: 100%; border-collapse: collapse; margin-top: 14px; }
        th { background: #f1f5f9; text-align: left; padding: 8px; border-bottom: 2px solid #cbd5e1; font-size: 13px; }
        .summary-box { background: #f8fafc; border: 1px solid #cbd5e1; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
        @media print { button { display: none; } }
      </style>
    </head>
    <body>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h1>📋 Bid Submission Document Checklist</h1>
        <button onclick="window.print()" style="padding:8px 16px;background:#1e3a8a;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:bold">🖨️ Print / Save PDF</button>
      </div>
      <div class="meta">
        <strong>Tender:</strong> ${esc(d.title)}<br>
        <strong>Reference No:</strong> ${esc(d.bid_number || 'N/A')} | <strong>Procuring Entity:</strong> ${esc(d.company)}<br>
        <strong>Submission Deadline:</strong> ${fmtDeadline(d.deadline)} | <strong>Delivery Location:</strong> ${esc(d.location || d.company)}
      </div>
      <div class="summary-box">
        <strong>Readiness Status:</strong> ${d.prepared_docs} of ${d.total_docs} documents ready (${d.progress_percent}%) | 
        <strong>Bid Security:</strong> ${d.bid_security_amount ? fmtMoney(d.bid_security_amount, d.bid_security_currency) : 'As per bid document'} |
        <strong>Physical Sample:</strong> 1 finished sample required before closing
      </div>
      <table>
        <thead>
          <tr>
            <th style="width:40px;text-align:center">Ready</th>
            <th>Required Document & Instructions</th>
          </tr>
        </thead>
        <tbody>
          ${itemsHtml}
        </tbody>
      </table>
      <div style="margin-top:24px;border-top:1px dashed #94a3b8;padding-top:12px;font-size:12px;color:#64748b;display:flex;justify-content:space-between">
        <span>Verified by: _______________________</span>
        <span>Signature: _______________________</span>
        <span>Date: _______________</span>
      </div>
      <div style="margin-top:16px;text-align:center;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:8px">
        Powered by <strong>Fashion-Flow 2026</strong> • Created by <strong>Enquzer Getachew</strong>
      </div>
    </body>
    </html>
  `);
  win.document.close();
}

// ── CHARTS ────────────────────────────────────────────────────────────────────
const PALETTE = ['#1a73e8','#16a34a','#f59e0b','#dc2626','#7c3aed','#0284c7','#ea580c','#475569','#b45309','#0d9488'];

function mkChart(id, config) {
  const ctx = document.getElementById(id);
  if (!ctx) return null;
  if (charts[id]) { charts[id].destroy(); }
  // Ensure responsive and maintainAspectRatio is false so it fits .chart-wrapper smoothly
  config.options = config.options || {};
  config.options.responsive = true;
  config.options.maintainAspectRatio = false;
  charts[id] = new Chart(ctx, config);
  return charts[id];
}

function renderMiniCategoryChart(cats) {
  if (!cats.length) return;
  mkChart('chart-category', {
    type: 'doughnut',
    data: {
      labels: cats.map(c => c.category || 'Unknown'),
      datasets: [{ data: cats.map(c => c.count), backgroundColor: PALETTE, borderWidth: 2 }]
    },
    options: {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 13, weight: '600' }, boxWidth: 16, padding: 12, color: '#1e293b' }
        },
        datalabels: {
          color: '#ffffff',
          font: { weight: '800', size: 15 },
          textStrokeColor: 'rgba(0,0,0,0.6)',
          textStrokeWidth: 3,
          formatter: v => v > 0 ? v : ''
        }
      }
    }
  });
}

function renderMiniPipelineChart(statuses) {
  const labels = statuses.map(s => STATUS_CONFIG[s.status]?.label || s.status);
  const values = statuses.map(s => s.count);
  const colors = statuses.map(s => STATUS_CONFIG[s.status]?.color || '#94a3b8');
  mkChart('chart-pipeline', {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors, borderRadius: 6 }]
    },
    options: {
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        datalabels: {
          color: '#0f172a',
          anchor: 'end',
          align: 'end',
          offset: 4,
          font: { weight: '800', size: 14 },
          formatter: v => v > 0 ? v : ''
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 13, weight: '600' }, color: '#475569' },
          grid: { color: '#f1f5f9' }
        },
        y: {
          ticks: { font: { size: 13, weight: '600' }, color: '#0f172a' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderTimelineChart(bids) {
  const grouped = {};
  bids.forEach(b => {
    if (!b.deadline) return;
    const d = b.deadline.substring(0, 10);
    grouped[d] = (grouped[d] || 0) + 1;
  });
  const labels = Object.keys(grouped).sort();
  mkChart('chart-timeline', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Bids Closing',
        data: labels.map(l => grouped[l]),
        backgroundColor: '#3b82f6',
        borderRadius: 6
      }]
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: {
          color: '#0f172a',
          anchor: 'end',
          align: 'top',
          offset: 4,
          font: { weight: '800', size: 14 },
          formatter: v => v > 0 ? v : ''
        }
      },
      scales: {
        x: {
          ticks: { font: { size: 13, weight: '600' }, color: '#334155' },
          grid: { display: false }
        },
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 13, weight: '600' }, color: '#475569' },
          grid: { color: '#e2e8f0' }
        }
      }
    }
  });
}

async function loadCharts() {
  const bids = await api('/api/bids?sort_by=bid_security_amount&sort_dir=desc&limit=500&show_expired=true').catch(() => []);
  renderSecurityBar(bids);
  renderDeadlineBarFull(bids);
  renderSecTypePie(bids);
}

function renderCategoryDonut(cats) {
  mkChart('chart-cat-donut', {
    type: 'doughnut',
    data: {
      labels: cats.map(c => c.category || '?'),
      datasets: [{ data: cats.map(c => c.count), backgroundColor: PALETTE, borderWidth: 2 }]
    },
    options: {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 13, weight: '600' }, boxWidth: 16, padding: 14, color: '#1e293b' }
        },
        datalabels: {
          color: '#ffffff',
          font: { weight: '800', size: 16 },
          textStrokeColor: 'rgba(0,0,0,0.6)',
          textStrokeWidth: 3,
          formatter: v => v > 0 ? v : ''
        }
      }
    }
  });
}

function renderSiteBar(sites) {
  mkChart('chart-site-bar', {
    type: 'bar',
    data: {
      labels: sites.map(s => s.site || '?'),
      datasets: [{ data: sites.map(s => s.count), backgroundColor: PALETTE, borderRadius: 6 }]
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: {
          color: '#0f172a',
          anchor: 'end',
          align: 'top',
          offset: 4,
          font: { weight: '800', size: 14 },
          formatter: v => v > 0 ? v : ''
        }
      },
      scales: {
        x: {
          ticks: { font: { size: 12, weight: '600' }, color: '#1e293b' },
          grid: { display: false }
        },
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 13, weight: '600' }, color: '#475569' },
          grid: { color: '#e2e8f0' }
        }
      }
    }
  });
}

function renderPipelineFull(statuses) {
  const labels = statuses.map(s => STATUS_CONFIG[s.status]?.label || s.status);
  const values = statuses.map(s => s.count);
  const colors = statuses.map(s => STATUS_CONFIG[s.status]?.color || '#94a3b8');
  mkChart('chart-pipeline-full', {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors, borderRadius: 6 }]
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: {
          color: '#0f172a',
          anchor: 'end',
          align: 'top',
          offset: 4,
          font: { weight: '800', size: 15 },
          formatter: v => v > 0 ? v : ''
        }
      },
      scales: {
        x: {
          ticks: { font: { size: 13, weight: '700' }, color: '#0f172a' },
          grid: { display: false }
        },
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 13, weight: '600' }, color: '#475569' },
          grid: { color: '#e2e8f0' }
        }
      }
    }
  });
}

function renderSecurityBar(bids) {
  const filtered = bids.filter(b => b.bid_security_amount > 0).slice(0, 15);
  mkChart('chart-security-bar', {
    type: 'bar',
    data: {
      labels: filtered.map(b => esc(b.title.substring(0, 32) + '…')),
      datasets: [{
        label: 'Security (ETB)',
        data: filtered.map(b => b.bid_security_amount),
        backgroundColor: '#ef4444',
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        datalabels: {
          color: '#0f172a',
          anchor: 'end',
          align: 'end',
          offset: 6,
          font: { weight: '800', size: 13 },
          formatter: v => v ? `${(v/1000).toLocaleString()}k ETB` : ''
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { font: { size: 13, weight: '600' }, color: '#475569' },
          grid: { color: '#e2e8f0' }
        },
        y: {
          ticks: { font: { size: 12, weight: '600' }, color: '#0f172a' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderDeadlineBarFull(bids) {
  const grouped = {};
  bids.forEach(b => {
    if (!b.deadline) return;
    const d = b.deadline.substring(0, 10);
    grouped[d] = (grouped[d] || 0) + 1;
  });
  const labels = Object.keys(grouped).sort();
  mkChart('chart-deadline-bar', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Bids Closing',
        data: labels.map(l => grouped[l]),
        backgroundColor: '#3b82f6',
        borderRadius: 6
      }]
    },
    options: {
      plugins: {
        legend: { display: false },
        datalabels: {
          color: '#0f172a',
          anchor: 'end',
          align: 'top',
          offset: 4,
          font: { weight: '800', size: 14 },
          formatter: v => v > 0 ? v : ''
        }
      },
      scales: {
        x: {
          ticks: { font: { size: 13, weight: '600' }, color: '#1e293b' },
          grid: { display: false }
        },
        y: {
          beginAtZero: true,
          ticks: { stepSize: 1, font: { size: 13, weight: '600' }, color: '#475569' },
          grid: { color: '#e2e8f0' }
        }
      }
    }
  });
}

function renderSecTypePie(bids) {
  const grouped = {};
  bids.forEach(b => {
    const t = b.bid_security_type || 'Unknown';
    grouped[t] = (grouped[t] || 0) + 1;
  });
  const labels = Object.keys(grouped);
  mkChart('chart-sectype', {
    type: 'pie',
    data: {
      labels,
      datasets: [{ data: labels.map(l => grouped[l]), backgroundColor: PALETTE, borderWidth: 2 }]
    },
    options: {
      plugins: {
        legend: {
          position: 'bottom',
          labels: { font: { size: 13, weight: '600' }, boxWidth: 16, padding: 14, color: '#1e293b' }
        },
        datalabels: {
          color: '#ffffff',
          font: { weight: '800', size: 16 },
          textStrokeColor: 'rgba(0,0,0,0.6)',
          textStrokeWidth: 3,
          formatter: v => v > 0 ? v : ''
        }
      }
    }
  });
}

// ── ACTIONS ───────────────────────────────────────────────────────────────────
async function crawlNow() {
  const btn = document.getElementById('crawl-now-btn');
  btn.disabled = true; btn.textContent = '⏳ Crawling…';
  showToast('Crawl started — may take a few minutes.', 'success');
  await api('/api/crawl/now', 'POST');
  setTimeout(async () => {
    await loadStats();
    if (currentPage === 'dashboard') await loadDashboard();
    if (currentPage === 'table')     await loadTable();
    btn.disabled = false; btn.textContent = '🔍 Crawl Now';
    document.getElementById('last-crawl-info').textContent = 'Last: just now';
    showToast('Crawl complete!', 'success');
  }, 18000);
}

async function checkLinksNow() {
  showToast('Link check started…', 'success');
  await api('/api/links/check', 'POST');
  setTimeout(() => { if (currentPage === 'table') loadTable(); showToast('Link check done.', 'success'); }, 12000);
}

async function deleteBid(id, btn) {
  if (!confirm('Delete this bid?')) return;
  await api(`/api/bids/${id}`, 'DELETE');
  btn.closest('tr').remove();
  allBids = allBids.filter(b => b.id !== id);
  document.getElementById('table-count').textContent = `${allBids.length} bids`;
  showToast('Bid deleted.', 'success');
  loadStats();
}

async function markAllRead() {
  await api('/api/bids/mark_all_read', 'POST');
  loadStats();
  if (currentPage === 'table') loadTable();
  showToast('All bids marked as read.', 'success');
}

function exportExcel() {
  const params = new URLSearchParams({
    search: document.getElementById('filter-search')?.value || '',
    category: document.getElementById('filter-category')?.value || '',
    site: document.getElementById('filter-site')?.value || '',
    app_status: document.getElementById('filter-appstatus')?.value || '',
    days: document.getElementById('filter-days')?.value || '0',
    show_expired: document.getElementById('filter-expired')?.checked ? 'true' : 'false',
    hide_dead_links: document.getElementById('filter-hide-dead')?.checked ? 'true' : 'false',
    sort_by: sortBy,
    sort_dir: sortDir,
  });

  showToast('Generating Excel spreadsheet…', 'info');
  const downloadUrl = `/api/bids/export/excel?${params.toString()}`;
  const a = document.createElement('a');
  a.href = downloadUrl;
  a.download = `bidscouter_garment_bids_${fmtDateShort(new Date())}.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => showToast('Excel file downloaded.', 'success'), 1200);
}

async function exportCSV() {
  const params = new URLSearchParams({
    search: document.getElementById('filter-search')?.value || '',
    category: document.getElementById('filter-category')?.value || '',
    site: document.getElementById('filter-site')?.value || '',
    app_status: document.getElementById('filter-appstatus')?.value || '',
    days: document.getElementById('filter-days')?.value || '0',
    show_expired: document.getElementById('filter-expired')?.checked ? 'true' : 'false',
    hide_dead_links: document.getElementById('filter-hide-dead')?.checked ? 'true' : 'false',
    sort_by: sortBy,
    sort_dir: sortDir,
    limit: 2000,
  });

  const bids = await api(`/api/bids?${params.toString()}`).catch(() => []);
  const headers = ['Title','Company','Category','Bid Number','Status','Deadline','Reg Fee (ETB)',
    'Security Type','Security Amount (ETB)','Location','Contact Phone','Contact Email',
    'Link Status','Source URL','Source Site','Notes','Required Documents'];
  const rows = bids.map(b => [
    b.title, b.company, b.category, b.bid_number,
    STATUS_CONFIG[b.application_status]?.label || b.application_status,
    b.deadline ? b.deadline.substring(0,16).replace('T', ' ') : '',
    b.registration_fee || '',
    b.bid_security_type, b.bid_security_amount || '',
    b.location, b.contact_phone, b.contact_email,
    b.link_status, b.source_url, b.source_site, b.application_notes,
    b.docs_summary || '11 Required Documents (CPO, Physical Sample, Legal Docs)'
  ].map(v => `"${String(v||'').replace(/"/g,'""')}"`));
  const csv = [headers.join(','), ...rows.map(r=>r.join(','))].join('\n');
  const blob = new Blob(['\uFEFF'+csv], {type:'text/csv;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href=url; a.download=`bidscouter_${fmtDateShort(new Date())}.csv`; a.click();
  showToast('CSV file downloaded.', 'success');
}

// ── SETTINGS ──────────────────────────────────────────────────────────────────
async function loadSettings() {
  try {
    settingsData = await api('/api/settings');
    const cfg = settingsData.crawler || {};
    const notif = settingsData.notifications || {};
    setVal('set-interval', cfg.interval_hours || 6);
    setVal('set-reminder', notif.reminder_hours_before || 30);
    setChk('set-notif-enabled', notif.enabled !== false);
    setChk('set-sound-enabled', notif.sound_enabled !== false);
    setVal('set-keywords', ((settingsData.keywords || {}).primary || []).join('\n'));
    renderCredentials(settingsData.credentials?.sites || []);
  } catch (e) { console.error(e); }
}

function renderCredentials(sites) {
  document.getElementById('credentials-list').innerHTML = sites.map((s, i) => `
    <div class="cred-card" data-idx="${i}">
      <h4>${esc(s.name)}</h4>
      <div class="cred-toggle"><input type="checkbox" id="ce-${i}" ${s.enabled?'checked':''}/> Enabled</div>
      <div class="cred-field"><label>URL</label><input type="text" id="cu-${i}" value="${esc(s.url||'')}"/></div>
      <div class="cred-field"><label>Username / Email</label><input type="text" id="cn-${i}" value="${esc(s.username||'')}" autocomplete="off"/></div>
      <div class="cred-field"><label>Password</label><input type="password" id="cp-${i}" value="${esc(s.password||'')}" autocomplete="new-password"/></div>
    </div>
  `).join('');
}

async function saveGeneralSettings() {
  await api('/api/settings', 'PUT', {
    crawler: { interval_hours: parseInt(getVal('set-interval')) },
    notifications: {
      enabled: getChk('set-notif-enabled'),
      sound_enabled: getChk('set-sound-enabled'),
      reminder_hours_before: parseInt(getVal('set-reminder')),
    }
  });
  showToast('Settings saved!', 'success');
}

async function saveKeywords() {
  const lines = getVal('set-keywords').split('\n').map(l=>l.trim()).filter(Boolean);
  await api('/api/settings', 'PUT', { keywords: { primary: lines } });
  showToast('Keywords saved!', 'success');
}

async function saveCredentials() {
  const sites = settingsData.credentials?.sites || [];
  const updated = sites.map((s, i) => ({
    ...s,
    enabled: document.getElementById(`ce-${i}`)?.checked,
    url: document.getElementById(`cu-${i}`)?.value || s.url,
    username: document.getElementById(`cn-${i}`)?.value || '',
    password: document.getElementById(`cp-${i}`)?.value || '',
  }));
  await api('/api/settings', 'PUT', { credentials: { sites: updated } });
  showToast('Credentials saved!', 'success');
}

async function loadCrawlLogs() {
  try {
    const logs = await api('/api/crawl/logs?limit=40');
    const el = document.getElementById('crawl-logs');
    if (!logs.length) { el.innerHTML = '<p class="empty-msg">No crawl runs yet.</p>'; return; }
    el.innerHTML = logs.map(l => `
      <div class="log-row">
        <span><strong>${esc(l.site_name)}</strong></span>
        <span class="log-${l.status}">${l.status.toUpperCase()}</span>
        <span>${l.new_bids||0} new / ${l.bids_found||0} found</span>
        <span style="color:#999">${l.started_at ? new Date(l.started_at).toLocaleString() : '—'}</span>
        ${l.error_message ? `<span style="color:var(--danger);font-size:10px">${esc(l.error_message.substring(0,60))}</span>` : ''}
      </div>
    `).join('');
    const last = logs.find(l => l.status==='success');
    if (last) document.getElementById('last-crawl-info').textContent = `Last: ${new Date(last.started_at).toLocaleTimeString()}`;
  } catch (e) {}
}

async function populateSiteFilter() {
  try {
    const data = await api('/api/settings');
    const sel = document.getElementById('filter-site');
    (data.credentials?.sites || []).forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id; opt.textContent = s.name; sel.appendChild(opt);
    });
  } catch (e) {}
}

// ── HELPERS ───────────────────────────────────────────────────────────────────
async function api(path, method='GET', body=null) {
  const opts = { method, headers: {} };
  if (body) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const r = await fetch(API + path, opts);
  if (!r.ok) throw new Error(`API ${path}: ${r.status}`);
  return r.json();
}

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function fmtMoney(v, cur='ETB') {
  return `${cur} ${Number(v).toLocaleString('en-US',{minimumFractionDigits:0})}`;
}

function fmtDeadline(dl) {
  if (!dl) return '—';
  const d = new Date(dl), now = new Date();
  const h = (d - now) / 3600000;
  const fmt = d.toLocaleDateString('en-ET',{day:'2-digit',month:'short',year:'numeric'}) + ' ' +
               d.toLocaleTimeString('en-ET',{hour:'2-digit',minute:'2-digit'});
  if (h < 0)  return `⛔ ${fmt}`;
  if (h < 30) return `⚠ ${Math.round(h)}h — ${fmt}`;
  if (h < 72) return `🟡 ${Math.round(h/24)}d — ${fmt}`;
  return `✅ ${fmt}`;
}

function fmtDeadlineShort(dl) {
  if (!dl) return '—';
  const d = new Date(dl), now = new Date();
  const h = (d-now)/3600000;
  if (h < 0)  return 'Expired';
  if (h < 30) return `${Math.round(h)}h left`;
  return d.toLocaleDateString('en-ET',{day:'2-digit',month:'short'});
}

function deadlineClass(dl) {
  if (!dl) return '';
  const h = (new Date(dl) - new Date()) / 3600000;
  if (h < 0)  return 'dl-expired';
  if (h < 30) return 'dl-urgent';
  if (h < 72) return 'dl-soon';
  return 'dl-ok';
}

function secClass(t) {
  if (!t) return 'sec-other';
  const l = t.toLowerCase();
  if (l.includes('bank')) return 'sec-bank';
  if (l.includes('cpo'))  return 'sec-cpo';
  if (l.includes('cash')) return 'sec-cash';
  return 'sec-other';
}

function fmtDate(s) { return s ? new Date(s).toLocaleDateString('en-ET',{day:'2-digit',month:'short',year:'numeric'}) : '—'; }
function fmtDateShort(d) { return d.toISOString().substring(0,10); }

function set(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function setVal(id, v) { const el = document.getElementById(id); if (el) el.value = v; }
function getVal(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function setChk(id, v) { const el = document.getElementById(id); if (el) el.checked = v; }
function getChk(id) { const el = document.getElementById(id); return el ? el.checked : false; }

function debounce(fn, ms) {
  return (...args) => {
    clearTimeout(_debounceTimer);
    _debounceTimer = setTimeout(() => fn(...args), ms);
  };
}

function showToast(msg, type='info') {
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${type==='success'?'✅':type==='error'?'❌':type==='warning'?'⚠':'ℹ'}</span><span>${esc(msg)}</span>`;
  c.appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

if ('Notification' in window) Notification.requestPermission();
