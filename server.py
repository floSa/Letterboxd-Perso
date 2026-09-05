import os
import sys
import json
import sqlite3
import threading

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

import database as db
import tmdb_client as tmdb
import obsidian_export as obs

# Initialisation de la base
db.init_db()

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# État de synchronisation globale
sync_state = {
    "is_syncing": False,
    "progress": 0,
    "message": ""
}

class CineTriageHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Silence standard HTTP logs pour garder la console propre
        pass

    def send_json(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status_code=400):
        self.send_json({"error": message, "success": False}, status_code=status_code)

    def get_post_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw = self.rfile.read(content_length).decode("utf-8")
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 1. API : Statistiques globales
        if path == "/api/stats":
            stats = db.get_stats()
            cur_year = datetime.now().year
            missing, _ = db.get_missing_years(2000, cur_year)
            stats["missing_years_count"] = len(missing)
            stats["current_year"] = cur_year
            return self.send_json(stats)

        # 2. API : Genres
        elif path == "/api/genres":
            genres = db.get_all_genres()
            return self.send_json({"genres": genres})

        # 3. API : Liste des films selon échelle (Semaine, Mois, Année)
        elif path == "/api/movies":
            scale = params.get("scale", ["week"])[0]
            date_str = params.get("date", [datetime.now().strftime("%Y-%m-%d")])[0]
            api_key = tmdb.load_api_key()

            try:
                target_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                target_dt = datetime.now().date()

            cinema_only = params.get("cinema_only", ["true"])[0].lower() in ["true", "1", "yes"]
            hide_reprises = params.get("hide_reprises", ["false"])[0].lower() in ["true", "1", "yes"]
            sort_by = params.get("sort", ["tmdb_desc"])[0]

            if scale == "week":
                offset = (target_dt.weekday() - 2) % 7
                wednesday = target_dt - timedelta(days=offset)
                tuesday = wednesday + timedelta(days=6)
                wed_str = wednesday.strftime("%Y-%m-%d")
                tue_str = tuesday.strftime("%Y-%m-%d")

                movies = db.get_movies_by_week(wed_str, include_dismissed=False, cinema_only=cinema_only, sort_by=sort_by, hide_reprises=hide_reprises)

                # Fetch TMDb automatique si vide et clé présente
                if not movies and api_key and not cinema_only:
                    fetched = tmdb.fetch_movies_for_date_range(wed_str, tue_str, api_key)
                    if fetched:
                        for f_m in fetched:
                            db.insert_or_update_movie(f_m)
                        movies = db.get_movies_by_week(wed_str, include_dismissed=False, cinema_only=cinema_only, sort_by=sort_by, hide_reprises=hide_reprises)

                # Enrichissement casting, réalisateur et reprise en arrière-plan (non-bloquant)
                if api_key and movies:
                    def enrich_background(m_list, key):
                        for m in m_list:
                            needs_credits = not m.get("director") or m.get("director") == "Inconnu" or not m.get("cast")
                            needs_reprise = m.get("is_reprise") is None or (m.get("is_reprise") == 0 and not m.get("original_release_date"))
                            if needs_credits or needs_reprise:
                                d, cast, rt, is_rep, o_yr, o_rd = tmdb.fetch_movie_director_and_runtime(m["tmdb_id"], key, movie_year=m.get("year", 0))
                                db.update_movie_credits_and_runtime(m["tmdb_id"], d, cast, rt, is_rep, o_yr, o_rd)
                    threading.Thread(target=enrich_background, args=(list(movies), api_key), daemon=True).start()

                return self.send_json({
                    "scale": "week",
                    "target_date": date_str,
                    "week_start": wed_str,
                    "week_end": tue_str,
                    "title": f"Semaine du mercredi {wednesday.strftime('%d/%m/%Y')} au {tuesday.strftime('%d/%m/%Y')}",
                    "movies": movies
                })

            elif scale == "month":
                year = int(params.get("year", [target_dt.year])[0])
                month = int(params.get("month", [target_dt.month])[0])
                month_movies = db.get_movies_by_month(year, month, cinema_only=cinema_only, sort_by=sort_by, hide_reprises=hide_reprises)

                # Grouper par semaine de sortie (mercredi)
                weeks_map = {}
                for m in month_movies:
                    w_key = m.get("week_start_date") or m.get("release_date")
                    if w_key not in weeks_map:
                        weeks_map[w_key] = []
                    weeks_map[w_key].append(m)

                # Trier les semaines par ordre croissant de date
                sorted_keys = sorted(weeks_map.keys())
                weeks_list = []
                for idx, w_key in enumerate(sorted_keys, 1):
                    try:
                        w_dt = datetime.strptime(w_key, "%Y-%m-%d")
                        w_label = f"Semaine du {w_dt.strftime('%d/%m')}"
                    except Exception:
                        w_label = f"Semaine du {w_key}"

                    weeks_list.append({
                        "week_key": w_key,
                        "label": w_label,
                        "movie_count": len(weeks_map[w_key]),
                        "movies": weeks_map[w_key]
                    })

                month_names = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
                m_label = f"{month_names[month - 1]} {year}"

                return self.send_json({
                    "scale": "month",
                    "year": year,
                    "month": month,
                    "title": f"{m_label}",
                    "total_movies": len(month_movies),
                    "weeks": weeks_list
                })

            elif scale == "year":
                year = int(params.get("year", [target_dt.year])[0])
                page = int(params.get("page", [1])[0])
                page_size = 40  # 40 films par page pour fluidité totale

                all_year_movies = db.get_movies_by_year(year, cinema_only=cinema_only, sort_by=sort_by, hide_reprises=hide_reprises)
                total_movies = len(all_year_movies)
                total_pages = max(1, (total_movies + page_size - 1) // page_size)
                page = max(1, min(page, total_pages))

                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paged_movies = all_year_movies[start_idx:end_idx]

                return self.send_json({
                    "scale": "year",
                    "year": year,
                    "title": f"Année {year}",
                    "page": page,
                    "total_pages": total_pages,
                    "total_movies": total_movies,
                    "page_size": page_size,
                    "movies": paged_movies
                })

        # 4. API : Watchlist (À Voir)
        elif path == "/api/watchlist":
            genre = params.get("genre", ["Tous"])[0]
            min_want = float(params.get("min_want", [1.0])[0])
            search = params.get("search", [""])[0]
            movies = db.get_watchlist(genre=genre, min_want=int(min_want), search=search if search else None)
            return self.send_json({"movies": movies, "count": len(movies)})

        # 5. API : Films Vus
        elif path == "/api/watched":
            year_val = params.get("year", [""])[0]
            year = int(year_val) if year_val and year_val.isdigit() else None
            genre = params.get("genre", ["Tous"])[0]
            sort_by = params.get("sort", ["rating_desc"])[0]
            movies = db.get_watched_movies(year=year, genre=genre, sort_by=sort_by)
            return self.send_json({"movies": movies, "count": len(movies)})

        # 6. API : État de la synchronisation
        elif path == "/api/sync-status":
            return self.send_json(sync_state)

        # 7. Redirection racine vers /index.html
        elif path == "/" or path == "":
            self.path = "/index.html"
            return super().do_GET()

        # Fichiers statiques
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.get_post_body()

        # 1. Noter un film (Étoiles 0.0 à 5.0)
        if path == "/api/rate":
            tmdb_id = body.get("tmdb_id")
            rating = float(body.get("rating", 0.0))
            if not tmdb_id:
                return self.send_error_json("tmdb_id requis")
            db.set_movie_rating(tmdb_id, rating)
            stats = db.get_stats()
            return self.send_json({"success": True, "tmdb_id": tmdb_id, "user_rating": rating, "stats": stats})

        # 2. Recommandation / Envie (Cœurs 0.0 à 5.0)
        elif path == "/api/want":
            tmdb_id = body.get("tmdb_id")
            want_rating = float(body.get("want_rating", 0.0))
            if not tmdb_id:
                return self.send_error_json("tmdb_id requis")
            db.set_movie_want(tmdb_id, want_rating)
            stats = db.get_stats()
            return self.send_json({"success": True, "tmdb_id": tmdb_id, "want_rating": want_rating, "stats": stats})

        # 3. Supprimer / Éliminer un film
        elif path == "/api/dismiss":
            tmdb_id = body.get("tmdb_id")
            if not tmdb_id:
                return self.send_error_json("tmdb_id requis")
            db.set_movie_status(tmdb_id, "dismissed")
            stats = db.get_stats()
            return self.send_json({"success": True, "tmdb_id": tmdb_id, "stats": stats})

        # 4. Restaurer un film (annuler suppression)
        elif path == "/api/restore":
            tmdb_id = body.get("tmdb_id")
            if not tmdb_id:
                return self.send_error_json("tmdb_id requis")
            db.set_movie_status(tmdb_id, "kept")
            stats = db.get_stats()
            return self.send_json({"success": True, "tmdb_id": tmdb_id, "stats": stats})

        # 4b. Nettoyer le bruit (courts-métrages, sans affiche, placeholder 31/12)
        elif path == "/api/clean-noise":
            week_date = body.get("week_date")
            all_db = bool(body.get("all", False))
            count = db.dismiss_noise(week_date=week_date, all_db=all_db)
            stats = db.get_stats()
            return self.send_json({"success": True, "dismissed_count": count, "stats": stats})

        # 5. Déclencher la synchronisation TMDb intelligente
        elif path == "/api/sync":
            global sync_state
            if sync_state["is_syncing"]:
                return self.send_json({"success": False, "message": "Synchronisation déjà en cours."})

            api_key = tmdb.load_api_key()
            if not api_key:
                return self.send_error_json("Aucune clé API TMDb trouvée dans config.json.")

            def run_background_sync():
                global sync_state
                sync_state["is_syncing"] = True
                sync_state["progress"] = 5
                sync_state["message"] = "Vérification des sorties récentes..."
                try:
                    cur_y = datetime.now().year
                    def cb_cur(c, t, cnt):
                        sync_state["progress"] = int((c / max(1, t)) * 30)
                        sync_state["message"] = f"Mise à jour {cur_y} ({c}/{t})..."

                    movies = tmdb.fetch_french_releases_for_year(cur_y, api_key, progress_callback=cb_cur)
                    for m in movies:
                        db.insert_or_update_movie(m)

                    missing, _ = db.get_missing_years(2000, cur_y)
                    if missing:
                        batch = missing[:2]
                        for idx, y in enumerate(batch):
                            def cb_m(c, t, cnt):
                                base = 30 + int((idx / len(batch)) * 65)
                                sync_state["progress"] = base + int((c / max(1, t)) * (65 // len(batch)))
                                sync_state["message"] = f"Importation {y} ({cnt} films)..."
                            m_y = tmdb.fetch_french_releases_for_year(y, api_key, progress_callback=cb_m)
                            for m in m_y:
                                db.insert_or_update_movie(m)

                    sync_state["progress"] = 100
                    sync_state["message"] = "Synchronisation terminée avec succès !"
                except Exception as e:
                    sync_state["message"] = f"Erreur : {e}"
                finally:
                    sync_state["is_syncing"] = False

            t = threading.Thread(target=run_background_sync, daemon=True)
            t.start()
            return self.send_json({"success": True, "message": "Synchronisation lancée."})

        # 6. Export Obsidian
        elif path == "/api/export-obsidian":
            vault_dir = body.get("path", "").strip()
            export_type = body.get("type", "all")
            if not vault_dir:
                return self.send_error_json("Chemin de dossier Obsidian requis.")

            try:
                os.makedirs(vault_dir, exist_ok=True)
                if export_type == "watchlist":
                    movies = db.get_watchlist(min_want=1)
                elif export_type == "watched":
                    movies = db.get_watched_movies()
                else:
                    with db.get_connection() as conn:
                        c = conn.cursor()
                        c.execute("SELECT * FROM movies WHERE status = 'kept' OR is_watched = 1")
                        movies = [dict(r) for r in c.fetchall()]

                count = 0
                for m in movies:
                    obs.export_movie_to_markdown(m, vault_dir)
                    count += 1

                obs.create_obsidian_index_note(vault_dir)
                return self.send_json({"success": True, "exported_count": count})
            except Exception as e:
                return self.send_error_json(str(e))

        return self.send_error_json("Route inconnue", 404)

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, CineTriageHandler)
    print(f"Serveur CineTriage actif sur http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
