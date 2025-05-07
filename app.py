import cherrypy
import json
import os
from pathlib import Path
import bcrypt
import re
import requests
import urllib.parse
from datetime import datetime, timedelta

class MovieApp:
    def __init__(self):
        self.api_key = "659366279cadcf5ba9ce8bfe1ff54f91"  # Votre clé TMDb
        self.base_url = "https://api.themoviedb.org/3"
        self.cache = {}  # Cache en mémoire pour les requêtes API
        self.cache_duration = timedelta(minutes=60)  # Durée de validité du cache

    def validate_input(self, username, password):
        """Valide les entrées pour éviter les injections et vérifier les formats."""
        if not username or not password:
            return False, "Username and password are required"
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            return False, "Username must be 3-20 characters (letters, numbers, underscores)"
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        return True, ""

    def get_cached_data(self, url):
        """Récupère les données du cache ou effectue une nouvelle requête."""
        now = datetime.now()
        if url in self.cache:
            data, timestamp = self.cache[url]
            if now - timestamp < self.cache_duration:
                return data
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            self.cache[url] = (data, now)
            return data
        except requests.RequestException as e:
            raise cherrypy.HTTPError(500, f"Error fetching data: {str(e)}")

    @cherrypy.expose
    def index(self):
        if cherrypy.session.get('username'):
            return open('templates/index.html')
        raise cherrypy.HTTPRedirect('/login')

    @cherrypy.expose
    def login(self):
        return open('templates/login.html')

    @cherrypy.expose
    def register(self):
        return open('templates/register.html')

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def do_register(self):
        data = cherrypy.request.json
        username = data.get('username')
        password = data.get('password')

        is_valid, message = self.validate_input(username, password)
        if not is_valid:
            return {'status': 'error', 'message': message}

        users_file = Path('users.json')
        users = {}
        if users_file.exists():
            with users_file.open('r') as f:
                users = json.load(f)

        if username in users:
            return {'status': 'error', 'message': 'Username already exists'}

        # Hacher le mot de passe
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        users[username] = {'password': hashed_password, 'favorites': []}
        with users_file.open('w') as f:
            json.dump(users, f)

        return {'status': 'success', 'message': 'User registered successfully'}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def do_login(self):
        data = cherrypy.request.json
        username = data.get('username')
        password = data.get('password')

        users_file = Path('users.json')
        if not users_file.exists():
            return {'status': 'error', 'message': 'No users registered'}

        with users_file.open('r') as f:
            users = json.load(f)

        if username in users and bcrypt.checkpw(password.encode('utf-8'), users[username]['password'].encode('utf-8')):
            cherrypy.session['username'] = username
            return {'status': 'success', 'message': 'Login successful'}
        return {'status': 'error', 'message': 'Invalid credentials'}

    @cherrypy.expose
    def logout(self):
        cherrypy.session.pop('username', None)
        raise cherrypy.HTTPRedirect('/login')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def movies(self, query=None):
        """Récupère les films depuis TMDb, avec ou sans recherche."""
        if query:
            url = f"{self.base_url}/search/movie?api_key={self.api_key}&query={urllib.parse.quote(query)}"
        else:
            url = f"{self.base_url}/movie/popular?api_key={self.api_key}"
        return self.get_cached_data(url)

    @cherrypy.expose
    def movie(self, id):
        """Affiche la page de détail d'un film."""
        if not cherrypy.session.get('username'):
            raise cherrypy.HTTPRedirect('/login')

        # Valider l'ID du film
        try:
            movie_id = int(id)
        except ValueError:
            raise cherrypy.HTTPError(400, "Invalid movie ID")

        # Récupérer les détails du film
        movie_url = f"{self.base_url}/movie/{movie_id}?api_key={self.api_key}&language=fr-FR"
        movie_data = self.get_cached_data(movie_url)

        # Récupérer les crédits (casting et réalisateur)
        credits_url = f"{self.base_url}/movie/{movie_id}/credits?api_key={self.api_key}"
        credits_data = self.get_cached_data(credits_url)

        # Récupérer la bande-annonce
        videos_url = f"{self.base_url}/movie/{movie_id}/videos?api_key={self.api_key}&language=fr-FR"
        videos_data = self.get_cached_data(videos_url)
        trailer_key = None
        for video in videos_data.get('results', []):
            if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                trailer_key = video.get('key')
                break

        # Générer le HTML pour la bande-annonce
        title = movie_data.get('title', 'N/A').replace('<', '<').replace('>', '>')
        if trailer_key:
            trailer_html = (
                f'<div class="trailer">'
                f'<iframe width="100%" height="315" src="https://www.youtube.com/embed/{trailer_key}" '
                f'title="Bande-annonce de {title}" frameborder="0" '
                f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                f'allowfullscreen aria-label="Bande-annonce du film {title}"></iframe>'
                f'</div>'
            )
        else:
            trailer_html = '<p>Aucune bande-annonce disponible.</p>'

        # Extraire le casting (3 premiers acteurs)
        cast = [actor['name'] for actor in credits_data.get('cast', [])[:3]]
        # Extraire le réalisateur
        director = next((crew['name'] for crew in credits_data.get('crew', []) if crew['job'] == 'Director'), 'N/A')

        # Vérifier si le film est dans les favoris de l'utilisateur
        username = cherrypy.session.get('username')
        users_file = Path('users.json')
        users = {}
        is_favorite = False
        if users_file.exists():
            with users_file.open('r') as f:
                users = json.load(f)
            is_favorite = str(movie_id) in users.get(username, {}).get('favorites', [])

        # Créer une description alternative pour l'affiche
        alt_description = f"Affiche du film {movie_data.get('title', 'N/A')}, {movie_data.get('overview', 'Aucun synopsis disponible.')[:100]}..."

        # Nettoyer les données pour éviter les injections XSS
        safe_movie_data = {
            'title': title,
            'poster_path': movie_data.get('poster_path', ''),
            'overview': movie_data.get('overview', 'Aucun synopsis disponible.').replace('<', '<').replace('>', '>'),
            'release_date': movie_data.get('release_date', 'N/A'),
            'vote_average': movie_data.get('vote_average', 'N/A'),
            'genres': ', '.join(genre['name'] for genre in movie_data.get('genres', [])).replace('<', '<').replace('>', '>'),
            'cast': ', '.join(cast).replace('<', '<').replace('>', '>') if cast else 'N/A',
            'director': director.replace('<', '<').replace('>', '>'),
            'movie_id': movie_id,
            'is_favorite': 'true' if is_favorite else 'false',
            'favorite_icon': '★' if is_favorite else '☆',
            'favorite_aria_label': 'Retirer des favoris' if is_favorite else 'Ajouter aux favoris',
            'trailer_html': trailer_html,
            'alt_description': alt_description.replace('<', '<').replace('>', '>')
        }

        # Rendre le template
        with open('templates/movie_detail.html', 'r', encoding='utf-8') as f:
            template = f.read()
        return template.format(**safe_movie_data)

    @cherrypy.expose
    def favorites(self):
        """Affiche la page des films favoris de l'utilisateur."""
        if not cherrypy.session.get('username'):
            raise cherrypy.HTTPRedirect('/login')

        username = cherrypy.session.get('username')
        users_file = Path('users.json')
        users = {}
        favorite_ids = []
        if users_file.exists():
            with users_file.open('r') as f:
                users = json.load(f)
            favorite_ids = users.get(username, {}).get('favorites', [])

        # Récupérer les détails des films favoris
        favorite_movies = []
        for movie_id in favorite_ids:
            try:
                movie_url = f"{self.base_url}/movie/{movie_id}?api_key={self.api_key}&language=fr-FR"
                movie_data = self.get_cached_data(movie_url)
                favorite_movies.append({
                    'id': movie_id,
                    'title': movie_data.get('title', 'N/A').replace('<', '<').replace('>', '>'),
                    'poster_path': movie_data.get('poster_path', ''),
                    'overview': movie_data.get('overview', 'Aucun synopsis disponible.').replace('<', '<').replace('>', '>')[:100] + '...',
                    'alt_description': f"Affiche du film {movie_data.get('title', 'N/A')}, {movie_data.get('overview', 'Aucun synopsis disponible.')[:100]}..."
                })
            except cherrypy.HTTPError:
                continue  # Ignorer les films non trouvés

        # Générer le HTML pour les favoris
        if favorite_movies:
            favorites_content = ''.join(
                f'<div class="movie-card" onclick="window.location.href=\'/movie/{movie["id"]}\'" role="button" tabindex="0" aria-label="Voir les détails de {movie["title"]}">'
                f'<img src="https://image.tmdb.org/t/p/w500{movie["poster_path"]}" alt="{movie["alt_description"]}" loading="lazy">'
                f'<h3>{movie["title"]}</h3>'
                f'<p>{movie["overview"]}</p>'
                f'</div>'
                for movie in favorite_movies
            )
        else:
            favorites_content = '<p>Aucun film favori pour le moment.</p>'

        # Rendre le template
        with open('templates/favorites.html', 'r', encoding='utf-8') as f:
            template = f.read()
        return template.format(favorites_content=favorites_content)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def add_favorite(self):
        """Ajoute ou supprime un film des favoris de l'utilisateur."""
        if not cherrypy.session.get('username'):
            return {'status': 'error', 'message': 'User not logged in'}

        data = cherrypy.request.json
        movie_id = str(data.get('movie_id'))

        if not movie_id.isdigit():
            return {'status': 'error', 'message': 'Invalid movie ID'}

        username = cherrypy.session.get('username')
        users_file = Path('users.json')
        users = {}
        if users_file.exists():
            with users_file.open('r') as f:
                users = json.load(f)

        if username not in users:
            return {'status': 'error', 'message': 'User not found'}

        # Ajouter ou supprimer le film des favoris
        favorites = users[username].get('favorites', [])
        if movie_id in favorites:
            favorites.remove(movie_id)
            action = 'removed'
        else:
            favorites.append(movie_id)
            action = 'added'
        users[username]['favorites'] = favorites

        with users_file.open('w') as f:
            json.dump(users, f)

        return {'status': 'success', 'message': f'Movie {action} to favorites'}

if __name__ == '__main__':
    conf = {
        '/': {
            'tools.sessions.on': True,
            'tools.sessions.secure': True,
            'tools.sessions.httponly': True,
            'tools.staticdir.root': os.path.abspath(os.getcwd()),
            'tools.encode.on': True,
            'tools.encode.encoding': 'utf-8',
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './static'
        }
    }
    cherrypy.quickstart(MovieApp(), '/', conf)