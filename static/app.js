const API_BASE = window.location.origin;

async function searchProducts() {
    const query = document.getElementById('searchQuery').value.trim();
    const platform = document.getElementById('platformSelect').value;
    
    if (!query) {
        alert('Please enter a product name');
        return;
    }

    // Show loading state
    document.getElementById('emptyState').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('loadingState').classList.remove('hidden');

    try {
        const url = platform === 'all' 
            ? `${API_BASE}/api/search/${encodeURIComponent(query)}`
            : `${API_BASE}/api/search/${encodeURIComponent(query)}?platform=${platform}`;
        
        const response = await fetch(url);
        const data = await response.json();

        // Hide loading, show results
        document.getElementById('loadingState').classList.add('hidden');
        document.getElementById('resultsSection').classList.remove('hidden');

        // Update results count
        document.getElementById('resultsCount').textContent = 
            `Found ${data.products.length} products with fraud analysis`;

        // Display results
        displayResults(data.products);
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
    card.className = 'bg-white rounded-lg shadow-md card-hover overflow-hidden';

    const riskLevel = product.fraud_analysis.scam_probability < 0.4 ? 'low' 
                    : product.fraud_analysis.scam_probability < 0.7 ? 'medium' 
                    : 'high';
    
    const riskClass = `risk-${riskLevel}`;
    const riskText = riskLevel === 'low' ? 'Low Risk' 
                   : riskLevel === 'medium' ? 'Medium Risk' 
                   : 'High Risk';
    
    const riskIcon = riskLevel === 'low' ? 'fa-check-circle' 
                   : riskLevel === 'medium' ? 'fa-exclamation-triangle' 
                   : 'fa-times-circle';

    card.innerHTML = `
        <div class="${riskClass} p-4 text-white">
            <div class="flex items-center justify-between">
                <span class="font-semibold">
                    <i class="fas ${riskIcon} mr-2"></i>${riskText}
                </span>
                <span class="text-2xl font-bold">${(product.fraud_analysis.scam_probability * 100).toFixed(0)}%</span>
            </div>
        </div>
        
        <div class="p-4">
            ${product.thumbnail ? `
                <img src="${product.thumbnail}" alt="${product.title}" 
                     class="w-full h-48 object-contain mb-4 bg-gray-50 rounded">
            ` : ''}
            
            <h4 class="font-semibold text-gray-800 mb-2 line-clamp-2">${product.title}</h4>
            
            <div class="flex items-center justify-between mb-3">
                <span class="text-2xl font-bold text-purple-600">$${product.price}</span>
                <span class="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    ${product.source}
                </span>
            </div>

            ${product.condition ? `
                <div class="mb-3">
                    <span class="text-sm text-gray-600">
                        <i class="fas fa-info-circle mr-1"></i>
                        Condition: <strong>${product.condition}</strong>
                    </span>
                </div>
            ` : ''}

            <div class="mb-3">
                <p class="text-sm text-gray-600 font-semibold mb-2">
                    <i class="fas fa-robot mr-1"></i>AI Analysis:
                </p>
                <p class="text-sm text-gray-700">${product.fraud_analysis.reasoning}</p>
            </div>

            ${product.fraud_analysis.red_flags.length > 0 ? `
                <div class="mb-3">
                    <p class="text-sm font-semibold text-red-600 mb-1">
                        <i class="fas fa-flag mr-1"></i>Red Flags:
                    </p>
                    <ul class="text-xs text-gray-600 space-y-1">
                        ${product.fraud_analysis.red_flags.map(flag => 
                            `<li><i class="fas fa-exclamation-circle text-red-500 mr-1"></i>${flag}</li>`
                        ).join('')}
                    </ul>
                </div>
            ` : ''}

            <div class="pt-3 border-t border-gray-200">
                <span class="text-sm font-semibold ${
                    product.fraud_analysis.recommendation === 'SAFE TO BUY' ? 'text-green-600' :
                    product.fraud_analysis.recommendation === 'PROCEED WITH CAUTION' ? 'text-yellow-600' :
                    'text-red-600'
                }">
                    <i class="fas ${
                        product.fraud_analysis.recommendation === 'SAFE TO BUY' ? 'fa-thumbs-up' :
                        product.fraud_analysis.recommendation === 'PROCEED WITH CAUTION' ? 'fa-exclamation-triangle' :
                        'fa-ban'
                    } mr-1"></i>
                    ${product.fraud_analysis.recommendation}
                </span>
            </div>

            <a href="${product.link}" target="_blank" 
               class="mt-3 block w-full text-center bg-gray-100 hover:bg-gray-200 text-gray-800 font-semibold py-2 px-4 rounded transition-colors">
                View on ${product.source} <i class="fas fa-external-link-alt ml-1 text-sm"></i>
            </a>
        </div>
    `;

    return card;
}