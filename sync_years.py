import sys
import os
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import database as db
import tmdb_client as tmdb

def sync_year(year: int, api_key: str):
    print(f"\n--- Synchronisation de l'annee {year} ---")
    def on_progress(month, total_months, count):
        print(f"  [Annee {year}] Mois {month:02d}/{total_months:02d} : {count} films recuperes...", end="\r", flush=True)

    try:
        movies = tmdb.fetch_french_releases_for_year(year, api_key, progress_callback=on_progress)
        for m in movies:
            db.insert_or_update_movie(m)
        print(f"\n  -> Succes pour {year} : {len(movies)} films integres en base.")
        return len(movies)
    except Exception as e:
        print(f"\n  -> Erreur lors de la synchronisation de {year} : {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Synchronisation des sorties cinema TMDb par annee.")
    parser.add_argument("years", nargs="*", type=int, help="Annees specifiques a synchroniser (ex: 2025 ou 2020 2024)")
    parser.add_argument("--missing", action="store_true", help="Synchronise toutes les annees manquantes (< 50 films)")
    parser.add_argument("--all", action="store_true", help="Synchronise toutes les annees de 2000 a 2026")
    args = parser.parse_args()

    api_key = tmdb.load_api_key()
    if not api_key:
        print("Erreur : Aucune cle TMDb configuree dans config.json.")
        sys.exit(1)

    years_to_sync = []
    if args.all:
        years_to_sync = list(range(2026, 1999, -1))
    elif args.missing:
        missing, _ = db.get_missing_years(2000, 2026)
        years_to_sync = missing
    elif len(args.years) == 1:
        years_to_sync = [args.years[0]]
    elif len(args.years) >= 2:
        start_y = min(args.years)
        end_y = max(args.years)
        years_to_sync = list(range(end_y, start_y - 1, -1))
    else:
        # Par defaut, proposer l'annee en cours et la precedente
        years_to_sync = [2026, 2025]

    print(f"Annees a synchroniser : {years_to_sync}")
    total_imported = 0
    for y in years_to_sync:
        total_imported += sync_year(y, api_key)

    stats = db.get_stats()
    print("\n" + "=" * 50)
    print("Synchronisation terminee avec succes !")
    print(f"Total de films traites sur cette session : {total_imported}")
    print(f"Nombre total de films dans la base : {stats['total']}")
    print("=" * 50)

if __name__ == "__main__":
    main()
