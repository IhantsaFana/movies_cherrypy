document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const loginForm = document.getElementById('login-form');
    const searchForm = document.getElementById('search-form');
    const moviesContainer = document.getElementById('movies');
    const favoritesContainer = document.getElementById('favorites');
    const message = document.getElementById('message');
    const toggleDarkModeBtn = document.getElementById('toggle-dark-mode');
    const favoriteBtn = document.getElementById('favorite-btn');

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

    // Gestion du bouton favori
    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', async () => {
            const movieId = favoriteBtn.dataset.movieId;
            const isFavorite = favoriteBtn.dataset.isFavorite === 'true';

            const response = await fetch('/add_favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ movie_id: movieId })
            });

            const result = await response.json();
            if (result.status === 'success') {
                const newIsFavorite = !isFavorite;
                favoriteBtn.dataset.isFavorite = newIsFavorite;
                favoriteBtn.querySelector('.favorite-icon').textContent = newIsFavorite ? '★' : '☆';
                favoriteBtn.setAttribute('aria-label', newIsFavorite ? 'Retirer des favoris' : 'Ajouter aux favoris');
            }
        });
    }

    // Chargement initial des films
    if (moviesContainer) {
        loadMovies();
    }

    // Gestion de la recherche
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const query = document.getElementById('search-input').value.trim();
            loadMovies(query);
        });
    }

    // Ajouter la navigabilité au clavier pour les cartes de films
    if (favoritesContainer || moviesContainer) {
        const cards = document.querySelectorAll('.movie-card');
        cards.forEach(card => {
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    card.click();
                }
            });
        });
    }

    async function loadMovies(query = '') {
        const url = query ? `/movies?query=${encodeURIComponent(query)}` : '/movies';
        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.status === 'error') {
                moviesContainer.innerHTML = `<p>${data.message}</p>`;
                return;
            }
            displayMovies(data.results || []);
        } catch (error) {
            moviesContainer.innerHTML = '<p>Erreur lors du chargement des films.</p>';
        }
    }

    function displayMovies(movies) {
        moviesContainer.innerHTML = '';
        movies.forEach((movie, index) => {
            const movieCard = document.createElement('div');
            movieCard.classList.add('movie-card');
            movieCard.style.setProperty('--index', index);
            movieCard.setAttribute('role', 'button');
            movieCard.setAttribute('tabindex', '0');
            movieCard.setAttribute('aria-label', `Voir les détails de ${movie.title}`);
            movieCard.innerHTML = `
                <img src="https://image.tmdb.org/t/p/w500${movie.poster_path}" alt="Affiche du film ${movie.title}, ${movie.overview.substring(0, 100)}..." loading="lazy">
                <h3>${movie.title}</h3>
                <p>${movie.overview.substring(0, 100)}...</p>
            `;
            movieCard.addEventListener('click', () => {
                window.location.href = `/movie/${movie.id}`;
            });
            moviesContainer.appendChild(movieCard);
        });
    }
});