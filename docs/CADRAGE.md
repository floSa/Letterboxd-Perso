# Cadrage — Letterboxd-Perso

## 1. Pitch

Letterboxd-Perso est une application web personnelle de tri, de notation et d'archivage cinématographique locale, conçue pour remplacer les services distants par un outil ultra-réactif sans latence, synchronisé avec The Movie Database (TMDb) et exportable vers un coffre Obsidian.

1. **Tri rapide des sorties en salle** : navigation temporelle fluide (semaine, mois, année), élimination du bruit en un clic et distinction automatique des reprises.
2. **Double système d'évaluation fine** : notation de visionnage (étoiles de 0 à 5 par pas de 0.5), priorité d'envie (cœurs de 0 à 5 par pas de 0.5) et suivi de possession en bibliothèque (cible).
3. **Archivage et pérennité locale** : persistance continue en base SQLite locale et génération de fiches Markdown enrichies pour coffre personnel Obsidian.

---

## 2. Objectifs et périmètre

**Dans le périmètre (V1)** :
- Consultation et tri par période des sorties cinéma françaises (calendrier des mercredis, mois, années).
- Recherche globale dans la base locale (titre, saga, réalisateur) avec tri chronologique et édition directe.
- Filtrage anti-bruit ciblé : exclusion des courts-métrages (< 50 minutes), des entrées techniques TMDb factices et des séances uniques non commerciales.
- Traitement spécifique des ressorties et reprises en salle (isolement en bas de liste et bascule masquer/afficher).
- Marquage d'état en base : films rejetés (`status = 'dismissed'`), conservés (`status = 'kept'`), vus (`is_watched = 1`), possédés (`is_owned = 1`).
- Navigation réactive avec cache client et requêtes préchargées.
- Exportation Markdown riche (frontmatter YAML, affiches, index Dataview) vers un dossier Obsidian local.
- Entêtes et filtres fixes au défilement (`sticky`) pour un confort de navigation continu.

**Hors périmètre (V1)** :
- Authentification multi-utilisateurs (application à usage strictement personnel et mono-utilisateur en réseau local).
- Gestionnaire de téléchargement ou lecteur multimédia embarqué (l'outil référence et note, il ne diffuse pas de flux vidéo).
- Déploiement cloud distant avec passerelle SaaS publique.

---

## 3. Contraintes (fermes)

| Contrainte | Détail |
|---|---|
| Déploiement | Local strict (`localhost:8080`), mono-machine ou synchronisation par Git |
| Données | Stockage SQLite autonome dans le dépôt (`cinetrack.db`), volume maîtrisé (~31 Mo pour 44 758 films de 1960 à 2026) |
| Latence | Réponse inférieure à 10 ms sur toutes les requêtes locales via indexation SQLite et Single Page Application Vanilla JS |
| Dépendances | Minimales : Python standard library + bibliothèque `requests`, aucun framework lourd (pas de Node.js en production, pas de buildpack complexe) |
| Compatibilité | Windows (lanceur batch fourni), Linux et macOS |

---

## 4. Hypothèses

- **Calendrier des sorties en France** : Le mercredi constitue la date pivot des sorties cinéma en France ; les semaines sont modélisées du mercredi au mardi suivant.
- **Détection des reprises** : Un film dont la date de sortie en salle en France présente un écart supérieur ou égal à 2 ans avec sa date de sortie initiale mondiale est qualifié de reprise.
- **Accès TMDb** : Une clé d'API personnelle (ou jeton v4) valide est nécessaire pour synchroniser les métadonnées et affiches depuis The Movie Database.
- **Pérennité du fichier SQLite** : La base de données reste sous le seuil des 50 Mo recommandés par GitHub, permettant son inclusion directe dans les commits sans recours à Git LFS.

---

## 5. Stack technique

| Brique | Choix | Licence | Justification |
|---|---|---|---|
| Backend | Python 3.12 (`http.server.ThreadingHTTPServer`) | PSF License | Serveur multi-threadé natif sans dépendance externe lourde |
| Base de données | SQLite 3 (`sqlite3`) | Public Domain | Moteur relationnel intégré, zéro configuration, transactions ACID |
| Client HTTP | `requests` 2.x | Apache 2.0 | Requêtes simples vers l'API TMDb avec gestion des timeouts |
| Frontend | Vanilla JavaScript ES6+ / HTML5 / CSS3 | MIT | Zéro étape de compilation, chargement instantané, composants vectoriels directs |
| Export | Générateur Markdown Python (`obsidian_export.py`) | MIT | Compatibilité native avec le format Dataview d'Obsidian |

---

## 6. Décisions

**Décisions figées**
- **Serveur HTTP standard plutôt que framework lourd (FastAPI / Django)** : Choisi car l'application est mono-utilisateur locale ; évite les dépendances complexes d'environnement et garantit un démarrage en une fraction de seconde.
- **Composants d'évaluation vectoriels purs (SVG) plutôt que bibliothèques tierces** : Évite les décalages de disposition (*layout shifts*), autorise le pas de 0.5 (demi-étoile et demi-cœur) et garantit un alignement géométrique strict.
- **Bouton de possession sous forme de cible iconique** : Emplacement aligné horizontalement sous la première étoile pour une symétrie visuelle parfaite, avec retour visuel immédiat (bleu non possédé, vert possédé).
- **Barres d'outils et de filtres fixes (`position: sticky`)** : Maintien continu des commandes de filtrage visibles en haut de l'écran lors du défilement des longues listes de films.

**À trancher**
- Synchronisation automatique programmée en tâche de fond (cron/scheduler local) vs synchronisation manuelle déclenchée depuis l'interface (recommandation actuelle : maintien du bouton manuel pour maîtriser les quotas d'appels TMDb).

---

## 7. Roadmap

0. **Socle technique** : Base de données relationnelle SQLite, ingestion des sorties TMDb et serveur API REST minimal.
1. **Interface de tri et notation** : Vues temporelles (semaine, mois, année), widgets de notation par demi-unités et indicateur de possession.
2. **Filtres avancés et anti-bruit** : Masquage des reprises, nettoyage en un clic des fiches sans affiche ou de faible durée, barres de filtres par date et possession.
3. **Pérennisation et export** : Passerelle vers coffres Obsidian et fiabilisation de l'intégration dans l'écosystème local multi-machines.

---

## 8. Stratégie de tests

- **Validation syntaxique continue** : Analyse statique Python (`compile`) et JavaScript (`node -c`) à chaque modification.
- **Tests d'intégration d'API** : Requêtes automatisées sur les routes REST principales (`/api/movies`, `/api/watchlist`, `/api/watched`, `/api/owned`).
- **Contrôle documentaire mécanique** : Exécution systématique du script `check_doc.py` pour valider l'absence d'émojis décoratifs, l'intégrité des liens relatifs et la validité des diagrammes Mermaid.

---

## 9. Références

- [The Movie Database API Documentation](https://developer.themoviedb.org/docs)
- [Obsidian Dataview Plugin Documentation](https://blacksmithgu.github.io/obsidian-dataview/)
- [Architecture technique détaillée](ARCHITECTURE.md)
