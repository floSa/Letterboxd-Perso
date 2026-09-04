import database as db
import tmdb_client as tmdb
import obsidian_export as obs
import os
import shutil

def run_tests():
    print("--- 1. Initialisation de la BDD ---")
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    db.init_db()
    
    print("--- 2. Insertion des films démo ---")
    demo_movies = tmdb.get_demo_movies()
    for m in demo_movies:
        db.insert_or_update_movie(m)
        
    stats = db.get_stats()
    print(f"Films en base : {stats['total']}")
    assert stats['total'] >= 10, "Moins de 10 films trouvés"
    
    print("--- 3. Test de triage & statuts ---")
    # Prendre le premier film (ex: Mickey 17 ou Dune)
    m1 = demo_movies[0]
    tmdb_id = m1["tmdb_id"]
    
    # 3.1 Test suppression/élimination
    db.set_movie_status(tmdb_id, "dismissed")
    m_list = db.get_movies_by_week(m1["week_start_date"], include_dismissed=False)
    assert not any(x["tmdb_id"] == tmdb_id for x in m_list), "Le film éliminé ne devrait pas apparaître sans include_dismissed"
    
    # 3.2 Test restauration
    db.set_movie_status(tmdb_id, "pending")
    m_list = db.get_movies_by_week(m1["week_start_date"], include_dismissed=False)
    assert any(x["tmdb_id"] == tmdb_id for x in m_list), "Le film devrait réapparaître"
    
    # 3.3 Test Envie / Priorité
    db.set_movie_want(tmdb_id, 4)
    wl = db.get_watchlist(min_want=1)
    assert any(x["tmdb_id"] == tmdb_id for x in wl), "Le film devrait être dans la watchlist"
    
    # 3.4 Test Vu + Demi-étoile (ex: 4.5 / 5)
    db.set_movie_watched(tmdb_id, True, user_rating=4.5)
    watched = db.get_watched_movies()
    found = next((x for x in watched if x["tmdb_id"] == tmdb_id), None)
    assert found is not None, "Film non trouvé dans les vus"
    assert found["user_rating"] == 4.5, f"Note attendue 4.5, obtenu {found['user_rating']}"
    print(f"Film vu et note avec succes : {found['title']} -> {found['user_rating']} / 5")
    
    print("--- 4. Test d'export Obsidian ---")
    test_export_dir = os.path.join(os.path.dirname(__file__), "test_obsidian_export")
    if os.path.exists(test_export_dir):
        shutil.rmtree(test_export_dir)
        
    count = obs.export_all_movies(watched, test_export_dir)
    print(f"Fiches exportees : {count}")
    assert count > 0, "Aucune fiche exportee"
    assert os.path.exists(os.path.join(test_export_dir, "00_Index_Films.md")), "Index manquant"
    
    # Verifier le contenu d'un markdown
    files = [f for f in os.listdir(test_export_dir) if f.endswith(".md") and not f.startswith("00_")]
    with open(os.path.join(test_export_dir, files[0]), "r", encoding="utf-8") as f:
        md_text = f.read()
        assert "---" in md_text and "titre:" in md_text, "YAML Frontmatter absent"
        assert "4.5" in md_text, "Note 4.5 absente du markdown"
        
    shutil.rmtree(test_export_dir)
    print("[SUCCES] TOUS LES TESTS SONT PASSES AVEC SUCCES !")

if __name__ == "__main__":
    run_tests()
