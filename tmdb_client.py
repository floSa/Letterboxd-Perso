import requests
import json
import os
import calendar
from datetime import datetime, timedelta

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

TMDB_GENRES = {
    28: "Action",
    12: "Aventure",
    16: "Animation",
    35: "Comédie",
    80: "Policier",
    99: "Documentaire",
    18: "Drame",
    10751: "Famille",
    14: "Fantastique",
    36: "Histoire",
    27: "Horreur",
    10402: "Musique",
    9648: "Mystère",
    10749: "Romance",
    878: "Science-Fiction",
    10770: "Téléfilm",
    53: "Thriller",
    10752: "Guerre",
    37: "Western"
}

def load_api_key():
    """Charge la clé API TMDb depuis config.json ou la variable d'environnement."""
    env_key = os.environ.get("TMDB_API_KEY")
    if env_key:
        return env_key.strip()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("tmdb_api_key", "").strip()
        except Exception:
            return ""
    return ""

def save_api_key(api_key: str):
    """Enregistre la clé API TMDb localement."""
    data = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data["tmdb_api_key"] = api_key.strip()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_wednesday_of_date(date_str: str) -> str:
    """
    En France, les sorties cinéma ont lieu le mercredi.
    Cette fonction retourne la date du mercredi associé à une date de sortie.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Monday is 0, Tuesday is 1, Wednesday is 2...
        weekday = dt.weekday()
        # Si le film sort un mercredi (2), c'est ce jour.
        # S'il sort un vendredi (4) ou dimanche, il se rattache au mercredi précédent.
        offset = (weekday - 2) % 7
        wednesday = dt - timedelta(days=offset)
        return wednesday.strftime("%Y-%m-%d")
    except Exception:
        return date_str

def _build_auth(api_key_or_token: str):
    """Prépare les params ou les headers selon que l'utilisateur a collé la Clé v3 ou le Jeton v4."""
    key = api_key_or_token.strip()
    headers = {"accept": "application/json"}
    params = {}
    if key.startswith("eyJ") or len(key) > 40:
        # C'est un jeton d'accès en lecture (v4 auth Bearer token)
        headers["Authorization"] = f"Bearer {key}"
    else:
        # C'est la clé API classique (v3 auth)
        params["api_key"] = key
    return params, headers

def fetch_movie_director_and_runtime(movie_id: int, api_key: str, movie_year: int = 0):
    """Récupère le réalisateur, les acteurs principaux, la durée et détecte si c'est une reprise."""
    director = "Inconnu"
    cast_str = ""
    runtime = 0
    is_reprise = 0
    orig_year = 0
    orig_release_date = ""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        auth_params, headers = _build_auth(api_key)
        params = {
            **auth_params,
            "append_to_response": "credits,release_dates",
            "language": "fr-FR"
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            runtime = data.get("runtime", 0) or 0
            credits = data.get("credits", {})
            crew = credits.get("crew", [])
            directors = [m["name"] for m in crew if m.get("job") == "Director"]
            if directors:
                director = ", ".join(directors[:2])
            cast = credits.get("cast", [])
            if cast:
                cast_str = ", ".join([c["name"] for c in cast[:3]])
            
            # Détection de reprise via date de sortie mondiale originelle (>= 2 ans d'écart)
            orig_release_date = data.get("release_date") or ""
            if orig_release_date and len(orig_release_date) >= 4:
                try:
                    orig_year = int(orig_release_date[:4])
                    if movie_year > 0 and (movie_year - orig_year) >= 2:
                        is_reprise = 1
                except Exception:
                    pass

            # Détection via les notes explicites de sortie cinéma en France
            if not is_reprise:
                fr_releases = [c for c in data.get("release_dates", {}).get("results", []) if c.get("iso_3166_1") == "FR"]
                for fr_c in fr_releases:
                    for r in fr_c.get("release_dates", []):
                        note = (r.get("note") or "").lower()
                        if any(k in note for k in ["reprise", "ressortie", "re-release", "version restaurée"]):
                            is_reprise = 1
                            break
    except Exception:
        pass
    return director, cast_str, runtime, is_reprise, orig_year, orig_release_date

def fetch_french_releases_for_year(year: int, api_key: str, progress_callback=None):
    """
    Interroge l'API TMDb pour récupérer toutes les sorties cinéma en France pour une année.
    Effectue les requêtes mois par mois (1 à 12) pour éviter le plafonnement artificiel de pagination
    et garantir une couverture complète de janvier à décembre.
    """
    if not api_key:
        raise ValueError("Clé ou Jeton API TMDb requis.")

    base_url = "https://api.themoviedb.org/3/discover/movie"
    auth_params, headers = _build_auth(api_key)
    all_movies = []
    seen_ids = set()

    for month in range(1, 13):
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        page = 1
        total_pages = 1
        while page <= total_pages and page <= 20: # Sécurité ~400 films/mois
            params = {
                **auth_params,
                "region": "FR",
                "language": "fr-FR",
                "release_date.gte": start_date,
                "release_date.lte": end_date,
                "with_release_type": "2|3", # 2: Limited Theatrical, 3: Theatrical
                "sort_by": "release_date.asc",
                "page": page
            }
            try:
                resp = requests.get(base_url, params=params, headers=headers, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
            except Exception:
                break

            total_pages = data.get("total_pages", 1)
            results = data.get("results", [])

            for item in results:
                tmdb_id = item.get("id")
                if not tmdb_id or tmdb_id in seen_ids:
                    continue
                seen_ids.add(tmdb_id)

                release_date = item.get("release_date")
                if not release_date:
                    continue

                wednesday = get_wednesday_of_date(release_date)
                genre_names = [TMDB_GENRES.get(gid, "") for gid in item.get("genre_ids", []) if gid in TMDB_GENRES]
                genres_str = ", ".join(filter(None, genre_names))

                poster_path = item.get("poster_path")
                poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else ""

                # Détection de reprise sur l'année de sortie originelle
                is_reprise = 0
                orig_year = 0
                orig_date = release_date
                if release_date and len(release_date) >= 4:
                    try:
                        rd_year = int(release_date[:4])
                        if (year - rd_year) >= 2:
                            is_reprise = 1
                            orig_year = rd_year
                    except Exception:
                        pass

                movie_obj = {
                    "tmdb_id": tmdb_id,
                    "title": item.get("title") or item.get("original_title", "Sans titre"),
                    "original_title": item.get("original_title", ""),
                    "release_date": release_date,
                    "year": year,
                    "week_start_date": wednesday,
                    "director": "Inconnu",
                    "cast": "",
                    "genres": genres_str,
                    "synopsis": item.get("overview", "Aucun synopsis disponible."),
                    "poster_url": poster_url,
                    "runtime": 0,
                    "vote_average": round(item.get("vote_average", 0.0), 1),
                    "is_reprise": is_reprise,
                    "original_year": orig_year,
                    "original_release_date": orig_date
                }
                all_movies.append(movie_obj)

            page += 1

        if progress_callback:
            progress_callback(month, 12, len(all_movies))

    return all_movies

def fetch_movies_for_date_range(start_date: str, end_date: str, api_key: str):
    """
    Récupère directement les sorties cinéma en France pour un intervalle précis de dates (ex: une semaine précise).
    """
    if not api_key:
        return []
    base_url = "https://api.themoviedb.org/3/discover/movie"
    auth_params, headers = _build_auth(api_key)
    all_movies = []
    page = 1
    total_pages = 1
    while page <= total_pages and page <= 10:
        params = {
            **auth_params,
            "region": "FR",
            "language": "fr-FR",
            "release_date.gte": start_date,
            "release_date.lte": end_date,
            "with_release_type": "2|3",
            "sort_by": "release_date.desc",
            "page": page
        }
        resp = requests.get(base_url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            break
        data = resp.json()
        total_pages = data.get("total_pages", 1)
        for item in data.get("results", []):
            rel_date = item.get("release_date")
            if not rel_date:
                continue
            wednesday = get_wednesday_of_date(rel_date)
            year = int(rel_date[:4]) if len(rel_date) >= 4 else 2026
            genre_names = [TMDB_GENRES.get(gid, "") for gid in item.get("genre_ids", []) if gid in TMDB_GENRES]
            poster_path = item.get("poster_path")
            poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else ""
            
            is_reprise = 0
            orig_year = 0
            if rel_date and len(rel_date) >= 4:
                try:
                    rd_year = int(rel_date[:4])
                    if (year - rd_year) >= 2:
                        is_reprise = 1
                        orig_year = rd_year
                except Exception:
                    pass

            all_movies.append({
                "tmdb_id": item["id"],
                "title": item.get("title") or item.get("original_title", "Sans titre"),
                "original_title": item.get("original_title", ""),
                "release_date": rel_date,
                "year": year,
                "week_start_date": wednesday,
                "director": "Inconnu",
                "cast": "",
                "genres": ", ".join(filter(None, genre_names)),
                "synopsis": item.get("overview", "Aucun synopsis disponible."),
                "poster_url": poster_url,
                "runtime": 0,
                "vote_average": round(item.get("vote_average", 0.0), 1),
                "is_reprise": is_reprise,
                "original_year": orig_year,
                "original_release_date": rel_date
            })
        page += 1
    return all_movies

def get_demo_movies():
    """
    Jeu de données riche prêt à l'emploi (sorties récentes 2026, 2025 et 2024 en France)
    permettant de tester l'outil immédiatement sans attendre de clé TMDb.
    """
    return [
        # --- Sorties 2026 (Exemples d'anticipation et sorties début 2026) ---
        {
            "tmdb_id": 990001,
            "title": "Mickey 17",
            "original_title": "Mickey 17",
            "release_date": "2025-01-29",
            "year": 2025,
            "week_start_date": "2025-01-29",
            "director": "Bong Joon-ho",
            "genres": "Science-Fiction, Comédie, Drame",
            "synopsis": "Mickey 17 est un 'consommable', un employé jetable envoyé coloniser une planète de glace. À chaque décès, un nouveau corps est régénéré avec ses souvenirs.",
            "poster_url": "https://image.tmdb.org/t/p/w342/lr17nbiGbhijgq6n2e6sI8fQhM3.jpg",
            "runtime": 139,
            "vote_average": 7.4
        },
        {
            "tmdb_id": 990002,
            "title": "Un Parfait Inconnu",
            "original_title": "A Complete Unknown",
            "release_date": "2025-01-29",
            "year": 2025,
            "week_start_date": "2025-01-29",
            "director": "James Mangold",
            "genres": "Drame, Musique, Histoire",
            "synopsis": "Dans le New York du début des années 1960, un jeune musicien de 19 ans originaire du Minnesota, Bob Dylan, bouleverse la scène musicale folk.",
            "poster_url": "https://image.tmdb.org/t/p/w342/ct0q1cWwN4T79e491oI04PZ0x7p.jpg",
            "runtime": 141,
            "vote_average": 7.6
        },
        {
            "tmdb_id": 990003,
            "title": "Nosferatu",
            "original_title": "Nosferatu",
            "release_date": "2024-12-25",
            "year": 2024,
            "week_start_date": "2024-12-25",
            "director": "Robert Eggers",
            "genres": "Horreur, Fantastique, Drame",
            "synopsis": "Une histoire gothique d'obsession entre une jeune femme hantée et le terrifiant vampire épris d'elle, semant un carnage indicible sur son passage.",
            "poster_url": "https://image.tmdb.org/t/p/w342/5qGIxdEO841C0tdY8Y4XuioqJ2.jpg",
            "runtime": 132,
            "vote_average": 7.2
        },
        {
            "tmdb_id": 990004,
            "title": "L'Amour Ouf",
            "original_title": "L'Amour Ouf",
            "release_date": "2024-10-16",
            "year": 2024,
            "week_start_date": "2024-10-16",
            "director": "Gilles Lellouche",
            "genres": "Drame, Romance, Policier",
            "synopsis": "Les années 80, dans le nord de la France. Jackie et Clotaire grandissent entre les bancs du lycée et les docks du port. Elle étudie, lui traîne. Leurs destins se croisent et ils tombent éperdument amoureux.",
            "poster_url": "https://image.tmdb.org/t/p/w342/oB1pZ2iX4lC2T8x9hRkYq5M7Lz0.jpg",
            "runtime": 166,
            "vote_average": 7.7
        },
        {
            "tmdb_id": 990005,
            "title": "Dune : Deuxième Partie",
            "original_title": "Dune: Part Two",
            "release_date": "2024-02-28",
            "year": 2024,
            "week_start_date": "2024-02-28",
            "director": "Denis Villeneuve",
            "genres": "Science-Fiction, Aventure",
            "synopsis": "Paul Atreides s'unit à Chani et aux Fremen tout en préparant sa revanche contre les conspirateurs qui ont détruit sa famille.",
            "poster_url": "https://image.tmdb.org/t/p/w342/8b8R8l88Qje9dn9OE8PY05Nxl1X.jpg",
            "runtime": 166,
            "vote_average": 8.2
        },
        {
            "tmdb_id": 990006,
            "title": "Le Comte de Monte-Cristo",
            "original_title": "Le Comte de Monte-Cristo",
            "release_date": "2024-06-28",
            "year": 2024,
            "week_start_date": "2024-06-26",
            "director": "Matthieu Delaporte, Alexandre De La Patellière",
            "genres": "Aventure, Histoire, Action, Drame",
            "synopsis": "Victime d’un complot, le jeune Edmond Dantès est arrêté le jour de son mariage pour un crime qu’il n’a pas commis. Après quatorze ans de détention, il réussit à s’évader.",
            "poster_url": "https://image.tmdb.org/t/p/w342/s5v0T46P0wG4x1914I0x6yP7v5z.jpg",
            "runtime": 178,
            "vote_average": 8.0
        },
        {
            "tmdb_id": 990007,
            "title": "Anora",
            "original_title": "Anora",
            "release_date": "2024-10-30",
            "year": 2024,
            "week_start_date": "2024-10-30",
            "director": "Sean Baker",
            "genres": "Comédie, Drame, Romance",
            "synopsis": "Anora, jeune strip-teaseuse de Brooklyn, a la chance de vivre un conte de fées lorsqu'elle rencontre et épouse sur un coup de tête le fils d'un oligarque russe.",
            "poster_url": "https://image.tmdb.org/t/p/w342/p0B1q2x7yG4vK8m5nL8oQ1x9z.jpg",
            "runtime": 139,
            "vote_average": 7.8
        },
        {
            "tmdb_id": 990008,
            "title": "Emilia Pérez",
            "original_title": "Emilia Pérez",
            "release_date": "2024-08-21",
            "year": 2024,
            "week_start_date": "2024-08-21",
            "director": "Jacques Audiard",
            "genres": "Comédie, Drame, Musique, Policier",
            "synopsis": "Au Mexique, une avocate surqualifiée reçoit une offre inattendue : aider un redoutable chef de cartel à se retirer des affaires pour enfin devenir la femme qu'il a toujours rêvé d'être.",
            "poster_url": "https://image.tmdb.org/t/p/w342/8q8aM8yF5lK0k4mP2v9zN1o9b.jpg",
            "runtime": 132,
            "vote_average": 7.3
        },
        {
            "tmdb_id": 990009,
            "title": "Vice-Versa 2",
            "original_title": "Inside Out 2",
            "release_date": "2024-06-19",
            "year": 2024,
            "week_start_date": "2024-06-19",
            "director": "Kelsey Mann",
            "genres": "Animation, Famille, Aventure, Comédie",
            "synopsis": "Fraîchement diplômée, Riley est désormais une adolescente, ce qui n’est pas sans déclencher un chamboulement majeur au sein du quartier général des émotions.",
            "poster_url": "https://image.tmdb.org/t/p/w342/9U6h6pGZ2U7hC2Q8x9vN4oK0z.jpg",
            "runtime": 96,
            "vote_average": 7.6
        },
        {
            "tmdb_id": 990010,
            "title": "Alien: Romulus",
            "original_title": "Alien: Romulus",
            "release_date": "2024-08-14",
            "year": 2024,
            "week_start_date": "2024-08-14",
            "director": "Fede Álvarez",
            "genres": "Horreur, Science-Fiction",
            "synopsis": "En fouillant les profondeurs d'une station spatiale abandonnée, un groupe de jeunes colonisateurs de l'espace se retrouve face à face avec la forme de vie la plus terrifiante de l'univers.",
            "poster_url": "https://image.tmdb.org/t/p/w342/b33nnKl1vE0wPqV8kC3p0u8.jpg",
            "runtime": 119,
            "vote_average": 7.2
        },
        {
            "tmdb_id": 990011,
            "title": "Gladiator II",
            "original_title": "Gladiator II",
            "release_date": "2024-11-13",
            "year": 2024,
            "week_start_date": "2024-11-13",
            "director": "Ridley Scott",
            "genres": "Action, Aventure, Drame",
            "synopsis": "Des années après avoir assisté à la mort du héros Maximus aux mains de son oncle, Lucius doit à son tour entrer dans le Colisée lorsque son pays est conquis par les empereurs tyranniques.",
            "poster_url": "https://image.tmdb.org/t/p/w342/2cxhvwyEwRlysAmRHbtvK76QeeL.jpg",
            "runtime": 148,
            "vote_average": 6.8
        },
        {
            "tmdb_id": 990012,
            "title": "Vaiana 2",
            "original_title": "Moana 2",
            "release_date": "2024-11-27",
            "year": 2024,
            "week_start_date": "2024-11-27",
            "director": "David G. Derrick Jr.",
            "genres": "Animation, Aventure, Famille, Musique",
            "synopsis": "Après avoir reçu un appel inattendu de ses ancêtres navigateurs, Vaiana entreprend un voyage qui la mènera dans les eaux dangereuses et oubliées des confins de l'Océanie.",
            "poster_url": "https://image.tmdb.org/t/p/w342/m0S69v0p8j8U4fC0u7P8x9vN.jpg",
            "runtime": 100,
            "vote_average": 6.9
        }
    ]
