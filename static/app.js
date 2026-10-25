// ========================================================
// CINETRIAGE • FRONTEND JAVASCRIPT ULTRA-RÉACTIF (0 MS)
// ========================================================

const state = {
  activeTab: "triage",
  scale: "week",          // "week" | "month" | "year"
  targetDate: new Date(), // Date courante
  yearPage: 1,
  cinemaOnly: true,       // Masquer les courts-métrages < 50 min, sans affiche et bruit
  hideReprises: localStorage.getItem("cinetrack_hide_reprises") === "true", // Masquer ou afficher en bas les reprises
  sortBy: "tmdb_desc",    // "tmdb_desc" | "date_desc" | "title_asc"
  genres: [],
  lastDismissedId: null
};

// --- INITIALISATION ---
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadStats();
  loadGenres();
  renderCurrentView();
  startSyncPolling();
});

// --- GESTION DES ÉVÉNEMENTS GLOBAUX ---
function initEventListeners() {
  // 1. Navigation par onglets principaux
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const tabId = tab.getAttribute("data-tab");
      state.activeTab = tabId;

      document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.add("hidden"));
      const targetPane = document.getElementById(`tab-content-${tabId}`);
      if (targetPane) targetPane.classList.remove("hidden");

      if (tabId === "watchlist") loadWatchlist();
      else if (tabId === "watched") loadWatched();
    });
  });

  // 2. Sélecteur d'échelle (Semaine / Mois / Année)
  document.querySelectorAll(".scale-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".scale-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.scale = btn.getAttribute("data-scale");
      state.yearPage = 1;
      renderCurrentView();
    });
  });

  // 3. Boutons de navigation période (Précédent / Suivant)
  document.getElementById("btn-nav-prev").addEventListener("click", () => navigatePeriod(-1));
  document.getElementById("btn-nav-next").addEventListener("click", () => navigatePeriod(1));

  // 4. Bouton Aujourd'hui
  document.getElementById("btn-today").addEventListener("click", () => {
    state.targetDate = new Date();
    updateDateInput();
    renderCurrentView();
  });

  // 5. Calendrier sélecteur de date
  const dateInput = document.getElementById("nav-date-input");
  updateDateInput();
  dateInput.addEventListener("change", (e) => {
    if (e.target.value) {
      state.targetDate = new Date(e.target.value);
      renderCurrentView();
    }
  });

  // 6. Pagination Année
  document.getElementById("btn-page-prev").addEventListener("click", () => {
    if (state.yearPage > 1) {
      state.yearPage--;
      renderCurrentView();
    }
  });
  document.getElementById("btn-page-next").addEventListener("click", () => {
    state.yearPage++;
    renderCurrentView();
  });

  // 7. Bouton Synchroniser TMDb
  document.getElementById("btn-sync").addEventListener("click", triggerSync);

  // 8. Filtres Watchlist
  document.getElementById("wl-genre-filter").addEventListener("change", loadWatchlist);
  document.getElementById("wl-min-want").addEventListener("change", loadWatchlist);
  document.getElementById("wl-search").addEventListener("input", debounce(loadWatchlist, 300));

  // 9. Filtres Vus
  document.getElementById("watched-sort").addEventListener("change", loadWatched);
  document.getElementById("watched-year").addEventListener("input", debounce(loadWatched, 300));
  document.getElementById("watched-genre").addEventListener("change", loadWatched);

  // 10. Boutons Obsidian
  document.getElementById("btn-export-all").addEventListener("click", () => exportObsidian("all"));
  document.getElementById("btn-export-watchlist").addEventListener("click", () => exportObsidian("watchlist"));
  document.getElementById("btn-export-watched").addEventListener("click", () => exportObsidian("watched"));

  // 11. Toast Annuler
  document.getElementById("toast-undo").addEventListener("click", undoLastDismiss);

  // 12. Filtre Longs-métrages cinéma uniquement
  const btnCinema = document.getElementById("btn-toggle-cinema");
  if (btnCinema) {
    btnCinema.addEventListener("click", () => {
      state.cinemaOnly = !state.cinemaOnly;
      btnCinema.classList.toggle("active", state.cinemaOnly);
      viewCache.clear();
      renderCurrentView();
    });
  }

  // 12 bis. Filtre Masquer les reprises
  const btnReprises = document.getElementById("btn-toggle-reprises");
  if (btnReprises) {
    btnReprises.classList.toggle("active", state.hideReprises);
    btnReprises.addEventListener("click", () => {
      state.hideReprises = !state.hideReprises;
      localStorage.setItem("cinetrack_hide_reprises", state.hideReprises ? "true" : "false");
      btnReprises.classList.toggle("active", state.hideReprises);
      viewCache.clear();
      renderCurrentView();
    });
  }

  // 13. Tri personnalisé (par note TMDb par défaut)
  const sortSelect = document.getElementById("triage-sort");
  if (sortSelect) {
    sortSelect.value = state.sortBy;
    sortSelect.addEventListener("change", (e) => {
      state.sortBy = e.target.value;
      viewCache.clear();
      renderCurrentView();
    });
  }

  // 14. Bouton éliminer le bruit (nettoyage en masse)
  const btnClean = document.getElementById("btn-clean-noise");
  if (btnClean) {
    btnClean.addEventListener("click", cleanCurrentNoise);
  }
}

function formatDateISO(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function updateDateInput() {
  const dateInput = document.getElementById("nav-date-input");
  dateInput.value = formatDateISO(state.targetDate);
}

function navigatePeriod(direction) {
  const d = new Date(state.targetDate);
  if (state.scale === "week") {
    d.setDate(d.getDate() + (direction * 7));
  } else if (state.scale === "month") {
    d.setMonth(d.getMonth() + direction);
  } else if (state.scale === "year") {
    d.setFullYear(d.getFullYear() + direction);
    state.yearPage = 1;
  }
  state.targetDate = d;
  updateDateInput();
  renderCurrentView();
}

// --- STATISTIQUES & GENRES ---
async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    document.getElementById("stat-total").textContent = data.total.toLocaleString("fr-FR");
    document.getElementById("stat-watched").textContent = data.watched.toLocaleString("fr-FR");
    document.getElementById("badge-watched").textContent = data.watched;
  } catch (e) {
    console.error("Erreur stats :", e);
  }
}

async function loadGenres() {
  try {
    const res = await fetch("/api/genres");
    const data = await res.json();
    state.genres = data.genres || [];

    const wlSel = document.getElementById("wl-genre-filter");
    const watchedSel = document.getElementById("watched-genre");

    wlSel.innerHTML = '<option value="Tous">Tous</option>';
    watchedSel.innerHTML = '<option value="Tous">Tous</option>';

    state.genres.forEach(g => {
      const opt1 = document.createElement("option");
      opt1.value = g; opt1.textContent = g;
      wlSel.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = g; opt2.textContent = g;
      watchedSel.appendChild(opt2);
    });
  } catch (e) {
    console.error("Erreur genres :", e);
  }
}

// --- CACHE EN MÉMOIRE & PRÉCHARGEMENT INSTANTANÉ (0 MS) ---
const viewCache = new Map();

function getCacheKey(scale, targetDate, page) {
  return `${scale}_${formatDateISO(targetDate)}_${page || 1}_${state.cinemaOnly}_${state.sortBy}_${state.hideReprises}`;
}

async function fetchViewData(scale, targetDate, page) {
  const key = getCacheKey(scale, targetDate, page);
  if (viewCache.has(key)) {
    return viewCache.get(key);
  }

  const dateStr = formatDateISO(targetDate);
  const year = targetDate.getFullYear();
  const month = targetDate.getMonth() + 1;
  const url = `/api/movies?scale=${scale}&date=${dateStr}&year=${year}&month=${month}&page=${page || 1}&cinema_only=${state.cinemaOnly}&sort=${state.sortBy}&hide_reprises=${state.hideReprises ? 1 : 0}`;

  const res = await fetch(url);
  const data = await res.json();
  viewCache.set(key, data);
  return data;
}

// Préchargement en arrière-plan des périodes précédente et suivante
function prefetchNeighbors() {
  if (state.scale === "week") {
    const dPrev = new Date(state.targetDate);
    dPrev.setDate(dPrev.getDate() - 7);
    fetchViewData("week", dPrev, 1).catch(() => {});

    const dNext = new Date(state.targetDate);
    dNext.setDate(dNext.getDate() + 7);
    fetchViewData("week", dNext, 1).catch(() => {});
  } else if (state.scale === "month") {
    const dPrev = new Date(state.targetDate);
    dPrev.setMonth(dPrev.getMonth() - 1);
    fetchViewData("month", dPrev, 1).catch(() => {});

    const dNext = new Date(state.targetDate);
    dNext.setMonth(dNext.getMonth() + 1);
    fetchViewData("month", dNext, 1).catch(() => {});
  }
}

// --- RENDU PRINCIPAL DU TRIAGE ---
async function renderCurrentView() {
  const container = document.getElementById("movies-container");
  const periodTitle = document.getElementById("period-title");
  const countBar = document.getElementById("period-movie-count");
  const yearPag = document.getElementById("year-pagination");

  const key = getCacheKey(state.scale, state.targetDate, state.yearPage);

  // Si pas encore en cache, afficher un message d'attente bref
  if (!viewCache.has(key)) {
    container.innerHTML = '<div style="text-align:center; padding: 40px; color: #64748b;">Chargement instantané...</div>';
  }

  try {
    const data = await fetchViewData(state.scale, state.targetDate, state.yearPage);

    periodTitle.textContent = data.title;

    if (state.scale === "week") {
      yearPag.classList.add("hidden");
      renderWeekView(data.movies, container, countBar);
    } else if (state.scale === "month") {
      yearPag.classList.add("hidden");
      renderMonthView(data.weeks, container, countBar);
    } else if (state.scale === "year") {
      yearPag.classList.remove("hidden");
      renderYearView(data, container, countBar);
    }

    // Précharger immédiatement les semaines/mois voisins en arrière-plan
    prefetchNeighbors();

  } catch (e) {
    container.innerHTML = `<div style="color: #ef4444; padding: 20px;">Erreur de chargement : ${e.message}</div>`;
  }
}

// 1. VUE SEMAINE : RANGÉES HORIZONTALES (CENTRAGE CROIX PARFAIT, ÉTOILES CALÉES À DROITE, LIENS TMDB)
function renderWeekView(movies, container, countBar) {
  if (!movies || movies.length === 0) {
    countBar.textContent = "0 film répertorié cette semaine";
    container.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8;">Aucune sortie répertoriée pour cette semaine. Utilisez le bouton "Synchroniser" en haut à droite.</div>';
    return;
  }

  countBar.textContent = `${movies.length} film(s) sorti(s) cette semaine :`;
  const list = document.createElement("div");
  list.className = "movies-list-week";

  movies.forEach(m => {
    const row = document.createElement("div");
    row.className = "movie-row";
    row.id = `movie-row-${m.tmdb_id}`;

    // Colonne 1 : Croix parfaitement centrée verticalement
    const colDel = document.createElement("div");
    colDel.className = "col-del";
    const btnDel = document.createElement("button");
    btnDel.className = "btn-dismiss";
    btnDel.innerHTML = "✕";
    btnDel.title = "Éliminer ce film";
    btnDel.onclick = () => dismissMovie(m.tmdb_id, row);
    colDel.appendChild(btnDel);

    // Colonne 2 : Affiche (agrandie x1.5 et cliquable vers TMDb)
    const colPoster = document.createElement("div");
    colPoster.className = "col-poster";
    if (m.poster_url) {
      colPoster.innerHTML = `
        <a href="https://www.themoviedb.org/movie/${m.tmdb_id}" target="_blank" rel="noopener noreferrer" class="poster-link" title="Ouvrir la fiche TMDb de ${escapeHtml(m.title)} (nouvel onglet)">
          <img src="${m.poster_url}" class="poster-img" alt="${escapeHtml(m.title)}" loading="lazy">
        </a>`;
    } else {
      colPoster.innerHTML = `
        <a href="https://www.themoviedb.org/movie/${m.tmdb_id}" target="_blank" rel="noopener noreferrer" class="poster-link">
          <div class="poster-placeholder">Sans affiche</div>
        </a>`;
    }

    // Colonne 3 : Informations centrales
    const colInfo = document.createElement("div");
    colInfo.className = "col-info";

    let badgesHtml = "";
    if (m.is_reprise) {
      const origYr = m.original_year || (m.original_release_date ? m.original_release_date.substring(0, 4) : "");
      badgesHtml += `<span class="badge-reprise" title="Film de reprise / patrimoine (sortie originelle : ${origYr || 'antérieure'})">🔄 Reprise ${origYr ? `(${origYr})` : ''}</span>`;
    }
    if (m.runtime) badgesHtml += `<span class="movie-runtime">${m.runtime} min</span>`;
    if (m.vote_average > 0) {
      badgesHtml += `<span class="badge-tmdb" title="Note moyenne de la communauté The Movie Database : ${m.vote_average} sur 10">★ TMDb ${m.vote_average}/10</span>`;
    }
    if (m.is_watched) badgesHtml += `<span class="badge-watched" id="badge-vu-${m.tmdb_id}">VU : ${m.user_rating}★</span>`;

    let creditsParts = [];
    if (m.director && m.director !== "Inconnu") creditsParts.push(`👤 <b>De :</b> ${escapeHtml(m.director)}`);
    if (m.cast) creditsParts.push(`🎭 <b>Avec :</b> ${escapeHtml(m.cast)}`);

    let genresHtml = "";
    if (m.genres) {
      genresHtml = m.genres.split(",").map(g => `<span class="genre-pill">${escapeHtml(g.trim())}</span>`).join("");
    }

    const synopsisText = m.synopsis || "Aucun synopsis disponible.";

    colInfo.innerHTML = `
      <div class="movie-headline">
        <a href="https://www.themoviedb.org/movie/${m.tmdb_id}" target="_blank" rel="noopener noreferrer" class="movie-link" title="Ouvrir la fiche sur TMDb (nouvel onglet)">
          <span class="movie-title">${escapeHtml(m.title)}</span>
        </a>
        ${badgesHtml}
      </div>
      ${creditsParts.length ? `<div class="movie-credits">${creditsParts.join(" • ")}</div>` : ""}
      ${genresHtml ? `<div class="movie-genres">${genresHtml}</div>` : ""}
      <div class="movie-synopsis">${escapeHtml(synopsisText)}</div>
    `;

    // Colonne 4 : Actions calées tout à droite (Étoiles et Cœurs)
    const colActions = document.createElement("div");
    colActions.className = "col-actions";

    const starWidget = createRatingWidget(m.tmdb_id, m.user_rating || 0.0, "star");
    const heartWidget = createRatingWidget(m.tmdb_id, m.want_rating || 0.0, "heart");

    colActions.appendChild(starWidget);
    colActions.appendChild(heartWidget);

    row.appendChild(colDel);
    row.appendChild(colPoster);
    row.appendChild(colInfo);
    row.appendChild(colActions);

    list.appendChild(row);
  });

  container.innerHTML = "";
  container.appendChild(list);
}

// 2. VUE MOIS : CARRÉS ENGLOBANTS PAR SEMAINE AVEC LISERÉ FIN ET GRILLE
function renderMonthView(weeks, container, countBar) {
  if (!weeks || weeks.length === 0) {
    countBar.textContent = "0 film pour ce mois";
    container.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8;">Aucune sortie en base pour ce mois. Utilisez "Synchroniser".</div>';
    return;
  }

  let totalM = weeks.reduce((sum, w) => sum + w.movie_count, 0);
  countBar.textContent = `${totalM} film(s) réparti(s) sur ${weeks.length} semaine(s) :`;

  container.innerHTML = "";

  weeks.forEach(w => {
    const block = document.createElement("div");
    block.className = "month-week-block";

    const header = document.createElement("div");
    header.className = "month-week-header";
    header.innerHTML = `
      <span class="month-week-title">${escapeHtml(w.label)}</span>
      <span class="month-week-badge">${w.movie_count} film(s)</span>
    `;
    block.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "grid-month";

    w.movies.forEach(m => {
      const card = createCompactCard(m);
      grid.appendChild(card);
    });

    block.appendChild(grid);
    container.appendChild(block);
  });
}

// 3. VUE ANNÉE : GRILLE DENSE (5 PAR LIGNE MINIMUM) AVEC PAGINATION RAPIDE
function renderYearView(data, container, countBar) {
  countBar.textContent = `${data.total_movies} film(s) en ${data.year} (Page ${data.page} sur ${data.total_pages}) :`;

  // Mettre à jour les boutons de pagination
  document.getElementById("page-indicator").textContent = `Page ${data.page} / ${data.total_pages}`;
  document.getElementById("btn-page-prev").disabled = (data.page <= 1);
  document.getElementById("btn-page-next").disabled = (data.page >= data.total_pages);

  if (!data.movies || data.movies.length === 0) {
    container.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8;">Aucun film répertorié pour cette année.</div>';
    return;
  }

  const grid = document.createElement("div");
  grid.className = "grid-year";

  data.movies.forEach(m => {
    const card = createCompactCard(m);
    grid.appendChild(card);
  });

  container.innerHTML = "";
  container.appendChild(grid);
}

// CARTE COMPACTE POUR LES GRILLES MOIS ET ANNÉE (RATIO 2:3, TITRES CLAIRS, CLIC TMDB)
function createCompactCard(m) {
  const card = document.createElement("div");
  card.className = "card-compact";
  card.id = `card-compact-${m.tmdb_id}`;

  const headerBar = document.createElement("div");
  headerBar.className = "card-header-bar";
  const origYr = m.original_year || (m.original_release_date ? m.original_release_date.substring(0, 4) : "");
  const repriseHtml = m.is_reprise ? `<span class="badge-reprise" title="Reprise (sortie initiale ${origYr})">🔄 ${origYr || 'Reprise'}</span>` : "";
  headerBar.innerHTML = `
    <span class="card-date">📅 ${m.release_date || ''}</span>
    ${repriseHtml}
  `;
  const delBtn = document.createElement("button");
  delBtn.className = "btn-card-del";
  delBtn.innerHTML = "✕";
  delBtn.title = "Éliminer";
  delBtn.onclick = () => dismissMovie(m.tmdb_id, card);
  headerBar.appendChild(delBtn);

  const posterBox = document.createElement("div");
  posterBox.className = "card-poster-box";
  if (m.poster_url) {
    posterBox.innerHTML = `
      <a href="https://www.themoviedb.org/movie/${m.tmdb_id}" target="_blank" rel="noopener noreferrer" class="poster-link" title="Ouvrir la fiche sur TMDb (nouvel onglet)">
        <img src="${m.poster_url}" class="card-poster-img" alt="${escapeHtml(m.title)}" loading="lazy">
      </a>`;
  } else {
    posterBox.innerHTML = `
      <a href="https://www.themoviedb.org/movie/${m.tmdb_id}" target="_blank" rel="noopener noreferrer" class="poster-link">
        <div class="poster-placeholder">Sans affiche</div>
      </a>`;
  }

  const content = document.createElement("div");
  content.className = "card-content";
  content.innerHTML = `
    <div class="card-title">
      <a href="https://www.themoviedb.org/movie/${m.tmdb_id}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(m.title)} (Ouvrir sur TMDb)">
        ${escapeHtml(m.title)}
      </a>
    </div>`;

  const ratings = document.createElement("div");
  ratings.className = "card-ratings";
  ratings.appendChild(createRatingWidget(m.tmdb_id, m.user_rating || 0.0, "star"));
  ratings.appendChild(createRatingWidget(m.tmdb_id, m.want_rating || 0.0, "heart"));
  content.appendChild(ratings);

  card.appendChild(headerBar);
  card.appendChild(posterBox);
  card.appendChild(content);

  return card;
}

// --- COMPOSANT VECTORIEL DEMI-ÉTOILES & DEMI-CŒURS (STABILITÉ STRICTE, ZÉRO DÉCALAGE, ZÉRO SAUT) ---
function createRatingWidget(tmdbId, initialVal, mode) {
  const widget = document.createElement("div");
  widget.className = "rating-widget";

  let curVal = parseFloat(initialVal) || 0.0;
  const isHeart = (mode === "heart");
  const starClips = [];

  const pathD = isHeart
    ? "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
    : "M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z";
  const fgColor = isHeart ? "#ef4444" : "#f59e0b";
  const bgColor = "#334155";

  for (let i = 1; i <= 5; i++) {
    const unit = document.createElement("div");
    unit.className = "star-unit";

    unit.innerHTML = `
      <svg class="star-svg star-bg" viewBox="0 0 24 24">
        <path fill="${bgColor}" d="${pathD}"/>
      </svg>
      <div class="star-fill-clip">
        <svg class="star-svg star-fg" viewBox="0 0 24 24">
          <path fill="${fgColor}" d="${pathD}"/>
        </svg>
      </div>
      <div class="click-half left" title="${i - 0.5} / 5"></div>
      <div class="click-half right" title="${i} / 5"></div>
    `;

    const clip = unit.querySelector(".star-fill-clip");
    starClips.push(clip);

    const leftHalf = unit.querySelector(".click-half.left");
    const rightHalf = unit.querySelector(".click-half.right");

    leftHalf.addEventListener("mouseenter", () => updateDisplay(i - 0.5));
    leftHalf.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      const target = (curVal === (i - 0.5)) ? 0.0 : (i - 0.5);
      setRating(target);
    });

    rightHalf.addEventListener("mouseenter", () => updateDisplay(i));
    rightHalf.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      const target = (curVal === i) ? 0.0 : i;
      setRating(target);
    });

    widget.appendChild(unit);
  }

  // Label score fixe
  const lbl = document.createElement("span");
  lbl.className = "rating-score-label";
  widget.appendChild(lbl);

  // Bouton de réinitialisation permanent (maintient l'espace exact sans décalage)
  const btnReset = document.createElement("button");
  btnReset.className = "btn-reset-rating";
  btnReset.innerHTML = "✕";
  btnReset.title = "Remettre à zéro (0)";
  btnReset.addEventListener("click", (e) => {
    e.stopPropagation();
    e.preventDefault();
    setRating(0.0);
  });
  widget.appendChild(btnReset);

  // Rétablir la note réelle dès la sortie du curseur du widget
  widget.addEventListener("mouseleave", () => {
    updateDisplay(curVal);
  });

  function updateDisplay(val) {
    for (let i = 1; i <= 5; i++) {
      const clip = starClips[i - 1];
      if (val >= i) {
        clip.style.width = "100%";
      } else if (val >= (i - 0.5)) {
        clip.style.width = "50%";
      } else {
        clip.style.width = "0%";
      }
    }
    lbl.textContent = val > 0 ? `${val}/5` : "-";
    if (curVal > 0) {
      btnReset.style.visibility = "visible";
      btnReset.style.opacity = "1";
      btnReset.style.pointerEvents = "auto";
    } else {
      btnReset.style.visibility = "hidden";
      btnReset.style.opacity = "0";
      btnReset.style.pointerEvents = "none";
    }
  }

  async function setRating(newVal) {
    curVal = newVal;
    updateDisplay(curVal); // Rendu instantané 0 ms sans aucune reconstruction DOM

    try {
      const endpoint = isHeart ? "/api/want" : "/api/rate";
      const payload = isHeart ? { tmdb_id: tmdbId, want_rating: newVal } : { tmdb_id: tmdbId, rating: newVal };
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success && data.stats) {
        const totalEl = document.getElementById("stat-total");
        const watchedEl = document.getElementById("stat-watched");
        const badgeEl = document.getElementById("badge-watched");
        if (totalEl) totalEl.textContent = data.stats.total.toLocaleString("fr-FR");
        if (watchedEl) watchedEl.textContent = data.stats.watched.toLocaleString("fr-FR");
        if (badgeEl) badgeEl.textContent = data.stats.watched;
      }
    } catch (e) {
      console.error("Erreur enregistrement note :", e);
    }
  }

  // Initialisation visuelle immédiate
  updateDisplay(curVal);

  return widget;
}

// --- ÉLIMINATION INSTANTANÉE (DISMISS) AVEC ANNULATION RAPIDE ---
async function dismissMovie(tmdbId, element) {
  element.classList.add("fade-out");
  setTimeout(() => element.remove(), 200);

  state.lastDismissedId = tmdbId;
  showToast("Film éliminé de la liste.");

  try {
    const res = await fetch("/api/dismiss", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tmdb_id: tmdbId })
    });
    const data = await res.json();
    if (data.success && data.stats) {
      document.getElementById("stat-total").textContent = data.stats.total.toLocaleString("fr-FR");
    }
  } catch (e) {
    console.error("Erreur suppression :", e);
  }
}

async function undoLastDismiss() {
  if (!state.lastDismissedId) return;
  const idToRestore = state.lastDismissedId;
  state.lastDismissedId = null;
  hideToast();

  try {
    await fetch("/api/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tmdb_id: idToRestore })
    });
    viewCache.clear();
    renderCurrentView();
  } catch (e) {
    console.error("Erreur restauration :", e);
  }
}

// Nettoyage automatique en 1 clic de tout le bruit (courts-métrages, sans affiche, placeholder 31/12)
async function cleanCurrentNoise() {
  const dateStr = formatDateISO(state.targetDate);
  const btn = document.getElementById("btn-clean-noise");
  if (btn) btn.disabled = true;

  try {
    const isYear = (state.scale === "year");
    const res = await fetch("/api/clean-noise", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        week_date: isYear ? null : dateStr,
        all: isYear
      })
    });
    const data = await res.json();
    if (data.success) {
      viewCache.clear();
      showToast(`🧹 ${data.dismissed_count} élément(s) de bruit éliminé(s) !`);
      loadStats();
      renderCurrentView();
    }
  } catch (e) {
    console.error("Erreur nettoyage bruit :", e);
  } finally {
    if (btn) btn.disabled = false;
  }
}

let toastTimer = null;
function showToast(msg) {
  const toast = document.getElementById("toast");
  document.getElementById("toast-message").textContent = msg;
  toast.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideToast, 4000);
}

function hideToast() {
  const toast = document.getElementById("toast");
  toast.classList.add("hidden");
}

// --- SYNCHRONISATION TMDB EN ARRIÈRE-PLAN ---
async function triggerSync() {
  const btn = document.getElementById("btn-sync");
  btn.disabled = true;
  try {
    const res = await fetch("/api/sync", { method: "POST" });
    const data = await res.json();
    if (!data.success && data.message) {
      alert(data.message);
      btn.disabled = false;
    }
  } catch (e) {
    console.error("Erreur lancement sync :", e);
    btn.disabled = false;
  }
}

function startSyncPolling() {
  setInterval(async () => {
    try {
      const res = await fetch("/api/sync-status");
      const status = await res.json();
      const banner = document.getElementById("sync-banner");
      const bar = document.getElementById("sync-prog-bar");
      const txt = document.getElementById("sync-text");
      const btn = document.getElementById("btn-sync");

      if (status.is_syncing) {
        banner.classList.remove("hidden");
        bar.style.width = `${status.progress}%`;
        txt.textContent = status.message || "Synchronisation...";
        btn.disabled = true;
      } else {
        if (!banner.classList.contains("hidden")) {
          banner.classList.add("hidden");
          btn.disabled = false;
          loadStats();
          renderCurrentView();
        }
      }
    } catch (e) {}
  }, 2000);
}

// --- ONGLETS SECONDAIRES : WATCHLIST & VUS ---
async function loadWatchlist() {
  const container = document.getElementById("watchlist-container");
  container.innerHTML = '<div style="color: #64748b; padding: 20px;">Chargement...</div>';

  const genre = document.getElementById("wl-genre-filter").value;
  const minWant = document.getElementById("wl-min-want").value;
  const search = document.getElementById("wl-search").value;

  try {
    const res = await fetch(`/api/watchlist?genre=${encodeURIComponent(genre)}&min_want=${minWant}&search=${encodeURIComponent(search)}`);
    const data = await res.json();
    document.getElementById("badge-watchlist").textContent = data.count;

    if (!data.movies || data.movies.length === 0) {
      container.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8;">Aucun film dans votre sélection correspondant à ces critères.</div>';
      return;
    }

    const list = document.createElement("div");
    list.className = "movies-list-week";
    data.movies.forEach(m => {
      const row = document.createElement("div");
      row.className = "movie-row";
      row.innerHTML = `
        <div class="col-del">
          <button class="btn-dismiss" title="Retirer de la sélection" onclick="dismissMovie(${m.tmdb_id}, this.closest('.movie-row'))">✕</button>
        </div>
        <div class="col-poster">
          ${m.poster_url ? `<img src="${m.poster_url}" class="poster-img" alt="${escapeHtml(m.title)}">` : '<div class="poster-placeholder">Sans affiche</div>'}
        </div>
        <div class="col-info">
          <div class="movie-headline">
            <span class="movie-title">${escapeHtml(m.title)}</span>
            <span class="movie-runtime">${m.year} • ${m.runtime || 0} min</span>
            ${m.vote_average > 0 ? `<span class="badge-tmdb">TMDb ${m.vote_average}</span>` : ""}
          </div>
          <div class="movie-credits">👤 <b>De :</b> ${escapeHtml(m.director || 'Inconnu')} • 🎭 <b>Avec :</b> ${escapeHtml(m.cast || 'N/A')}</div>
          <div class="movie-synopsis">${escapeHtml(m.synopsis || '')}</div>
        </div>
      `;
      const colAct = document.createElement("div");
      colAct.className = "col-actions";
      colAct.appendChild(createRatingWidget(m.tmdb_id, m.user_rating || 0.0, "star"));
      colAct.appendChild(createRatingWidget(m.tmdb_id, m.want_rating || 0.0, "heart"));
      row.appendChild(colAct);
      list.appendChild(row);
    });

    container.innerHTML = "";
    container.appendChild(list);
  } catch (e) {
    container.innerHTML = `<div style="color: #ef4444; padding: 20px;">Erreur : ${e.message}</div>`;
  }
}

async function loadWatched() {
  const container = document.getElementById("watched-container");
  container.innerHTML = '<div style="color: #64748b; padding: 20px;">Chargement...</div>';

  const sort = document.getElementById("watched-sort").value;
  const year = document.getElementById("watched-year").value;
  const genre = document.getElementById("watched-genre").value;

  try {
    const res = await fetch(`/api/watched?sort=${sort}&year=${encodeURIComponent(year)}&genre=${encodeURIComponent(genre)}`);
    const data = await res.json();
    document.getElementById("badge-watched").textContent = data.count;

    if (!data.movies || data.movies.length === 0) {
      container.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8;">Aucun film vu correspondant.</div>';
      return;
    }

    const list = document.createElement("div");
    list.className = "movies-list-week";
    data.movies.forEach(m => {
      const row = document.createElement("div");
      row.className = "movie-row";
      row.innerHTML = `
        <div class="col-del"></div>
        <div class="col-poster">
          ${m.poster_url ? `<img src="${m.poster_url}" class="poster-img" alt="${escapeHtml(m.title)}">` : '<div class="poster-placeholder">Sans affiche</div>'}
        </div>
        <div class="col-info">
          <div class="movie-headline">
            <span class="movie-title">${escapeHtml(m.title)}</span>
            <span class="badge-watched">VU : ${m.user_rating}★</span>
            <span class="movie-runtime">${m.year}</span>
          </div>
          <div class="movie-credits">👤 <b>De :</b> ${escapeHtml(m.director || 'Inconnu')} • 🎭 <b>Avec :</b> ${escapeHtml(m.cast || 'N/A')}</div>
        </div>
      `;
      const colAct = document.createElement("div");
      colAct.className = "col-actions";
      colAct.appendChild(createRatingWidget(m.tmdb_id, m.user_rating || 0.0, "star"));
      row.appendChild(colAct);
      list.appendChild(row);
    });

    container.innerHTML = "";
    container.appendChild(list);
  } catch (e) {
    container.innerHTML = `<div style="color: #ef4444; padding: 20px;">Erreur : ${e.message}</div>`;
  }
}

// --- EXPORT OBSIDIAN ---
async function exportObsidian(type) {
  const path = document.getElementById("obsidian-path").value.trim();
  const resBox = document.getElementById("obsidian-result");
  if (!path) {
    alert("Veuillez renseigner un chemin de dossier pour votre coffre Obsidian.");
    return;
  }

  resBox.classList.remove("hidden");
  resBox.textContent = "Exportation en cours...";

  try {
    const res = await fetch("/api/export-obsidian", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path, type: type })
    });
    const data = await res.json();
    if (data.success) {
      resBox.innerHTML = `✅ <b>${data.exported_count} film(s)</b> exporté(s) avec succès dans : <code>${escapeHtml(path)}</code><br>Note d'index <code>00_Index_Films.md</code> créée avec succès !`;
    } else {
      resBox.textContent = `❌ Erreur : ${data.error}`;
    }
  } catch (e) {
    resBox.textContent = `❌ Erreur lors de l'export : ${e.message}`;
  }
}

// --- UTILITAIRES ---
function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function debounce(fn, delay) {
  let timer;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}
