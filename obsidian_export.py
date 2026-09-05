import os
import re

def sanitize_filename(name: str) -> str:
    """Nettoie le titre pour créer un nom de fichier valide Windows/Obsidian."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip().replace("  ", " ")
    return clean[:100]

def export_movie_to_markdown(movie: dict, output_dir: str) -> str:
    """Exporte un film au format Markdown avec métadonnées YAML."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{sanitize_filename(movie['title'])} ({movie['year']}).md"
    filepath = os.path.join(output_dir, filename)
    
    genres_list = [g.strip() for g in (movie.get("genres") or "").split(",") if g.strip()]
    genres_yaml = ", ".join([f'"{g}"' for g in genres_list])
    
    vu_checkbox = "[x]" if movie.get("is_watched") else "[ ]"
    note_str = f"{movie.get('user_rating', 0.0)} / 5 ⭐" if movie.get("is_watched") else "Non noté"
    envie_str = f"{movie.get('want_rating', 0)} / 5 🔥"
    
    content = f"""---
titre: "{movie.get('title', '')}"
titre_original: "{movie.get('original_title', '')}"
annee: {movie.get('year', 0)}
date_sortie_fr: {movie.get('release_date', '')}
mercredi_sortie: {movie.get('week_start_date', '')}
realisateur: "{movie.get('director', '')}"
acteurs: "{movie.get('cast', '')}"
genres: [{genres_yaml}]
duree_minutes: {movie.get('runtime', 0)}
note_tmdb: {movie.get('vote_average', 0.0)}
statut: "{movie.get('status', 'kept')}"
vu: {'true' if movie.get('is_watched') else 'false'}
note_perso: {movie.get('user_rating', 0.0)}
envie_priorite: {movie.get('want_rating', 0)}
affiche: "{movie.get('poster_url', '')}"
---

![affiche|220]({movie.get('poster_url', '')})

# {movie.get('title', '')}

- **Sortie en France :** {movie.get('release_date', 'Inconnue')}
- **Réalisateur :** {movie.get('director', 'Inconnu')}
- **Acteurs :** {movie.get('cast', 'N/A')}
- **Genres :** {movie.get('genres', 'N/A')}
- **Durée :** {movie.get('runtime', 'N/A')} min
- **Suivi :** {vu_checkbox} Vu | **Note :** {note_str} | **Envie :** {envie_str}

### Synopsis
{movie.get('synopsis', 'Aucun synopsis disponible.')}

### Mes notes
{movie.get('notes', '')}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
        
    return filepath

def export_all_movies(movies: list, target_directory: str):
    """Exporte une liste de films et génère une note d'index Dataview pour Obsidian."""
    count = 0
    for m in movies:
        export_movie_to_markdown(m, target_directory)
        count += 1
        
    # Fiche Index avec requête Dataview
    index_path = os.path.join(target_directory, "00_Index_Films.md")
    index_content = """# Mon Bilan & Catalogue Cinéma

Ce dossier contient vos fiches de films générées automatiquement.

### Vos Meilleurs Films (Requête Dataview)
Si vous avez le plugin **Dataview** installé dans Obsidian, collez ce bloc :

```dataview
TABLE date_sortie_fr as "Sortie", realisateur as "Réalisateur", note_perso as "Ma Note", genres as "Genres"
FROM ""
WHERE vu = true
SORT note_perso DESC
```

### Films à Voir en Priorité (Watchlist)
```dataview
TABLE date_sortie_fr as "Sortie", realisateur as "Réalisateur", envie_priorite as "Envie", genres as "Genres"
FROM ""
WHERE vu = false AND statut = "kept"
SORT envie_priorite DESC
```
"""
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)
        
    return count
