import sys
import os
import argparse
import zipfile
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

POSTERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "posters")
ZIP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posters_offline.zip")

def zip_posters(keep_files=True):
    if not os.path.isdir(POSTERS_DIR):
        print(f"Erreur : Le dossier {POSTERS_DIR} n'existe pas.")
        return

    files = [f for f in os.listdir(POSTERS_DIR) if os.path.isfile(os.path.join(POSTERS_DIR, f))]
    total = len(files)
    if total == 0:
        print(f"Aucune affiche a archiver dans {POSTERS_DIR}.")
        return

    print("=" * 60)
    print(f"Archivage de {total} affiches dans {ZIP_PATH}...")
    print("=" * 60)

    t0 = time.time()
    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, filename in enumerate(files, 1):
            filepath = os.path.join(POSTERS_DIR, filename)
            zf.write(filepath, arcname=filename)
            if idx % 100 == 0 or idx == total:
                pct = (idx / total) * 100
                print(f"  Compression: {idx}/{total} ({pct:.1f}%)...", end="\r", flush=True)

    elapsed = time.time() - t0
    zip_size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
    print(f"\nArchive creee avec succes en {elapsed:.1f}s ! Taille du zip : {zip_size_mb:.2f} Mo")

    if not keep_files:
        print("Nettoyage du dossier static/posters/...")
        for filename in files:
            try:
                os.remove(os.path.join(POSTERS_DIR, filename))
            except Exception:
                pass
        print("Dossier static/posters/ libere. L'archive zip est conservee.")

def unzip_posters():
    if not os.path.isfile(ZIP_PATH):
        print(f"Erreur : L'archive {ZIP_PATH} n'existe pas. Utilisez --zip d'abord.")
        return

    os.makedirs(POSTERS_DIR, exist_ok=True)
    t0 = time.time()
    print("=" * 60)
    print(f"Decompression de {ZIP_PATH} vers {POSTERS_DIR}...")
    print("=" * 60)

    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        members = zf.namelist()
        total = len(members)
        for idx, member in enumerate(members, 1):
            zf.extract(member, path=POSTERS_DIR)
            if idx % 100 == 0 or idx == total:
                pct = (idx / total) * 100
                print(f"  Extraction: {idx}/{total} ({pct:.1f}%)...", end="\r", flush=True)

    elapsed = time.time() - t0
    print(f"\nExtraction terminee en {elapsed:.1f}s ! {total} affiches pretes pour le mode hors-ligne.")

def show_status():
    os.makedirs(POSTERS_DIR, exist_ok=True)
    files = [f for f in os.listdir(POSTERS_DIR) if os.path.isfile(os.path.join(POSTERS_DIR, f))]
    folder_size_mb = sum(os.path.getsize(os.path.join(POSTERS_DIR, f)) for f in files) / (1024 * 1024) if files else 0.0

    has_zip = os.path.isfile(ZIP_PATH)
    zip_size_mb = (os.path.getsize(ZIP_PATH) / (1024 * 1024)) if has_zip else 0.0

    print("=" * 60)
    print("Etat du cache local et de l'archive hors-ligne :")
    print(f"  - Affiches locales dezippees : {len(files)} ({folder_size_mb:.2f} Mo)")
    print(f"  - Archive zip (posters_offline.zip) : {'Presente (' + f'{zip_size_mb:.2f} Mo)' if has_zip else 'Absente'}")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Gestion de l'archive zip des affiches (mode hors-ligne)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zip", action="store_true", help="Compresser le dossier static/posters/ en posters_offline.zip")
    group.add_argument("--unzip", action="store_true", help="Decompresser posters_offline.zip vers static/posters/ pour le mode hors-ligne")
    group.add_argument("--status", action="store_true", help="Afficher l'etat du cache et de l'archive")
    parser.add_argument("--clean", action="store_true", help="Avec --zip: supprime les fichiers non compresses apres archivage pour liberer de la place")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.zip:
        zip_posters(keep_files=not args.clean)
    elif args.unzip:
        unzip_posters()

if __name__ == "__main__":
    main()
