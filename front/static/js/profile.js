function showTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    document.getElementById(tabId).classList.add('active');
    if (event && event.target) {
        event.target.classList.add('active');
    }
}

async function updateProfile(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    const messageDiv = document.getElementById('editProfileMessage');
    messageDiv.style.display = 'none';
    messageDiv.className = 'alert';
    
    try {
        const response = await fetch('/profile/update', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        messageDiv.style.display = 'block';
        
        if (result.success) {
            messageDiv.classList.add('alert-success');
            messageDiv.textContent = result.message;
            
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            messageDiv.classList.add('alert-error');
            messageDiv.textContent = result.message;
        }
    } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.classList.add('alert-error');
        messageDiv.textContent = 'Ошибка при обновлении профиля';
    }
}

async function changePassword(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    const messageDiv = document.getElementById('securityMessage');
    messageDiv.style.display = 'none';
    messageDiv.className = 'alert';
    
    try {
        const response = await fetch('/profile/change-password', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        messageDiv.style.display = 'block';
        
        if (result.success) {
            messageDiv.classList.add('alert-success');
            messageDiv.textContent = result.message;
            form.reset();
        } else {
            messageDiv.classList.add('alert-error');
            messageDiv.textContent = result.message;
        }
    } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.classList.add('alert-error');
        messageDiv.textContent = 'Ошибка при смене пароля';
    }
}

async function deleteAccount(event) {
    event.preventDefault();
    
    if (!confirm('Вы уверены, что хотите удалить аккаунт? Это действие необратимо.')) {
        return;
    }
    
    const form = event.target;
    const formData = new FormData(form);
    
    const messageDiv = document.getElementById('deleteMessage');
    messageDiv.style.display = 'none';
    messageDiv.className = 'alert';
    
    try {
        const response = await fetch('/profile/delete', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            window.location.href = '/login';
        } else {
            messageDiv.style.display = 'block';
            messageDiv.classList.add('alert-error');
            messageDiv.textContent = result.message;
        }
    } catch (error) {
        messageDiv.style.display = 'block';
        messageDiv.classList.add('alert-error');
        messageDiv.textContent = 'Ошибка при удалении аккаунта';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Ничего не делаем при загрузке
});