document.addEventListener('DOMContentLoaded', function() {
    const gainersList = document.getElementById('gainersList');
    const losersList = document.getElementById('losersList');
    
    function redirectToMarket(ticker, assetType) {
        window.location.href = `/market/${assetType}?search=${encodeURIComponent(ticker)}`;
    }
    
    function attachClickHandlers(container) {
        if (!container) return;
        const items = container.querySelectorAll('.leader-item');
        items.forEach(item => {
            item.removeEventListener('click', handleItemClick);
            item.addEventListener('click', handleItemClick);
        });
    }
    
    function handleItemClick(event) {
        const item = event.currentTarget;
        const ticker = item.getAttribute('data-ticker');
        const assetType = item.getAttribute('data-asset-type');
        if (ticker && assetType) {
            redirectToMarket(ticker, assetType);
        }
    }
    
    function getAssetTypeDisplay(assetType) {
        const types = {
            'stock': 'Акция',
            'bond': 'Облигация',
            'fund': 'Фонд',
            'currency': 'Валюта',
            'index': 'Индекс'
        };
        return types[assetType] || assetType;
    }
    
    function createLeaderItem(asset, rank) {
        const assetTypeDisplay = getAssetTypeDisplay(asset.asset_type);
        const changePercent = asset.change_percent || 0;
        const isPositive = changePercent > 0;
        const changeClass = isPositive ? 'positive' : 'negative';
        const changeSymbol = isPositive ? '+' : '';
        const absChangePercent = Math.abs(changePercent).toFixed(2);
        const price = asset.price || 0;
        
        return `
            <div class="leader-item" data-ticker="${escapeHtml(asset.ticker)}" data-asset-type="${asset.asset_type}">
                <div class="leader-rank">${rank}</div>
                <div class="leader-info">
                    <div class="leader-ticker">
                        ${escapeHtml(asset.ticker)}
                        <span class="asset-badge">${assetTypeDisplay}</span>
                    </div>
                    <div class="leader-name">${escapeHtml(asset.name.substring(0, 45))}${asset.name.length > 45 ? '...' : ''}</div>
                </div>
                <div class="leader-change ${changeClass}">
                    ${changeSymbol}${absChangePercent}%
                    <div class="leader-price">${price.toFixed(2)} ₽</div>
                </div>
            </div>
        `;
    }
    
    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }
    
    async function fetchLeadersData() {
        try {
            const response = await fetch('/api/main/leaders');
            const data = await response.json();
            
            if (data.success) {
                if (gainersList && data.top_gainers && data.top_gainers.length > 0) {
                    gainersList.innerHTML = data.top_gainers.map((asset, idx) => createLeaderItem(asset, idx + 1)).join('');
                    attachClickHandlers(gainersList);
                } else if (gainersList) {
                    gainersList.innerHTML = '<div class="empty-leaders">Нет данных о росте</div>';
                }
                
                if (losersList && data.top_losers && data.top_losers.length > 0) {
                    losersList.innerHTML = data.top_losers.map((asset, idx) => createLeaderItem(asset, idx + 1)).join('');
                    attachClickHandlers(losersList);
                } else if (losersList) {
                    losersList.innerHTML = '<div class="empty-leaders">Нет данных о падении</div>';
                }
            } else {
                if (gainersList) gainersList.innerHTML = '<div class="empty-leaders">Ошибка загрузки данных</div>';
                if (losersList) losersList.innerHTML = '<div class="empty-leaders">Ошибка загрузки данных</div>';
            }
        } catch (error) {
            console.error('Failed to fetch leaders data:', error);
            if (gainersList) gainersList.innerHTML = '<div class="empty-leaders">Ошибка соединения</div>';
            if (losersList) losersList.innerHTML = '<div class="empty-leaders">Ошибка соединения</div>';
        }
    }
    
    fetchLeadersData();
    
    setInterval(fetchLeadersData, 30000);
});