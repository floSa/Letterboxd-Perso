import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cinetrack.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialise le schéma de la base de données si nécessaire."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tmdb_id INTEGER UNIQUE,
                title TEXT NOT NULL,
                original_title TEXT,
                release_date TEXT,          -- YYYY-MM-DD
                year INTEGER,
                week_start_date TEXT,       -- Date du mercredi de sortie (YYYY-MM-DD)
                director TEXT,
                genres TEXT,                -- 'Drame, Comédie'
                synopsis TEXT,
                poster_url TEXT,
                runtime INTEGER DEFAULT 0,
                vote_average REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending', -- 'pending' (à trier), 'kept' (gardé), 'dismissed' (supprimé/ignoré)
                is_watched INTEGER DEFAULT 0,  -- 0 ou 1
                want_rating INTEGER DEFAULT 0, -- 0 à 5 (envie de voir / priorité)
                user_rating REAL DEFAULT 0.0,  -- 0.0 à 5.0 (par pas de 0.5)
                notes TEXT DEFAULT '',
                cast TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Migration automatique des colonnes si elles manquent
        cursor.execute("PRAGMA table_info(movies);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "cast" not in columns:
            cursor.execute("ALTER TABLE movies ADD COLUMN cast TEXT DEFAULT '';")
        if "is_reprise" not in columns:
            cursor.execute("ALTER TABLE movies ADD COLUMN is_reprise INTEGER DEFAULT 0;")
        if "original_year" not in columns:
            cursor.execute("ALTER TABLE movies ADD COLUMN original_year INTEGER DEFAULT 0;")
        if "original_release_date" not in columns:
            cursor.execute("ALTER TABLE movies ADD COLUMN original_release_date TEXT DEFAULT '';")
        if "is_owned" not in columns:
            cursor.execute("ALTER TABLE movies ADD COLUMN is_owned INTEGER DEFAULT 0;")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_year ON movies(year);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_week ON movies(week_start_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_status ON movies(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_watched ON movies(is_watched);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_reprise ON movies(is_reprise);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movies_owned ON movies(is_owned);")

        # Identification automatique immédiate des reprises évidentes (règles locales 0 ms)
        cursor.execute("""
            UPDATE movies 
            SET is_reprise = 1,
                original_year = CAST(SUBSTR(release_date, 1, 4) AS INT),
                original_release_date = release_date
            WHERE CAST(SUBSTR(release_date, 1, 4) AS INT) <= (year - 2)
              AND is_reprise = 0
              AND release_date IS NOT NULL
              AND length(release_date) >= 4;
        """)
        cursor.execute("""
            UPDATE movies 
            SET is_reprise = 1
            WHERE is_reprise = 0
              AND (
                  title LIKE '%(reprise)%' 
                  OR title LIKE '%(ressortie)%' 
                  OR synopsis LIKE '%ressortie en version%' 
                  OR synopsis LIKE '%reprise en salle%'
                  OR synopsis LIKE '%restauration 4K%'
                  OR synopsis LIKE '%version restaurée%'
              );
        """)
        conn.commit()

def insert_or_update_movie(movie: dict):
    """Insère ou met à jour les métadonnées d'un film sans écraser le statut utilisateur."""
    m = dict(movie)
    m.setdefault("is_reprise", 0)
    m.setdefault("original_year", 0)
    m.setdefault("original_release_date", "")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO movies (
                tmdb_id, title, original_title, release_date, year, 
                week_start_date, director, genres, synopsis, poster_url, 
                runtime, vote_average, is_reprise, original_year, original_release_date
            ) VALUES (
                :tmdb_id, :title, :original_title, :release_date, :year, 
                :week_start_date, :director, :genres, :synopsis, :poster_url, 
                :runtime, :vote_average, :is_reprise, :original_year, :original_release_date
            )
            ON CONFLICT(tmdb_id) DO UPDATE SET
                title=excluded.title,
                original_title=excluded.original_title,
                release_date=excluded.release_date,
                year=excluded.year,
                week_start_date=excluded.week_start_date,
                director=COALESCE(excluded.director, movies.director),
                genres=COALESCE(excluded.genres, movies.genres),
                synopsis=COALESCE(excluded.synopsis, movies.synopsis),
                poster_url=COALESCE(excluded.poster_url, movies.poster_url),
                runtime=CASE WHEN excluded.runtime > 0 THEN excluded.runtime ELSE movies.runtime END,
                vote_average=excluded.vote_average,
                is_reprise=CASE WHEN excluded.is_reprise = 1 THEN 1 ELSE movies.is_reprise END,
                original_year=CASE WHEN excluded.original_year > 0 THEN excluded.original_year ELSE movies.original_year END,
                original_release_date=CASE WHEN excluded.original_release_date != '' THEN excluded.original_release_date ELSE movies.original_release_date END,
                updated_at=CURRENT_TIMESTAMP
        """, m)
        conn.commit()

def insert_or_update_movies_batch(movies: list[dict]):
    """Insère ou met à jour en lot (transaction unique) une liste de films sans écraser le statut utilisateur."""
    if not movies:
        return
    cleaned = []
    for movie in movies:
        m = dict(movie)
        m.setdefault("is_reprise", 0)
        m.setdefault("original_year", 0)
        m.setdefault("original_release_date", "")
        cleaned.append(m)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO movies (
                tmdb_id, title, original_title, release_date, year, 
                week_start_date, director, genres, synopsis, poster_url, 
                runtime, vote_average, is_reprise, original_year, original_release_date
            ) VALUES (
                :tmdb_id, :title, :original_title, :release_date, :year, 
                :week_start_date, :director, :genres, :synopsis, :poster_url, 
                :runtime, :vote_average, :is_reprise, :original_year, :original_release_date
            )
            ON CONFLICT(tmdb_id) DO UPDATE SET
                title=excluded.title,
                original_title=excluded.original_title,
                release_date=excluded.release_date,
                year=excluded.year,
                week_start_date=excluded.week_start_date,
                director=COALESCE(excluded.director, movies.director),
                genres=COALESCE(excluded.genres, movies.genres),
                synopsis=COALESCE(excluded.synopsis, movies.synopsis),
                poster_url=COALESCE(excluded.poster_url, movies.poster_url),
                runtime=CASE WHEN excluded.runtime > 0 THEN excluded.runtime ELSE movies.runtime END,
                vote_average=excluded.vote_average,
                is_reprise=CASE WHEN excluded.is_reprise = 1 THEN 1 ELSE movies.is_reprise END,
                original_year=CASE WHEN excluded.original_year > 0 THEN excluded.original_year ELSE movies.original_year END,
                original_release_date=CASE WHEN excluded.original_release_date != '' THEN excluded.original_release_date ELSE movies.original_release_date END,
                updated_at=CURRENT_TIMESTAMP
        """, cleaned)
        conn.commit()

def get_available_years():
    """Retourne la liste des années présentes en base par ordre décroissant."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT year FROM movies WHERE year IS NOT NULL ORDER BY year DESC")
        return [row["year"] for row in cursor.fetchall()]

def get_wednesdays_for_year(year: int):
    """Retourne la liste des mercredis avec des sorties pour l'année donnée."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT week_start_date, COUNT(*) as total,
                   SUM(CASE WHEN status != 'dismissed' THEN 1 ELSE 0 END) as active_count,
                   SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count
            FROM movies 
            WHERE year = ? 
            GROUP BY week_start_date 
            ORDER BY week_start_date DESC
        """, (year,))
        return [dict(row) for row in cursor.fetchall()]

def get_movies_by_week(week_date: str, include_dismissed: bool = False, cinema_only: bool = False, sort_by: str = "tmdb_desc", hide_reprises: bool = False):
    """Récupère les films d'une semaine donnée avec filtres et tri (reprises reléguées en bas)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM movies WHERE week_start_date = ?"
        params = [week_date]
        if not include_dismissed:
            query += " AND status != 'dismissed'"
        if cinema_only:
            query += """ AND (runtime = 0 OR runtime >= 50) 
                         AND (poster_url IS NOT NULL AND poster_url != '')
                         AND NOT (release_date LIKE '%-12-31' AND vote_average = 0)"""
        if hide_reprises:
            query += " AND (is_reprise = 0 OR status = 'kept' OR is_watched = 1)"
        
        # Les reprises sont toujours placées plus bas que les vraies nouveautés
        if sort_by == "tmdb_desc":
            query += " ORDER BY is_reprise ASC, vote_average DESC, title ASC"
        elif sort_by == "date_desc":
            query += " ORDER BY is_reprise ASC, release_date DESC, vote_average DESC"
        elif sort_by == "title_asc":
            query += " ORDER BY is_reprise ASC, title ASC"
        else:
            query += " ORDER BY is_reprise ASC, vote_average DESC, title ASC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_movies_by_month(year: int, month: int, cinema_only: bool = False, sort_by: str = "tmdb_desc", hide_reprises: bool = False):
    """Récupère les films d'un mois donné avec filtres et tri."""
    prefix = f"{year}-{month:02d}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM movies WHERE release_date LIKE ? AND status != 'dismissed'"
        params = [prefix]
        if cinema_only:
            query += """ AND (runtime = 0 OR runtime >= 50) 
                         AND (poster_url IS NOT NULL AND poster_url != '')
                         AND NOT (release_date LIKE '%-12-31' AND vote_average = 0)"""
        if hide_reprises:
            query += " AND (is_reprise = 0 OR status = 'kept' OR is_watched = 1)"
        
        if sort_by == "date_asc":
            query += " ORDER BY is_reprise ASC, release_date ASC, title ASC"
        elif sort_by == "tmdb_desc":
            query += " ORDER BY is_reprise ASC, vote_average DESC, release_date DESC"
        elif sort_by == "date_desc":
            query += " ORDER BY is_reprise ASC, release_date DESC, vote_average DESC"
        elif sort_by == "title_asc":
            query += " ORDER BY is_reprise ASC, title ASC"
        else:
            query += " ORDER BY is_reprise ASC, release_date ASC, title ASC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_movies_by_year(year: int, cinema_only: bool = False, sort_by: str = "tmdb_desc", hide_reprises: bool = False):
    """Récupère les films d'une année donnée avec filtres et tri."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM movies WHERE year = ? AND status != 'dismissed'"
        params = [year]
        if cinema_only:
            query += """ AND (runtime = 0 OR runtime >= 50) 
                         AND (poster_url IS NOT NULL AND poster_url != '')
                         AND NOT (release_date LIKE '%-12-31' AND vote_average = 0)"""
        if hide_reprises:
            query += " AND (is_reprise = 0 OR status = 'kept' OR is_watched = 1)"
        
        if sort_by == "date_asc":
            query += " ORDER BY is_reprise ASC, release_date ASC, title ASC"
        elif sort_by == "tmdb_desc":
            query += " ORDER BY is_reprise ASC, vote_average DESC, release_date DESC"
        elif sort_by == "date_desc":
            query += " ORDER BY is_reprise ASC, release_date DESC, vote_average DESC"
        elif sort_by == "title_asc":
            query += " ORDER BY is_reprise ASC, title ASC"
        else:
            query += " ORDER BY is_reprise ASC, release_date ASC, title ASC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def dismiss_noise(week_date: str = None, all_db: bool = False) -> int:
    """
    Élimine en masse (status = 'dismissed') le bruit :
    - Courts-métrages (< 50 min)
    - Entrées sans affiche
    - Placeholder 31/12 TMDb sans note ni synopsis
    Ne touche JAMAIS aux films vus ou mis en favoris (status='kept').
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            UPDATE movies 
            SET status = 'dismissed', updated_at = CURRENT_TIMESTAMP
            WHERE is_watched = 0 
              AND status != 'kept'
              AND (
                  (runtime > 0 AND runtime < 50)
                  OR (poster_url IS NULL OR poster_url = '')
                  OR ((synopsis IS NULL OR synopsis = '' OR synopsis = 'Aucun synopsis disponible.') AND vote_average = 0)
                  OR (release_date LIKE '%-12-31' AND vote_average = 0)
              )
        """
        params = []
        if not all_db and week_date:
            query += " AND week_start_date = ?"
            params.append(week_date)
            
        cursor.execute(query, params)
        count = cursor.rowcount
        conn.commit()
        return count

def set_movie_status(tmdb_id: int, status: str):
    """Met à jour le statut du film ('pending', 'kept', 'dismissed')."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE movies SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE tmdb_id = ?", (status, tmdb_id))
        conn.commit()

def set_movie_want(tmdb_id: int, want_rating: float):
    """Met à jour l'envie/recommandation (0.0 à 5.0). Si want > 0, marque automatiquement comme 'kept'."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if want_rating > 0:
            cursor.execute("UPDATE movies SET want_rating = ?, status = 'kept', updated_at = CURRENT_TIMESTAMP WHERE tmdb_id = ?", (want_rating, tmdb_id))
        else:
            cursor.execute("UPDATE movies SET want_rating = 0.0, updated_at = CURRENT_TIMESTAMP WHERE tmdb_id = ?", (tmdb_id,))
        conn.commit()

def set_movie_watched(tmdb_id: int, is_watched: bool, user_rating: float = 0.0):
    """Marque un film comme vu et met à jour sa note sur 5."""
    with get_connection() as conn:
        cursor = conn.cursor()
        watched_val = 1 if is_watched else 0
        cursor.execute("""
            UPDATE movies 
            SET is_watched = ?, 
                user_rating = ?,
                status = CASE WHEN status = 'dismissed' THEN 'kept' ELSE status END,
                updated_at = CURRENT_TIMESTAMP 
            WHERE tmdb_id = ?
        """, (watched_val, user_rating, tmdb_id))
        conn.commit()

def update_movie_credits_and_runtime(tmdb_id: int, director: str, cast: str, runtime: int, is_reprise: int = None, original_year: int = None, original_release_date: str = None):
    """Met en cache le réalisateur, les acteurs, la durée et l'état de reprise récupérés depuis TMDb."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_reprise is not None:
            cursor.execute("""
                UPDATE movies 
                SET director = ?, cast = ?, runtime = ?,
                    is_reprise = CASE WHEN ? = 1 THEN 1 ELSE is_reprise END,
                    original_year = CASE WHEN ? > 0 THEN ? ELSE original_year END,
                    original_release_date = CASE WHEN ? != '' THEN ? ELSE original_release_date END,
                    updated_at = CURRENT_TIMESTAMP 
                WHERE tmdb_id = ?
            """, (director, cast, runtime, is_reprise, original_year or 0, original_year or 0, original_release_date or '', original_release_date or '', tmdb_id))
        else:
            cursor.execute("""
                UPDATE movies 
                SET director = ?, cast = ?, runtime = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE tmdb_id = ?
            """, (director, cast, runtime, tmdb_id))
        conn.commit()

def set_movie_reprise(tmdb_id: int, is_reprise: int, original_year: int = 0, original_release_date: str = ''):
    """Marque explicitement un film comme reprise ou nouveauté."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE movies 
            SET is_reprise = ?, 
                original_year = CASE WHEN ? > 0 THEN ? ELSE original_year END,
                original_release_date = CASE WHEN ? != '' THEN ? ELSE original_release_date END,
                updated_at = CURRENT_TIMESTAMP 
            WHERE tmdb_id = ?
        """, (is_reprise, original_year, original_year, original_release_date, original_release_date, tmdb_id))
        conn.commit()

def set_movie_rating(tmdb_id: int, user_rating: float):
    """
    Dès qu'une note est saisie (> 0), le film est automatiquement marqué comme 'Vu' et 'Garde'.
    Si la note est remise à 0, le film redevient 'Non vu'.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_rating > 0:
            cursor.execute("""
                UPDATE movies 
                SET is_watched = 1, 
                    user_rating = ?, 
                    status = CASE WHEN status = 'dismissed' THEN 'kept' ELSE status END,
                    updated_at = CURRENT_TIMESTAMP 
                WHERE tmdb_id = ?
            """, (user_rating, tmdb_id))
        else:
            cursor.execute("""
                UPDATE movies 
                SET is_watched = 0, 
                    user_rating = 0.0, 
                    updated_at = CURRENT_TIMESTAMP 
                WHERE tmdb_id = ?
            """, (tmdb_id,))
        conn.commit()

def toggle_movie_owned(tmdb_id: int) -> int:
    """Bascule l'état possédé (0 ou 1) d'un film dans la bibliothèque."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT is_owned FROM movies WHERE tmdb_id = ?", (tmdb_id,))
        row = cursor.fetchone()
        cur_val = row["is_owned"] if row and row["is_owned"] is not None else 0
        new_val = 0 if cur_val == 1 else 1
        cursor.execute("""
            UPDATE movies 
            SET is_owned = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE tmdb_id = ?
        """, (new_val, tmdb_id))
        conn.commit()
        return new_val

def set_movie_owned(tmdb_id: int, is_owned: int):
    """Définit explicitement l'état possédé (0 ou 1) d'un film."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE movies 
            SET is_owned = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE tmdb_id = ?
        """, (1 if is_owned else 0, tmdb_id))
        conn.commit()

def get_closest_available_wednesday():
    """Trouve la semaine la plus proche de la date actuelle parmi les semaines enregistrées."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        # Semaine la plus proche aujourd'hui ou dans le passé
        cursor.execute("""
            SELECT week_start_date FROM movies 
            WHERE week_start_date <= ? 
            ORDER BY week_start_date DESC LIMIT 1
        """, (today_str,))
        row = cursor.fetchone()
        if row:
            return row["week_start_date"]
        # Sinon la plus proche disponible dans le futur
        cursor.execute("SELECT week_start_date FROM movies ORDER BY week_start_date ASC LIMIT 1")
        row = cursor.fetchone()
        return row["week_start_date"] if row else today_str

def get_watchlist(genre: str = None, min_want: int = 1, search: str = None, date_from: str = None, date_to: str = None, owned: str = None):
    """Retourne la liste des films gardés et non vus (priorité à voir) avec filtres de date et possession."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM movies WHERE is_watched = 0 AND status = 'kept' AND want_rating >= ?"
        params = [min_want]
        if genre and genre != "Tous":
            query += " AND genres LIKE ?"
            params.append(f"%{genre}%")
        if search:
            query += " AND (title LIKE ? OR director LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if date_from:
            query += " AND release_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND release_date <= ?"
            params.append(date_to)
        if owned in ["1", "true", "owned"]:
            query += " AND is_owned = 1"
        elif owned in ["0", "false", "not_owned"]:
            query += " AND is_owned = 0"
        query += " ORDER BY want_rating DESC, release_date DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_watched_movies(year: int = None, genre: str = None, sort_by: str = "rating_desc", date_from: str = None, date_to: str = None, owned: str = None):
    """Retourne les films vus avec possibilité de filtrer par plage de dates, genre, possession et note."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM movies WHERE is_watched = 1"
        params = []
        if year:
            query += " AND year = ?"
            params.append(year)
        if genre and genre != "Tous":
            query += " AND genres LIKE ?"
            params.append(f"%{genre}%")
        if date_from:
            query += " AND release_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND release_date <= ?"
            params.append(date_to)
        if owned in ["1", "true", "owned"]:
            query += " AND is_owned = 1"
        elif owned in ["0", "false", "not_owned"]:
            query += " AND is_owned = 0"
            
        if sort_by == "rating_desc":
            query += " ORDER BY user_rating DESC, title ASC"
        elif sort_by == "date_desc":
            query += " ORDER BY release_date DESC"
        elif sort_by == "title_asc":
            query += " ORDER BY title ASC"
            
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_all_genres():
    """Extrait tous les genres uniques présents en base."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT genres FROM movies WHERE genres IS NOT NULL AND genres != ''")
        genres_set = set()
        for row in cursor.fetchall():
            for g in row["genres"].split(","):
                clean = g.strip()
                if clean:
                    genres_set.add(clean)
        return sorted(list(genres_set))

def get_stats():
    """Statistiques globales du profil."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM movies")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM movies WHERE status = 'kept'")
        kept = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM movies WHERE status = 'dismissed'")
        dismissed = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM movies WHERE is_watched = 1")
        watched = cursor.fetchone()[0]
        cursor.execute("SELECT AVG(user_rating) FROM movies WHERE is_watched = 1 AND user_rating > 0")
        avg_rating_row = cursor.fetchone()[0]
        avg_rating = round(avg_rating_row, 2) if avg_rating_row else 0.0
        return {
            "total": total,
            "kept": kept,
            "dismissed": dismissed,
            "watched": watched,
            "avg_rating": avg_rating
        }

def get_missing_years(start_year: int = 2000, end_year: int = 2026):
    """Identifie les années manquantes ou incomplètes entre start_year et end_year."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT year, COUNT(*) as cnt 
            FROM movies 
            WHERE year >= ? AND year <= ? 
            GROUP BY year
        """, (start_year, end_year))
        counts = {row["year"]: row["cnt"] for row in cursor.fetchall()}
        missing = [y for y in range(start_year, end_year + 1) if counts.get(y, 0) < 50]
        missing.sort(reverse=True)
        return missing, counts

def search_movies(query_str: str, sort_by: str = "date_asc", owned: str = None, limit: int = 150) -> list[dict]:
    """Recherche tous les films en base par titre, titre original ou réalisateur."""
    if not query_str or not query_str.strip():
        return []
    with get_connection() as conn:
        cursor = conn.cursor()
        q = f"%{query_str.strip()}%"
        sql = """
            SELECT * FROM movies 
            WHERE (title LIKE ? OR original_title LIKE ? OR director LIKE ?)
        """
        params = [q, q, q]

        if owned in ["1", "true", "owned"]:
            sql += " AND is_owned = 1"
        elif owned in ["0", "false", "not_owned"]:
            sql += " AND is_owned = 0"
        
        if sort_by == "date_asc":
            sql += " ORDER BY CASE WHEN release_date IS NULL OR release_date = '' THEN 1 ELSE 0 END, release_date ASC, title ASC"
        elif sort_by == "date_desc":
            sql += " ORDER BY release_date DESC, title ASC"
        elif sort_by == "rating_desc":
            sql += " ORDER BY user_rating DESC, release_date DESC"
        elif sort_by == "title_asc":
            sql += " ORDER BY title ASC"
        else:
            sql += " ORDER BY release_date ASC"
            
        sql += " LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

