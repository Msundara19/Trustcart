const API_BASE = window.location.origin;

async function searchProducts() {
    const query = document.getElementById('searchQuery').value.trim();
    const platform = document.getElementById('platformSelect').value;
    const numResults = document.getElementById('numResults').value;
    const maxPrice = document.getElementById('maxPrice').value;
    
    if (!query) {
        alert('Please enter a product name');
        return;
    }

    // Show loading
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('loadingState').classList.remove('hidden');

    try {
        let url = `${API_BASE}/api/search/${encodeURIComponent(query)}?platform=${platform}&num_results=${numResults}`;
        
        // Add max_price if specified
        if (maxPrice && maxPrice > 0) {
            url += `&max_price=${maxPrice}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();

        // Hide loading, show results
        document.getElementById('loadingState').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

        // Show filtering info if any
        let countText = `Found ${data.products ? data.products.length : 0} products`;
        if (data.filtered_out && data.filtered_out > 0) {
            countText += ` (${data.filtered_out} filtered out)`;
        }
        document.getElementById('resultsCount').textContent = countText;

        // Display results
        if (data.products && data.products.length > 0) {
            displayResults(data.products);
        } else {
            document.getElementById('resultsGrid').innerHTML = 
                '<div class="col-span-full text-center py-8 text-gray-600">No products found</div>';
        }
    } catch (error) {
        document.getElementById('loadingState').classList.add('hidden');
        alert('Error fetching results. Please try again.');
        console.error('Error:', error);
    }
}

function displayResults(products) {
    const resultsGrid = document.getElementById('resultsGrid');
    resultsGrid.innerHTML = '';

    products.forEach(product => {
        const card = createProductCard(product);
        resultsGrid.appendChild(card);
    });
}

function createProductCard(product) {
    const card = document.createElement('div');
    card.className = 'bg-white rounded-lg shadow hover:shadow-lg transition-shadow border border-gray-200';

    // Get risk level from product
    const riskLevel = product.risk_level || 'UNKNOWN';
    const riskColors = {
        'LOW': 'bg-green-50 border-green-200 text-green-800',
        'MEDIUM': 'bg-yellow-50 border-yellow-200 text-yellow-800',
        'HIGH': 'bg-red-50 border-red-200 text-red-800',
        'UNKNOWN': 'bg-gray-50 border-gray-200 text-gray-800'
    };

    // Get fraud analysis
    const fraudAnalysis = product.fraud_analysis || {};
    const reasoning = fraudAnalysis.reasoning || 'No analysis available';
    const redFlags = fraudAnalysis.red_flags || [];
    const recommendation = fraudAnalysis.recommendation || 'REVIEW CAREFULLY';

    // FIXED: Check multiple possible link fields
    const productLink = product.link || product.product_link || '';

    card.innerHTML = `
        <div class="p-4">
            ${product.thumbnail ? `
                <img src="${product.thumbnail}" alt="${product.title}" 
                     class="w-full h-48 object-contain mb-4 bg-gray-50 rounded">
            ` : ''}
            
            <div class="mb-3">
                <span class="inline-block px-3 py-1 rounded-full text-sm font-medium ${riskColors[riskLevel]}">
                    ${riskLevel} RISK
                </span>
            </div>

            <h3 class="font-semibold text-gray-900 mb-2 line-clamp-2 min-h-[3rem]">${product.title}</h3>
            
            <div class="flex items-baseline justify-between mb-3">
                <span class="text-2xl font-bold text-blue-600">$${product.price}</span>
                <span class="text-sm text-gray-500">${product.source || 'Unknown'}</span>
            </div>

            ${product.condition ? `
                <p class="text-sm text-gray-600 mb-3">Condition: <strong>${product.condition}</strong></p>
            ` : ''}

            <div class="mb-3 pb-3 border-b border-gray-200">
                <p class="text-sm text-gray-700">${reasoning}</p>
            </div>

            ${redFlags.length > 0 ? `
                <div class="mb-3">
                    <p class="text-sm font-semibold text-red-600 mb-2">⚠️ Red Flags:</p>
                    <ul class="text-xs text-gray-600 space-y-1">
                        ${redFlags.map(flag => `<li>• ${flag}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            <div class="pt-3 border-t border-gray-200">
                <p class="text-sm font-semibold text-gray-700 mb-2">Recommendation:</p>
                <p class="text-sm ${
                    recommendation.includes('SAFE') ? 'text-green-600' :
                    recommendation.includes('CAUTION') ? 'text-yellow-600' :
                    'text-red-600'
                }">${recommendation}</p>
            </div>

            ${productLink ? `
                <a href="${productLink}" target="_blank" 
                   class="mt-4 block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors">
                    View Listing →
                </a>
            ` : `
                <div class="mt-4 block w-full text-center bg-gray-300 text-gray-600 font-medium py-2 px-4 rounded cursor-not-allowed">
                    Link Not Available
                </div>
            `}
        </div>
    `;

    return card;
}