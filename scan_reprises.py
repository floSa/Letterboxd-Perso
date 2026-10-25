import sys
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database as db
import tmdb_client as tmdb

def scan_reprises():
    print("🎬 Initialisation de la base et colonnes...")
    db.init_db()

    api_key = tmdb.load_api_key()
    if not api_key:
        print("⚠️ Aucune clé TMDb trouvée.")
        return

    auth_params, headers = tmdb._build_auth(api_key)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        # Sélectionner en priorité les films avec de bonnes notes (les classiques et ressorties ont généralement de bonnes notes TMDb)
        cursor.execute("""
            SELECT tmdb_id, title, year, release_date 
            FROM movies 
            WHERE year >= 2024 AND is_reprise = 0
            ORDER BY vote_average DESC, release_date DESC
            LIMIT 400
        """)
        movies = [dict(row) for row in cursor.fetchall()]

    print(f"🔍 Analyse de {len(movies)} films pour identifier les reprises TMDb...")

    reprises_found = 0

    def check_movie(m):
        mid = m["tmdb_id"]
        myear = m["year"]
        url = f"https://api.themoviedb.org/3/movie/{mid}"
        try:
            res = requests.get(url, params={**auth_params, "append_to_response": "release_dates", "language": "fr-FR"}, headers=headers, timeout=6)
            if res.status_code == 200:
                data = res.json()
                orig_date = data.get("release_date") or ""
                is_rep = 0
                orig_yr = 0
                if orig_date and len(orig_date) >= 4:
                    try:
                        orig_yr = int(orig_date[:4])
                        if myear > 0 and (myear - orig_yr) >= 2:
                            is_rep = 1
                    except Exception:
                        pass
                
                # Check French release notes
                fr_rels = [c for c in data.get("release_dates", {}).get("results", []) if c.get("iso_3166_1") == "FR"]
                for fr_c in fr_rels:
                    for r in fr_c.get("release_dates", []):
                        note = (r.get("note") or "").lower()
                        if any(k in note for k in ["reprise", "ressortie", "re-release", "restaur", "4k", "retrospective"]):
                            is_rep = 1
                            break

                return mid, is_rep, orig_yr, orig_date, m["title"]
        except Exception:
            pass
        return mid, 0, 0, "", m["title"]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_movie, m) for m in movies]
        for f in as_completed(futures):
            mid, is_rep, orig_yr, orig_date, title = f.result()
            if is_rep:
                reprises_found += 1
                db.set_movie_reprise(mid, 1, orig_yr, orig_date)
                print(f"  🔄 Reprise identifiée : {title} ({orig_yr or orig_date[:4]})")

    print(f"✅ Analyse terminée : {reprises_found} reprise(s) identifiée(s) et enregistrée(s) en base.")

if __name__ == "__main__":
    scan_reprises()
