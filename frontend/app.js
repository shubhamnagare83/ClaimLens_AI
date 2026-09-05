/* ═══════════════════════════════════════════════
   ClaimLens AI — Frontend Application
   PS02 Insurance Claims Evidence Review Assistant
   ═══════════════════════════════════════════════ */

// ── State ──
let allClaims = [];
let currentFilter = 'all';
let searchQuery = '';
let currentClaimId = null;
let currentNav = 'dashboard';
let previousNav = 'dashboard';
let outcomesChart = null;
let typesChart = null;
let vehiclesChart = null;
let insightsOutcomesChart = null;
let latestStats = {};

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
    checkGeminiStatus();
    loadDashboard();
    initBannerCarousel();
    initAssistant();
});


// Close demo dropdown on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.demo-dropdown')) {
        document.getElementById('demo-menu')?.classList.remove('show');
    }
});

// ── API Helpers ──
async function api(url, options = {}) {
    try {
        const resp = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        return await resp.json();
    } catch (e) {
        console.error('API Error:', e);
        throw e;
    }
}

function showLoading(text = 'Processing evidence...') {
    const el = document.getElementById('loading-overlay');
    if (el) {
        document.getElementById('loading-text').textContent = text;
        el.style.display = 'flex';
    }
}

function hideLoading() {
    const el = document.getElementById('loading-overlay');
    if (el) el.style.display = 'none';
}

function toast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => el.remove(), 4000);
}

// ── Gemini & System Status ──
async function checkGeminiStatus() {
    try {
        const data = await api('/health');
        const badge = document.getElementById('gemini-status');
        if (!badge) return;
        if (data.gemini === 'configured') {
            badge.className = 'status-badge connected';
            badge.querySelector('.status-text').textContent = 'Gemini AI Active';
        } else {
            badge.className = 'status-badge disconnected';
            badge.querySelector('.status-text').textContent = 'Deterministic Mode';
        }
    } catch {
        const badge = document.getElementById('gemini-status');
        if (badge) {
            badge.className = 'status-badge disconnected';
            badge.querySelector('.status-text').textContent = 'Offline';
        }
    }
}

// ── Navigation Switching ──
function switchNav(navId) {
    if (currentNav !== 'detail') {
        previousNav = currentNav;
    }
    currentNav = navId;

    // Update sidebar buttons
    ['dashboard', 'claims', 'insights', 'ml', 'doc-studio', 'assistant'].forEach(id => {
        const btn = document.getElementById(`nav-${id}`);
        if (btn) btn.classList.toggle('active', id === navId);
    });

    // Update view visibility
    document.getElementById('view-dashboard').style.display = navId === 'dashboard' ? '' : 'none';
    document.getElementById('view-claims').style.display = navId === 'claims' ? '' : 'none';
    document.getElementById('view-insights').style.display = navId === 'insights' ? '' : 'none';
    const mlView = document.getElementById('view-ml');
    if (mlView) mlView.style.display = navId === 'ml' ? '' : 'none';
    const studioView = document.getElementById('view-doc-studio');
    if (studioView) studioView.style.display = navId === 'doc-studio' ? '' : 'none';
    const assistantView = document.getElementById('view-assistant');
    if (assistantView) assistantView.style.display = navId === 'assistant' ? '' : 'none';
    document.getElementById('view-detail').style.display = navId === 'detail' ? '' : 'none';

    // Update header title and subtitle
    const titles = {
        'dashboard': {
            title: 'Dashboard Overview',
            sub: 'Monitor claims, evidence scores, and investigation queues'
        },
        'claims': {
            title: 'Claims Investigation Master',
            sub: 'Search, filter, and inspect claims across vehicles, accidents, and theft'
        },
        'insights': {
            title: 'Investigation Insights & Analytics',
            sub: 'Portfolio analytics, policy rule compliance, and risk distribution'
        },
        'ml': {
            title: 'Kaggle ML Risk Engine & Fraud Analytics',
            sub: 'LightGBM model (91.4% Accuracy) trained on 508,499 real-world vehicle insurance records'
        },
        'doc-studio': {
            title: 'PDF & Document AI Studio (Real-World Evidence Extractor)',
            sub: 'Multi-engine PDF layout parser, document type auto-classification, and entity extraction'
        },
        'assistant': {
            title: 'ClaimLens AI Copilot (Evidence & Policy Assistant)',
            sub: 'Ground-truth evidence cross-referencing, contradiction detection, and policy reasoning'
        },
        'detail': {
            title: `Claim Investigation: ${currentClaimId || ''}`,
            sub: 'Evidence grounding, contradiction detection, and policy citations'
        }
    };

    const info = titles[navId] || titles['dashboard'];
    document.getElementById('view-title').textContent = info.title;
    document.getElementById('view-subtitle').textContent = info.sub;

    // Render respective views
    if (navId === 'claims') {
        renderClaimsTable();
    } else if (navId === 'insights') {
        renderInsights(latestStats);
    } else if (navId === 'ml') {
        loadMLMetrics();
    } else if (navId === 'doc-studio') {
        loadDocStudio();
    } else if (navId === 'assistant') {
        loadAssistantView();
    } else if (navId === 'dashboard') {
        renderDashboardView();
    }

    // Close mobile sidebar if open
    const sidebar = document.getElementById('sidebar');

    if (sidebar) sidebar.classList.remove('open');
}

function showDashboard() {
    switchNav('dashboard');
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

function goBackFromDetail() {
    switchNav(previousNav || 'dashboard');
}

// ── Data Loading ──
async function loadDashboard() {
    try {
        const [claimsData, stats] = await Promise.all([
            api('/api/claims'),
            api('/api/dashboard'),
        ]);
        allClaims = claimsData.claims || [];
        latestStats = stats || {};

        renderStats(latestStats);
        renderPriorityClaims(allClaims);
        renderCharts(latestStats);
        renderClaimsTable();
        updateFilterCounts();
    } catch (e) {
        toast('Failed to load dashboard data: ' + e.message, 'error');
    }
}

// ── Search Handling ──
function handleSearch(query) {
    searchQuery = (query || '').trim().toLowerCase();
    const clearBtn = document.getElementById('search-clear-btn');
    const badge = document.getElementById('search-match-badge');

    if (searchQuery) {
        if (clearBtn) clearBtn.style.display = 'block';

        const matches = getFilteredClaims();
        if (badge) {
            badge.textContent = `${matches.length} matching claim${matches.length === 1 ? '' : 's'}`;
            badge.style.display = 'flex';
        }

        // Automatically show Claims view so user sees search results instantly
        if (currentNav !== 'claims' && currentNav !== 'detail') {
            switchNav('claims');
        } else {
            renderClaimsTable();
        }
    } else {
        if (clearBtn) clearBtn.style.display = 'none';
        if (badge) badge.style.display = 'none';
        renderClaimsTable();
    }
}

function clearSearch() {
    searchQuery = '';
    const input = document.getElementById('sidebar-search-input');
    if (input) input.value = '';
    const clearBtn = document.getElementById('search-clear-btn');
    if (clearBtn) clearBtn.style.display = 'none';
    const badge = document.getElementById('search-match-badge');
    if (badge) badge.style.display = 'none';
    renderClaimsTable();
}

// ── Filtering Logic ──
function getFilteredClaims() {
    let list = allClaims;

    // Apply quick filter or table filter
    if (currentFilter !== 'all') {
        if (['Accident', 'Theft'].includes(currentFilter)) {
            list = list.filter(c => c.incident_type === currentFilter);
        } else {
            list = list.filter(c => c.status === currentFilter);
        }
    }

    // Apply real-time search across Customer Name, Vehicle Reg, Claim ID, Policy Number, etc.
    if (searchQuery) {
        list = list.filter(c => {
            const name = (c.customer_name || '').toLowerCase();
            const reg = (c.vehicle_registration || '').toLowerCase();
            const id = (c.claim_id || '').toLowerCase();
            const policy = (c.policy_number || '').toLowerCase();
            const loc = (c.incident_location || '').toLowerCase();
            const vtype = (c.vehicle_type || '').toLowerCase();

            return name.includes(searchQuery) ||
                   reg.includes(searchQuery) ||
                   id.includes(searchQuery) ||
                   policy.includes(searchQuery) ||
                   loc.includes(searchQuery) ||
                   vtype.includes(searchQuery);
        });
    }

    return list;
}

function filterClaims(filter) {
    currentFilter = filter;

    // Update filter chips in Claims view
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-filter') === filter);
    });

    // Update sidebar quick filter links
    document.querySelectorAll('.filter-link').forEach(link => {
        link.classList.toggle('active', link.getAttribute('data-filter') === filter);
    });

    renderClaimsTable();
}

function applyQuickFilter(filter) {
    currentFilter = filter;
    switchNav('claims');
    filterClaims(filter);
}

function updateFilterCounts() {
    const counts = {
        all: allClaims.length,
        accident: allClaims.filter(c => c.incident_type === 'Accident').length,
        theft: allClaims.filter(c => c.incident_type === 'Theft').length,
        pending: allClaims.filter(c => c.status === 'PENDING').length,
        escalate: allClaims.filter(c => c.status === 'ESCALATE').length,
        request: allClaims.filter(c => c.status === 'REQUEST_INFORMATION').length,
    };

    const countAllEl = document.getElementById('count-all');
    if (countAllEl) countAllEl.textContent = counts.all;
    const countAccEl = document.getElementById('count-accident');
    if (countAccEl) countAccEl.textContent = counts.accident;
    const countTheftEl = document.getElementById('count-theft');
    if (countTheftEl) countTheftEl.textContent = counts.theft;
    const countPendEl = document.getElementById('count-pending');
    if (countPendEl) countPendEl.textContent = counts.pending;
    const countEscEl = document.getElementById('count-escalate');
    if (countEscEl) countEscEl.textContent = counts.escalate;
    const countReqEl = document.getElementById('count-request');
    if (countReqEl) countReqEl.textContent = counts.request;

    const navBadge = document.getElementById('nav-claims-count');
    if (navBadge) navBadge.textContent = counts.all;
}

// ── Render Stats & Dashboard ──
function renderStats(stats) {
    const grid = document.getElementById('stats-grid');
    if (!grid) return;
    grid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${stats.total_claims || 0}</div>
            <div class="stat-label">Total Claims</div>
        </div>
        <div class="stat-card purple">
            <div class="stat-value">${stats.pending || 0}</div>
            <div class="stat-label">Pending Review</div>
        </div>
        <div class="stat-card green">
            <div class="stat-value">${stats.approved || 0}</div>
            <div class="stat-label">Approved</div>
        </div>
        <div class="stat-card red">
            <div class="stat-value">${stats.rejected || 0}</div>
            <div class="stat-label">Rejected</div>
        </div>
        <div class="stat-card blue">
            <div class="stat-value">${stats.request_info || 0}</div>
            <div class="stat-label">Info Needed</div>
        </div>
        <div class="stat-card amber">
            <div class="stat-value">${stats.escalated || 0}</div>
            <div class="stat-label">Escalated</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.avg_evidence_score || '—'}</div>
            <div class="stat-label">Avg Evidence Score</div>
        </div>
    `;
}

function renderPriorityClaims(claims) {
    const tbody = document.getElementById('priority-claims-tbody');
    if (!tbody) return;

    // Filter to prioritized claims: ESCALATE, REQUEST_INFORMATION, or PENDING
    const priority = claims.filter(c => ['ESCALATE', 'REQUEST_INFORMATION', 'PENDING'].includes(c.status)).slice(0, 8);

    if (priority.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-muted)">No priority claims pending investigation.</td></tr>`;
        return;
    }

    tbody.innerHTML = priority.map(c => `
        <tr>
            <td><strong style="color:var(--accent)">${c.claim_id}</strong></td>
            <td>${c.customer_name}</td>
            <td>
                <span style="color:var(--text-primary);font-weight:500;">${c.vehicle_registration}</span>
                <br><span style="font-size:0.75rem;color:var(--text-muted)">${c.vehicle_type}</span>
            </td>
            <td><span class="tag tag-${c.incident_type?.toLowerCase()}">${c.incident_type}</span></td>
            <td>${c.incident_date}</td>
            <td>${statusTag(c.status)}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewClaim('${c.claim_id}')">View</button>
                ${c.status === 'PENDING' ? `<button class="btn btn-sm btn-primary" onclick="runReview('${c.claim_id}')">Review</button>` : ''}
            </td>
        </tr>
    `).join('');
}

function renderDashboardView() {
    renderPriorityClaims(allClaims);
    renderCharts(latestStats);
}

// ── Render Claims Table View ──
function renderClaimsTable() {
    const tbody = document.getElementById('claims-tbody');
    const empty = document.getElementById('empty-state');
    const counter = document.getElementById('claims-counter-text');
    const activeSearchBar = document.getElementById('active-search-bar');
    const activeSearchTerm = document.getElementById('active-search-term');

    if (!tbody) return;

    const filtered = getFilteredClaims();

    // Update active search indicator
    if (activeSearchBar && activeSearchTerm) {
        if (searchQuery) {
            activeSearchTerm.textContent = `"${searchQuery}"`;
            activeSearchBar.style.display = 'flex';
        } else {
            activeSearchBar.style.display = 'none';
        }
    }

    // Update count text
    if (counter) {
        counter.textContent = `Showing ${filtered.length} of ${allClaims.length} claims`;
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '';
        if (empty) {
            empty.style.display = '';
            const msg = document.getElementById('empty-state-message');
            if (msg) {
                msg.textContent = searchQuery
                    ? `No claims matched "${searchQuery}". Check the vehicle registration number or name.`
                    : 'No claims found in this category.';
            }
        }
        return;
    }

    if (empty) empty.style.display = 'none';

    tbody.innerHTML = filtered.map(c => `
        <tr>
            <td><strong style="color:var(--accent)">${c.claim_id}</strong></td>
            <td>
                <span style="font-weight:600;color:var(--text-primary);">${c.customer_name}</span>
                <br><span style="font-size:0.75rem;color:var(--text-muted)">${c.policy_number}</span>
            </td>
            <td>
                <span style="color:var(--text-primary);font-weight:500;">${c.vehicle_registration}</span>
                <br><span style="font-size:0.75rem;color:var(--text-muted)">${c.vehicle_type}</span>
            </td>
            <td><span class="tag tag-${c.incident_type?.toLowerCase()}">${c.incident_type}</span></td>
            <td>${c.incident_date}</td>
            <td>${statusTag(c.status)}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="viewClaim('${c.claim_id}')">View</button>
                ${c.status === 'PENDING' ? `<button class="btn btn-sm btn-primary" onclick="runReview('${c.claim_id}')">Review</button>` : ''}
            </td>
        </tr>
    `).join('');
}

function statusTag(status) {
    const map = {
        'APPROVE': 'approve', 'REJECT': 'reject', 'ESCALATE': 'escalate',
        'REQUEST_INFORMATION': 'request', 'PENDING': 'pending',
    };
    const label = status === 'REQUEST_INFORMATION' ? 'INFO NEEDED' : status;
    return `<span class="tag tag-${map[status] || 'pending'}">${label || 'PENDING'}</span>`;
}

// ── Charts Rendering ──
function renderCharts(stats) {
    const outcomesCtx = document.getElementById('chart-outcomes');
    const typesCtx = document.getElementById('chart-types');

    if (!outcomesCtx || !typesCtx) return;

    if (outcomesChart) outcomesChart.destroy();
    if (typesChart) typesChart.destroy();

    const chartColors = {
        bg: ['rgba(22,163,74,0.75)', 'rgba(220,38,38,0.75)', 'rgba(37,99,235,0.75)', 'rgba(217,119,6,0.75)', 'rgba(147,51,234,0.75)'],
        border: ['#16a34a', '#dc2626', '#2563eb', '#d97706', '#9333ea'],
    };

    outcomesChart = new Chart(outcomesCtx, {
        type: 'doughnut',
        data: {
            labels: ['Approved', 'Rejected', 'Info Needed', 'Escalated', 'Pending'],
            datasets: [{
                data: [stats.approved || 0, stats.rejected || 0, stats.request_info || 0, stats.escalated || 0, stats.pending || 0],
                backgroundColor: chartColors.bg,
                borderColor: chartColors.border,
                borderWidth: 1,
            }],
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#475569', font: { size: 11 } }
                }
            },
            cutout: '65%',
        },
    });

    const typeLabels = Object.keys(stats.by_incident_type || {});
    const typeData = Object.values(stats.by_incident_type || {});

    typesChart = new Chart(typesCtx, {
        type: 'bar',
        data: {
            labels: typeLabels,
            datasets: [{
                label: 'Claims',
                data: typeData,
                backgroundColor: ['rgba(220,38,38,0.7)', 'rgba(217,119,6,0.7)'],
                borderColor: ['#dc2626', '#d97706'],
                borderWidth: 1,
                borderRadius: 6,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(226, 232, 240, 0.9)' } },
                y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(226, 232, 240, 0.9)' }, beginAtZero: true },
            },
        },
    });
}

// ── Render Insights View ──
function renderInsights(stats) {
    const kpiGrid = document.getElementById('insights-kpi-grid');
    if (!kpiGrid) return;

    const totalClaims = stats.total_claims || 1;
    const escalationRate = Math.round(((stats.escalated || 0) / totalClaims) * 100);
    const totEst = (stats.total_repair_estimates || 0).toLocaleString('en-IN');
    const totIdv = (stats.total_idv || 0).toLocaleString('en-IN');

    kpiGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">₹${totIdv}</div>
            <div class="stat-label">Total Insured Portfolio (IDV)</div>
        </div>
        <div class="stat-card amber">
            <div class="stat-value">₹${totEst}</div>
            <div class="stat-label">Repair Estimates Claimed</div>
        </div>
        <div class="stat-card red">
            <div class="stat-value">${escalationRate}%</div>
            <div class="stat-label">Escalation & Contradiction Rate</div>
        </div>
        <div class="stat-card green">
            <div class="stat-value">${stats.avg_evidence_score || 92} / 100</div>
            <div class="stat-label">Evidence Grounding Score</div>
        </div>
    `;

    // Render Insights Charts
    const vehCtx = document.getElementById('chart-vehicles');
    const insOutcomesCtx = document.getElementById('chart-insights-outcomes');

    if (vehCtx) {
        if (vehiclesChart) vehiclesChart.destroy();
        const vehLabels = Object.keys(stats.by_vehicle_type || { 'Car': 40, 'Two-Wheeler': 40 });
        const vehData = Object.values(stats.by_vehicle_type || { 'Car': 40, 'Two-Wheeler': 40 });

        vehiclesChart = new Chart(vehCtx, {
            type: 'pie',
            data: {
                labels: vehLabels,
                datasets: [{
                    data: vehData,
                    backgroundColor: ['rgba(79, 70, 229, 0.75)', 'rgba(8, 145, 178, 0.75)'],
                    borderColor: ['#4f46e5', '#0891b2'],
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#475569', font: { size: 11 } }
                    }
                }
            }
        });
    }

    if (insOutcomesCtx) {
        if (insightsOutcomesChart) insightsOutcomesChart.destroy();
        insightsOutcomesChart = new Chart(insOutcomesCtx, {
            type: 'bar',
            data: {
                labels: ['Approved', 'Rejected', 'Info Needed', 'Escalated', 'Pending'],
                datasets: [{
                    label: 'Cases',
                    data: [stats.approved || 0, stats.rejected || 0, stats.request_info || 0, stats.escalated || 0, stats.pending || 0],
                    backgroundColor: ['rgba(22,163,74,0.75)', 'rgba(220,38,38,0.75)', 'rgba(37,99,235,0.75)', 'rgba(217,119,6,0.75)', 'rgba(147,51,234,0.75)'],
                    borderColor: ['#16a34a', '#dc2626', '#2563eb', '#d97706', '#9333ea'],
                    borderWidth: 1,
                    borderRadius: 6,
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(226, 232, 240, 0.9)' } },
                    y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(226, 232, 240, 0.9)' }, beginAtZero: true },
                }
            }
        });
    }
}

// ── Demo Loading ──
function toggleDemoMenu() {
    document.getElementById('demo-menu')?.classList.toggle('show');
}

async function loadDemo(scenarioKey) {
    document.getElementById('demo-menu')?.classList.remove('show');
    showLoading(`Loading demo: ${scenarioKey.replace(/_/g, ' ')}...`);
    try {
        const result = await api(`/api/demo/${scenarioKey}`);
        hideLoading();
        toast(`Loaded claim ${result.claim_id}: ${result.scenario_description}`, 'success');
        await loadDashboard();
        viewClaim(result.claim_id);
    } catch (e) {
        hideLoading();
        toast('Failed to load demo: ' + e.message, 'error');
    }
}

// ── Claim Review Execution ──
async function runReview(claimId) {
    showLoading(`Running AI Evidence Review for ${claimId}...`);
    try {
        const report = await api(`/api/claims/${claimId}/review`, { method: 'POST' });
        hideLoading();
        toast(`Review completed: ${report.recommendation}`, 'success');
        await loadDashboard();
        viewClaim(claimId);
    } catch (e) {
        hideLoading();
        toast('Review failed: ' + e.message, 'error');
    }
}

// ── Claim Detail View Rendering ──
async function viewClaim(claimId) {
    currentClaimId = claimId;
    showLoading(`Loading evidence for ${claimId}...`);
    try {
        const [detail, review, mlPred] = await Promise.all([
            api(`/api/claims/${claimId}`),
            api(`/api/claims/${claimId}/review-latest`).catch(() => null),
            api(`/api/ml/claim-prediction/${claimId}`).catch(() => null),
        ]);
        hideLoading();

        const claim = detail.claim;
        const report = review?.report_json || {};
        const docs = detail.documents || [];

        switchNav('detail');

        const content = document.getElementById('detail-content');
        const rec = report.recommendation || claim.status || 'PENDING';
        const conf = report.confidence || 'LOW';
        const score = report.evidence_score || 0;
        const scoreClass = score >= 75 ? 'high' : score >= 50 ? 'medium' : 'low';

        let html = '';

        // Header Card
        html += `
        <div class="detail-header">
            <div class="detail-header-top">
                <div>
                    <div class="detail-claim-id">${claim.claim_id}</div>
                    <div class="detail-meta">
                        <span class="detail-meta-item"><span class="tag tag-${claim.incident_type?.toLowerCase()}">${claim.incident_type}</span></span>
                        <span class="detail-meta-item"><strong>${claim.vehicle_type}</strong> &bull; ${claim.vehicle_registration}</span>
                        <span class="detail-meta-item">${claim.customer_name}</span>
                        <span class="detail-meta-item">Policy: ${claim.policy_number}</span>
                    </div>
                </div>
                <div class="detail-recommendation ${rec}">
                    <div class="rec-label">Recommendation</div>
                    <div class="rec-value ${rec}">${rec === 'REQUEST_INFORMATION' ? 'REQUEST INFO' : rec}</div>
                    <div class="rec-sub">Confidence: ${conf} ${rec !== 'APPROVE' ? '&bull; Human Review Required' : ''}</div>
                </div>
            </div>
            ${review ? '' : `<div style="margin-top:16px"><button class="btn btn-primary" onclick="runReview('${claimId}')">Run Evidence Review</button></div>`}
        </div>`;

        // ML Risk Assessment Card (Kaggle Model)
        if (mlPred) {
            const pColor = mlPred.risk_score >= 70 ? 'var(--red)' : (mlPred.risk_score >= 40 ? 'var(--amber)' : 'var(--green)');
            html += `
            <div class="evidence-score-card" style="margin-bottom:16px; border-left: 4px solid ${pColor};">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="background:var(--accent); color:#fff; font-size:0.72rem; font-weight:700; padding:2px 8px; border-radius:12px;">ML RISK ENGINE</span>
                        <span style="font-weight:700; color:var(--text-primary);">Kaggle LightGBM Model Assessment (91.4% Accuracy)</span>
                    </div>
                    <span class="tag" style="background:${pColor}1a; color:${pColor}; font-weight:700;">${mlPred.risk_level} (${mlPred.risk_score}/100)</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:10px; font-size:0.83rem;">
                    <div><span style="color:var(--text-muted);">Historical Median Payout:</span><br><strong style="font-size:0.92rem;">₹${mlPred.benchmark_payout?.toLocaleString()}</strong></div>
                    <div><span style="color:var(--text-muted);">Claim vs Benchmark:</span><br><strong style="font-size:0.92rem;">${mlPred.overclaim_ratio}x Median</strong></div>
                    <div><span style="color:var(--text-muted);">Claim Probability:</span><br><strong style="font-size:0.92rem;">${mlPred.claim_probability}%</strong></div>
                    <div><span style="color:var(--text-muted);">Recommended Action:</span><br><strong style="color:${pColor}; font-size:0.88rem;">${mlPred.recommendation}</strong></div>
                </div>
                ${mlPred.anomalies && mlPred.anomalies.length > 0 ? `
                    <div style="margin-top:10px; padding-top:8px; border-top:1px dashed var(--border);">
                        ${mlPred.anomalies.map(a => `
                            <div style="font-size:0.8rem; color:${a.severity === 'HIGH' ? 'var(--red)' : 'var(--amber)'}; margin-top:3px;">
                                ⚠️ <strong>${a.type.replace(/_/g, ' ')}:</strong> ${a.description}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>`;
        }

        // Evidence Consistency Score Gauge
        if (review) {
            const breakdown = report.evidence_score_breakdown || {};
            html += `
            <div class="evidence-score-card">
                <h3 style="margin-bottom:16px;font-size:0.9rem;font-weight:600;">Evidence Consistency Score</h3>
                <div class="score-gauge">
                    <div class="score-circle ${scoreClass}">${Math.round(score)}</div>
                    <div class="score-breakdown">
                        ${Object.entries(breakdown).map(([k, v]) => `
                            <div class="breakdown-item">
                                <span class="breakdown-label">${k.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                                <div class="breakdown-bar-bg"><div class="breakdown-bar" style="width:${v}%;background:${v >= 75 ? 'var(--green)' : v >= 50 ? 'var(--amber)' : 'var(--red)'}"></div></div>
                                <span class="breakdown-val">${Math.round(v)}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>`;
        }

        // Section Container
        html += `<div class="detail-sections">`;

        // Why This Recommendation?
        if (report.explanation) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Why this Recommendation?</h3>
                    <span class="section-chevron open">&#9662;</span>
                </div>
                <div class="section-body open">
                    <div class="explanation-box">${report.explanation}</div>
                </div>
            </div>`;
        }

        // Documents Viewer
        html += `
        <div class="detail-section">
            <div class="section-header" onclick="toggleSection(this)">
                <div style="display:flex; justify-content:space-between; align-items:center; width:100%; padding-right:12px;">
                    <h3>Claim Evidence Documents <span class="count">${docs.length}</span></h3>
                    <button type="button" class="btn btn-sm btn-primary" onclick="event.stopPropagation(); openUploadDocModal('${claimId}')">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                        Upload & Scan PDF
                    </button>
                </div>
                <span class="section-chevron open">&#9662;</span>
            </div>
            <div class="section-body open">
                ${docs.length === 0 ? `
                    <div style="padding:20px; text-align:center; color:var(--text-muted);">
                        <p>No documents uploaded yet for this claim.</p>
                        <button class="btn btn-primary btn-sm" onclick="openUploadDocModal('${claimId}')" style="margin-top:10px;">+ Upload Claim Form / Estimate / FIR PDF</button>
                    </div>
                ` : `
                <div class="doc-tab-bar">
                        ${docs.map((d, i) => `
                            <button class="doc-tab ${i === 0 ? 'active' : ''}" onclick="switchDocTab(this, 'doc-${i}')">
                                ${d.document_type.replace(/_/g, ' ')}
                            </button>
                        `).join('')}
                    </div>
                    ${docs.map((d, i) => `
                        <div id="doc-${i}" class="doc-viewer" style="${i > 0 ? 'display:none;' : ''}">
                            <pre>${escapeHtml(d.content || '')}</pre>
                        </div>
                    `).join('')}
                </div>`}
            </div>`;


        // Extracted Facts
        const facts = report.facts || {};
        const factKeys = Object.keys(facts);
        if (factKeys.length > 0) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Extracted Facts <span class="count">${factKeys.length}</span></h3>
                    <span class="section-chevron">&#9662;</span>
                </div>
                <div class="section-body">
                    <table class="matrix-table">
                        <thead><tr><th>Field</th><th>Value</th><th>Source Document</th><th>Confidence</th></tr></thead>
                        <tbody>
                            ${factKeys.map(k => {
                                const f = facts[k];
                                return `<tr>
                                    <td><strong>${f.field_name || k}</strong></td>
                                    <td>${f.field_value || '—'}</td>
                                    <td>${f.source_document || '—'}</td>
                                    <td>${f.confidence ? Math.round(f.confidence * 100) + '%' : '—'}</td>
                                </tr>`;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>`;
        }

        // Contradictions
        const contradictions = report.contradictions || [];
        if (contradictions.length > 0) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3 style="color:var(--red)">Contradictions Detected <span class="count" style="background:var(--red-bg);color:var(--red)">${contradictions.length}</span></h3>
                    <span class="section-chevron open">&#9662;</span>
                </div>
                <div class="section-body open">
                    ${contradictions.map(c => `
                        <div class="contradiction-card">
                            <span class="contradiction-severity ${c.severity || 'HIGH'}">${c.severity || 'HIGH'} SEVERITY</span>
                            <strong>${c.field_name}</strong>
                            <div class="contradiction-values">
                                ${Object.entries(c.values || {}).map(([doc, val]) => `
                                    <div class="contradiction-value">
                                        <span class="contradiction-source">${doc.replace(/_/g, ' ')}:</span>
                                        <span class="contradiction-val">${val}</span>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="contradiction-impact"><strong>Impact:</strong> ${c.impact || ''}</div>
                            <div class="contradiction-action"><strong>Recommended Action:</strong> ${c.action || ''}</div>
                        </div>
                    `).join('')}
                </div>
            </div>`;
        }

        // Policy Findings
        const findings = report.policy_findings || [];
        if (findings.length > 0) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Policy Rules & Citations <span class="count">${findings.length}</span></h3>
                    <span class="section-chevron open">&#9662;</span>
                </div>
                <div class="section-body open">
                    ${findings.map(f => `
                        <div class="finding-card ${f.status?.toLowerCase()}">
                            <div class="finding-header">
                                <span class="finding-clause">${f.clause_id}</span>
                                <span class="tag tag-${f.status === 'PASS' ? 'approve' : f.status === 'FAIL' ? 'reject' : 'escalate'}">${f.status}</span>
                            </div>
                            <div class="finding-title">${f.rule_title}</div>
                            <div class="finding-rule">${f.rule_text}</div>
                            ${f.evidence_found ? `<div class="finding-evidence"><strong>Evidence:</strong> ${f.evidence_found}</div>` : ''}
                            ${f.calculation ? `<div class="finding-calc"><strong>Calculation:</strong> ${f.calculation}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>`;
        }

        // Missing Information
        const missing = report.missing_information || [];
        if (missing.length > 0) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3 style="color:var(--blue)">Missing Information <span class="count" style="background:var(--blue-bg);color:var(--blue)">${missing.length}</span></h3>
                    <span class="section-chevron open">&#9662;</span>
                </div>
                <div class="section-body open">
                    ${missing.map(m => `
                        <div class="missing-card">
                            <div class="label">${m.field || m.document || 'Item'}</div>
                            <div class="required">Impact: ${m.impact || 'Claim cannot be fully evaluated'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>`;
        }

        // Incident Timeline
        const timeline = report.timeline || [];
        if (timeline.length > 0) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Incident Timeline</h3>
                    <span class="section-chevron">&#9662;</span>
                </div>
                <div class="section-body">
                    <div class="timeline">
                        ${timeline.map(t => `
                            <div class="timeline-item">
                                <div class="timeline-dot"></div>
                                <div class="timeline-event">${t.event}</div>
                                <div class="timeline-date">${t.date || '—'} &bull; ${t.source || ''}</div>
                                ${t.days_from_incident != null ? `<div class="timeline-days">${t.days_from_incident} days after incident</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>`;
        }

        // Evidence Matrix
        const matrix = report.evidence_matrix || [];
        if (matrix.length > 0) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Cross-Document Evidence Matrix</h3>
                    <span class="section-chevron">&#9662;</span>
                </div>
                <div class="section-body">
                    <table class="matrix-table">
                        <thead><tr><th>Field</th><th>Claim Form</th><th>FIR / Police</th><th>Repair Est.</th><th>Description</th><th>Status</th></tr></thead>
                        <tbody>
                            ${matrix.map(m => `
                                <tr>
                                    <td><strong>${m.field}</strong></td>
                                    <td>${m.claim_form || '—'}</td>
                                    <td>${m.fir || '—'}</td>
                                    <td>${m.repair_estimate || '—'}</td>
                                    <td>${m.incident_description || '—'}</td>
                                    <td><span class="tag tag-${m.status === 'MATCH' ? 'approve' : m.status === 'CONTRADICTION' ? 'reject' : 'pending'}">${m.status}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>`;
        }

        // Decision Simulator
        html += `
        <div class="detail-section">
            <div class="section-header" onclick="toggleSection(this)">
                <h3>Decision Simulator (What-If Analysis)</h3>
                <span class="section-chevron open">&#9662;</span>
            </div>
            <div class="section-body open">
                <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:14px">Adjust claim parameters to test how recommendations change in real-time:</p>
                <div class="simulator-grid">
                    <div class="sim-field">
                        <label>Repair Estimate (₹)</label>
                        <input type="number" id="sim-repair" value="${claim.repair_estimate || 0}">
                    </div>
                    <div class="sim-field">
                        <label>Claim Date</label>
                        <input type="text" id="sim-claim-date" value="${claim.claim_date || ''}">
                    </div>
                    <div class="sim-field">
                        <label>Missing Documents Uploaded?</label>
                        <select id="sim-docs">
                            <option value="false">No</option>
                            <option value="true">Yes (All Provided)</option>
                        </select>
                    </div>
                    <div class="sim-field">
                        <label>Intoxication Evidence?</label>
                        <select id="sim-intox">
                            <option value="false">No</option>
                            <option value="true">Yes</option>
                        </select>
                    </div>
                </div>
                <button class="btn btn-sm btn-primary" onclick="runSimulation('${claimId}')">Recalculate Decision</button>
                <div id="sim-result" style="display:none;" class="sim-result"></div>
            </div>
        </div>`;

        // Investigator Handoff
        const handoff = report.handoff || {};
        if (handoff.investigation_steps || handoff.key_issues) {
            html += `
            <div class="detail-section">
                <div class="section-header" onclick="toggleSection(this)">
                    <h3>Investigator Handoff Summary</h3>
                    <span class="section-chevron">&#9662;</span>
                </div>
                <div class="section-body">
                    <div class="handoff-card">
                        ${(handoff.key_issues || []).length > 0 ? `
                            <h4 style="color:var(--amber)">Issues Requiring Attention</h4>
                            <ul class="handoff-list">
                                ${handoff.key_issues.map(i => `<li class="issue">${i}</li>`).join('')}
                            </ul>
                        ` : ''}
                        ${(handoff.investigation_steps || []).length > 0 ? `
                            <h4 style="color:var(--accent);margin-top:14px">Recommended Next Steps</h4>
                            <ul class="handoff-list">
                                ${handoff.investigation_steps.map(s => `<li class="step">${s}</li>`).join('')}
                            </ul>
                        ` : ''}
                    </div>
                </div>
            </div>`;
        }

        // Audit Trail
        try {
            const auditData = await api(`/api/claims/${claimId}/audit`);
            const trail = auditData.audit_trail || [];
            if (trail.length > 0) {
                html += `
                <div class="detail-section">
                    <div class="section-header" onclick="toggleSection(this)">
                        <h3>Investigation Audit Trail <span class="count">${trail.length}</span></h3>
                        <span class="section-chevron">&#9662;</span>
                    </div>
                    <div class="section-body">
                        ${trail.map(a => `
                            <div class="audit-item">
                                <span class="audit-time">${a.timestamp || ''}</span>
                                <span class="audit-type">${a.action_type || ''}</span>
                                <span class="audit-desc">${a.description || ''}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>`;
            }
        } catch {}

        // Disclaimer
        html += `
        <div class="disclaimer">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span><strong>Regulatory Compliance Note:</strong> ClaimLens AI assists claims investigators with automated evidence grounding and contradiction detection. All decisions require licensed human investigator sign-off before settlement.</span>
        </div>`;

        html += `</div>`; // Close detail-sections
        content.innerHTML = html;
        window.scrollTo({ top: 0, behavior: 'smooth' });

    } catch (e) {
        hideLoading();
        toast('Failed to load claim detail: ' + e.message, 'error');
    }
}

// ── Accordion & Tab Controls ──
function toggleSection(header) {
    const chevron = header.querySelector('.section-chevron');
    const body = header.nextElementSibling;
    if (!body) return;
    const isOpen = body.classList.contains('open');
    body.classList.toggle('open', !isOpen);
    body.style.display = isOpen ? 'none' : 'block';
    chevron?.classList.toggle('open', !isOpen);
}

function switchDocTab(btn, docId) {
    btn.parentElement.querySelectorAll('.doc-tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    const viewer = btn.closest('.section-body');
    viewer.querySelectorAll('.doc-viewer').forEach(v => v.style.display = 'none');
    const target = document.getElementById(docId);
    if (target) target.style.display = 'block';
}

// ── Simulator Execution ──
async function runSimulation(claimId) {
    const params = {
        repair_estimate: parseFloat(document.getElementById('sim-repair')?.value || 0),
        claim_date: document.getElementById('sim-claim-date')?.value || null,
        missing_documents_provided: document.getElementById('sim-docs')?.value === 'true',
        intoxication_reported: document.getElementById('sim-intox')?.value === 'true',
    };

    try {
        const result = await api(`/api/claims/${claimId}/simulate`, {
            method: 'POST',
            body: JSON.stringify(params),
        });

        const resEl = document.getElementById('sim-result');
        if (resEl) {
            resEl.style.display = 'block';
            resEl.innerHTML = `
                <div class="sim-label">SIMULATION RESULT: ${result.simulated_recommendation}</div>
                <div style="font-size:0.85rem;color:var(--text-secondary);margin-top:6px">${result.explanation || ''}</div>
                ${result.impact_analysis ? `
                    <div style="font-size:0.78rem;color:var(--text-muted);margin-top:8px">
                        <strong>Change Impact:</strong> ${result.impact_analysis.key_changes?.join('; ') || 'No critical status change'}
                    </div>
                ` : ''}
            `;
        }
    } catch (e) {
        toast('Simulation failed: ' + e.message, 'error');
    }
}

// ── HTML Escaping Utility ──
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ═══════════════════════════════════════════════
// BANNER CAROUSEL (Rotates every 3 seconds)
// ═══════════════════════════════════════════════
let bannerCurrentIndex = 0;
let bannerInterval = null;
let bannerProgressInterval = null;
let bannerProgress = 0;
let bannerIsPaused = false;
const BANNER_DURATION = 3000;

function initBannerCarousel() {
    const container = document.getElementById('banner-carousel-container');
    if (!container) return;

    goToBannerSlide(0);
    startBannerAutoRotate();
}

function startBannerAutoRotate() {
    if (bannerInterval) clearInterval(bannerInterval);
    if (bannerProgressInterval) clearInterval(bannerProgressInterval);

    bannerProgress = 0;
    const pBar = document.getElementById('banner-progress-bar');
    if (pBar) pBar.style.width = '0%';

    const step = 40; // ms
    bannerProgressInterval = setInterval(() => {
        if (!bannerIsPaused) {
            bannerProgress += (step / BANNER_DURATION) * 100;
            if (pBar) pBar.style.width = Math.min(100, bannerProgress) + '%';
        }
    }, step);

    bannerInterval = setInterval(() => {
        if (!bannerIsPaused) {
            nextBannerSlide();
        }
    }, BANNER_DURATION);
}

function pauseBannerCarousel() {
    bannerIsPaused = true;
}

function resumeBannerCarousel() {
    bannerIsPaused = false;
}

function goToBannerSlide(index) {
    const container = document.getElementById('banner-carousel-container');
    const slides = document.querySelectorAll('.banner-slide');
    const dots = document.querySelectorAll('.banner-dot');
    if (!container || slides.length === 0) return;

    const total = slides.length;
    bannerCurrentIndex = ((index % total) + total) % total;

    container.style.transform = `translateX(-${bannerCurrentIndex * 100}%)`;

    slides.forEach((s, idx) => {
        s.classList.toggle('active', idx === bannerCurrentIndex);
    });
    dots.forEach((d, idx) => {
        d.classList.toggle('active', idx === bannerCurrentIndex);
    });

    // Reset progress animation
    bannerProgress = 0;
    const pBar = document.getElementById('banner-progress-bar');
    if (pBar) pBar.style.width = '0%';
}

function nextBannerSlide() {
    goToBannerSlide(bannerCurrentIndex + 1);
}

function prevBannerSlide() {
    goToBannerSlide(bannerCurrentIndex - 1);
}

// ═══════════════════════════════════════════════
// CRUD: CREATE CLAIM / CASE
// ═══════════════════════════════════════════════
function openNewClaimModal() {
    const modal = document.getElementById('modal-new-claim');
    if (modal) {
        modal.style.display = 'flex';
        const today = new Date().toISOString().split('T')[0];
        const dateInput = document.getElementById('new-claim-date');
        const incInput = document.getElementById('new-incident-date');
        if (dateInput && !dateInput.value) dateInput.value = today;
        if (incInput && !incInput.value) incInput.value = today;
    }
}

function closeNewClaimModal() {
    const modal = document.getElementById('modal-new-claim');
    if (modal) modal.style.display = 'none';
}

function fillNewClaimPreset(type) {
    const today = new Date().toISOString().split('T')[0];
    if (type === 'accident') {
        document.getElementById('new-customer-name').value = 'Vikram Malhotra';
        document.getElementById('new-vehicle-reg').value = 'MH-02-DN-8842';
        document.getElementById('new-vehicle-type').value = 'Car';
        document.getElementById('new-incident-type').value = 'Accident';
        document.getElementById('new-incident-date').value = today;
        document.getElementById('new-incident-location').value = 'Bandra Reclamation, Mumbai';
        document.getElementById('new-idv').value = 750000;
        document.getElementById('new-repair-estimate').value = 145000;
        document.getElementById('new-description').value = 'Vehicle was hit on front right quarter panel by another car jumping red light at intersection. Front bumper, headlight, radiator, and suspension damaged.';
    } else if (type === 'theft') {
        document.getElementById('new-customer-name').value = 'Ananya Sen';
        document.getElementById('new-vehicle-reg').value = 'DL-01-BK-3390';
        document.getElementById('new-vehicle-type').value = 'Two-Wheeler';
        document.getElementById('new-incident-type').value = 'Theft';
        document.getElementById('new-incident-date').value = today;
        document.getElementById('new-incident-location').value = 'Sector 18 Metro Station Parking, Noida';
        document.getElementById('new-idv').value = 120000;
        document.getElementById('new-repair-estimate').value = 120000;
        document.getElementById('new-description').value = 'Motorcycle was parked at metro station parking lot at 08:30 AM. When returned at 07:00 PM, vehicle was missing. FIR lodged immediately at Sector 20 Police Station.';
    } else if (type === 'commercial') {
        document.getElementById('new-customer-name').value = 'Express Logistics Corp';
        document.getElementById('new-vehicle-reg').value = 'KA-05-TR-9122';
        document.getElementById('new-vehicle-type').value = 'Commercial';
        document.getElementById('new-incident-type').value = 'Accident';
        document.getElementById('new-incident-date').value = today;
        document.getElementById('new-incident-location').value = 'Hosur Road, Bengaluru';
        document.getElementById('new-idv').value = 980000;
        document.getElementById('new-repair-estimate').value = 210000;
        document.getElementById('new-description').value = 'Delivery van side swiped by heavy truck in rain on highway. Left sliding door, side body panel, and glass damaged.';
    }
}

async function submitNewClaim(e) {
    e.preventDefault();
    const btn = document.getElementById('btn-create-submit');
    if (btn) btn.disabled = true;
    showLoading('Creating new claim case...');

    try {
        const payload = {
            customer_name: document.getElementById('new-customer-name').value,
            vehicle_registration: document.getElementById('new-vehicle-reg').value,
            vehicle_type: document.getElementById('new-vehicle-type').value,
            incident_type: document.getElementById('new-incident-type').value,
            incident_date: document.getElementById('new-incident-date').value,
            incident_time: document.getElementById('new-incident-time').value,
            incident_location: document.getElementById('new-incident-location').value,
            claim_date: document.getElementById('new-claim-date').value,
            idv: parseFloat(document.getElementById('new-idv').value) || 500000,
            repair_estimate: parseFloat(document.getElementById('new-repair-estimate').value) || 0,
            description: document.getElementById('new-description').value
        };

        const res = await api('/api/claims', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        hideLoading();
        closeNewClaimModal();
        toast(`Claim ${res.claim_id} created successfully!`, 'success');

        await loadDashboard();
        viewClaim(res.claim_id);
    } catch (err) {
        hideLoading();
        toast('Failed to create claim: ' + err.message, 'error');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ═══════════════════════════════════════════════
// CRUD: EDIT CLAIM / CASE
// ═══════════════════════════════════════════════
function openEditClaimModal() {
    if (!currentClaimId) return;
    const claim = allClaims.find(c => c.claim_id === currentClaimId);
    if (!claim) {
        toast('Claim data not available to edit', 'error');
        return;
    }

    document.getElementById('edit-status').value = claim.status || 'PENDING';
    document.getElementById('edit-vehicle-reg').value = claim.vehicle_registration || '';
    document.getElementById('edit-idv').value = claim.idv || 0;
    document.getElementById('edit-repair-estimate').value = claim.repair_estimate || 0;
    document.getElementById('edit-incident-location').value = claim.incident_location || '';

    document.getElementById('modal-edit-claim').style.display = 'flex';
}

function closeEditClaimModal() {
    const modal = document.getElementById('modal-edit-claim');
    if (modal) modal.style.display = 'none';
}

async function submitEditClaim(e) {
    e.preventDefault();
    if (!currentClaimId) return;
    showLoading('Updating claim details...');

    try {
        const updates = {
            status: document.getElementById('edit-status').value,
            vehicle_registration: document.getElementById('edit-vehicle-reg').value,
            idv: parseFloat(document.getElementById('edit-idv').value) || 0,
            repair_estimate: parseFloat(document.getElementById('edit-repair-estimate').value) || 0,
            incident_location: document.getElementById('edit-incident-location').value
        };

        await api(`/api/claims/${currentClaimId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });

        hideLoading();
        closeEditClaimModal();
        toast(`Claim ${currentClaimId} updated successfully!`, 'success');

        await loadDashboard();
        viewClaim(currentClaimId);
    } catch (err) {
        hideLoading();
        toast('Failed to update claim: ' + err.message, 'error');
    }
}

// ═══════════════════════════════════════════════
// CRUD: DELETE CLAIM / CASE
// ═══════════════════════════════════════════════
async function confirmDeleteClaim() {
    if (!currentClaimId) return;
    if (!confirm(`Are you sure you want to permanently delete claim ${currentClaimId}? This will remove all associated documents, findings, and reviews.`)) {
        return;
    }

    showLoading(`Deleting claim ${currentClaimId}...`);
    try {
        await api(`/api/claims/${currentClaimId}`, { method: 'DELETE' });
        hideLoading();
        toast(`Claim ${currentClaimId} deleted successfully.`, 'info');
        currentClaimId = null;
        await loadDashboard();
        switchNav('claims');
    } catch (err) {
        hideLoading();
        toast('Failed to delete claim: ' + err.message, 'error');
    }
}

// ═══════════════════════════════════════════════
// ML RISK ENGINE & LIVE PREDICTOR
// ═══════════════════════════════════════════════
async function loadMLMetrics() {
    try {
        const data = await api('/api/ml/metrics');
        const m = data.metrics || {};

        if (m.accuracy) {
            const accEl = document.getElementById('ml-stat-acc');
            if (accEl) accEl.textContent = m.accuracy + '%';
        }
        if (m.roc_auc) {
            const aucEl = document.getElementById('ml-stat-auc');
            if (aucEl) aucEl.textContent = m.roc_auc;
        }
        if (m.precision) {
            const precEl = document.getElementById('ml-stat-prec');
            if (precEl) precEl.textContent = m.precision + '%';
        }
    } catch (err) {
        console.error('Failed to load ML metrics:', err);
    }
}

function fillMLPreset(type) {
    if (type === 'clean') {
        document.getElementById('ml-input-vtype').value = 'Car / Sedan';
        document.getElementById('ml-input-usage').value = 'Private';
        document.getElementById('ml-input-idv').value = 700000;
        document.getElementById('ml-input-repair').value = 35000;
        document.getElementById('ml-input-year').value = 2023;
        document.getElementById('ml-input-premium').value = 21000;
    } else if (type === 'inflated') {
        document.getElementById('ml-input-vtype').value = 'Pick-up / Delivery Van';
        document.getElementById('ml-input-usage').value = 'Own Goods';
        document.getElementById('ml-input-idv').value = 450000;
        document.getElementById('ml-input-repair').value = 380000;
        document.getElementById('ml-input-year').value = 2017;
        document.getElementById('ml-input-premium').value = 11000;
    } else if (type === 'highrisk') {
        document.getElementById('ml-input-vtype').value = 'Motor-cycle';
        document.getElementById('ml-input-usage').value = 'Private';
        document.getElementById('ml-input-idv').value = 220000;
        document.getElementById('ml-input-repair').value = 195000;
        document.getElementById('ml-input-year').value = 2015;
        document.getElementById('ml-input-premium').value = 3500;
    }
}

async function runMLPrediction(e) {
    e.preventDefault();
    const resultBox = document.getElementById('ml-prediction-result');
    if (!resultBox) return;

    resultBox.style.display = 'block';
    resultBox.innerHTML = '<div style="text-align:center;padding:12px;color:var(--text-muted);">Running LightGBM inference on 508k-record Kaggle benchmark...</div>';

    try {
        const payload = {
            type_vehicle: document.getElementById('ml-input-vtype').value,
            usage: document.getElementById('ml-input-usage').value,
            insured_value: parseFloat(document.getElementById('ml-input-idv').value),
            repair_estimate: parseFloat(document.getElementById('ml-input-repair').value),
            prod_year: parseInt(document.getElementById('ml-input-year').value),
            premium: parseFloat(document.getElementById('ml-input-premium').value)
        };

        const res = await api('/api/ml/predict', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        const color = res.risk_score >= 70 ? '#dc2626' : (res.risk_score >= 40 ? '#d97706' : '#16a34a');
        const badgeBg = res.risk_score >= 70 ? '#fee2e2' : (res.risk_score >= 40 ? '#fef3c7' : '#dcfce7');

        resultBox.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <div>
                    <span style="font-size:0.75rem; font-weight:700; color:var(--text-muted); text-transform:uppercase;">ML Risk Assessment</span>
                    <h4 style="font-size:1.15rem; font-weight:800; color:${color}; margin-top:2px;">${res.risk_level} (${res.risk_score}/100)</h4>
                </div>
                <div style="background:${badgeBg}; color:${color}; padding:6px 14px; border-radius:20px; font-weight:700; font-size:0.8rem;">
                    Probability: ${res.claim_probability}%
                </div>
            </div>

            <div class="risk-meter">
                <div class="risk-meter-fill" style="width:${res.risk_score}%; background:${color};"></div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; font-size:0.82rem;">
                <div style="background:var(--bg-card); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                    <span style="color:var(--text-muted);">Historical Median Payout:</span>
                    <strong style="display:block; font-size:0.95rem; color:var(--text-primary); margin-top:2px;">₹${res.benchmark_payout?.toLocaleString()}</strong>
                </div>
                <div style="background:var(--bg-card); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                    <span style="color:var(--text-muted);">Overclaim Ratio:</span>
                    <strong style="display:block; font-size:0.95rem; color:${res.overclaim_ratio > 1.5 ? '#dc2626' : 'var(--text-primary)'}; margin-top:2px;">${res.overclaim_ratio}x Benchmark</strong>
                </div>
            </div>

            <div style="margin-top:10px;">
                <span style="font-size:0.78rem; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Recommended Action:</span>
                <p style="font-size:0.85rem; font-weight:600; color:var(--text-primary); margin-top:4px;">${res.recommendation}</p>
            </div>

            ${res.anomalies && res.anomalies.length > 0 ? `
                <div style="margin-top:14px;">
                    <span style="font-size:0.78rem; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Detected Anomalies (${res.anomalies.length}):</span>
                    ${res.anomalies.map(a => `
                        <div class="anomaly-item">
                            <span class="anomaly-icon">${a.severity === 'HIGH' ? '🚨' : '⚠️'}</span>
                            <div>
                                <strong style="color:var(--text-primary);">${a.type.replace(/_/g, ' ')}</strong>
                                <p style="color:var(--text-secondary); margin-top:2px;">${a.description}</p>
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : '<div style="margin-top:10px; font-size:0.82rem; color:var(--green); font-weight:600;">✓ No statistical anomaly detected relative to vehicle class benchmarks.</div>'}
        `;
    } catch (err) {
        resultBox.innerHTML = `<div style="color:var(--red); padding:10px;">Prediction error: ${err.message}</div>`;
    }
}

/* ═══════════════════════════════════════════════
   PDF & DOCUMENT AI STUDIO LOGIC
   ═══════════════════════════════════════════════ */
let lastExtractedDocument = null;
let currentUploadTargetClaimId = null;

async function loadDocStudio() {
    try {
        const data = await api('/api/documents/sample-files');
        const listEl = document.getElementById('sample-docs-list');
        if (!listEl || !data.samples || data.samples.length === 0) return;

        listEl.innerHTML = data.samples.map(s => {
            const isAlert = s.category.includes('Risk') || s.category.includes('Overclaim');
            const iconBg = isAlert ? '#fef3c7' : '#fee2e2';
            const iconColor = isAlert ? '#b45309' : '#dc2626';
            return `
            <div class="sample-item-card" onclick="scanSampleFile('${s.filename}')">
                <div class="sample-item-left">
                    <div class="sample-pdf-icon" style="background:${iconBg}; color:${iconColor};">PDF</div>
                    <div>
                        <div class="sample-item-title">${s.filename.replace(/_/g, ' ').replace('.pdf', '')}</div>
                        <div class="sample-item-desc">${s.description} &bull; <span style="font-weight:600;">${s.size_formatted}</span></div>
                    </div>
                </div>
                <button type="button" class="sample-scan-btn">Scan & Extract →</button>
            </div>`;
        }).join('');
    } catch (e) {
        console.warn('Failed to load sample docs list:', e);
    }
}

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('studio-dropzone')?.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('studio-dropzone')?.classList.remove('dragover');
}

function handleFileDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('studio-dropzone')?.classList.remove('dragover');
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleStudioFileUpload(e.dataTransfer.files[0]);
    }
}

function handleStudioFileSelect(e) {
    if (e.target.files && e.target.files.length > 0) {
        handleStudioFileUpload(e.target.files[0]);
    }
}

async function handleStudioFileUpload(file) {
    if (!file) return;
    showLoading(`PyMuPDF parsing layout & extracting entities from ${file.name}...`);
    try {
        const formData = new FormData();
        formData.append('file', file);

        const resp = await fetch('/api/documents/extract', {
            method: 'POST',
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Server returned ${resp.status}`);
        }

        const data = await resp.json();
        hideLoading();
        toast(`Successfully parsed ${file.name} with ${data.engine}!`, 'success');
        renderStudioExtractionResult(data);
    } catch (err) {
        hideLoading();
        toast(`Document parsing failed: ${err.message}`, 'error');
    }
}

async function scanSampleFile(filename) {
    showLoading(`Scanning sample PDF: ${filename.replace(/_/g, ' ')}...`);
    try {
        const data = await api(`/api/documents/scan-sample/${encodeURIComponent(filename)}`, {
            method: 'POST'
        });
        hideLoading();
        toast(`Extracted entities from ${filename}!`, 'success');
        renderStudioExtractionResult(data);
    } catch (err) {
        hideLoading();
        toast(`Sample extraction error: ${err.message}`, 'error');
    }
}

function renderStudioExtractionResult(data) {
    lastExtractedDocument = data;
    const container = document.getElementById('studio-extraction-result');
    if (!container) return;

    container.style.display = 'grid';
    const ent = data.entities || {};
    const math = ent.math_consistency || { is_valid: true };
    const lineItems = ent.line_items || [];
    const flags = ent.flags || [];

    // Document Type styling
    const typeNames = {
        'claim_form': 'Motor Claim Form',
        'repair_estimate': 'Workshop Repair Estimate',
        'fir': 'Police First Information Report (FIR)',
        'surveyor_report': 'Surveyor & Loss Report',
        'incident_statement': 'Customer Incident Statement'
    };
    const humanType = typeNames[data.document_type] || data.document_type;
    const confPct = Math.round((data.classification_confidence || 0.9) * 100);

    let html = `
    <!-- Left: Structured Entities & Validation -->
    <div class="studio-card">
        <div class="studio-card-header">
            <div class="studio-card-title">
                <span>📑 AI Document Classification</span>
                <span class="tag tag-approve">${humanType}</span>
            </div>
            <span class="card-badge" style="background:var(--accent); color:#fff;">Confidence: ${confPct}%</span>
        </div>

        <div style="display:flex; gap:16px; font-size:0.8rem; color:var(--text-muted); margin-bottom:16px; flex-wrap:wrap;">
            <span><strong>File:</strong> ${data.filename}</span>
            <span><strong>Size:</strong> ${(data.file_size / 1024).toFixed(1)} KB</span>
            <span><strong>Pages:</strong> ${data.page_count}</span>
            <span><strong>Engine:</strong> ${data.engine}</span>
        </div>

        ${data.classification_reasons && data.classification_reasons.length > 0 ? `
            <div style="background:var(--bg-surface); padding:8px 12px; border-radius:6px; border:1px solid var(--border); margin-bottom:16px; font-size:0.8rem;">
                <span style="color:var(--text-muted); font-weight:600;">Detection Reasons:</span>
                <ul style="margin:4px 0 0 18px; color:var(--text-secondary);">
                    ${data.classification_reasons.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        ` : ''}

        <!-- Invoice Math Consistency Card -->
        ${lineItems.length > 0 ? `
            <div class="math-alert ${math.is_valid ? 'math-alert-valid' : 'math-alert-invalid'}">
                <span style="font-size:1.2rem;">${math.is_valid ? '✅' : '🚨'}</span>
                <div>
                    <strong>${math.is_valid ? 'Invoice Arithmetic Verified' : 'Arithmetic Discrepancy / Tampering Alert'}</strong>
                    <p style="margin:2px 0 0 0; font-size:0.8rem;">
                        ${math.is_valid 
                            ? `Sum of itemized parts & labour (₹${math.parts_sum?.toLocaleString()}) matches total estimate exactly.`
                            : `Itemized breakdown sums to ₹${math.parts_sum?.toLocaleString()}, but declared total is ${ent.repair_estimate_formatted} (Diff: ₹${math.discrepancy?.toLocaleString()}).`}
                    </p>
                </div>
            </div>
        ` : ''}

        <!-- Red Flags -->
        ${flags.length > 0 ? `
            <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:6px; padding:10px 14px; margin-bottom:16px;">
                <strong style="color:#b91c1c; font-size:0.83rem;">⚠️ Automated Risk Warnings:</strong>
                <ul style="margin:4px 0 0 18px; color:#991b1b; font-size:0.8rem;">
                    ${flags.map(f => `<li>${f}</li>`).join('')}
                </ul>
            </div>
        ` : ''}

        <h4 style="font-size:0.92rem; font-weight:700; margin-bottom:10px; color:var(--text-primary);">
            Extracted Claim Entities
        </h4>
        <div class="entity-key-val-grid">
            <div class="entity-box">
                <div class="entity-key">Vehicle Registration</div>
                <div class="entity-val" style="color:var(--accent);">${ent.vehicle_registration || '—'}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Policy Number</div>
                <div class="entity-val">${ent.policy_number || '—'}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Insured / Claimant</div>
                <div class="entity-val">${ent.customer_name || '—'}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Vehicle Type & Model</div>
                <div class="entity-val">${ent.vehicle_type || 'Vehicle'} ${ent.vehicle_make_model ? `&bull; ${ent.vehicle_make_model}` : ''}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Incident Date & Time</div>
                <div class="entity-val">${ent.incident_date || '—'} ${ent.incident_time ? `&bull; ${ent.incident_time}` : ''}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Incident Location</div>
                <div class="entity-val">${ent.incident_location || '—'}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Claimed Repair Cost</div>
                <div class="entity-val" style="color:var(--red);">${ent.repair_estimate_formatted || (ent.repair_estimate_total ? `₹${ent.repair_estimate_total.toLocaleString()}` : '—')}</div>
            </div>
            <div class="entity-box">
                <div class="entity-key">Police FIR Reference</div>
                <div class="entity-val">${ent.fir_number || '—'}</div>
            </div>
        </div>

        ${lineItems.length > 0 ? `
            <div style="margin-top:16px;">
                <h4 style="font-size:0.88rem; font-weight:700; margin-bottom:8px; color:var(--text-primary);">
                    Itemized Parts & Labour Breakdown (${lineItems.length} items)
                </h4>
                <div style="max-height:220px; overflow-y:auto; border:1px solid var(--border); border-radius:6px;">
                    <table class="line-items-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Description</th>
                                <th>Category</th>
                                <th>Amount (INR)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${lineItems.map(item => `
                                <tr>
                                    <td>${item.index}</td>
                                    <td><strong>${item.description}</strong></td>
                                    <td><span class="tag" style="padding:1px 6px; font-size:0.7rem;">${item.category}</span></td>
                                    <td style="font-weight:600;">${item.amount_formatted}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        ` : ''}

        <!-- Primary Actions -->
        <div style="margin-top:20px; display:flex; gap:10px; flex-wrap:wrap;">
            <button type="button" class="btn btn-primary" onclick="createClaimFromExtracted()" style="flex:1; justify-content:center;">
                🚀 Create & Review Claim Case From This PDF
            </button>
            <button type="button" class="btn btn-secondary" onclick="downloadExtractedJSON()">
                📥 Export JSON
            </button>
        </div>
    </div>

    <!-- Right: Raw Document Layout Preview -->
    <div class="studio-card">
        <div class="studio-card-header">
            <div class="studio-card-title">
                <span>📜 Extracted Raw Document Text</span>
            </div>
            <button class="btn btn-ghost btn-sm" onclick="copyRawDocText()">
                📋 Copy Text
            </button>
        </div>
        <p style="font-size:0.8rem; color:var(--text-muted); margin-bottom:10px;">
            Preserves physical line structures, indentation, and OCR tokens for evidence grounding:
        </p>
        <pre class="raw-text-box" id="raw-doc-text-content">${escapeHtml(data.text_full || data.text_preview || '')}</pre>
    </div>
    `;

    container.innerHTML = html;
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function createClaimFromExtracted() {
    if (!lastExtractedDocument) {
        toast('No extracted document data available', 'error');
        return;
    }
    const ent = lastExtractedDocument.entities || {};
    const docType = lastExtractedDocument.document_type || 'claim_form';

    showLoading('Creating new claim docket and running AI evidence cross-referencing...');
    try {
        const newClaimPayload = {
            customer_name: ent.customer_name || 'Rahul Sharma',
            vehicle_registration: ent.vehicle_registration || 'KA01MJ9082',
            vehicle_type: ent.vehicle_type || 'Car',
            incident_type: docType === 'fir' ? 'Theft' : 'Accident',
            incident_date: ent.incident_date || '2024-11-12',
            incident_time: ent.incident_time || '14:30',
            incident_location: ent.incident_location || 'Outer Ring Road, Bengaluru',
            claim_date: '2024-11-13',
            policy_start_date: '2024-01-01',
            policy_end_date: '2025-01-01',
            idv: ent.vehicle_type === 'Car' ? 650000 : 180000,
            repair_estimate: ent.repair_estimate_total || 48500,
            description: `Auto-ingested from ${lastExtractedDocument.filename}. ${ent.vehicle_registration ? 'Vehicle Reg: ' + ent.vehicle_registration : ''}. Estimated amount: ${ent.repair_estimate_formatted || ''}`
        };

        const result = await api('/api/claims', {
            method: 'POST',
            body: JSON.stringify(newClaimPayload)
        });

        const newId = result.claim_id;

        // Attach this document to the new claim
        await api(`/api/claims/${newId}/documents`, {
            method: 'POST',
            body: JSON.stringify({
                document_type: docType,
                filename: lastExtractedDocument.filename,
                content: lastExtractedDocument.text_full
            })
        }).catch(() => null);

        // Trigger AI review
        await api(`/api/claims/${newId}/review`, { method: 'POST' }).catch(() => null);

        hideLoading();
        toast(`Claim ${newId} created and reviewed successfully!`, 'success');
        await loadDashboard();
        viewClaim(newId);
    } catch (err) {
        hideLoading();
        toast(`Failed to create claim from document: ${err.message}`, 'error');
    }
}

function copyRawDocText() {
    const el = document.getElementById('raw-doc-text-content');
    if (!el) return;
    navigator.clipboard.writeText(el.innerText).then(() => {
        toast('Raw document text copied to clipboard!', 'success');
    }).catch(() => {
        toast('Copy failed. Please select text manually.', 'error');
    });
}

function downloadExtractedJSON() {
    if (!lastExtractedDocument) return;
    const blob = new Blob([JSON.stringify(lastExtractedDocument, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `extracted_${lastExtractedDocument.filename || 'claim'}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast('Extracted JSON downloaded', 'success');
}

/* ═══════════════════════════════════════════════
   MODAL: UPLOAD DOCUMENT DIRECTLY TO CASE
   ═══════════════════════════════════════════════ */
function openUploadDocModal(claimId) {
    currentUploadTargetClaimId = claimId;
    const modal = document.getElementById('modal-upload-doc');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('claim-doc-file-name').textContent = 'Select or Drag & Drop PDF / Document';
        const fileIn = document.getElementById('claim-doc-file-input');
        if (fileIn) fileIn.value = '';
    }
}

function closeUploadDocModal() {
    const modal = document.getElementById('modal-upload-doc');
    if (modal) modal.style.display = 'none';
    currentUploadTargetClaimId = null;
}

function handleClaimDocFileChange(input) {
    if (input.files && input.files[0]) {
        const f = input.files[0];
        document.getElementById('claim-doc-file-name').textContent = `📄 ${f.name} (${(f.size / 1024).toFixed(1)} KB)`;
    }
}

async function submitClaimDocUpload(e) {
    e.preventDefault();
    if (!currentUploadTargetClaimId) return;

    const fileIn = document.getElementById('claim-doc-file-input');
    if (!fileIn || !fileIn.files || fileIn.files.length === 0) {
        toast('Please select a file to upload', 'error');
        return;
    }

    const file = fileIn.files[0];
    const slot = document.getElementById('upload-doc-slot')?.value || '';

    closeUploadDocModal();
    showLoading(`Uploading ${file.name} to ${currentUploadTargetClaimId} and re-evaluating evidence...`);

    try {
        const formData = new FormData();
        formData.append('file', file);
        if (slot) formData.append('doc_slot', slot);

        const resp = await fetch(`/api/claims/${currentUploadTargetClaimId}/documents`, {
            method: 'POST',
            body: formData
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Server returned ${resp.status}`);
        }

        hideLoading();
        toast(`Document uploaded and claim re-evaluated!`, 'success');
        await loadDashboard();
        viewClaim(currentUploadTargetClaimId);
    } catch (err) {
        hideLoading();
        toast(`Upload failed: ${err.message}`, 'error');
    }
}

/* ═══════════════════════════════════════════════
   CLAIM AI ASSISTANT & COPILOT CLIENT ENGINE
   ═══════════════════════════════════════════════ */
let assistantClaimsList = [];
let assistantSelectedClaimId = null;
let assistantChatHistory = [];
let assistantSpeechRec = null;
let isRecordingVoice = false;
let isAssistantSending = false;

async function initAssistant() {
    try {
        await loadAssistantClaims();
        await loadAssistantSuggestions();
        setupAssistantSpeech();
        renderInitialAssistantGreeting();
    } catch (err) {
        console.warn('Assistant init warning:', err);
    }
}

async function loadAssistantClaims() {
    try {
        const res = await api('/api/assistant/claims');
        assistantClaimsList = res.claims || [];
        const selectEl = document.getElementById('assistant-claim-select');
        if (!selectEl) return;

        selectEl.innerHTML = '<option value="">🌐 All Claims & General Policy Knowledge</option>';
        assistantClaimsList.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.claim_id;
            opt.textContent = `${c.claim_id} — ${c.customer_name} (${c.vehicle_registration || c.vehicle_type}) [${c.scenario_type || c.incident_type}]`;
            selectEl.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load assistant claims:', e);
    }
}

async function loadAssistantSuggestions(claimId = null) {
    try {
        const url = claimId ? `/api/assistant/suggestions?claim_id=${encodeURIComponent(claimId)}` : '/api/assistant/suggestions';
        const res = await api(url);
        const suggestions = res.suggestions || [];
        
        // Render in full view
        const pillsContainer = document.getElementById('assistant-suggestions-pills');
        if (pillsContainer) {
            pillsContainer.innerHTML = '';
            suggestions.forEach(s => {
                const btn = document.createElement('button');
                btn.className = 'suggestion-pill';
                btn.textContent = s.label;
                btn.title = s.prompt;
                btn.onclick = () => submitAssistantQuery(s.prompt);
                pillsContainer.appendChild(btn);
            });
        }

        // Render in floating drawer
        const drawerPills = document.getElementById('drawer-suggestions-pills');
        if (drawerPills) {
            drawerPills.innerHTML = '';
            suggestions.slice(0, 3).forEach(s => {
                const btn = document.createElement('button');
                btn.className = 'suggestion-pill';
                btn.textContent = s.label;
                btn.onclick = () => {
                    const drawerInput = document.getElementById('drawer-input-text');
                    if (drawerInput) drawerInput.value = s.prompt;
                    submitDrawerQuery();
                };
                drawerPills.appendChild(btn);
            });
        }
    } catch (e) {
        console.error('Failed to load suggestions:', e);
    }
}

function renderInitialAssistantGreeting() {
    const container = document.getElementById('assistant-messages-container');
    if (!container || container.children.length > 0) return;

    const welcomeHTML = `
        <div class="assistant-msg-row assistant">
            <div class="msg-avatar ai-avatar">AI</div>
            <div class="msg-bubble-wrap">
                <div class="msg-sender-meta">
                    <strong>ClaimLens AI Copilot</strong>
                    <span>Just now</span>
                </div>
                <div class="msg-bubble">
                    <h3>👋 Welcome to ClaimLens AI Copilot</h3>
                    <p>I am your specialized motor insurance claims investigation assistant. I can inspect claims, identify evidence contradictions across documents, check policy coverage & IRDAI exclusions, compute net settlements, and draft formal RFI letters.</p>
                    <p><strong>To begin:</strong> Select a target claim from the dropdown above to ground our conversation in its specific evidence, or click any suggested inquiry below.</p>
                </div>
                <div class="msg-actions">
                    <button class="action-btn-pill" onclick="submitAssistantQuery('Which claims in the database have critical contradictions or high fraud risk?')">🔍 Find High-Risk Claims</button>
                    <button class="action-btn-pill" onclick="submitAssistantQuery('What are the IRDAI rules and policy clauses regarding FIR filing delay in theft claims?')">🚨 FIR Delay Rules</button>
                    <button class="action-btn-pill" onclick="submitAssistantQuery('What are the standard depreciation rates for rubber, plastic, glass, and metal parts?')">📊 Depreciation Schedule</button>
                </div>
            </div>
        </div>
    `;
    container.innerHTML = welcomeHTML;

    const drawerContainer = document.getElementById('drawer-messages-container');
    if (drawerContainer && drawerContainer.children.length === 0) {
        drawerContainer.innerHTML = welcomeHTML;
    }
}

function loadAssistantView() {
    // If user was viewing a claim, auto-select it if not already selected
    if (currentClaimId && !assistantSelectedClaimId) {
        selectAssistantClaim(currentClaimId);
    } else {
        updateAssistantContextStrip();
    }
    const container = document.getElementById('assistant-messages-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function onAssistantClaimChanged() {
    const selectEl = document.getElementById('assistant-claim-select');
    const claimId = selectEl ? selectEl.value : null;
    selectAssistantClaim(claimId);
}

function selectAssistantClaim(claimId) {
    assistantSelectedClaimId = claimId || null;
    const selectEl = document.getElementById('assistant-claim-select');
    if (selectEl && selectEl.value !== (claimId || '')) {
        selectEl.value = claimId || '';
    }

    updateAssistantContextStrip();
    loadAssistantSuggestions(assistantSelectedClaimId);

    // Update drawer context label
    const drawerLabel = document.getElementById('drawer-context-label');
    if (drawerLabel) {
        drawerLabel.textContent = assistantSelectedClaimId ? `Context: Claim ${assistantSelectedClaimId}` : 'Context: All Claims';
    }

    if (assistantSelectedClaimId) {
        toast(`Assistant context focused on ${assistantSelectedClaimId}`, 'info');
    }
}

function updateAssistantContextStrip() {
    const strip = document.getElementById('assistant-context-strip');
    if (!strip) return;

    if (!assistantSelectedClaimId) {
        strip.style.display = 'none';
        return;
    }

    const claim = assistantClaimsList.find(c => c.claim_id === assistantSelectedClaimId);
    if (!claim) {
        strip.style.display = 'none';
        return;
    }

    strip.style.display = 'flex';
    document.getElementById('strip-claim-id').textContent = claim.claim_id;
    document.getElementById('strip-customer').textContent = claim.customer_name || 'Claimant';
    document.getElementById('strip-vehicle').textContent = `${claim.vehicle_registration || 'No Reg'} • ${claim.vehicle_type || 'Vehicle'}`;
    document.getElementById('strip-incident').textContent = `${claim.incident_type || 'Accident'} (${claim.scenario_type || 'CASE'})`;
    document.getElementById('strip-estimate').textContent = `Est: ₹${Number(claim.repair_estimate || 0).toLocaleString()}`;
    
    const badge = document.getElementById('strip-status');
    if (badge) {
        badge.textContent = claim.status || 'PENDING';
        badge.style.background = claim.status === 'APPROVE' ? '#dcfce7' : (claim.status === 'REJECT' ? '#fee2e2' : '#fef3c7');
        badge.style.color = claim.status === 'APPROVE' ? '#166534' : (claim.status === 'REJECT' ? '#991b1b' : '#92400e');
    }
}

function viewClaimFromAssistant() {
    if (assistantSelectedClaimId) {
        viewClaim(assistantSelectedClaimId);
    }
}

function openAssistantWithClaim(claimId) {
    selectAssistantClaim(claimId);
    switchNav('assistant');
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 140) + 'px';
}

function handleAssistantKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitAssistantQuery();
    }
}

function handleDrawerKeyDown(e) {
    if (e.key === 'Enter') {
        e.preventDefault();
        submitDrawerQuery();
    }
}

async function submitDrawerQuery() {
    const input = document.getElementById('drawer-input-text');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    await submitAssistantQuery(text);
}

async function submitAssistantQuery(promptOverride = null) {
    if (isAssistantSending) return;

    const input = document.getElementById('assistant-input-text');
    const message = promptOverride || (input ? input.value.trim() : '');
    if (!message) return;

    if (!promptOverride && input) {
        input.value = '';
        input.style.height = 'auto';
    }

    isAssistantSending = true;
    const sendBtn = document.getElementById('assistant-send-btn');
    if (sendBtn) sendBtn.disabled = true;

    // Append user message to containers
    appendUserMessage(message);

    // Append thinking bubble
    const thinkingId = appendThinkingBubble();

    try {
        const payload = {
            message: message,
            claim_id: assistantSelectedClaimId || null,
            history: assistantChatHistory.slice(-6)
        };

        const resp = await fetch('/api/assistant/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Server returned ${resp.status}`);
        }

        const data = await resp.json();
        removeThinkingBubble(thinkingId);

        // Update history
        assistantChatHistory.push({ role: 'user', content: message });
        assistantChatHistory.push({ role: 'assistant', content: data.answer });

        // Render AI message
        appendAIMessage(data);

        // If backend returned or shifted claim_id and none was selected, update context
        if (data.claim_id && !assistantSelectedClaimId) {
            selectAssistantClaim(data.claim_id);
        }
    } catch (err) {
        removeThinkingBubble(thinkingId);
        appendErrorMessage(err.message);
        toast(`Assistant error: ${err.message}`, 'error');
    } finally {
        isAssistantSending = false;
        if (sendBtn) sendBtn.disabled = false;
    }
}

function appendUserMessage(text) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userHTML = `
        <div class="assistant-msg-row user">
            <div class="msg-avatar user-avatar">YOU</div>
            <div class="msg-bubble-wrap">
                <div class="msg-sender-meta">
                    <span>${time}</span>
                    <strong>Investigator</strong>
                </div>
                <div class="msg-bubble">${escapeHtml(text)}</div>
            </div>
        </div>
    `;

    ['assistant-messages-container', 'drawer-messages-container'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.insertAdjacentHTML('beforeend', userHTML);
            el.scrollTop = el.scrollHeight;
        }
    });
}

function appendThinkingBubble() {
    const id = 'thinking-' + Date.now();
    const thinkingHTML = `
        <div class="assistant-msg-row assistant" id="${id}">
            <div class="msg-avatar ai-avatar">AI</div>
            <div class="msg-bubble-wrap">
                <div class="msg-sender-meta">
                    <strong>ClaimLens AI Copilot</strong>
                    <span>Analyzing evidence...</span>
                </div>
                <div class="msg-bubble">
                    <div class="typing-dots">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    ['assistant-messages-container', 'drawer-messages-container'].forEach(containerId => {
        const el = document.getElementById(containerId);
        if (el) {
            el.insertAdjacentHTML('beforeend', thinkingHTML);
            el.scrollTop = el.scrollHeight;
        }
    });

    return id;
}

function removeThinkingBubble(id) {
    const els = document.querySelectorAll(`[id="${id}"]`);
    els.forEach(el => el.remove());
}

function appendAIMessage(data) {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedBody = formatMarkdownToHTML(data.answer);
    const engineBadge = data.engine === 'gemini-2.5-flash' ? '✨ Gemini AI' : '⚡ Policy Engine';

    // Build citations HTML
    let citationsHTML = '';
    if (data.grounding_citations && data.grounding_citations.length > 0) {
        citationsHTML = `
            <div class="msg-citations">
                <span class="citations-label">Grounded in:</span>
                ${data.grounding_citations.map(c => `
                    <span class="citation-chip" title="Grounding source (Confidence: ${c.confidence || '0.90'})">
                        📜 ${c.clause_id || 'Policy'}: ${escapeHtml(c.source)}
                    </span>
                `).join('')}
            </div>
        `;
    }

    // Build actions HTML
    let actionsHTML = '';
    if (data.suggested_actions && data.suggested_actions.length > 0) {
        actionsHTML = `
            <div class="msg-actions">
                ${data.suggested_actions.map(a => `
                    <button class="action-btn-pill" onclick="executeAssistantAction('${a.action}', '${a.claim_id || ''}')">
                        ${escapeHtml(a.label)}
                    </button>
                `).join('')}
            </div>
        `;
    }

    const msgId = 'msg-' + Date.now();
    const rawAnswerAttr = encodeURIComponent(data.answer);

    const aiHTML = `
        <div class="assistant-msg-row assistant" id="${msgId}">
            <div class="msg-avatar ai-avatar">AI</div>
            <div class="msg-bubble-wrap">
                <div class="msg-sender-meta">
                    <strong>ClaimLens AI Copilot</strong>
                    <span style="font-size:0.7rem; color:#4f46e5; font-weight:600;">${engineBadge}</span>
                    <span>${time}</span>
                </div>
                <div class="msg-bubble">
                    ${formattedBody}
                    ${citationsHTML}
                    ${actionsHTML}
                </div>
                <button class="copy-msg-btn" onclick="copyAssistantResponse('${rawAnswerAttr}')">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    Copy response
                </button>
            </div>
        </div>
    `;

    ['assistant-messages-container', 'drawer-messages-container'].forEach(containerId => {
        const el = document.getElementById(containerId);
        if (el) {
            el.insertAdjacentHTML('beforeend', aiHTML);
            el.scrollTop = el.scrollHeight;
        }
    });
}

function appendErrorMessage(errText) {
    const errorHTML = `
        <div class="assistant-msg-row assistant">
            <div class="msg-avatar" style="background:#fee2e2; color:#dc2626;">!</div>
            <div class="msg-bubble-wrap">
                <div class="msg-bubble" style="border-color:#fecaca; background:#fef2f2; color:#991b1b;">
                    <strong>Investigation Assistant Notice:</strong>
                    <p style="margin-top:4px;">${escapeHtml(errText)}</p>
                </div>
            </div>
        </div>
    `;
    ['assistant-messages-container', 'drawer-messages-container'].forEach(containerId => {
        const el = document.getElementById(containerId);
        if (el) {
            el.insertAdjacentHTML('beforeend', errorHTML);
            el.scrollTop = el.scrollHeight;
        }
    });
}

function executeAssistantAction(action, claimId) {
    if (action === 'open_claim' && claimId) {
        viewClaim(claimId);
    } else if (action === 'select_claim' && claimId) {
        selectAssistantClaim(claimId);
        submitAssistantQuery(`Audit all evidence contradictions and timeline discrepancies for claim ${claimId}.`);
    } else if (action === 'open_claims_list') {
        switchNav('claims');
    } else if (action === 'open_ml_engine') {
        switchNav('ml');
    } else if (action === 'open_doc_studio') {
        switchNav('doc-studio');
    } else if (action === 'open_simulator' && claimId) {
        viewClaim(claimId);
        setTimeout(() => {
            const simTab = document.querySelector('[data-tab="simulation"]');
            if (simTab) simTab.click();
        }, 400);
    } else if (action === 'copy_rfi') {
        toast('RFI draft copied to clipboard!', 'success');
    }
}

function copyAssistantResponse(encodedText) {
    try {
        const text = decodeURIComponent(encodedText);
        navigator.clipboard.writeText(text);
        toast('Response copied to clipboard!', 'success');
    } catch (e) {
        toast('Failed to copy', 'error');
    }
}

function clearAssistantChat() {
    assistantChatHistory = [];
    const container = document.getElementById('assistant-messages-container');
    if (container) container.innerHTML = '';
    const drawerContainer = document.getElementById('drawer-messages-container');
    if (drawerContainer) drawerContainer.innerHTML = '';
    renderInitialAssistantGreeting();
    toast('Assistant conversation cleared', 'info');
}

function exportAssistantTranscript() {
    if (assistantChatHistory.length === 0) {
        toast('No conversation history to export', 'info');
        return;
    }

    let transcript = `========================================================\n`;
    transcript += `ClaimLens AI — Investigation Assistant Chat Transcript\n`;
    transcript += `Generated: ${new Date().toLocaleString()}\n`;
    transcript += `Target Claim: ${assistantSelectedClaimId || 'All Claims'}\n`;
    transcript += `========================================================\n\n`;

    assistantChatHistory.forEach(item => {
        transcript += `[${item.role.toUpperCase()}]:\n${item.content}\n\n`;
        transcript += `--------------------------------------------------------\n\n`;
    });

    const blob = new Blob([transcript], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ClaimLens_Copilot_Transcript_${assistantSelectedClaimId || 'Global'}_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast('Chat transcript exported successfully!', 'success');
}

function setupAssistantSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
        assistantSpeechRec = new SpeechRecognition();
        assistantSpeechRec.continuous = false;
        assistantSpeechRec.interimResults = false;
        assistantSpeechRec.lang = 'en-US';

        assistantSpeechRec.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const input = document.getElementById('assistant-input-text');
            if (input) {
                input.value = (input.value ? input.value + ' ' : '') + transcript;
                autoResizeTextarea(input);
            }
            toast(`Heard: "${transcript}"`, 'info');
            stopVoiceInput();
        };

        assistantSpeechRec.onerror = (e) => {
            console.warn('Speech recognition error:', e);
            stopVoiceInput();
        };

        assistantSpeechRec.onend = () => {
            stopVoiceInput();
        };
    } catch (e) {
        console.warn('Speech setup error:', e);
    }
}

function toggleVoiceInput() {
    if (!assistantSpeechRec) {
        toast('Speech recognition not supported in this browser.', 'info');
        return;
    }
    if (isRecordingVoice) {
        stopVoiceInput();
    } else {
        startVoiceInput();
    }
}

function startVoiceInput() {
    try {
        assistantSpeechRec.start();
        isRecordingVoice = true;
        const btn = document.getElementById('assistant-voice-btn');
        if (btn) btn.classList.add('recording');
        toast('Listening... Speak your query clearly', 'info');
    } catch (e) {
        stopVoiceInput();
    }
}

function stopVoiceInput() {
    if (isRecordingVoice && assistantSpeechRec) {
        try { assistantSpeechRec.stop(); } catch (e) {}
    }
    isRecordingVoice = false;
    const btn = document.getElementById('assistant-voice-btn');
    if (btn) btn.classList.remove('recording');
}

function toggleFloatingAssistant() {
    const drawer = document.getElementById('floating-ai-drawer');
    if (!drawer) return;

    const isVisible = drawer.style.display !== 'none';
    drawer.style.display = isVisible ? 'none' : 'flex';

    if (!isVisible) {
        // Sync context with current view if claim is open
        if (currentClaimId && currentClaimId !== assistantSelectedClaimId) {
            selectAssistantClaim(currentClaimId);
        }
        const drawerBody = document.getElementById('drawer-messages-container');
        if (drawerBody) drawerBody.scrollTop = drawerBody.scrollHeight;
    }
}

function expandAssistantToFullScreen() {
    const drawer = document.getElementById('floating-ai-drawer');
    if (drawer) drawer.style.display = 'none';
    switchNav('assistant');
}

// ── Markdown Parser for Assistant Responses ──
function formatMarkdownToHTML(md) {
    if (!md) return '';

    let text = md;

    // Headings
    text = text.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^# (.*$)/gim, '<h3>$1</h3>');

    // Horizontal rules
    text = text.replace(/^---$/gim, '<hr>');

    // Tables
    const tableRegex = /((?:\|.+?\|\r?\n)+)/g;
    text = text.replace(tableRegex, (match) => {
        const rows = match.trim().split(/\r?\n/).map(r => r.trim());
        if (rows.length < 2) return match;

        let tableHtml = '<table><thead>';
        let isHeader = true;

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            if (row.includes('---')) {
                // Divider row
                isHeader = false;
                tableHtml += '</thead><tbody>';
                continue;
            }
            const cells = row.split('|').filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
            tableHtml += '<tr>';
            cells.forEach(cell => {
                const tag = isHeader ? 'th' : 'td';
                tableHtml += `<${tag}>${formatInlineMarkdown(cell.trim())}</${tag}>`;
            });
            tableHtml += '</tr>';
        }
        tableHtml += '</tbody></table>';
        return tableHtml;
    });

    // Unordered lists
    text = text.replace(/^\s*[-*]\s+(.*$)/gim, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
    // Clean up multiple consecutive <ul> tags
    text = text.replace(/<\/ul>\s*<ul>/gim, '');

    // Numbered lists
    text = text.replace(/^\s*\d+\.\s+(.*$)/gim, '<li>$1</li>');

    // Format paragraphs & inline markdown
    const lines = text.split(/\n\n+/);
    text = lines.map(block => {
        block = block.trim();
        if (block.startsWith('<h') || block.startsWith('<table') || block.startsWith('<ul') || block.startsWith('<hr')) {
            return block;
        }
        return `<p>${formatInlineMarkdown(block)}</p>`;
    }).join('');

    return text;
}

function formatInlineMarkdown(str) {
    return str
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}


