document.querySelectorAll('.accordion-header').forEach(button => {
    button.addEventListener('click', () => {
        const targetId = button.getAttribute('data-target');
        const content = document.getElementById(targetId);
        const arrow = button.querySelector('.accordion-arrow');
        
        if (content.style.maxHeight) {
            content.style.maxHeight = null;
            arrow.textContent = '▼';
        } else {
            content.style.maxHeight = content.scrollHeight + "px";
            arrow.textContent = '▲';
        }
    });
});
