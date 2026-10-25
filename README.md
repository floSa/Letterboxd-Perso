# 🎬 Letterboxd-Perso

> **Application web personnelle de tri, notation et archivage cinématographique ultra-réactive.**  
> Connectée directement à l'API **The Movie Database (TMDb)** et intégrée à **Obsidian**.

---

## ✨ Points forts & Fonctionnalités

- ⚡ **Performance instantanée (0 ms de latence)** : Architecture légère en Python natif (`server.py`) combinée à une Single Page Application Vanilla JS optimisée.
- 🎯 **Tri et filtrage intelligent anti-bruit** :
  - **Filtre Cinéma uniquement** : Élimine automatiquement les courts-métrages (< 50 min), les émissions TV et les entrées factices TMDb (dumps du 31 décembre sans note).
  - **Gestion dédiée des reprises (ressorties en salle)** : Détecte les ressorties de classiques et de films de patrimoine (écart $\ge 2$ ans avec la sortie mondiale), les isole en bas de liste et permet de les masquer en un clic (`🔄 Masquer les reprises`).
  - **Bouton 1-clic « 🧹 Éliminer le bruit »** : Permet de rejeter en masse les éléments parasites d'une période donnée.
- ⭐ **Système de notation précis par demi-étoiles & demi-cœurs** :
  - Évaluation de 0 à 5 (par pas de 0.5) pour la note de visionnage (étoiles dorées) et la priorité d'envie (cœurs rouges).
  - Rendu vectoriel strict sans décalage de mise en page (*zero layout shift*).
- 📅 **Navigation temporelle multi-échelles** :
  - **Vue Semaine** : Rangées horizontales détaillées avec réalisateur, acteurs principaux, note TMDb, durée et affiches haute qualité au ratio vertical 2:3.
  - **Vue Mois** : Grille élégante par carrés hebdomadaires avec liseré fin.
  - **Vue Année** : Mosaïque dense avec pagination rapide.
  - Préchargement asynchrone des périodes adjacentes pour une navigation immédiate.
- 🔗 **Liens directs TMDb** : Clic direct sur n'importe quelle affiche ou titre pour ouvrir la fiche détaillée sur The Movie Database dans un nouvel onglet.
- 📝 **Intégration Obsidian** : Exportation directe de vos films vus et de votre sélection vers votre coffre Markdown personnel (fiches formatées avec métadonnées YAML).

---

## 🚀 Démarrage rapide

### 1. Prérequis
- Python 3.10+ (idéalement 3.12)
- Une clé API gratuite ou un jeton de lecture TMDb v4 (à récupérer sur [themoviedb.org](https://www.themoviedb.org/settings/api)).

### 2. Installation
```bash
git clone git@github.com-perso:floSa/Letterboxd-Perso.git
cd Letterboxd-Perso

# Création de l'environnement virtuel
python -m venv .venv
.\.venv\Scripts\activate  # Sous Windows (ou source .venv/bin/activate sous Linux/macOS)

# Installation des dépendances
pip install -r requirements.txt
```

### 3. Configuration de la clé TMDb
Copiez `config.example.json` vers `config.json` et renseignez votre clé :
```json
{
  "tmdb_api_key": "VOTRE_CLE_OU_JETON_TMDB"
}
```

### 4. Lancement
- **Sous Windows** : Double-cliquez simplement sur `lancer_app.bat` (démarre le serveur et ouvre votre navigateur à l'adresse `http://localhost:8080`).
- **En ligne de commande** :
```bash
python server.py
```

---

## 🗂️ Structure du projet

```
Letterboxd-Perso/
├── server.py              # Serveur HTTP haute performance multi-threadé & API REST
├── database.py            # Modèle SQLite, indexation, filtres anti-bruit et reprises
├── tmdb_client.py         # Client TMDb (découverte, crédits, détection ressorties)
├── obsidian_export.py     # Module d'exportation vers coffres Obsidian (Markdown)
├── cinetrack.db           # Base SQLite locale (8 000+ films répertoriés & notes)
├── config.json            # Configuration locale (clé TMDb - ignorée par Git)
├── config.example.json    # Modèle de configuration
├── requirements.txt       # Dépendances Python minimales (requests)
├── lancer_app.bat         # Lanceur 1-clic pour Windows
└── static/                # Frontend Web Vanilla JS / CSS (Thème sombre Letterboxd)
    ├── index.html         # Structure SPA
    ├── style.css          # Design system et composants vectoriels
    └── app.js             # Logique applicative réactive, cache et préchargement
```

---

## 👤 Auteur
**Florian Horellou** ([@floSa](https://github.com/floSa))
