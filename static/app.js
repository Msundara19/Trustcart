const API_BASE = window.location.origin;
let allProducts = [];   // keep original for re-sorting
let activeSort  = 'risk-asc'; // default sort

// ── Stage animation ───────────────────────────────────────────────────

const STAGE_TIMINGS = [0, 800, 1800, 2800, 4200];

function startStageAnimation() {
    for (let i = 0; i < 5; i++) {
        document.getElementById(`stage-${i}`).classList.remove('active','done');
        document.getElementById(`stage-status-${i}`).innerHTML = '';
    }
    STAGE_TIMINGS.forEach((delay, i) => {
        setTimeout(() => {
            if (i > 0) {
                document.getElementById(`stage-${i-1}`).classList.replace('active','done');
                document.getElementById(`stage-status-${i-1}`).innerHTML =
                    `<span style="color:#4ade80;font-size:.8rem;font-weight:700">✓</span>`;
            }
            document.getElementById(`stage-${i}`).classList.add('active');
            document.getElementById(`stage-status-${i}`).innerHTML =
                `<span class="dot w-2 h-2 rounded-full inline-block" style="background:#38bdf8"></span>`;
        }, delay);
    });
}

function stopStageAnimation() {
    for (let i = 0; i < 5; i++) {
        const el = document.getElementById(`stage-${i}`);
        el.classList.add('done'); el.classList.remove('active');
        document.getElementById(`stage-status-${i}`).innerHTML =
            `<span style="color:#4ade80;font-size:.8rem;font-weight:700">✓</span>`;
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
        await new Promise(r => setTimeout(r, 500));

        allProducts = data.products || [];
        activeSort  = 'risk-asc';

        setLoading(false);
        renderSummaryBar(data);
        renderSortBar();
        renderResults(sortedProducts());

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
    document.getElementById('sortBar').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('searchBtn').disabled = on;
}

// ── Sort ──────────────────────────────────────────────────────────────

const SORT_OPTIONS = [
    { key: 'risk-asc',   label: '🛡 Safest first' },
    { key: 'risk-desc',  label: '⚠️ Riskiest first' },
    { key: 'price-asc',  label: '💲 Price: Low → High' },
    { key: 'price-desc', label: '💰 Price: High → Low' },
];

function riskOrder(p) {
    const level = p.xgb_risk_level || p.risk_level || 'UNKNOWN';
    return { LOW: 0, MEDIUM: 1, HIGH: 2, UNKNOWN: 1 }[level] ?? 1;
}

function sortedProducts() {
    const arr = [...allProducts];
    switch (activeSort) {
        case 'risk-asc':   return arr.sort((a,b) => riskOrder(a) - riskOrder(b));
        case 'risk-desc':  return arr.sort((a,b) => riskOrder(b) - riskOrder(a));
        case 'price-asc':  return arr.sort((a,b) => (a.price||0) - (b.price||0));
        case 'price-desc': return arr.sort((a,b) => (b.price||0) - (a.price||0));
        default:           return arr;
    }
}

function setSort(key) {
    activeSort = key;
    renderSortBar();
    renderResults(sortedProducts());
}

function renderSortBar() {
    const bar = document.getElementById('sortBar');
    bar.innerHTML = `
        <div class="flex flex-wrap items-center gap-2 max-w-7xl mx-auto">
            <span class="text-white/60 text-xs font-semibold uppercase tracking-wide mr-1">Sort by</span>
            ${SORT_OPTIONS.map(o => `
                <button onclick="setSort('${o.key}')"
                    class="px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
                        activeSort === o.key
                        ? 'bg-white text-blue-700 shadow'
                        : 'bg-white/10 text-white/80 hover:bg-white/20'
                    }">
                    ${o.label}
                </button>
            `).join('')}
        </div>
    `;
    bar.classList.remove('hidden');
}

// ── Summary bar ───────────────────────────────────────────────────────

function renderSummaryBar(data) {
    const rs    = data.risk_summary     || {};
    const ps    = data.price_statistics || {};
    const ds    = data.duplicate_summary || {};
    const high  = rs.high_risk_count   || 0;
    const med   = rs.medium_risk_count || 0;
    const low   = rs.low_risk_count    || 0;
    const total = high + med + low || 1;

    document.getElementById('summaryContent').innerHTML = `
        <div class="flex flex-wrap gap-6 items-start">

            <div class="flex-1 min-w-[200px]">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Safety Overview</p>
                <div class="space-y-1.5">
                    ${riskBar('HIGH',   high, total, '🔴 Avoid')}
                    ${riskBar('MEDIUM', med,  total, '🟡 Check first')}
                    ${riskBar('LOW',    low,  total, '🟢 Looks safe')}
                </div>
            </div>

            ${ps.median ? `
            <div class="flex-1 min-w-[160px]">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Typical Price</p>
                <p class="text-2xl font-bold text-gray-800">$${ps.median.toFixed(0)}</p>
                <p class="text-xs text-gray-400 mt-1">Range $${ps.min.toFixed(0)} – $${ps.max.toFixed(0)}</p>
            </div>
            ` : ''}

            <div class="flex-1 min-w-[140px]">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Listings Found</p>
                <p class="text-2xl font-bold text-gray-800">${data.valid_products || 0}</p>
                <p class="text-xs text-gray-400 mt-1">${(data.platforms_searched||[]).map(s => s === 'google_shopping' ? 'Google' : 'eBay').join(' + ')}${data.filtered_out ? ` · ${data.filtered_out} removed` : ''}</p>
            </div>

            ${ds.duplicate_groups > 0 ? `
            <div class="flex-1 min-w-[140px]">
                <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Same Item, Different Sellers</p>
                <p class="text-2xl font-bold text-purple-700">${ds.total_duplicates}</p>
                <p class="text-xs text-gray-400 mt-1">${ds.duplicate_groups} group${ds.duplicate_groups!==1?'s':''} · ${ds.cross_platform_pairs} cross-platform</p>
            </div>
            ` : ''}

        </div>
        ${data.category_warning ? `<p class="mt-4 text-xs text-amber-700 bg-amber-50 rounded px-3 py-2">${data.category_warning}</p>` : ''}
    `;

    document.getElementById('summaryBar').classList.remove('hidden');
    document.getElementById('summaryBar').style.display = 'flex';
}

function riskBar(level, count, total, label) {
    const colors = { HIGH:'#ef4444', MEDIUM:'#f59e0b', LOW:'#22c55e' };
    const pct = Math.round((count / total) * 100);
    return `
        <div class="flex items-center gap-2">
            <span class="text-xs w-28 text-gray-600">${label}</span>
            <div class="bar-bg flex-1"><div class="bar-fill" style="width:${pct}%;background:${colors[level]}"></div></div>
            <span class="text-xs font-bold text-gray-700 w-5 text-right">${count}</span>
        </div>`;
}

// ── Results grid ──────────────────────────────────────────────────────

function renderResults(products) {
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';
    if (!products.length) {
        grid.innerHTML = '<div class="col-span-full text-center py-12 text-white/50">No products found.</div>';
    } else {
        products.forEach((p, i) => {
            const card = createCard(p);
            card.style.animationDelay = `${i * 25}ms`;
            card.classList.add('card-enter');
            grid.appendChild(card);
        });
    }
    document.getElementById('resultsSection').classList.remove('hidden');
}

// ── Card ──────────────────────────────────────────────────────────────

function createCard(p) {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-lg transition-shadow flex flex-col overflow-hidden';

    // Use XGBoost level as primary signal when available
    const primaryLevel = p.xgb_risk_level || p.risk_level || 'UNKNOWN';
    const xgbScore     = p.xgb_score;
    const ruleScore    = p.risk_score || 0;
    const fa           = p.fraud_analysis || {};
    const redFlags     = fa.red_flags || [];
    const link         = p.link || p.product_link || '';

    // Trust score = inverse of the primary risk score (user-facing %)
    const trustPct = Math.round((1 - (xgbScore ?? ruleScore)) * 100);
    const trustColor = trustPct >= 75 ? '#16a34a' : trustPct >= 45 ? '#d97706' : '#dc2626';

    // Models disagree
    const conflict = p.xgb_risk_level && p.risk_level &&
                     p.xgb_risk_level !== p.risk_level &&
                     ((p.risk_level === 'LOW' && p.xgb_risk_level === 'HIGH') ||
                      (p.risk_level === 'HIGH' && p.xgb_risk_level === 'LOW'));

    // Price context in plain English
    const priceNote = priceContext(p);

    // Friendly condition label
    const condLabel = { new:'New', used:'Used', refurbished:'Refurbished', unknown:'' }[p.condition] || '';

    // Platform display
    const platformLabel = p.platform === 'ebay' ? 'eBay' : 'Google Shopping';
    const platformColor = p.platform === 'ebay' ? '#e53e3e' : '#4285f4';

    card.innerHTML = `
        <!-- Top colour strip based on safety -->
        <div style="height:4px;background:${trustColor};width:100%"></div>

        ${p.thumbnail ? `
        <div class="relative bg-gray-50 p-2">
            <img src="${escHtml(p.thumbnail)}" alt="${escHtml(p.title)}"
                 class="w-full h-40 object-contain">
            <span class="absolute top-2 right-2 text-xs font-bold px-2 py-0.5 rounded-full text-white"
                  style="background:${platformColor}">${platformLabel}</span>
        </div>
        ` : `
        <div class="flex justify-end px-3 pt-2">
            <span class="text-xs font-bold px-2 py-0.5 rounded-full text-white"
                  style="background:${platformColor}">${platformLabel}</span>
        </div>
        `}

        <div class="p-4 flex flex-col flex-1 gap-3">

            <!-- Title + price -->
            <div>
                <h3 class="font-bold text-gray-900 text-sm leading-snug line-clamp-2 mb-1">${escHtml(p.title)}</h3>
                <div class="flex items-baseline justify-between">
                    <span class="text-2xl font-black text-blue-600">$${p.price != null ? Number(p.price).toLocaleString() : '—'}</span>
                    ${condLabel ? `<span class="text-xs text-gray-400 font-medium">${condLabel}</span>` : ''}
                </div>
            </div>

            <!-- Trust meter -->
            <div class="bg-gray-50 rounded-xl p-3">
                <div class="flex items-center justify-between mb-1.5">
                    <span class="text-xs font-bold text-gray-600">Safety Score</span>
                    <span class="text-sm font-black" style="color:${trustColor}">${trustPct}%</span>
                </div>
                <div class="bar-bg"><div class="bar-fill" style="width:${trustPct}%;background:${trustColor}"></div></div>
                <p class="text-xs mt-1.5 font-semibold" style="color:${trustColor}">${safetyVerdict(primaryLevel, trustPct)}</p>
            </div>

            <!-- Models disagree -->
            ${conflict ? `
            <div class="conflict-banner rounded-lg px-3 py-2 text-xs text-amber-800">
                ⚠️ Our two AI models gave different signals — double-check this listing before buying.
            </div>
            ` : ''}

            <!-- Price context -->
            ${priceNote ? `<p class="text-xs text-gray-500">${priceNote}</p>` : ''}

            <!-- Rating -->
            <div class="flex items-center gap-3 text-xs text-gray-500">
                ${p.rating > 0
                    ? `<span>⭐ ${p.rating} ${p.reviews > 0 ? `<span class="text-gray-400">(${fmtNum(p.reviews)} reviews)</span>` : ''}</span>`
                    : `<span class="text-amber-600 font-medium">⚠ No reviews yet</span>`}
                ${p.source ? `<span class="text-gray-300">·</span><span class="truncate">${escHtml(p.source)}</span>` : ''}
            </div>

            <!-- AI explanation -->
            ${fa.reasoning ? `
            <p class="text-xs text-gray-600 leading-relaxed border-t border-gray-100 pt-3">${escHtml(fa.reasoning)}</p>
            ` : ''}

            <!-- Red flags in plain English -->
            ${redFlags.length > 0 ? `
            <div class="bg-red-50 rounded-lg p-2.5">
                <p class="text-xs font-bold text-red-600 mb-1">Things to watch out for</p>
                <ul class="text-xs text-red-700 space-y-0.5">
                    ${redFlags.map(f => `<li>• ${friendlyFlag(f)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            <!-- Duplicate / cross-platform notice -->
            ${p.is_cross_platform ? `
            <div class="bg-blue-50 rounded-lg px-3 py-2 text-xs text-blue-700">
                🔁 This item appears on multiple platforms — compare prices before buying.
            </div>
            ` : p.duplicate_group != null ? `
            <div class="bg-purple-50 rounded-lg px-3 py-2 text-xs text-purple-700">
                👯 Multiple sellers listing the same item — you may find a better deal elsewhere.
            </div>
            ` : ''}

            <!-- CTA -->
            <div class="mt-auto pt-3 border-t border-gray-100 flex items-center justify-between gap-3">
                <span class="text-xs font-black ${recBadgeClass(fa.recommendation)}">${friendlyRec(fa.recommendation)}</span>
                ${link ? `
                    <a href="${link}" target="_blank" rel="noopener"
                       class="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg transition-colors">
                        View listing →
                    </a>
                ` : `<span class="text-xs text-gray-300">No link</span>`}
            </div>

        </div>
    `;

    return card;
}

// ── User-friendly helpers ─────────────────────────────────────────────

function safetyVerdict(level, pct) {
    if (level === 'LOW')    return '✅ Looks legitimate — safe to consider';
    if (level === 'MEDIUM') return '⚠️ Some concerns — verify before buying';
    return '🚫 High risk — we recommend avoiding this';
}

function friendlyRec(rec) {
    if (!rec) return '—';
    if (rec.includes('SAFE'))    return '✅ Safe to buy';
    if (rec.includes('CAUTION')) return '⚠️ Proceed with caution';
    return '🚫 Avoid this listing';
}

function recBadgeClass(rec) {
    if (!rec) return 'text-gray-400';
    if (rec.includes('SAFE'))    return 'text-green-600';
    if (rec.includes('CAUTION')) return 'text-yellow-600';
    return 'text-red-600';
}

function priceContext(p) {
    if (!p.price_tier) return '';
    const pct = p.price_percentile;
    switch (p.price_tier) {
        case 'extremely_cheap':
            return `🔻 Priced ${pct != null ? Math.round(100 - pct) + '% cheaper' : 'much cheaper'} than similar listings — investigate why`;
        case 'budget':
            return `💲 Below-average price — worth verifying condition`;
        case 'mid':
            return `〰️ Fairly priced compared to similar listings`;
        case 'premium':
            return `💎 Higher-end price — typical for this quality`;
        case 'luxury':
            return `👑 Among the most expensive for this product`;
        case 'outlier_high':
            return `📈 Unusually expensive — verify this is the right listing`;
        default: return '';
    }
}

function friendlyFlag(flag) {
    // Translate internal flag messages into plain consumer language
    if (flag.includes('Extremely cheap'))   return 'Price is suspiciously low compared to other listings';
    if (flag.includes('below typical'))     return 'Price is well below the typical market rate';
    if (flag.includes('No rating or reviews')) return 'This seller has no ratings or reviews yet';
    if (flag.includes('No rating'))         return 'No star rating available for this seller';
    if (flag.includes('Very few reviews')
     || flag.includes('Few reviews'))       return 'Very few customer reviews — hard to verify trustworthiness';
    if (flag.includes('Low rating'))        return `Low customer rating — check reviews carefully`;
    if (flag.includes('Low seller rating')) return 'This seller has a below-average reputation';
    if (flag.includes('condition unknown')) return 'Item condition is not clearly stated';
    if (flag.includes('Vague product'))     return 'Product description is very short or vague';
    if (flag.includes('High-value item from seller with no reviews'))
        return 'Expensive item from a seller with no track record';
    if (flag.includes('Lower-priced'))      return 'Priced lower than usual — confirm it meets your expectations';
    if (flag.includes('High-value or rare')) return 'Rare or high-value item — verify authenticity carefully';
    return flag; // fallback: show as-is
}

// ── Misc helpers ──────────────────────────────────────────────────────

function fmtNum(n) {
    if (n >= 1000) return (n / 1000).toFixed(0) + 'k';
    return String(n);
}

function escHtml(str) {
    return String(str || '')
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
