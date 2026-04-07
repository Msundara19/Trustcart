const API_BASE = window.location.origin;
let allProducts = [];
let activeSort  = 'risk-asc';

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
                    `<svg style="color:#4ade80;width:16px;height:16px" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>`;
            }
            document.getElementById(`stage-${i}`).classList.add('active');
            document.getElementById(`stage-status-${i}`).innerHTML =
                `<span class="dot w-1.5 h-1.5 rounded-full inline-block" style="background:#38bdf8"></span>`;
        }, delay);
    });
}

function stopStageAnimation() {
    for (let i = 0; i < 5; i++) {
        const el = document.getElementById(`stage-${i}`);
        el.classList.add('done'); el.classList.remove('active');
        document.getElementById(`stage-status-${i}`).innerHTML =
            `<svg style="color:#4ade80;width:16px;height:16px" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>`;
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
    ['risk-asc','risk-desc','price-asc','price-desc'].forEach(k => {
        document.getElementById(`btn-${k}`).classList.toggle('active-sort', k === key);
    });
    renderResults(sortedProducts());
}

function renderSortBar() {
    document.getElementById('sortBar').classList.remove('hidden');
    setSort(activeSort);
}

// ── Summary bar ───────────────────────────────────────────────────────

function renderSummaryBar(data) {
    const rs    = data.risk_summary      || {};
    const ps    = data.price_statistics  || {};
    const ds    = data.duplicate_summary || {};
    const high  = rs.high_risk_count   || 0;
    const med   = rs.medium_risk_count || 0;
    const low   = rs.low_risk_count    || 0;
    const total = high + med + low || 1;

    document.getElementById('summaryContent').innerHTML = `
        <div class="flex flex-wrap gap-3">

            <!-- Safety overview -->
            <div class="flex-1 min-w-[200px] rounded-xl p-4"
                 style="background:#eef7f1;border:1px solid rgba(0,0,0,0.06)">
                <p class="text-xs font-bold uppercase tracking-widest mb-3"
                   style="color:#6e9e82;letter-spacing:0.12em">Safety Overview</p>
                <div class="space-y-2.5">
                    ${summaryRiskBar('Avoid',  high, total, '#f87171')}
                    ${summaryRiskBar('Verify', med,  total, '#fbbf24')}
                    ${summaryRiskBar('Safe',   low,  total, '#4ade80')}
                </div>
            </div>

            ${ps.median != null ? `
            <div class="rounded-xl p-4 flex flex-col justify-between"
                 style="background:#eef7f1;border:1px solid rgba(0,0,0,0.06);min-width:130px">
                <p class="text-xs font-bold uppercase tracking-widest mb-2"
                   style="color:#6e9e82;letter-spacing:0.12em">Typical Price</p>
                <div>
                    <p class="text-2xl font-black" style="color:#0f2318">$${ps.median.toFixed(0)}</p>
                    <p class="text-xs mt-1" style="color:#6e9e82">$${ps.min.toFixed(0)} – $${ps.max.toFixed(0)}</p>
                </div>
            </div>
            ` : ''}

            <div class="rounded-xl p-4 flex flex-col justify-between"
                 style="background:#eef7f1;border:1px solid rgba(0,0,0,0.06);min-width:120px">
                <p class="text-xs font-bold uppercase tracking-widest mb-2"
                   style="color:#6e9e82;letter-spacing:0.12em">Listings Found</p>
                <div>
                    <p class="text-2xl font-black" style="color:#0f2318">${data.valid_products || 0}</p>
                    <p class="text-xs mt-1" style="color:#6e9e82">${(data.platforms_searched||[]).map(s => s === 'google_shopping' ? 'Google' : 'eBay').join(' + ')}${data.filtered_out ? ` · ${data.filtered_out} filtered` : ''}</p>
                </div>
            </div>

            ${ds.duplicate_groups > 0 ? `
            <div class="rounded-xl p-4 flex flex-col justify-between"
                 style="background:rgba(5,150,105,0.07);border:1px solid rgba(5,150,105,0.18);min-width:120px">
                <p class="text-xs font-bold uppercase tracking-widest mb-2"
                   style="color:#059669;letter-spacing:0.12em">Duplicates</p>
                <div>
                    <p class="text-2xl font-black" style="color:#065f46">${ds.total_duplicates}</p>
                    <p class="text-xs mt-1" style="color:#059669">${ds.duplicate_groups} group${ds.duplicate_groups!==1?'s':''} · ${ds.cross_platform_pairs} cross-platform</p>
                </div>
            </div>
            ` : ''}

        </div>
        ${data.category_warning ? `
        <div class="mt-4 rounded-xl px-4 py-3 text-xs font-medium"
             style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.22);color:#b45309">
            ${data.category_warning}
        </div>` : ''}
    `;

    document.getElementById('summaryBar').classList.remove('hidden');
    document.getElementById('summaryBar').style.display = 'flex';
}

function summaryRiskBar(label, count, total, color) {
    const pct = Math.round((count / total) * 100);
    return `
        <div class="flex items-center gap-2.5">
            <span class="text-xs font-semibold w-10 shrink-0" style="color:${color}">${label}</span>
            <div style="flex:1;height:4px;border-radius:99px;background:rgba(0,0,0,0.07);overflow:hidden">
                <div style="height:100%;border-radius:99px;width:${pct}%;background:${color};transition:width .6s ease"></div>
            </div>
            <span class="text-sm font-bold w-5 text-right shrink-0" style="color:${color}">${count}</span>
        </div>`;
}

// ── Results grid ──────────────────────────────────────────────────────

function renderResults(products) {
    const grid = document.getElementById('resultsGrid');
    grid.innerHTML = '';
    if (!products.length) {
        grid.innerHTML = `<div class="col-span-full text-center py-16" style="color:#9abfac">No products found.</div>`;
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
    card.className = 'product-card rounded-xl overflow-hidden flex flex-col';

    const primaryLevel = p.xgb_risk_level || p.risk_level || 'UNKNOWN';
    const xgbScore     = p.xgb_score;
    const ruleScore    = p.risk_score || 0;
    const fa           = p.fraud_analysis || {};
    const redFlags     = fa.red_flags || [];
    const link         = p.link || p.product_link || '';

    let trustPct = Math.round((1 - (xgbScore ?? ruleScore)) * 100);
    const rec = fa.recommendation || '';
    if (rec.includes('AVOID'))   trustPct = Math.min(trustPct, 20);
    else if (rec.includes('CAUTION')) trustPct = Math.min(trustPct, 55);

    const trustColor  = trustPct >= 75 ? '#15803d' : trustPct >= 45 ? '#b45309' : '#dc2626';
    const trustBg     = trustPct >= 75 ? 'rgba(22,163,74,0.08)'  : trustPct >= 45 ? 'rgba(245,158,11,0.08)'  : 'rgba(239,68,68,0.08)';
    const trustBorder = trustPct >= 75 ? 'rgba(22,163,74,0.2)'   : trustPct >= 45 ? 'rgba(245,158,11,0.2)'   : 'rgba(239,68,68,0.2)';

    const conflict = p.xgb_risk_level && p.risk_level &&
                     p.xgb_risk_level !== p.risk_level &&
                     ((p.risk_level === 'LOW' && p.xgb_risk_level === 'HIGH') ||
                      (p.risk_level === 'HIGH' && p.xgb_risk_level === 'LOW'));

    const priceNote    = priceContext(p);
    const condLabel    = { new:'New', used:'Used', refurbished:'Refurb', unknown:'' }[p.condition] || '';
    const platformLabel = p.platform === 'ebay' ? 'eBay' : 'Google';
    const platformBg    = p.platform === 'ebay' ? 'rgba(220,38,38,0.1)' : 'rgba(37,99,235,0.1)';
    const platformColor = p.platform === 'ebay' ? '#dc2626' : '#2563eb';
    const riskLabel     = { HIGH:'High Risk', MEDIUM:'Medium Risk', LOW:'Low Risk', UNKNOWN:'Unknown' }[primaryLevel] || 'Unknown';

    card.innerHTML = `
        <!-- Header: platform + risk badge -->
        <div class="flex items-center justify-between px-4 py-3"
             style="border-bottom:1px solid rgba(0,0,0,0.06)">
            <span class="text-xs font-semibold px-2.5 py-1 rounded-md"
                  style="background:${platformBg};color:${platformColor}">${platformLabel}</span>
            <span class="text-xs font-bold px-2.5 py-1 rounded-md flex items-center gap-1.5"
                  style="background:${trustBg};color:${trustColor};border:1px solid ${trustBorder}">
                <span style="width:6px;height:6px;border-radius:50%;background:${trustColor};display:inline-block;flex-shrink:0"></span>
                ${riskLabel}
            </span>
        </div>

        ${p.thumbnail ? `
        <div style="background:#eef7f1">
            <img src="${escHtml(p.thumbnail)}" alt="${escHtml(p.title)}"
                 class="w-full h-36 object-contain p-2">
        </div>
        ` : ''}

        <div class="p-4 flex flex-col flex-1 gap-3">

            <!-- Title + price + condition -->
            <div>
                <h3 class="font-semibold text-sm leading-snug line-clamp-2 mb-2"
                    style="color:#0f2318">${escHtml(p.title)}</h3>
                <div class="flex items-center gap-2.5 mb-1.5">
                    <span class="text-xl font-bold text-white">$${p.price != null ? Number(p.price).toLocaleString() : '—'}</span>
                    ${condLabel ? `<span class="text-xs font-medium px-2 py-0.5 rounded-md"
                        style="background:#eef2fa;color:#6e9e82">${condLabel}</span>` : ''}
                </div>
                <div class="text-xs" style="color:#6e9e82">${ratingDisplay(p)}</div>
            </div>

            <!-- Trust meter -->
            <div class="rounded-lg p-3"
                 style="background:#eef7f1;border:1px solid rgba(0,0,0,0.06)">
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-semibold" style="color:#6e9e82">Safety Score</span>
                    <span class="text-base font-bold" style="color:${trustColor}">${trustPct}%</span>
                </div>
                <div class="tbar-bg">
                    <div class="tbar-fill" style="width:${trustPct}%;background:${trustColor}"></div>
                </div>
                <p class="text-xs mt-1.5 font-medium" style="color:${trustColor}">${safetyVerdict(primaryLevel, trustPct)}</p>
            </div>

            <!-- Model conflict -->
            ${conflict ? `
            <div class="rounded-lg px-3 py-2.5 text-xs font-medium"
                 style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.22);color:#b45309">
                ⚠ Two AI models gave conflicting signals — verify before buying.
            </div>
            ` : ''}

            <!-- Price context -->
            ${priceNote ? `<p class="text-xs leading-relaxed" style="color:#6e9e82">${priceNote}</p>` : ''}

            <!-- AI reasoning -->
            ${fa.reasoning ? `
            <p class="text-xs leading-relaxed pt-2"
               style="color:#4e7862;border-top:1px solid rgba(0,0,0,0.06)">${escHtml(fa.reasoning)}</p>
            ` : ''}

            <!-- Red flags -->
            ${redFlags.length > 0 ? `
            <div class="rounded-lg p-3"
                 style="background:rgba(239,68,68,0.06);border:1px solid rgba(239,68,68,0.16)">
                <p class="text-xs font-semibold mb-2" style="color:#dc2626">Watch out for</p>
                <ul class="space-y-1">
                    ${redFlags.map(f => `<li class="text-xs flex gap-1.5" style="color:#b91c1c">
                        <span style="color:#ef4444;flex-shrink:0">•</span>${friendlyFlag(f)}
                    </li>`).join('')}
                </ul>
            </div>
            ` : ''}

            <!-- Cross-platform / duplicate notice -->
            ${p.is_cross_platform ? `
            <div class="rounded-lg px-3 py-2 text-xs font-medium"
                 style="background:rgba(22,163,74,0.07);border:1px solid rgba(22,163,74,0.2);color:#166534"
                Appears on multiple platforms — compare prices before buying.
            </div>
            ` : p.duplicate_group != null ? `
            <div class="rounded-lg px-3 py-2 text-xs font-medium"
                 style="background:rgba(5,150,105,0.07);border:1px solid rgba(5,150,105,0.2);color:#065f46"
                Multiple sellers listing this item — you may find a better deal.
            </div>
            ` : ''}

            <!-- Footer: recommendation + link -->
            <div class="mt-auto pt-3 flex items-center justify-between gap-2"
                 style="border-top:1px solid rgba(0,0,0,0.06)">
                <span class="text-xs font-semibold ${recBadgeClass(fa.recommendation)}">${friendlyRec(fa.recommendation)}</span>
                ${link ? `
                    <a href="${link}" target="_blank" rel="noopener"
                       class="shrink-0 px-4 py-1.5 text-xs font-bold rounded-lg text-white transition-opacity hover:opacity-85"
                       style="background:#16a34a">
                        View listing →
                    </a>
                ` : `<span class="text-xs" style="color:#9abfac">No link</span>`}
            </div>

        </div>
    `;

    return card;
}

// ── User-friendly helpers ─────────────────────────────────────────────

function safetyVerdict(level, pct) {
    if (pct >= 70) return '✓ Looks legitimate — safe to consider';
    if (pct >= 40) return '⚠ Some concerns — verify before buying';
    return '✕ High risk — we recommend avoiding this';
}

function friendlyRec(rec) {
    if (!rec) return '—';
    if (rec.includes('SAFE'))    return '✓ Safe to buy';
    if (rec.includes('CAUTION')) return '⚠ Proceed with caution';
    return '✕ Avoid this listing';
}

function recBadgeClass(rec) {
    if (!rec) return '';
    if (rec.includes('SAFE'))    return 'text-green-700';
    if (rec.includes('CAUTION')) return 'text-amber-700';
    return 'text-red-600';
}

function priceContext(p) {
    if (!p.price_tier) return '';
    const isUsed = p.condition === 'used' || p.condition === 'refurbished';
    switch (p.price_tier) {
        case 'extremely_cheap':
            return isUsed
                ? 'Much cheaper than similar listings — expected for older/used models, but verify condition'
                : 'Price is suspiciously low — investigate before buying';
        case 'budget':
            return isUsed
                ? 'Good price for a used item — verify condition and seller'
                : 'Below-average price — worth verifying condition';
        case 'mid':
            return 'Fairly priced compared to similar listings';
        case 'premium':
            return 'Higher-end price — typical for this quality tier';
        case 'luxury':
            return 'Among the most expensive for this product';
        case 'outlier_high':
            return 'Unusually expensive — verify this is the right listing';
        default: return '';
    }
}

function friendlyFlag(flag) {
    if (flag.includes('Extremely cheap'))   return 'Price is suspiciously low compared to other listings';
    if (flag.includes('below typical'))     return 'Price is well below the typical market rate';
    if (flag.includes('No rating or reviews')) return 'This seller has no ratings or reviews yet';
    if (flag.includes('No rating'))         return 'No star rating available for this seller';
    if (flag.includes('Very few reviews')
     || flag.includes('Few reviews'))       return 'Very few customer reviews — hard to verify trustworthiness';
    if (flag.includes('Low rating'))        return 'Low customer rating — check reviews carefully';
    if (flag.includes('Low seller rating')) return 'This seller has a below-average reputation';
    if (flag.includes('condition unknown')) return 'Item condition is not clearly stated';
    if (flag.includes('Vague product'))     return 'Product description is very short or vague';
    if (flag.includes('High-value item from seller with no reviews'))
        return 'Expensive item from a seller with no track record';
    if (flag.includes('Lower-priced'))      return 'Priced lower than usual — confirm it meets your expectations';
    if (flag.includes('High-value or rare')) return 'Rare or high-value item — verify authenticity carefully';
    return flag;
}

function ratingDisplay(p) {
    const seller = p.seller || {};
    const feedbackPct  = seller.feedback_pct;
    const sellerReviews = seller.reviews;

    if (p.rating > 0) {
        return `⭐ ${p.rating}${p.reviews > 0 ? ` (${fmtNum(p.reviews)})` : ''}`;
    }
    if (feedbackPct > 0) {
        const c = feedbackPct >= 98 ? '#15803d' : feedbackPct >= 95 ? '#b45309' : '#dc2626';
        return `<span style="color:${c}">👤 ${feedbackPct}% positive${sellerReviews > 0 ? ` (${fmtNum(sellerReviews)} ratings)` : ''}</span>`;
    }
    return `<span style="color:#b45309">No reviews yet</span>`;
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
