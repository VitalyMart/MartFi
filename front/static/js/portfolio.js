document.addEventListener('DOMContentLoaded', function() {
    const addAssetBtn = document.getElementById('addAssetBtn');
    const addFirstAssetBtn = document.getElementById('addFirstAssetBtn');
    const addAssetModal = document.getElementById('addAssetModal');
    const closeModalBtn = document.getElementById('closeModal');
    const cancelAddBtn = document.getElementById('cancelAdd');
    const addAssetForm = document.getElementById('addAssetForm');
    const refreshPortfolioBtn = document.getElementById('refreshPortfolio');
    const deleteButtons = document.querySelectorAll('.delete-btn');
    const editButtons = document.querySelectorAll('.edit-btn');
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;

    
    function openModal() {
        addAssetModal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }

    
    function closeModal() {
        addAssetModal.classList.remove('show');
        document.body.style.overflow = '';
        addAssetForm.reset();
    }

    
    if (addAssetBtn) {
        addAssetBtn.addEventListener('click', openModal);
    }
    
    if (addFirstAssetBtn) {
        addFirstAssetBtn.addEventListener('click', openModal);
    }

    
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }
    
    if (cancelAddBtn) {
        cancelAddBtn.addEventListener('click', closeModal);
    }

    
    addAssetModal.addEventListener('click', function(e) {
        if (e.target === addAssetModal) {
            closeModal();
        }
    });

    
    if (addAssetForm) {
        addAssetForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/api/portfolio/add', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showNotification('Актив успешно добавлен в портфель', 'success');
                    closeModal();
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showNotification(result.message || 'Ошибка при добавлении актива', 'error');
                }
            } catch (error) {
                showNotification('Ошибка сети. Проверьте соединение.', 'error');
                console.error('Add asset error:', error);
            }
        });
    }

    
    if (refreshPortfolioBtn) {
        refreshPortfolioBtn.addEventListener('click', function() {
            window.location.reload();
        });
    }

    
    deleteButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const itemId = this.getAttribute('data-item-id');
            const itemName = this.closest('tr').querySelector('.ticker').textContent;
            
            if (confirm(`Удалить актив ${itemName} из портфеля?`)) {
                try {
                    const formData = new FormData();
                    formData.append('csrf_token', csrfToken);
                    
                    const response = await fetch(`/api/portfolio/remove/${itemId}`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        showNotification('Актив удален из портфеля', 'success');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
                        showNotification(result.message || 'Ошибка при удалении актива', 'error');
                    }
                } catch (error) {
                    showNotification('Ошибка сети. Проверьте соединение.', 'error');
                    console.error('Delete asset error:', error);
                }
            }
        });
    });

    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.getAttribute('data-item-id');
            const row = this.closest('tr');
            const ticker = row.querySelector('.ticker').textContent;
            const name = row.querySelector('.name-cell').textContent;
            const quantity = parseFloat(row.querySelector('.quantity-cell').textContent);
            const avgPrice = parseFloat(row.querySelector('.avg-price-cell').textContent.replace(' ₽', ''));
            
            
            alert(`Редактирование актива ${ticker}\nТекущее количество: ${quantity}\nСредняя цена: ${avgPrice} ₽\n\nФункция редактирования в разработке.`);
        });
    });

    
    function showNotification(message, type = 'info') {
        
        const existingNotification = document.querySelector('.notification');
        if (existingNotification) {
            existingNotification.remove();
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        
        setTimeout(() => {
            notification.classList.add('show');
        }, 10);
        
        
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            transform: translateX(100%);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            max-width: 400px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        }
        
        .notification.show {
            transform: translateX(0);
            opacity: 1;
        }
        
        .notification.success {
            background: linear-gradient(135deg, #059669, #10b981);
        }
        
        .notification.error {
            background: linear-gradient(135deg, #dc2626, #ef4444);
        }
        
        .notification.info {
            background: linear-gradient(135deg, #3b82f6, #6366f1);
        }
    `;
    document.head.appendChild(style);
});