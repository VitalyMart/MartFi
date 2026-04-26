// ./front/static/js/portfolio.js
document.addEventListener('DOMContentLoaded', function () {
    const addAssetBtn = document.getElementById('addAssetBtn');
    const addFirstAssetBtn = document.getElementById('addFirstAssetBtn');
    const addAssetModal = document.getElementById('addAssetModal');
    const closeModalBtn = document.getElementById('closeModal');
    const cancelAddBtn = document.getElementById('cancelAdd');
    const addAssetForm = document.getElementById('addAssetForm');
    const refreshPortfolioBtn = document.getElementById('refreshPortfolio');
    const copyPortfolioBtn = document.getElementById('copyPortfolioBtn');
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
        if (addAssetForm) addAssetForm.reset();
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

    if (addAssetModal) {
        addAssetModal.addEventListener('click', function (e) {
            if (e.target === addAssetModal) {
                closeModal();
            }
        });
    }

    if (addAssetForm) {
        addAssetForm.addEventListener('submit', async function (e) {
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
        refreshPortfolioBtn.addEventListener('click', function () {
            window.location.reload();
        });
    }

    if (copyPortfolioBtn) {
        copyPortfolioBtn.addEventListener('click', async function () {
            const portfolioData = getPortfolioDataFromTable();

            if (!portfolioData || portfolioData.length === 0) {
                showCopyNotification('Портфель пуст, нечего копировать', 'warning');
                return;
            }

            const formattedText = formatPortfolioForCopy(portfolioData);

            try {
                await navigator.clipboard.writeText(formattedText);

                const originalHTML = copyPortfolioBtn.innerHTML;
                copyPortfolioBtn.innerHTML = `
                    <svg viewBox="0 0 24 24">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                    </svg>
                    Скопировано!
                `;
                copyPortfolioBtn.classList.add('copied');

                showCopyNotification('Портфель скопирован в буфер обмена', 'success');

                setTimeout(() => {
                    copyPortfolioBtn.innerHTML = originalHTML;
                    copyPortfolioBtn.classList.remove('copied');
                }, 2000);
            } catch (err) {
                console.error('Ошибка копирования:', err);
                showCopyNotification('Не удалось скопировать портфель', 'error');
            }
        });
    }

    function getPortfolioDataFromTable() {
        const rows = document.querySelectorAll('.portfolio-table tbody tr');
        const portfolio = [];

        for (const row of rows) {
            const tickerElement = row.querySelector('.ticker');
            const nameElement = row.querySelector('.name-cell');
            const typeElement = row.querySelector('.asset-type-badge');
            const quantityElement = row.querySelector('.quantity-cell');
            const avgPriceElement = row.querySelector('.avg-price-cell');
            const currentPriceElement = row.querySelector('.current-price-cell');
            const currentValueElement = row.querySelector('.current-value-cell');
            const changeElement = row.querySelector('.change-wrapper');

            if (!tickerElement) continue;

            const ticker = tickerElement.textContent || '';
            const name = nameElement ? nameElement.textContent : '';
            const type = typeElement ? typeElement.textContent : '';

            let quantity = 0;
            if (quantityElement) {
                const quantityText = quantityElement.textContent.replace(/\s/g, '').replace(',', '.');
                quantity = parseFloat(quantityText) || 0;
            }

            let avgPrice = 0;
            if (avgPriceElement) {
                const avgPriceText = avgPriceElement.textContent.replace(/[^\d,.-]/g, '').replace(',', '.');
                avgPrice = parseFloat(avgPriceText) || 0;
            }

            let currentPrice = 0;
            if (currentPriceElement) {
                const currentPriceText = currentPriceElement.textContent.replace(/[^\d,.-]/g, '').replace(',', '.');
                currentPrice = parseFloat(currentPriceText) || 0;
            }

            let currentValue = 0;
            if (currentValueElement) {
                const currentValueText = currentValueElement.textContent.replace(/[^\d,.-]/g, '').replace(',', '.');
                currentValue = parseFloat(currentValueText) || 0;
            }

            let changePercent = 0;
            if (changeElement) {
                const percentElement = changeElement.querySelector('.change-percent');
                if (percentElement) {
                    const percentText = percentElement.textContent;
                    const match = percentText.match(/[+-]?\d+(?:[.,]\d+)?/);
                    if (match) {
                        changePercent = parseFloat(match[0].replace(',', '.'));
                    }
                }
            }

            portfolio.push({
                ticker: ticker,
                name: name,
                type: type,
                quantity: quantity,
                avg_price: avgPrice,
                current_price: currentPrice,
                current_value: currentValue,
                change_percent: changePercent
            });
        }

        return portfolio;
    }

    function formatPortfolioForCopy(portfolio) {
        const date = new Date().toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        let totalCurrentValue = 0;
        let totalPurchaseValue = 0;

        for (const item of portfolio) {
            totalCurrentValue += item.current_value;
            totalPurchaseValue += item.quantity * item.avg_price;
        }

        const totalChange = totalCurrentValue - totalPurchaseValue;
        const totalChangePercent = totalPurchaseValue > 0 ? (totalChange / totalPurchaseValue) * 100 : 0;

        let text = `===========================================================\n`;
        text += `МОЙ ИНВЕСТИЦИОННЫЙ ПОРТФЕЛЬ\n`;
        text += `===========================================================\n`;
        text += `Дата: ${date}\n`;
        text += `-----------------------------------------------------------\n\n`;
        text += `ОБЩАЯ СТАТИСТИКА:\n`;
        text += `  Текущая стоимость: ${formatNumber(totalCurrentValue)} ₽\n`;
        text += `  Инвестировано: ${formatNumber(totalPurchaseValue)} ₽\n`;
        text += `  Прибыль/убыток: ${totalChange >= 0 ? '+' : ''}${formatNumber(totalChange)} ₽\n`;
        text += `  Доходность: ${totalChangePercent >= 0 ? '+' : ''}${totalChangePercent.toFixed(2)}%\n`;
        text += `  Количество активов: ${portfolio.length}\n\n`;
        text += `-----------------------------------------------------------\n`;
        text += `АКТИВЫ:\n`;
        text += `-----------------------------------------------------------\n`;

        for (const item of portfolio) {
            const changeSymbol = item.change_percent >= 0 ? '+' : '';
            const ticker = item.ticker.padEnd(10).slice(0, 10);
            const name = item.name.replace(/\s+/g, ' ').trim().slice(0, 25).padEnd(25);
            const type = item.type.replace(/\s+/g, ' ').trim().slice(0, 10);
            text += `${ticker} | ${name} | ${type} | ${item.quantity.toFixed(2)} | ${item.avg_price.toFixed(2)} | ${Math.round(item.current_value)} | ${changeSymbol}${item.change_percent.toFixed(2)}%\n`;
        }

        text += `-----------------------------------------------------------\n`;
        text += `Данные получены через MartFi\n`;
        text += `===========================================================`;

        return text;
    }

    function formatNumber(value) {
        return new Intl.NumberFormat('ru-RU', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    }

    function showCopyNotification(message, type = 'success') {
        const existing = document.querySelector('.copy-notification');
        if (existing) existing.remove();

        const notification = document.createElement('div');
        notification.className = 'copy-notification';

        if (type === 'warning') {
            notification.style.background = '#f59e0b';
        } else if (type === 'error') {
            notification.style.background = '#dc2626';
        } else {
            notification.style.background = '#059669';
        }

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

    deleteButtons.forEach(button => {
        button.addEventListener('click', async function () {
            const itemId = this.getAttribute('data-item-id');
            const row = this.closest('tr');
            const tickerElement = row ? row.querySelector('.ticker') : null;
            const itemName = tickerElement ? tickerElement.textContent : 'актив';

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
        button.addEventListener('click', function () {
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

        .copy-btn {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1.25rem;
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #cbd5e0;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .copy-btn:hover {
            background: #e2e8f0;
            border-color: #94a3b8;
        }

        .copy-btn.copied {
            background: #059669;
            color: white;
            border-color: #059669;
        }

        .copy-btn.copied svg {
            fill: white;
        }

        .copy-btn svg {
            width: 18px;
            height: 18px;
            fill: currentColor;
        }

        .copy-notification {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 0.75rem 1.25rem;
            background: #059669;
            color: white;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            z-index: 10000;
            transform: translateY(100%);
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
        }

        .copy-notification.show {
            transform: translateY(0);
            opacity: 1;
        }
    `;
    document.head.appendChild(style);
});