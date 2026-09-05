import streamlit as st
import os
import importlib
from datetime import datetime, timedelta
import database as db
import tmdb_client as tmdb
import obsidian_export as obs
from rating_component import half_rating

# Rechargement automatique des modules
importlib.reload(db)
importlib.reload(tmdb)
importlib.reload(obs)

# Initialisation de la BDD
db.init_db()

# Configuration de la page
st.set_page_config(
    page_title="CinéTriage - Sorties France",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS : centrage vertical parfait de la croix, étoiles calées à droite, masquage header
st.markdown("""
<style>
    /* 1. Masquer totalement le bandeau d'outils Streamlit en haut */
    header[data-testid="stHeader"], [data-testid="stHeader"] {
        display: none !important;
    }
    .stAppDeployButton {
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }

    /* 2. Centrage vertical absolu de toutes les colonnes dans les lignes de films */
    div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }

    /* 3. Bouton croix (✕) miniature et centré */
    div.del-btn-box {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 100% !important;
    }
    div.del-btn-box button {
        background-color: transparent !important;
        color: #ef4444 !important;
        border: 1px solid #7f1d1d !important;
        border-radius: 4px !important;
        padding: 2px 6px !important;
        font-size: 0.85rem !important;
        font-weight: bold !important;
        min-height: 26px !important;
        height: 26px !important;
        line-height: 1 !important;
        margin: 0 !important;
    }
    div.del-btn-box button:hover {
        background-color: #ef4444 !important;
        color: white !important;
    }

    /* 4. Textes et badges */
    .movie-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #ffffff;
    }
    .movie-meta {
        font-size: 0.82rem;
        color: #a0aec0;
        margin-top: 2px;
        margin-bottom: 3px;
        line-height: 1.3;
    }
    .movie-synopsis {
        font-size: 0.82rem;
        color: #cbd5e0;
        line-height: 1.35;
        margin-top: 2px;
    }
    .badge-genre {
        display: inline-block;
        background-color: #2d3748;
        color: #e2e8f0;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 0.72rem;
        margin-right: 4px;
    }
    .badge-tmdb {
        background-color: #d97706;
        color: #000;
        font-weight: 700;
        padding: 1px 5px;
        border-radius: 4px;
        font-size: 0.72rem;
        margin-left: 6px;
    }
    .badge-rated {
        background-color: #10b981;
        color: #fff;
        font-weight: 700;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        margin-left: 6px;
    }

    /* Cartes pour les grilles Mois et Année */
    .mini-card {
        background-color: #1e222b;
        border-radius: 6px;
        padding: 8px;
        border: 1px solid #2d3342;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Clé API lue en silence depuis config.json
current_key = tmdb.load_api_key()

# -------------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------------
if "target_date" not in st.session_state:
    st.session_state["target_date"] = datetime.now().date()

with st.sidebar:
    st.title("🎬 CinéTriage")
    st.caption("Sorties cinéma France • 2000 à aujourd'hui")
    st.markdown("---")
    
    # 1. Total database et Vu au-dessus
    stats = db.get_stats()
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Total database", stats["total"])
    with col_s2:
        st.metric("Vus", stats["watched"])
        
    st.markdown("---")
    
    # 2. Boutons Précédent / Suivant juste au-dessus de l'échelle
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("◀ Précédent", use_container_width=True, key="side_prev"):
            cur_scale = st.session_state.get("view_scale", "Semaine")
            if cur_scale == "Semaine":
                st.session_state["target_date"] -= timedelta(days=7)
            elif cur_scale == "Mois":
                cur_y = st.session_state["target_date"].year
                cur_m = st.session_state["target_date"].month
                new_m = 12 if cur_m == 1 else cur_m - 1
                new_y = cur_y - 1 if cur_m == 1 else cur_y
                st.session_state["target_date"] = datetime(new_y, new_m, 1).date()
            elif cur_scale == "Année":
                st.session_state["target_date"] = datetime(st.session_state["target_date"].year - 1, 1, 1).date()
            st.rerun()
            
    with col_next:
        if st.button("Suivant ▶", use_container_width=True, key="side_next"):
            cur_scale = st.session_state.get("view_scale", "Semaine")
            if cur_scale == "Semaine":
                st.session_state["target_date"] += timedelta(days=7)
            elif cur_scale == "Mois":
                cur_y = st.session_state["target_date"].year
                cur_m = st.session_state["target_date"].month
                new_m = 1 if cur_m == 12 else cur_m + 1
                new_y = cur_y + 1 if cur_m == 12 else cur_y
                st.session_state["target_date"] = datetime(new_y, new_m, 1).date()
            elif cur_scale == "Année":
                st.session_state["target_date"] = datetime(st.session_state["target_date"].year + 1, 1, 1).date()
            st.rerun()

    # 3. Choix de l'échelle juste en dessous
    scale = st.radio("Échelle", ["Semaine", "Mois", "Année"], horizontal=True, key="view_scale")
    
    # 4. "Choisir date" (calendrier cliquable)
    picked_date = st.date_input(
        "Choisir date", 
        value=st.session_state["target_date"],
        min_value=datetime(1999, 1, 1).date(),
        max_value=datetime(2030, 12, 31).date(),
        key="calendar_picker"
    )
    if picked_date != st.session_state["target_date"]:
        st.session_state["target_date"] = picked_date
        st.rerun()

    st.markdown("---")
    
    # 5. Bouton unique "Synchroniser" intelligent
    current_year = datetime.now().year
    missing_years, year_counts = db.get_missing_years(2000, current_year)
    
    st.subheader("🔄 Synchronisation")
    if missing_years:
        st.caption(f"Années manquantes (2000–{current_year}) : {len(missing_years)}")
    else:
        st.caption(f"Base à jour (2000–{current_year}).")
        
    if st.button("🔄 Synchroniser", use_container_width=True, type="primary"):
        if not current_key:
            st.error("Renseignez la clé dans config.json.")
        else:
            prog_bar = st.progress(0, text="Vérification des sorties récentes...")
            try:
                def on_p_cur(c, t, cnt):
                    prog_bar.progress(int((c / t) * 30), text=f"Mise à jour {current_year} (page {c}/{t})...")
                cur_movies = tmdb.fetch_french_releases_for_year(current_year, current_key, progress_callback=on_p_cur)
                for m in cur_movies:
                    db.insert_or_update_movie(m)
                    
                if missing_years:
                    years_to_fetch = missing_years[:2]
                    for idx, y in enumerate(years_to_fetch):
                        def on_p(c, t, cnt):
                            base_prog = 30 + int((idx / len(years_to_fetch)) * 70)
                            prog_bar.progress(base_prog + int((c / t) * (70 // len(years_to_fetch))), text=f"Importation {y} ({cnt} films)...")
                        y_movies = tmdb.fetch_french_releases_for_year(y, current_key, progress_callback=on_p)
                        for m in y_movies:
                            db.insert_or_update_movie(m)
                            
                st.success("Synchronisation terminée !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

# -------------------------------------------------------------
# ONGLETS PRINCIPAUX
# -------------------------------------------------------------
tab_triage, tab_watchlist, tab_watched, tab_export = st.tabs([
    "🎬 Sorties Cinéma", 
    "🔥 Ma Sélection (À Voir)", 
    "⭐ Mes Films Vus & Tops",
    "📝 Export Obsidian"
])

target = st.session_state["target_date"]

# =============================================================
# ONGLET 1 : SORTIES CINÉMA (SEMAINE / MOIS / ANNÉE)
# =============================================================
with tab_triage:

    # ---------------------------------------------------------
    # CAS 1 : MODE SEMAINE
    # ---------------------------------------------------------
    if scale == "Semaine":
        offset = (target.weekday() - 2) % 7
        wednesday = target - timedelta(days=offset)
        tuesday = wednesday + timedelta(days=6)
        wed_str = wednesday.strftime("%Y-%m-%d")
        tue_str = tuesday.strftime("%Y-%m-%d")
        
        # BOUTONS SEMAINE PRÉCÉDENTE / SUIVANTE AU-DESSUS DU TITRE
        c_top1, c_top2 = st.columns(2)
        with c_top1:
            if st.button("◀ Semaine précédente", use_container_width=True, key="main_prev_w"):
                st.session_state["target_date"] -= timedelta(days=7)
                st.rerun()
        with c_top2:
            if st.button("Semaine suivante ▶", use_container_width=True, key="main_next_w"):
                st.session_state["target_date"] += timedelta(days=7)
                st.rerun()

        st.subheader(f"🗓️ Semaine du mercredi {wednesday.strftime('%d/%m/%Y')} au {tuesday.strftime('%d/%m/%Y')}")
        
        movies = db.get_movies_by_week(wed_str, include_dismissed=False)
        
        # Récupération automatique si vide
        if not movies and current_key:
            fetched = tmdb.fetch_movies_for_date_range(wed_str, tue_str, current_key)
            if fetched:
                for f_m in fetched:
                    db.insert_or_update_movie(f_m)
                movies = db.get_movies_by_week(wed_str, include_dismissed=False)
                
        # Enrichissement réalisateur et casting
        if current_key and movies:
            for m in movies:
                if not m.get("director") or m.get("director") == "Inconnu" or not m.get("cast"):
                    d, cast, rt = tmdb.fetch_movie_director_and_runtime(m["tmdb_id"], current_key)
                    if d and d != "Inconnu":
                        db.update_movie_credits_and_runtime(m["tmdb_id"], d, cast, rt)
                        m["director"] = d
                        m["cast"] = cast
                        m["runtime"] = rt
                        
        if not movies:
            st.info("Aucune sortie répertoriée pour cette semaine. Utilisez 'Synchroniser' dans la barre latérale.")
        else:
            st.caption(f"**{len(movies)}** film(s) sortis cette semaine :")
            
            for m in movies:
                with st.container(border=True):
                    # Colonnes : [Croix centrée, Affiche, Détails larges, Étoiles/Cœurs calés à droite]
                    c_del, c_img, c_info, c_act = st.columns([0.25, 0.75, 6.2, 1.8])
                    
                    # 1. Croix parfaitement centrée verticalement
                    with c_del:
                        st.markdown("<div class='del-btn-box'>", unsafe_allow_html=True)
                        if st.button("✕", key=f"del_w_{m['tmdb_id']}", help="Éliminer ce film"):
                            db.set_movie_status(m["tmdb_id"], "dismissed")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                    # 2. Affiche
                    with c_img:
                        if m["poster_url"]:
                            st.image(m["poster_url"], width=75)
                        else:
                            st.markdown("*(Sans affiche)*")
                            
                    # 3. Informations & Synopsis (largeur maximale, pas d'astérisques bruts)
                    with c_info:
                        titre_line = f"**{m['title']}**"
                        if m.get("runtime"):
                            titre_line += f" • {m['runtime']} min"
                        if m.get("vote_average") and m["vote_average"] > 0:
                            titre_line += f" <span class='badge-tmdb'>TMDb {m['vote_average']}</span>"
                        if m.get("is_watched"):
                            titre_line += f" <span class='badge-rated'>VU : {m['user_rating']:g}★</span>"
                        st.markdown(titre_line, unsafe_allow_html=True)
                        
                        meta_parts = []
                        if m.get("director") and m["director"] != "Inconnu":
                            meta_parts.append(f"👤 <b>De :</b> {m['director']}")
                        if m.get("cast"):
                            meta_parts.append(f"🎭 <b>Avec :</b> {m['cast']}")
                        if meta_parts:
                            st.markdown(f"<div class='movie-meta'>{' • '.join(meta_parts)}</div>", unsafe_allow_html=True)
                            
                        if m.get("genres"):
                            badges = "".join([f"<span class='badge-genre'>{g.strip()}</span>" for g in m["genres"].split(",")])
                            st.markdown(f"<div>{badges}</div>", unsafe_allow_html=True)
                            
                        synop = m.get("synopsis") or "Aucun synopsis disponible."
                        st.markdown(f"<div class='movie-synopsis'>{synop}</div>", unsafe_allow_html=True)
                        
                    # 4. Étoiles et Cœurs calés tout à droite sans texte
                    with c_act:
                        new_r = half_rating(
                            value=float(m.get("user_rating") or 0.0), 
                            mode="star", 
                            key=f"star_w_{m['tmdb_id']}"
                        )
                        if new_r != float(m.get("user_rating") or 0.0):
                            db.set_movie_rating(m["tmdb_id"], new_r)
                            st.rerun()
                            
                        new_w = half_rating(
                            value=float(m.get("want_rating") or 0.0), 
                            mode="heart", 
                            key=f"heart_w_{m['tmdb_id']}"
                        )
                        if new_w != float(m.get("want_rating") or 0.0):
                            db.set_movie_want(m["tmdb_id"], new_w)
                            st.rerun()

    # ---------------------------------------------------------
    # CAS 2 : MODE MOIS (CARRÉ ENGLOBANT PAR SEMAINE + GRILLE)
    # ---------------------------------------------------------
    elif scale == "Mois":
        m_names = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        m_name = m_names[target.month - 1]
        
        # Boutons navigation mois au-dessus
        c_top1, c_top2 = st.columns(2)
        with c_top1:
            if st.button("◀ Mois précédent", use_container_width=True, key="main_prev_m"):
                cur_y = target.year
                cur_m = target.month
                new_m = 12 if cur_m == 1 else cur_m - 1
                new_y = cur_y - 1 if cur_m == 1 else cur_y
                st.session_state["target_date"] = datetime(new_y, new_m, 1).date()
                st.rerun()
        with c_top2:
            if st.button("Mois suivant ▶", use_container_width=True, key="main_next_m"):
                cur_y = target.year
                cur_m = target.month
                new_m = 1 if cur_m == 12 else cur_m + 1
                new_y = cur_y + 1 if cur_m == 12 else cur_y
                st.session_state["target_date"] = datetime(new_y, new_m, 1).date()
                st.rerun()

        st.subheader(f"📅 Sorties de {m_name} {target.year}")
        all_month_movies = db.get_movies_by_month(target.year, target.month)
        
        if not all_month_movies:
            st.info(f"Aucune sortie en base pour {m_name} {target.year}. Utilisez 'Synchroniser' dans la barre latérale.")
        else:
            # Grouper par semaine (mercredi)
            weeks_dict = {}
            for m in all_month_movies:
                w_date = m.get("week_start_date") or m.get("release_date")
                if w_date not in weeks_dict:
                    weeks_dict[w_date] = []
                weeks_dict[w_date].append(m)
                
            sorted_weeks = sorted(weeks_dict.keys())
            
            # UN GRAND CARRÉ PAR SEMAINE DU MOIS
            for w_idx, w_key in enumerate(sorted_weeks, 1):
                week_movies = weeks_dict[w_key]
                try:
                    dt_w = datetime.strptime(w_key, "%Y-%m-%d")
                    label_w = f"Semaine {w_idx} : Mercredi {dt_w.strftime('%d/%m/%Y')}"
                except Exception:
                    label_w = f"Semaine {w_idx} ({w_key})"
                    
                with st.container(border=True):
                    st.markdown(f"### 🗓️ {label_w} — {len(week_movies)} sortie(s)")
                    
                    # Grille interne de 4 colonnes de cartes compactes
                    grid_cols = st.columns(4)
                    for idx, m in enumerate(week_movies):
                        col_target = grid_cols[idx % 4]
                        with col_target:
                            with st.container(border=True):
                                # Ligne tête : date + bouton ✕
                                c_m1, c_m2 = st.columns([3.5, 1])
                                with c_m1:
                                    st.caption(f"📅 {m['release_date']}")
                                with c_m2:
                                    st.markdown("<div class='del-btn-box'>", unsafe_allow_html=True)
                                    if st.button("✕", key=f"del_m_{m['tmdb_id']}", help="Éliminer"):
                                        db.set_movie_status(m["tmdb_id"], "dismissed")
                                        st.rerun()
                                    st.markdown("</div>", unsafe_allow_html=True)
                                    
                                if m["poster_url"]:
                                    st.image(m["poster_url"], width=85)
                                    
                                st.markdown(f"**{m['title']}**")
                                if m.get("genres"):
                                    st.caption(f"{m['genres'][:30]}...")
                                    
                                # Étoiles & Cœurs compacts
                                new_r = half_rating(
                                    value=float(m.get("user_rating") or 0.0), 
                                    mode="star", 
                                    key=f"star_m_{m['tmdb_id']}"
                                )
                                if new_r != float(m.get("user_rating") or 0.0):
                                    db.set_movie_rating(m["tmdb_id"], new_r)
                                    st.rerun()
                                    
                                new_w = half_rating(
                                    value=float(m.get("want_rating") or 0.0), 
                                    mode="heart", 
                                    key=f"heart_m_{m['tmdb_id']}"
                                )
                                if new_w != float(m.get("want_rating") or 0.0):
                                    db.set_movie_want(m["tmdb_id"], new_w)
                                    st.rerun()

    # ---------------------------------------------------------
    # CAS 3 : MODE ANNÉE (GRILLE DE PETITS RECTANGLES : 5 PAR LIGNE)
    # ---------------------------------------------------------
    elif scale == "Année":
        # Boutons navigation année au-dessus
        c_top1, c_top2 = st.columns(2)
        with c_top1:
            if st.button("◀ Année précédente", use_container_width=True, key="main_prev_y"):
                st.session_state["target_date"] = datetime(target.year - 1, 1, 1).date()
                st.rerun()
        with c_top2:
            if st.button("Année suivante ▶", use_container_width=True, key="main_next_y"):
                st.session_state["target_date"] = datetime(target.year + 1, 1, 1).date()
                st.rerun()

        st.subheader(f"📆 Année {target.year} — Grille complète des sorties")
        movies = db.get_movies_by_year(target.year)
        
        if not movies:
            st.info(f"Aucune sortie en base pour {target.year}. Utilisez 'Synchroniser' dans la barre latérale.")
        else:
            st.caption(f"**{len(movies)}** films pour {target.year} :")
            
            # GRILLE EN 5 COLONNES (PETITS RECTANGLES COMPACTS)
            cols = st.columns(5)
            for idx, m in enumerate(movies):
                target_col = cols[idx % 5]
                with target_col:
                    with st.container(border=True):
                        # Ligne du haut : date + bouton ✕
                        c_card_head1, c_card_head2 = st.columns([3.5, 1])
                        with c_card_head1:
                            st.caption(f"📅 {m['release_date']}")
                        with c_card_head2:
                            st.markdown("<div class='del-btn-box'>", unsafe_allow_html=True)
                            if st.button("✕", key=f"del_y_{m['tmdb_id']}", help="Éliminer"):
                                db.set_movie_status(m["tmdb_id"], "dismissed")
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)
                                
                        # Titre
                        st.markdown(f"**{m['title']}**")
                        
                        # Notations compactes en dessous
                        new_r = half_rating(
                            value=float(m.get("user_rating") or 0.0), 
                            mode="star", 
                            key=f"star_y_{m['tmdb_id']}"
                        )
                        if new_r != float(m.get("user_rating") or 0.0):
                            db.set_movie_rating(m["tmdb_id"], new_r)
                            st.rerun()
                            
                        new_w = half_rating(
                            value=float(m.get("want_rating") or 0.0), 
                            mode="heart", 
                            key=f"heart_y_{m['tmdb_id']}"
                        )
                        if new_w != float(m.get("want_rating") or 0.0):
                            db.set_movie_want(m["tmdb_id"], new_w)
                            st.rerun()

# =============================================================
# ONGLET 2 : MA WATCHLIST (À VOIR EN PRIORITÉ)
# =============================================================
with tab_watchlist:
    st.subheader("🎯 Ma Sélection de Films à Voir")
    st.caption("Films conservés non vus, classés par recommandation d'envie.")
    
    c_flt1, c_flt2, c_flt3 = st.columns([1.5, 1.5, 2])
    with c_flt1:
        genres = ["Tous"] + db.get_all_genres()
        wl_genre = st.selectbox("Genre", genres, key="wl_genre_box")
    with c_flt2:
        wl_prio = st.slider("Recommandation minimum (❤️)", min_value=1.0, max_value=5.0, value=1.0, step=0.5, key="wl_prio_s")
    with c_flt3:
        wl_search = st.text_input("🔍 Rechercher titre ou réalisateur", key="wl_search_box")
        
    watchlist = db.get_watchlist(genre=wl_genre, min_want=wl_prio, search=wl_search)
    
    if not watchlist:
        st.info("Aucun film dans votre sélection avec ces filtres.")
    else:
        st.markdown(f"**{len(watchlist)}** film(s) à voir en réserve :")
        for m in watchlist:
            with st.container(border=True):
                c_del, c_img, c_info, c_act = st.columns([0.25, 0.75, 6.2, 1.8])
                with c_del:
                    st.markdown("<div class='del-btn-box'>", unsafe_allow_html=True)
                    if st.button("✕", key=f"del_wl_{m['tmdb_id']}", help="Retirer de la sélection"):
                        db.set_movie_status(m["tmdb_id"], "dismissed")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_img:
                    if m["poster_url"]:
                        st.image(m["poster_url"], width=75)
                with c_info:
                    st.markdown(f"**{m['title']}** ({m['year']}) • 📅 Sortie : {m['release_date']}")
                    st.markdown(f"<div class='movie-meta'>👤 <b>De :</b> {m.get('director') or 'Inconnu'} • 🎭 <b>Avec :</b> {m.get('cast', '')}</div>", unsafe_allow_html=True)
                    synop = m.get("synopsis") or ""
                    st.markdown(f"<div class='movie-synopsis'>{synop}</div>", unsafe_allow_html=True)
                with c_act:
                    new_r = half_rating(
                        value=float(m.get("user_rating") or 0.0), 
                        mode="star", 
                        key=f"star_wl_{m['tmdb_id']}"
                    )
                    if new_r > 0 and new_r != float(m.get("user_rating") or 0.0):
                        db.set_movie_rating(m["tmdb_id"], new_r)
                        st.rerun()
                    new_w = half_rating(
                        value=float(m.get("want_rating") or 0.0), 
                        mode="heart", 
                        key=f"heart_wl_{m['tmdb_id']}"
                    )
                    if new_w != float(m.get("want_rating") or 0.0):
                        db.set_movie_want(m["tmdb_id"], new_w)
                        st.rerun()

# =============================================================
# ONGLET 3 : MES FILMS VUS & TOPS
# =============================================================
with tab_watched:
    st.subheader("⭐ Mes Bilan & Classement des Meilleurs Films")
    
    col_t1, col_t2, col_t3 = st.columns([1.5, 1.5, 2])
    with col_t1:
        years_opt = ["Toutes"] + [str(y) for y in db.get_available_years()]
        top_year = st.selectbox("Année", years_opt, key="top_y_filter")
        year_filter = int(top_year) if top_year != "Toutes" else None
    with col_t2:
        top_genre = st.selectbox("Genre", ["Tous"] + db.get_all_genres(), key="top_g_filter")
    with col_t3:
        sort_mode = st.selectbox("Trier par", [
            ("Meilleures notes d'abord (⭐)", "rating_desc"),
            ("Date de sortie la plus récente", "date_desc"),
            ("Titre (A-Z)", "title_asc")
        ], format_func=lambda x: x[0], key="top_s_filter")[1]
        
    watched_list = db.get_watched_movies(year=year_filter, genre=top_genre, sort_by=sort_mode)
    
    if not watched_list:
        st.info("Aucun film noté pour le moment.")
    else:
        st.markdown(f"**{len(watched_list)}** film(s) vu(s) et noté(s) :")
        for rank, m in enumerate(watched_list, 1):
            with st.container(border=True):
                c_del, c_img, c_info, c_act = st.columns([0.25, 0.75, 6.2, 1.8])
                with c_del:
                    st.markdown("<div class='del-btn-box'>", unsafe_allow_html=True)
                    if st.button("✕", key=f"del_top_{m['tmdb_id']}", help="Retirer"):
                        db.set_movie_status(m["tmdb_id"], "dismissed")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                with c_img:
                    if m["poster_url"]:
                        st.image(m["poster_url"], width=75)
                with c_info:
                    st.markdown(f"#### #{rank} — {m['title']} ({m['year']})")
                    st.markdown(f"<div class='movie-meta'>👤 <b>De :</b> {m.get('director')} • 📅 {m['release_date']} • 🏷️ {m['genres']}</div>", unsafe_allow_html=True)
                    synop = m.get("synopsis") or ""
                    st.markdown(f"<div class='movie-synopsis'>{synop}</div>", unsafe_allow_html=True)
                with c_act:
                    new_r = half_rating(
                        value=float(m.get("user_rating") or 3.0), 
                        mode="star", 
                        key=f"star_top_{m['tmdb_id']}"
                    )
                    if new_r != float(m.get("user_rating") or 3.0):
                        db.set_movie_rating(m["tmdb_id"], new_r)
                        st.rerun()

# =============================================================
# ONGLET 4 : EXPORT OBSIDIAN
# =============================================================
with tab_export:
    st.subheader("📝 Export vers Obsidian")
    st.caption("Générez des fiches Markdown avec métadonnées YAML prêtes pour votre coffre.")
    
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mes_fiches_obsidian")
    target_dir = st.text_input("Dossier de destination", value=default_dir)
    
    export_choice = st.radio("Sélection à exporter", [
        "Uniquement les films retenus et vus (Ma sélection propre)",
        "Uniquement les films vus avec mes notes",
        "Tous les films non éliminés"
    ])
    
    if st.button("🚀 Exporter vers Obsidian", type="primary"):
        if "Uniquement les films vus" in export_choice:
            movies_to_exp = db.get_watched_movies()
        elif "Uniquement les films retenus" in export_choice:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM movies WHERE status = 'kept' OR is_watched = 1")
                movies_to_exp = [dict(row) for row in cur.fetchall()]
        else:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM movies WHERE status != 'dismissed'")
                movies_to_exp = [dict(row) for row in cur.fetchall()]
                
        if not movies_to_exp:
            st.warning("Aucun film à exporter pour ce critère.")
        else:
            count = obs.export_all_movies(movies_to_exp, target_dir)
            st.success(f"✅ {count} fiches Markdown créées avec succès dans : {target_dir}")
