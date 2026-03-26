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
    // Update active button highlight
    ['risk-asc','risk-desc','price-asc','price-desc'].forEach(k => {
        document.getElementById(`btn-${k}`)
            .classList.toggle('active-sort', k === key);
    });
    renderResults(sortedProducts());
}

function renderSortBar() {
    document.getElementById('sortBar').classList.remove('hidden');
    // Reset to default active button
    setSort(activeSort);
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
                <p class="text-sm font-black text-white uppercase tracking-wide mb-2">Safety Overview</p>
                <div class="space-y-1.5">
                    ${riskBar('HIGH',   high, total, '🔴 Avoid')}
                    ${riskBar('MEDIUM', med,  total, '🟡 Check first')}
                    ${riskBar('LOW',    low,  total, '🟢 Looks safe')}
                </div>
            </div>

            ${ps.median ? `
            <div class="flex-1 min-w-[160px]">
                <p class="text-sm font-black text-white uppercase tracking-wide mb-2">Typical Price</p>
                <p class="text-3xl font-black text-white">$${ps.median.toFixed(0)}</p>
                <p class="text-sm font-semibold text-white mt-1">Range $${ps.min.toFixed(0)} – $${ps.max.toFixed(0)}</p>
            </div>
            ` : ''}

            <div class="flex-1 min-w-[140px]">
                <p class="text-sm font-black text-white uppercase tracking-wide mb-2">Listings Found</p>
                <p class="text-3xl font-black text-white">${data.valid_products || 0}</p>
                <p class="text-sm font-semibold text-white mt-1">${(data.platforms_searched||[]).map(s => s === 'google_shopping' ? 'Google' : 'eBay').join(' + ')}${data.filtered_out ? ` · ${data.filtered_out} removed` : ''}</p>
            </div>

            ${ds.duplicate_groups > 0 ? `
            <div class="flex-1 min-w-[140px]">
                <p class="text-sm font-black text-white uppercase tracking-wide mb-2">Same Item, Different Sellers</p>
                <p class="text-3xl font-black text-purple-300">${ds.total_duplicates}</p>
                <p class="text-sm font-semibold text-white mt-1">${ds.duplicate_groups} group${ds.duplicate_groups!==1?'s':''} · ${ds.cross_platform_pairs} cross-platform</p>
            </div>
            ` : ''}

        </div>
        ${data.category_warning ? `<p class="mt-4 text-xs text-amber-300 rounded px-3 py-2" style="background:rgba(245,158,11,0.12);border:1px solid rgba(251,191,36,0.3)">${data.category_warning}</p>` : ''}
    `;

    document.getElementById('summaryBar').classList.remove('hidden');
    document.getElementById('summaryBar').style.display = 'flex';
}

function riskBar(level, count, total, label) {
    const colors = { HIGH:'#f87171', MEDIUM:'#fbbf24', LOW:'#4ade80' };
    const pct = Math.round((count / total) * 100);
    return `
        <div class="flex items-center gap-2">
            <span class="text-sm font-bold text-white w-32">${label}</span>
            <div class="bar-bg flex-1"><div class="bar-fill" style="width:${pct}%;background:${colors[level]}"></div></div>
            <span class="text-sm font-black text-white w-8 text-right">${count}</span>
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
    card.className = 'glass rounded-xl overflow-hidden flex flex-col hover:shadow-2xl transition-shadow';

    // Use XGBoost level as primary signal when available
    const primaryLevel = p.xgb_risk_level || p.risk_level || 'UNKNOWN';
    const xgbScore     = p.xgb_score;
    const ruleScore    = p.risk_score || 0;
    const fa           = p.fraud_analysis || {};
    const redFlags     = fa.red_flags || [];
    const link         = p.link || p.product_link || '';

    // Trust score = inverse of the primary risk score (user-facing %)
    let trustPct = Math.round((1 - (xgbScore ?? ruleScore)) * 100);

    // Cap trust based on LLM recommendation — prevents "100% safe + AVOID" contradiction
    const rec = fa.recommendation || '';
    if (rec.includes('AVOID'))   trustPct = Math.min(trustPct, 20);
    else if (rec.includes('CAUTION')) trustPct = Math.min(trustPct, 55);

    const trustColor = trustPct >= 75 ? '#4ade80' : trustPct >= 45 ? '#fbbf24' : '#f87171';

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
        <div class="relative bg-black/20 p-2">
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
                <h3 class="font-bold text-white text-sm leading-snug line-clamp-2 mb-1">${escHtml(p.title)}</h3>
                <div class="flex items-baseline justify-between">
                    <span class="text-2xl font-black text-cyan-400">$${p.price != null ? Number(p.price).toLocaleString() : '—'}</span>
                    ${condLabel ? `<span class="text-xs text-blue-200/70 font-medium">${condLabel}</span>` : ''}
                </div>
            </div>

            <!-- Trust meter -->
            <div style="background:rgba(255,255,255,0.06);border-radius:12px;padding:12px;">
                <div class="flex items-center justify-between mb-1.5">
                    <span class="text-xs font-bold text-blue-200">Safety Score</span>
                    <span class="text-sm font-black" style="color:${trustColor}">${trustPct}%</span>
                </div>
                <div class="bar-bg"><div class="bar-fill" style="width:${trustPct}%;background:${trustColor}"></div></div>
                <p class="text-xs mt-1.5 font-semibold" style="color:${trustColor}">${safetyVerdict(primaryLevel, trustPct)}</p>
            </div>

            <!-- Models disagree -->
            ${conflict ? `
            <div class="conflict-banner rounded-lg px-3 py-2 text-xs text-amber-300"
                 style="background:rgba(245,158,11,0.12);border-left:3px solid #f59e0b">
                ⚠️ Our two AI models gave different signals — double-check this listing before buying.
            </div>
            ` : ''}

            <!-- Price context -->
            ${priceNote ? `<p class="text-xs text-blue-200">${priceNote}</p>` : ''}

            <!-- Rating -->
            <div class="flex items-center gap-3 text-xs text-blue-200">
                ${ratingDisplay(p)}
                ${p.source ? `<span class="text-white/25">·</span><span class="truncate text-blue-200/70">${escHtml(p.source)}</span>` : ''}
            </div>

            <!-- AI explanation -->
            ${fa.reasoning ? `
            <p class="text-xs text-blue-100 leading-relaxed border-t pt-3" style="border-color:rgba(255,255,255,0.1)">${escHtml(fa.reasoning)}</p>
            ` : ''}

            <!-- Red flags in plain English -->
            ${redFlags.length > 0 ? `
            <div style="background:rgba(220,38,38,0.15);border:1px solid rgba(248,113,113,0.3);border-radius:8px;padding:10px;">
                <p class="text-xs font-bold text-red-400 mb-1">Things to watch out for</p>
                <ul class="text-xs text-red-300 space-y-0.5">
                    ${redFlags.map(f => `<li>• ${friendlyFlag(f)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            <!-- Duplicate / cross-platform notice -->
            ${p.is_cross_platform ? `
            <div style="background:rgba(59,130,246,0.15);border:1px solid rgba(96,165,250,0.3);border-radius:8px;" class="px-3 py-2 text-xs text-blue-300">
                🔁 This item appears on multiple platforms — compare prices before buying.
            </div>
            ` : p.duplicate_group != null ? `
            <div style="background:rgba(139,92,246,0.15);border:1px solid rgba(167,139,250,0.3);border-radius:8px;" class="px-3 py-2 text-xs text-purple-300">
                👯 Multiple sellers listing the same item — you may find a better deal elsewhere.
            </div>
            ` : ''}

            <!-- CTA -->
            <div class="mt-auto pt-3 flex items-center justify-between gap-3" style="border-top:1px solid rgba(255,255,255,0.1)">
                <span class="text-xs font-black ${recBadgeClass(fa.recommendation)}">${friendlyRec(fa.recommendation)}</span>
                ${link ? `
                    <a href="${link}" target="_blank" rel="noopener"
                       class="px-5 py-2 bg-blue-500 hover:bg-blue-400 text-white text-xs font-bold rounded-lg transition-colors">
                        View listing →
                    </a>
                ` : `<span class="text-xs text-white/25">No link</span>`}
            </div>

        </div>
    `;

    return card;
}

// ── User-friendly helpers ─────────────────────────────────────────────

function safetyVerdict(level, pct) {
    // Drive verdict from trustPct so bar and text are always consistent
    if (pct >= 70) return '✅ Looks legitimate — safe to consider';
    if (pct >= 40) return '⚠️ Some concerns — verify before buying';
    return '🚫 High risk — we recommend avoiding this';
}

function friendlyRec(rec) {
    if (!rec) return '—';
    if (rec.includes('SAFE'))    return '✅ Safe to buy';
    if (rec.includes('CAUTION')) return '⚠️ Proceed with caution';
    return '🚫 Avoid this listing';
}

function recBadgeClass(rec) {
    if (!rec) return 'text-white/40';
    if (rec.includes('SAFE'))    return 'text-green-400';
    if (rec.includes('CAUTION')) return 'text-yellow-400';
    return 'text-red-400';
}

function priceContext(p) {
    if (!p.price_tier) return '';
    const isUsed = p.condition === 'used' || p.condition === 'refurbished';
    switch (p.price_tier) {
        case 'extremely_cheap':
            if (isUsed)
                return `🔻 Much cheaper than other listings — expected for older/used models, but verify condition`;
            return `🔻 Price is suspiciously low — investigate before buying`;
        case 'budget':
            return isUsed
                ? `💲 Good price for a used item — verify condition and seller`
                : `💲 Below-average price — worth verifying condition`;
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

function ratingDisplay(p) {
    const seller = p.seller || {};
    const feedbackPct = seller.feedback_pct;
    const sellerReviews = seller.reviews;

    if (p.rating > 0) {
        return `<span>⭐ ${p.rating}${p.reviews > 0 ? ` <span class="text-blue-300/60">(${fmtNum(p.reviews)})</span>` : ''}</span>`;
    }
    // eBay: use seller feedback % as proxy
    if (feedbackPct > 0) {
        const color = feedbackPct >= 98 ? 'text-green-400' : feedbackPct >= 95 ? 'text-yellow-400' : 'text-red-400';
        return `<span class="${color} font-medium">👤 ${feedbackPct}% positive${sellerReviews > 0 ? ` <span class="text-blue-300/60">(${fmtNum(sellerReviews)} seller ratings)</span>` : ''}</span>`;
    }
    return `<span class="text-amber-400 font-medium">⚠ No reviews yet</span>`;
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
