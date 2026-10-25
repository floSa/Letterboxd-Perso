import sys
import os
import argparse
import time
import concurrent.futures
import sqlite3
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cinetrack.db")
POSTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "posters")

def download_single_poster(item, size="w342"):
    tmdb_id, title, poster_url = item
    if not poster_url or "image.tmdb.org" not in poster_url:
        return False, "no_url"

    filename = poster_url.split("/")[-1]
    dest_path = os.path.join(POSTERS_DIR, filename)

    if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 500:
        return True, "already_exists"

    # URL avec la taille demandee (ex: w342)
    download_url = f"https://image.tmdb.org/t/p/{size}/{filename}"
    try:
        resp = requests.get(download_url, timeout=10)
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            return True, "downloaded"
        return False, f"status_{resp.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Telechargement local des affiches TMDb (mode hors-ligne)")
    parser.add_argument("years", nargs="*", type=int, help="Annees specifiques a telecharger (ex: 2026 ou 2024 2026)")
    parser.add_argument("--all", action="store_true", help="Telecharger toutes les affiches de la base (2000 a 2026)")
    parser.add_argument("--recent", action="store_true", help="Telecharger les annees recentes (2024 a 2026)")
    parser.add_argument("--test", action="store_true", help="Telecharger un echantillon de test (100 affiches)")
    parser.add_argument("--size", default="w342", choices=["w92", "w185", "w342", "w500"], help="Resolution des affiches (defaut: w342)")
    parser.add_argument("--workers", type=int, default=10, help="Nombre de threads simultanes (defaut: 10)")
    args = parser.parse_args()

    os.makedirs(POSTERS_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    query = "SELECT tmdb_id, title, poster_url FROM movies WHERE poster_url LIKE 'https://image.tmdb.org%'"
    params = []

    if args.test:
        query += " ORDER BY year DESC, release_date DESC LIMIT 100"
    elif args.recent:
        query += " AND year >= 2024 ORDER BY year DESC, release_date DESC"
    elif len(args.years) == 1:
        query += " AND year = ? ORDER BY release_date DESC"
        params.append(args.years[0])
    elif len(args.years) >= 2:
        start_y = min(args.years)
        end_y = max(args.years)
        query += " AND year >= ? AND year <= ? ORDER BY year DESC, release_date DESC"
        params.extend([start_y, end_y])
    elif not args.all:
        # Par defaut sans argument: annees 2025 et 2026
        query += " AND year >= 2025 ORDER BY year DESC, release_date DESC"

    cur.execute(query, params)
    items = cur.fetchall()
    conn.close()

    total = len(items)
    print("=" * 60)
    print(f"Telechargement des miniatures locales TMDb (Resolution: {args.size})")
    print(f"Nombre d'affiches cibles : {total}")
    print(f"Dossier de destination : {POSTERS_DIR}")
    print("=" * 60)

    if total == 0:
        print("Aucune affiche a telecharger pour ces criteres.")
        return

    downloaded = 0
    already = 0
    failed = 0
    t0 = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(download_single_poster, item, args.size): item for item in items}
        for idx, future in enumerate(concurrent.futures.as_completed(futures), 1):
            success, reason = future.result()
            if success:
                if reason == "downloaded":
                    downloaded += 1
                else:
                    already += 1
            else:
                failed += 1

            if idx % 20 == 0 or idx == total:
                elapsed = time.time() - t0
                speed = idx / max(0.1, elapsed)
                pct = (idx / total) * 100
                print(f"  Progression: {idx}/{total} ({pct:.1f}%) - {downloaded} telechargees, {already} deja presentes ({speed:.1f} affiches/sec)...", end="\r", flush=True)

    elapsed = time.time() - t0
    # Mesurer la taille du dossier
    total_size_mb = sum(os.path.getsize(os.path.join(POSTERS_DIR, f)) for f in os.listdir(POSTERS_DIR) if os.path.isfile(os.path.join(POSTERS_DIR, f))) / (1024 * 1024)

    print("\n" + "=" * 60)
    print(f"Session terminee en {elapsed:.1f}s !")
    print(f"Nouvelles affiches telechargees : {downloaded}")
    print(f"Affiches deja en cache local   : {already}")
    print(f"Echecs (indisponibles)        : {failed}")
    print(f"Total affiches dans le cache  : {len(os.listdir(POSTERS_DIR))}")
    print(f"Espace disque utilise         : {total_size_mb:.2f} Mo")
    print("=" * 60)

if __name__ == "__main__":
    main()
