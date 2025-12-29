document.addEventListener('DOMContentLoaded', function() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    
    function switchTab(tabName) {
        
        tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });
        
        
        tabButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        
        
        const activePane = document.getElementById(tabName);
        if (activePane) {
            activePane.classList.add('active');
        }
        
        
        const activeButton = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
        if (activeButton) {
            activeButton.classList.add('active');
        }
        
        
        localStorage.setItem('lastActiveTab', tabName);
    }
    
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
    
    
    const lastActiveTab = localStorage.getItem('lastActiveTab');
    if (lastActiveTab && document.getElementById(lastActiveTab)) {
        switchTab(lastActiveTab);
    } else {
        
        if (tabButtons.length > 0) {
            const defaultTab = tabButtons[0].getAttribute('data-tab');
            switchTab(defaultTab);
        }
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