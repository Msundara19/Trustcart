const API_BASE = window.location.origin;

// ── Stage animation ───────────────────────────────────────────────────

const STAGE_TIMINGS = [0, 800, 1800, 2800, 4200]; // ms after search starts
let stageTimer = null;

function startStageAnimation() {
    // Reset all stages
    for (let i = 0; i < 5; i++) {
        const el = document.getElementById(`stage-${i}`);
        el.classList.remove('active', 'done');
        const st = document.getElementById(`stage-status-${i}`);
        st.innerHTML = '';
    }

    // Activate each stage on a timer
    STAGE_TIMINGS.forEach((delay, i) => {
        setTimeout(() => {
            // Mark previous as done
            if (i > 0) {
                document.getElementById(`stage-${i-1}`).classList.add('done');
                document.getElementById(`stage-${i-1}`).classList.remove('active');
                document.getElementById(`stage-status-${i-1}`).innerHTML =
                    `<span style="color:#4ade80;font-size:.8rem;font-weight:700">✓</span>`;
            }
            const el = document.getElementById(`stage-${i}`);
            el.classList.add('active');
            document.getElementById(`stage-status-${i}`).innerHTML =
                `<span class="dot w-2 h-2 rounded-full inline-block" style="background:#38bdf8"></span>`;
        }, delay);
    });
}

function stopStageAnimation() {
    // Mark all as done
    for (let i = 0; i < 5; i++) {
        const el = document.getElementById(`stage-${i}`);
        el.classList.add('done');
        el.classList.remove('active');
        const st = document.getElementById(`stage-status-${i}`);
        st.innerHTML = `<span style="color:#4ade80;font-size:.8rem;font-weight:700">✓</span>`;
    }
}

// ── Search ────────────────────────────────────────────────────────────

async function searchProducts() {
    const query      = document.getElementById('searchQuery').value.trim();
    const platform   = document.getElementById('platformSelect').value;
    const numResults = document.getElementById('numResults').value;
    const maxPrice   = document.getElementById('maxPrice').value;

    if (!query) { alert('Please enter a product name'); return; }

    setLoading(true);
    startStageAnimation();

    try {
        let url = `${API_BASE}/api/search/${encodeURIComponent(query)}?platform=${platform}&num_results=${numResults}`;
        if (maxPrice && maxPrice > 0) url += `&max_price=${maxPrice}`;

        const res  = await fetch(url);
        const data = await res.json();

        stopStageAnimation();
        // Brief pause so user sees the completed stages
        await new Promise(r => setTimeout(r, 500));

        setLoading(false);
        renderSummaryBar(data);
        renderResults(data.products || []);

    } catch (err) {
        setLoading(false);
        alert('Error fetching results. Check the console for details.');
        console.error(err);
    }
}

// ── State helpers ─────────────────────────────────────────────────────

function setLoading(on) {
    document.getElementById('loadingState').classList.toggle('hidden', !on);
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('summaryBar').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('searchBtn').disabled = on;
}

// ── Summary bar ───────────────────────────────────────────────────────

function renderSummaryBar(data) {
    const rs   = data.risk_summary     || {};
    const ps   = data.price_statistics || {};
    const ds   = data.duplicate_summary || {};
    const high = rs.high_risk_count    || 0;
    const med  = rs.medium_risk_count  || 0;
    const low  = rs.low_risk_count     || 0;
    const total = high + med + low || 1;

    const pct = (n, t) => Math.round((n / t) * 100);

    document.getElementById('summaryContent').innerHTML = `
        <div class="flex flex-wrap gap-6 items-start">

                <!-- Risk breakdown -->
                <div class="flex-1 min-w-[200px]">
                    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Risk Breakdown</p>
                    <div class="space-y-1.5">
                        ${riskBar('HIGH',   high, total)}
                        ${riskBar('MEDIUM', med,  total)}
                        ${riskBar('LOW',    low,  total)}
                    </div>
                </div>

                <!-- Price stats -->
                ${ps.median ? `
                <div class="flex-1 min-w-[160px]">
                    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Price Range</p>
                    <p class="text-2xl font-bold text-gray-800">$${ps.median.toFixed(0)}<span class="text-sm font-normal text-gray-400"> median</span></p>
                    <p class="text-xs text-gray-400 mt-1">$${ps.min.toFixed(0)} – $${ps.max.toFixed(0)} &nbsp;·&nbsp; σ $${ps.std_dev.toFixed(0)}</p>
                </div>
                ` : ''}

                <!-- Counts -->
                <div class="flex-1 min-w-[160px]">
                    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Results</p>
                    <p class="text-2xl font-bold text-gray-800">${data.valid_products || 0}<span class="text-sm font-normal text-gray-400"> products</span></p>
                    <p class="text-xs text-gray-400 mt-1">${(data.platforms_searched||[]).join(' + ')}${data.filtered_out ? ` · ${data.filtered_out} filtered` : ''}</p>
                </div>

                <!-- Duplicates -->
                ${ds.duplicate_groups > 0 ? `
                <div class="flex-1 min-w-[160px]">
                    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Duplicates</p>
                    <p class="text-2xl font-bold text-purple-700">${ds.duplicate_groups}<span class="text-sm font-normal text-gray-400"> group${ds.duplicate_groups !== 1 ? 's' : ''}</span></p>
                    <p class="text-xs text-gray-400 mt-1">${ds.total_duplicates} listings · ${ds.cross_platform_pairs} cross-platform</p>
                </div>
                ` : ''}

            </div>
            ${data.category_warning ? `<p class="mt-4 text-xs text-amber-700 bg-amber-50 rounded px-3 py-2">${data.category_warning}</p>` : ''}
        </div>
    `;

    document.getElementById('summaryBar').classList.remove('hidden');
    document.getElementById('summaryBar').style.display = 'flex';
}

function riskBar(level, count, total) {
    const colors = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#22c55e' };
    const pct = Math.round((count / total) * 100);
    return `
        <div class="flex items-center gap-2">
            <span class="text-xs w-14 text-gray-600">${level}</span>
            <div class="bar-bg flex-1">
                <div class="bar-fill" style="width:${pct}%;background:${colors[level]}"></div>
            </div>
            <span class="text-xs font-semibold text-gray-700 w-6 text-right">${count}</span>
        </div>
    `;
}

// ── Results grid ──────────────────────────────────────────────────────

function renderResults(products) {
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';

    if (!products.length) {
        grid.innerHTML = '<div class="col-span-full text-center py-12 text-gray-400">No products found.</div>';
    } else {
        products.forEach((p, i) => {
            const card = createCard(p);
            card.style.animationDelay = `${i * 30}ms`;
            card.classList.add('card-enter');
            grid.appendChild(card);
        });
    }

    document.getElementById('resultsSection').classList.remove('hidden');
}

// ── Card ──────────────────────────────────────────────────────────────

function createCard(p) {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex flex-col';

    const riskLevel  = p.risk_level  || 'UNKNOWN';
    const xgbLevel   = p.xgb_risk_level;
    const xgbScore   = p.xgb_score;
    const ruleScore  = p.risk_score  || 0;
    const fa         = p.fraud_analysis || {};
    const redFlags   = fa.red_flags  || [];
    const link       = p.link || p.product_link || '';

    // Conflict: rule says LOW but XGB says HIGH (or vice versa — show a warning)
    const conflict = xgbLevel && riskLevel !== xgbLevel &&
                     ((riskLevel === 'LOW' && xgbLevel === 'HIGH') ||
                      (riskLevel === 'HIGH' && xgbLevel === 'LOW'));

    card.innerHTML = `
        <!-- Thumbnail -->
        ${p.thumbnail ? `
            <div class="relative">
                <img src="${p.thumbnail}" alt="${escHtml(p.title)}"
                     class="w-full h-44 object-contain bg-gray-50 rounded-t-xl p-2">
                <!-- Platform badge -->
                <span class="absolute top-2 right-2 pill" style="background:#1e293b;color:#f8fafc;font-size:0.65rem">
                    ${p.platform === 'ebay' ? 'eBay' : 'Google'}
                </span>
            </div>
        ` : `
            <div class="h-8 bg-gray-50 rounded-t-xl flex items-center justify-end px-3">
                <span class="pill" style="background:#1e293b;color:#f8fafc;font-size:0.65rem">
                    ${p.platform === 'ebay' ? 'eBay' : 'Google'}
                </span>
            </div>
        `}

        <div class="p-4 flex flex-col flex-1 gap-3">

            <!-- Title & price -->
            <div>
                <h3 class="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 mb-1">${escHtml(p.title)}</h3>
                <div class="flex items-baseline justify-between">
                    <span class="text-xl font-bold text-blue-600">$${p.price != null ? p.price.toLocaleString() : '—'}</span>
                    <span class="text-xs text-gray-400">${escHtml(p.source || '')}</span>
                </div>
            </div>

            <!-- Risk badges row -->
            <div class="flex flex-wrap gap-1.5 items-center">
                <span class="pill risk-badge-${riskLevel}">
                    ${riskIcon(riskLevel)} Rule: ${riskLevel}
                </span>
                ${xgbLevel ? `
                <span class="pill risk-badge-${xgbLevel}">
                    🤖 XGB: ${xgbLevel}
                    ${xgbScore != null ? `<span class="opacity-60">${(xgbScore * 100).toFixed(0)}%</span>` : ''}
                </span>
                ` : ''}
                ${p.duplicate_group != null ? `<span class="pill dup-badge">⬡ Dup #${p.duplicate_group}</span>` : ''}
                ${p.is_cross_platform ? `<span class="pill cross-badge">↔ Cross-platform</span>` : ''}
            </div>

            <!-- Model conflict warning -->
            ${conflict ? `
            <div class="conflict-banner rounded px-3 py-2 text-xs text-amber-800">
                ⚠️ Models disagree — rule-based says <strong>${riskLevel}</strong>, XGBoost says <strong>${xgbLevel}</strong>. Review carefully.
            </div>
            ` : ''}

            <!-- Score bars -->
            <div class="space-y-1.5">
                ${scoreLine('Rule score', ruleScore, riskLevel)}
                ${xgbScore != null ? scoreLine('XGB score', xgbScore, xgbLevel) : ''}
            </div>

            <!-- Price tier -->
            ${p.price_tier ? `
            <div class="flex items-center gap-2 text-xs text-gray-500">
                <span>${tierEmoji(p.price_tier)}</span>
                <span class="capitalize">${p.price_tier.replace('_', ' ')}</span>
                <span class="ml-auto">p${p.price_percentile ?? '?'}</span>
                <div class="bar-bg w-16">
                    <div class="bar-fill" style="width:${p.price_percentile ?? 50}%;background:#6366f1"></div>
                </div>
            </div>
            ` : ''}

            <!-- Rating / reviews / condition -->
            <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
                ${p.rating > 0 ? `<span>★ ${p.rating}${p.reviews > 0 ? ` (${fmtNum(p.reviews)})` : ''}</span>` : '<span class="text-amber-600">No rating</span>'}
                ${p.condition ? `<span>· ${p.condition}</span>` : ''}
            </div>

            <!-- AI reasoning -->
            ${fa.reasoning ? `
            <p class="text-xs text-gray-600 leading-relaxed border-t border-gray-100 pt-3">${escHtml(fa.reasoning)}</p>
            ` : ''}

            <!-- Red flags -->
            ${redFlags.length > 0 ? `
            <div>
                <p class="text-xs font-semibold text-red-600 mb-1">⚠ Red flags</p>
                <ul class="text-xs text-gray-600 space-y-0.5">
                    ${redFlags.map(f => `<li>• ${escHtml(f)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            <!-- Similar-to (duplicate info) -->
            ${(p.similar_to || []).length > 0 ? `
            <div class="text-xs text-purple-700 bg-purple-50 rounded px-2 py-1.5">
                Similar to: ${p.similar_to.map(s =>
                    `<span class="font-medium">${escHtml(s.title.slice(0,40))}…</span> <span class="opacity-60">(${(s.similarity*100).toFixed(0)}%)</span>`
                ).join(', ')}
            </div>
            ` : ''}

            <!-- Recommendation + CTA -->
            <div class="mt-auto pt-3 border-t border-gray-100 flex items-center justify-between gap-3">
                <span class="text-xs font-bold ${recColor(fa.recommendation)}">${fa.recommendation || '—'}</span>
                ${link ? `
                    <a href="${link}" target="_blank" rel="noopener"
                       class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors">
                        View →
                    </a>
                ` : `
                    <span class="px-4 py-1.5 bg-gray-100 text-gray-400 text-xs rounded-lg">No link</span>
                `}
            </div>

        </div>
    `;

    return card;
}

// ── Helpers ───────────────────────────────────────────────────────────

function riskIcon(level) {
    return { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢' }[level] || '⚪';
}

function tierEmoji(tier) {
    return { extremely_cheap: '🔻', budget: '💲', mid: '〰️', premium: '💎', luxury: '👑', outlier_high: '📈' }[tier] || '';
}

function recColor(rec) {
    if (!rec) return 'text-gray-500';
    if (rec.includes('SAFE'))    return 'text-green-600';
    if (rec.includes('CAUTION')) return 'text-yellow-600';
    return 'text-red-600';
}

function scoreLine(label, score, level) {
    const colors = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#22c55e', UNKNOWN: '#9ca3af' };
    const pct    = Math.min(Math.round(score * 100), 100);
    return `
        <div class="flex items-center gap-2 text-xs">
            <span class="text-gray-400 w-20 shrink-0">${label}</span>
            <div class="bar-bg flex-1">
                <div class="bar-fill" style="width:${pct}%;background:${colors[level]||'#9ca3af'}"></div>
            </div>
            <span class="font-semibold ${level === 'HIGH' ? 'xgb-HIGH' : level === 'MEDIUM' ? 'xgb-MEDIUM' : 'xgb-LOW'} w-8 text-right">${pct}%</span>
        </div>
    `;
}

function fmtNum(n) {
    if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
    return n;
}

function escHtml(str) {
    return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
