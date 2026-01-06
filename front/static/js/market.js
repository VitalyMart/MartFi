document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const searchForm = document.getElementById('searchForm');
    const sortForm = document.getElementById('sortForm');
    const sortBySelect = document.getElementById('sortBySelect');
    const sortOrderSelect = document.getElementById('sortOrderSelect');
    
    function switchTab(tabName) {
        const searchQuery = document.querySelector('.search-input').value;
        const sortBy = sortBySelect.value;
        const sortOrder = sortOrderSelect.value;
        
        window.location.href = `/market/${tabName}?search=${encodeURIComponent(searchQuery)}&sort_by=${sortBy}&sort_order=${sortOrder}`;
    }
    
    function updateForms(assetType) {
        if (searchForm) {
            searchForm.action = `/market/${assetType}`;
        }
        if (sortForm) {
            sortForm.action = `/market/${assetType}`;
        }
    }
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            tabButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
            
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
            });
            const activePane = document.getElementById(tabName);
            if (activePane) {
                activePane.classList.add('active');
            }
            
            updateForms(tabName);
            
            switchTab(tabName);
        });
    });
    
    if (sortBySelect) {
        sortBySelect.addEventListener('change', function() {
            sortForm.submit();
        });
    }
    
    if (sortOrderSelect) {
        sortOrderSelect.addEventListener('change', function() {
            sortForm.submit();
        });
    }
    
    const tabsHeader = document.querySelector('.tabs-header');
    if (tabsHeader) {
        let isDown = false;
        let startX;
        let scrollLeft;
        
        tabsHeader.addEventListener('mousedown', (e) => {
            isDown = true;
            tabsHeader.classList.add('active');
            startX = e.pageX - tabsHeader.offsetLeft;
            scrollLeft = tabsHeader.scrollLeft;
        });
        
        tabsHeader.addEventListener('mouseleave', () => {
            isDown = false;
            tabsHeader.classList.remove('active');
        });
        
        tabsHeader.addEventListener('mouseup', () => {
            isDown = false;
            tabsHeader.classList.remove('active');
        });
        
        tabsHeader.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - tabsHeader.offsetLeft;
            const walk = (x - startX) * 2;
            tabsHeader.scrollLeft = scrollLeft - walk;
        });
        
        tabsHeader.addEventListener('touchstart', (e) => {
            isDown = true;
            startX = e.touches[0].pageX - tabsHeader.offsetLeft;
            scrollLeft = tabsHeader.scrollLeft;
        });
        
        tabsHeader.addEventListener('touchend', () => {
            isDown = false;
        });
        
        tabsHeader.addEventListener('touchmove', (e) => {
            if (!isDown) return;
            const x = e.touches[0].pageX - tabsHeader.offsetLeft;
            const walk = (x - startX) * 2;
            tabsHeader.scrollLeft = scrollLeft - walk;
        });
    }
});