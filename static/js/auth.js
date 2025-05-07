document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');
    const message = document.getElementById('message');
    const toggleDarkModeBtn = document.getElementById('toggle-dark-mode');

    // Gestion du mode sombre
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.body.classList.add('dark-mode');
        toggleDarkModeBtn.textContent = 'Mode Clair';
    }

    toggleDarkModeBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        toggleDarkModeBtn.textContent = isDark ? 'Mode Clair' : 'Mode Sombre';
        localStorage.setItem('darkMode', isDark);
    });

    // Gestion du formulaire d'inscription
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            const response = await fetch('/do_register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const result = await response.json();
            message.textContent = result.message;
            if (result.status === 'success') {
                setTimeout(() => location.href = '/login', 1000);
            }
        });
    }

    // Gestion du formulaire de connexion
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            const response = await fetch('/do_login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const result = await response.json();
            message.textContent = result.message;
            if (result.status === 'success') {
                setTimeout(() => location.href = '/', 1000);
            }
        });
    }
});