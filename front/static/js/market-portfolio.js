
document.addEventListener('DOMContentLoaded', function() {
    
    const addToPortfolioModal = document.getElementById('addToPortfolioModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const addToPortfolioForm = document.getElementById('addToPortfolioForm');
    
    
    const assetTickerInput = document.getElementById('assetTicker');
    const assetTypeInput = document.getElementById('assetType');
    const previewTicker = document.getElementById('previewTicker');
    const previewName = document.getElementById('previewName');
    const priceInput = document.getElementById('priceInput');
    const quantityInput = document.getElementById('quantityInput');
    
    
    let currentAsset = null;
    
    
    document.addEventListener('click', function(e) {
        const addBtn = e.target.closest('.add-to-portfolio-btn:not(.disabled)');
        if (!addBtn) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        
        const ticker = addBtn.getAttribute('data-ticker');
        const name = addBtn.getAttribute('data-name');
        const assetType = addBtn.getAttribute('data-asset-type');
        const currentPrice = parseFloat(addBtn.getAttribute('data-price')) || 0;
        
        currentAsset = { ticker, name, assetType, currentPrice };
        
        
        assetTickerInput.value = ticker;
        assetTypeInput.value = assetType;
        previewTicker.textContent = ticker;
        previewName.textContent = name;
        
        
        if (currentPrice > 0) {
            priceInput.value = currentPrice.toFixed(2);
        } else {
            priceInput.value = '0';
        }
        
        
        quantityInput.value = '1';
        
        
        showAddToPortfolioModal();
    });
    
    
    function showAddToPortfolioModal() {
        addToPortfolioModal.classList.add('active');
        document.body.style.overflow = 'hidden';
        
        
        setTimeout(() => {
            quantityInput.focus();
            quantityInput.select();
        }, 100);
    }
    
    
    function hideAddToPortfolioModal() {
        addToPortfolioModal.classList.remove('active');
        document.body.style.overflow = '';
        addToPortfolioForm.reset();
        currentAsset = null;
    }
    
    
    closeModalBtn.addEventListener('click', hideAddToPortfolioModal);
    cancelBtn.addEventListener('click', hideAddToPortfolioModal);
    
    
    addToPortfolioModal.addEventListener('click', function(e) {
        if (e.target === this) {
            hideAddToPortfolioModal();
        }
    });
    
    
    addToPortfolioForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = this.querySelector('.btn-primary');
        const originalText = submitBtn.textContent;
        
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Добавление...';
        
        try {
            const formData = new FormData(this);
            
            const response = await fetch('/api/portfolio/add', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                showNotification('Успешно!', `Актив ${currentAsset.ticker} добавлен в портфель`, 'success');
                hideAddToPortfolioModal();
                
                
                updatePortfolioBadge();
            } else {
                showNotification('Ошибка', result.message || 'Не удалось добавить актив', 'error');
            }
        } catch (error) {
            console.error('Error adding to portfolio:', error);
            showNotification('Ошибка', 'Произошла ошибка при добавлении', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
    
    
    function showNotification(title, message, type = 'success') {
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <h4 class="notification-title">${title}</h4>
                <p class="notification-message">${message}</p>
            </div>
        `;
        
        
        document.body.appendChild(notification);
        
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 5000);
    }
    
    
    function updatePortfolioBadge() {
        
        console.log('Portfolio updated');
    }
    
   
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
            border-left: 4px solid #10b981;
            display: flex;
            align-items: center;
            gap: 12px;
            transform: translateX(120%);
            transition: transform 0.3s ease;
            z-index: 10000;
            max-width: 400px;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification.error {
            border-left-color: #ef4444;
        }
        
        .notification-content {
            flex: 1;
        }
        
        .notification-title {
            font-size: 16px;
            font-weight: 600;
            color: #1f2937;
            margin: 0 0 4px 0;
        }
        
        .notification-message {
            font-size: 14px;
            color: #6b7280;
            margin: 0;
            line-height: 1.4;
        }
    `;
    document.head.appendChild(style);
});