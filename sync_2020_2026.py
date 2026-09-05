import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database as db
import tmdb_client as tmdb

def main():
    print("Initialisation de la synchronisation 2020-2026...")
    api_key = tmdb.load_api_key()
    if not api_key:
        print("Erreur : Aucune cle TMDb trouvee dans config.json.")
        return

    years = [2026, 2025, 2024, 2023, 2022, 2021, 2020]
    total_imported = 0

    for y in years:
        print(f"\n--- Synchronisation Annee {y} ---")
        def on_progress(current_p, total_p, count):
            print(f"  [Annee {y}] Page {current_p}/{total_p} : {count} films trouves...", end="\r", flush=True)

        try:
            movies = tmdb.fetch_french_releases_for_year(y, api_key, progress_callback=on_progress)
            for m in movies:
                db.insert_or_update_movie(m)
            print(f"\n  -> Succes pour {y} : {len(movies)} films synchronises en base.")
            total_imported += len(movies)
        except Exception as e:
            print(f"\n  -> Erreur pour {y} : {e}")

    stats = db.get_stats()
    print("\n========================================================")
    print(f"Synchronisation terminee !")
    print(f"Films synchronises sur ce lot : {total_imported}")
    print(f"Total des films en base de donnees : {stats['total']}")
    print("========================================================")

if __name__ == "__main__":
    main()
