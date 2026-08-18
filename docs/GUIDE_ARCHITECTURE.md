# Guide d'architecture

Ce document explique d'abord l'architecture globale de l'application, puis
détaille **chaque fichier du code**, dans le but qu'une personne devant
réaliser une évolution puisse rapidement savoir **où** intervenir et
**comment**. Pour installer l'application, voir le
[guide d'installation](GUIDE_INSTALLATION.md). Pour l'utiliser ou
l'administrer au quotidien, voir le
[guide d'utilisation et d'administration](GUIDE_UTILISATION_ADMINISTRATION.md).

Sommaire :

1. [Vue d'ensemble](#1-vue-densemble)
2. [Modèle de données Neo4j](#2-modèle-de-données-neo4j)
3. [Structure complète du dépôt](#3-structure-complète-du-dépôt)
4. [Le workflow de demande / validation en détail](#4-le-workflow-de-demande--validation-en-détail)
5. [Backend — détail fichier par fichier](#5-backend--détail-fichier-par-fichier)
6. [Frontend — détail fichier par fichier](#6-frontend--détail-fichier-par-fichier)
7. [Infrastructure Docker — détail fichier par fichier](#7-infrastructure-docker--détail-fichier-par-fichier)
8. [Authentification et autorisation en détail](#8-authentification-et-autorisation-en-détail)
9. [Cookbook — comment réaliser les évolutions les plus courantes](#9-cookbook--comment-réaliser-les-évolutions-les-plus-courantes)
10. [Limites connues et dette technique](#10-limites-connues-et-dette-technique)
11. [Glossaire](#11-glossaire)

---

## 1. Vue d'ensemble

### 1.1 Schéma des flux

```
                     ┌───────────────────────────┐
Navigateur  ───────▶ │   proxy (Nginx, port 80)    │
                     └─────────────┬───────────────┘
                                    │
                   ┌────────────────┴────────────────┐
                   │                                   │
                   ▼                                   ▼
   /            → frontend (Nginx statique)     /api/ → backend (FastAPI, :8000)
                                                              │
                                                              ▼
                                                    neo4j (Bolt :7687 / Browser :7474)
```

Les 4 services (`neo4j`, `backend`, `frontend`, `proxy`) sont définis dans
`docker-compose.yml` et communiquent via le réseau Docker `app-network`
(résolution DNS interne par nom de service).

**Particularité importante** : en environnement de développement local, le
frontend n'appelle **pas** l'API via `/api/` (le chemin du proxy) mais
**directement** sur `http://localhost:8000`. Ce choix est fait dans le code
JavaScript lui-même (`frontend/common.js` et `frontend/login.html`) :

```js
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "/api";
```

Autrement dit :
- Page ouverte sur `localhost`/`127.0.0.1` → appels directs au port `8000`
  du conteneur `backend` (le proxy n'est alors pas sollicité pour l'API,
  seulement potentiellement pour servir les pages statiques si l'utilisateur
  passe par le port 80).
- Toute autre URL (nom de domaine de production) → appels relatifs `/api/...`,
  qui transitent par le `proxy` Nginx, lequel les redirige en interne vers
  `http://backend:8000/`.

C'est pourquoi le `proxy` sert avant tout de **point d'entrée unique pour un
déploiement serveur** (un seul port 80 exposé, une seule URL à retenir),
alors qu'en local les deux services `backend` et `neo4j` restent aussi
directement accessibles sur leurs ports respectifs pour faciliter le
développement et le débogage.

### 1.2 Les 4 services

| Service | Techno | Rôle | Construit localement |
|---|---|---|---|
| `neo4j` | Neo4j 2026.03 | Stockage de toutes les données (personnes, compétences, référentiel, comptes, historique) | Non (image officielle) |
| `backend` | Python 3.12 / FastAPI 0.115 | API REST : toute la logique métier | Oui (`backend/Dockerfile`) |
| `frontend` | Nginx 1.27-alpine | Sert les pages HTML/CSS/JS statiques | Oui (`frontend/Dockerfile`) |
| `proxy` | Nginx 1.27-alpine | Reverse proxy, point d'entrée unique (port 80) | Oui (`proxy/Dockerfile`) |

### 1.3 Absence de couche de build front

Le frontend n'a **aucune étape de compilation/transpilation** : ce sont des
fichiers `.html`/`.css`/`.js` servis tels quels par Nginx. Aucun
`package.json`, aucun framework (React/Vue/Angular). La seule dépendance
externe est la librairie **`vis-network`**, chargée directement depuis un
CDN (`https://unpkg.com/vis-network/standalone/umd/vis-network.min.js`)
dans `profils.html`, pour la visualisation en graphe.

### 1.4 Absence de tests automatisés et de CI/CD

Il n'existe à ce jour **aucun test automatisé** (pas de dossier `tests/`,
pas de `pytest` dans les dépendances) ni **aucune pipeline CI/CD** (pas de
`.github/workflows/`, pas d'équivalent). Toute vérification après une
modification du code est donc **manuelle** : redémarrer les conteneurs
concernés (voir le guide d'utilisation et d'administration, section F) et
tester directement l'application ou l'API (`http://localhost:8000/docs`).

---

## 2. Modèle de données Neo4j

### 2.1 Nœuds (labels)

| Label | Propriétés | Rôle |
|---|---|---|
| `Personne` | `nom` | Membre de l'équipe DBA |
| `Contexte` | `cle` (= `"techno\|domaine\|version"`), `createdAt` | Triplet unique techno/domaine/version — pivot entre une compétence et son référentiel |
| `Techno` | `nom`, `type` | Une technologie (ex. « MongoDB ») |
| `Domaine` | `nom` | Un domaine d'usage (ex. « Run MCO », « Build », « Architecture ») |
| `Version` | `nom` | Une version de technologie (ex. « MongoDB 6 »), ou `N/A` |
| `TechnoCategory` | `nom` | Regroupement de technologies (ex. « Base de données NoSQL ») |
| `User` | `email`, `password` *(en clair)*, `role` (`ADMIN`/`USER`), `active`, `createdAt`, `createdBy`, `updatedAt` | Compte applicatif |
| `AuditEvent` | `id` (UUID), `type`, `status` (`PROPOSED`/`VALIDATED`/`REJECTED`), `auteur`, `createdAt`, `manager`, `decisionAt`, `decisionComment`, + champs `before_*`/`after_*` selon le type, `data` (JSON, pour `QUESTIONNAIRE_REQUEST`) | Trace de toute demande et de sa décision |

### 2.2 Relations

```
(Personne)-[:COMPETENCE {niveau, actif, description, createdAt, updatedAt}]->(Contexte)
(Personne)-[:MAITRISE]->(Techno)                       # matérialisation, tenue à jour en même temps que COMPETENCE
(Contexte)-[:CTX_TECHNO]->(Techno)
(Contexte)-[:CTX_DOMAINE]->(Domaine)
(Contexte)-[:CTX_VERSION]->(Version)
(Techno)-[:APPARTIENT_A]->(TechnoCategory)
(AuditEvent)-[:AUDIT_OF]->(Personne)
(AuditEvent)-[:AUDIT_CTX]->(Contexte)
```

### 2.3 Types d'`AuditEvent`

| Type | Créé par | Effet à la validation (`VALIDATED`) |
|---|---|---|
| `PERSON_CREATE` | `POST /personnes` | *(aucun effet automatique câblé dans `historique.py` — voir §10, limite connue)* |
| `COMPETENCE_REQUEST` | `POST /personnes/{nom}/competences/demandes` | Crée/replace la relation `COMPETENCE` entre la `Personne` et le `Contexte`, avec les valeurs `after_*` de l'event |
| `TECHNO_CREATE` | `POST /ref/technos` | Crée le nœud `Techno` (et son `TechnoCategory` associé si besoin) |
| `PERSON_DELETE` | `POST /personnes/{nom}/suppression` | `DETACH DELETE` de la `Personne` (et de toutes ses relations) |
| `QUESTIONNAIRE_REQUEST` | `POST /questionnaire` | Applique en boucle chacune des compétences soumises (stockées en JSON dans `a.data`) |
| `COMPETENCE_DELETE` | `DELETE /personnes/{nom}/competences` | *(créé directement avec `status: "REJECTED"` — la suppression de la relation `COMPETENCE` est immédiate, l'event sert uniquement de trace, il n'y a rien à valider)* |

Pas de type `TECHNO_DELETE`, `DOMAINE_*` ni `VERSION_*` : voir §10.

Pour le détail du bloc Cypher qui applique ces effets, voir §4.

### 2.4 Pourquoi ce modèle en « Contexte » plutôt qu'une relation directe

Une compétence n'est pas directement `(Personne)-[COMPETENCE]->(Techno)` :
elle passe par un nœud intermédiaire `Contexte`, qui représente le triplet
unique `techno|domaine|version`. Cela permet à une même personne d'avoir
plusieurs niveaux de compétence sur une même technologie selon le
domaine/la version (ex. « MongoDB / Run MCO / v6 » niveau 3, mais
« MongoDB / Build / v7 » niveau 1), tout en gardant un seul nœud `Contexte`
partagé par toutes les personnes concernées par le même triplet — c'est le
rôle de la clé `cle` (générée par `backend/utils.py::make_cle`), qui sert
de clé unique de fusion (`MERGE`) sur ce nœud.

---

## 3. Structure complète du dépôt

```
Projet_cartographie_competences/
├── README.md
├── docker-compose.yml           # orchestration des 4 services
├── .env.example                  # modèle des variables d'environnement racine
├── .dockerignore                  # fichiers exclus du contexte de build Docker
│
├── backend/                        # API FastAPI
│   ├── Dockerfile                    # image backend (python:3.12-slim)
│   ├── requirements.txt               # dépendances Python figées
│   ├── .env.example                    # modèle .env backend (utile hors Docker)
│   ├── .dockerignore
│   ├── main.py                          # point d'entrée : app FastAPI, CORS, cycle de vie, montage des routers
│   ├── database.py                       # connexion Neo4j (driver Bolt), run_read() / run_write()
│   ├── models.py                          # schémas Pydantic (validation des requêtes/réponses)
│   ├── utils.py                            # helpers transverses (email, clé de contexte, dépendance get_user)
│   ├── auth_deps.py                         # vérification d'identité / de rôle admin (lookup Neo4j)
│   ├── security.py                           # scaffolding JWT — préparé, non branché (voir §10)
│   └── routers/                               # une route FastAPI par domaine métier
│       ├── __init__.py                          # vide
│       ├── auth.py                               # POST /auth/login
│       ├── users.py                               # /users — CRUD comptes (ADMIN)
│       ├── personnes.py                            # /personnes — le plus gros router
│       ├── ref.py                                   # /ref/* — référentiel technos/domaines/versions
│       ├── contextes.py                              # /contextes
│       ├── competences.py                             # /competences/contexte
│       ├── historique.py                               # /historique — cœur du workflow de validation
│       ├── graph.py                                     # /graph — données pour la visualisation vis-network
│       └── questionnaire.py                              # /questionnaire
│
├── frontend/                       # pages HTML statiques
│   ├── Dockerfile                    # image frontend (nginx:1.27-alpine)
│   ├── default.conf                   # configuration Nginx associée
│   ├── common.js                       # session, garde de connexion, dialogues stylées — partagé par toutes les pages sauf login.html
│   ├── style.css                        # feuille de style unique
│   ├── login.html                        # connexion
│   ├── index.html                         # accueil
│   ├── profils.html                        # consultation compétences + graphe
│   ├── recherche.html                       # recherche de profils
│   ├── gestion.html                          # création personnes/technos, demandes
│   ├── questionnaire.html                     # auto-évaluation groupée
│   ├── validation.html                         # validation/rejet des demandes (ADMIN)
│   ├── utilisateurs.html                        # gestion des comptes (ADMIN)
│   ├── synthese.html                             # vue de couverture d'équipe
│   └── historique.html                            # historique des décisions
│
├── proxy/                          # reverse proxy, point d'entrée unique
│   ├── Dockerfile                    # image proxy (nginx:1.27-alpine)
│   └── nginx.conf                     # règles de routage / → frontend, /api/ → backend
│
├── scripts/                        # scripts d'exploitation (shell)
│   ├── init_server.sh                 # bootstrap serveur : copie .env + docker compose up
│   ├── backup_neo4j.sh                 # sauvegarde Neo4j (neo4j-admin database dump)
│   └── restore_neo4j.sh                 # restauration Neo4j (neo4j-admin database load)
│
└── docs/                           # documentation (ce fichier + les 2 autres guides)
    ├── GUIDE_INSTALLATION.md
    ├── GUIDE_UTILISATION_ADMINISTRATION.md
    └── GUIDE_ARCHITECTURE.md
```

---

## 4. Le workflow de demande / validation en détail

### 4.1 Principe

La plupart des mutations ne modifient **pas directement** le graphe : elles
créent un nœud `AuditEvent` avec `status: "PROPOSED"`. Un administrateur
décide ensuite via `PUT /historique/{event_id}/decision`
(implémenté dans `backend/routers/historique.py`, fonction
`decide_competence_request`) :

- `decision: "VALIDATED"` → applique l'effet décrit par le type de l'event
  (voir tableau §2.3) et passe l'event à `VALIDATED`.
- `decision: "REJECTED"` → passe l'event à `REJECTED`, **aucune**
  modification du graphe hormis l'event lui-même.

### 4.2 Le bloc Cypher de validation (cas standard)

Pour les types `COMPETENCE_REQUEST`, `TECHNO_CREATE` et `PERSON_DELETE`,
une seule requête Cypher paramétrée gère tous les cas grâce à des blocs
`FOREACH (_ IN CASE WHEN <condition> THEN [1] ELSE [] END | <action>)` —
un idiome Cypher qui simule un `IF` conditionnel (Cypher n'a pas de `IF`
natif dans une requête d'écriture) :

```cypher
MATCH (a:AuditEvent {id: $id})
OPTIONAL MATCH (a)-[:AUDIT_CTX]->(c:Contexte)
MERGE (p:Personne {nom: a.personne})
WITH a, p, c
OPTIONAL MATCH (p)-[r:COMPETENCE]->(c)
WITH a, p, c, r

FOREACH (_ IN CASE WHEN a.type = "COMPETENCE_REQUEST" AND r IS NOT NULL THEN [1] ELSE [] END |
  DELETE r
)
FOREACH (_ IN CASE WHEN a.type = "COMPETENCE_REQUEST" AND c IS NOT NULL
                     AND NOT (a.after_description CONTAINS "suppression")
                THEN [1] ELSE [] END |
  MERGE (p)-[r2:COMPETENCE]->(c)
    ON CREATE SET r2.createdAt = datetime()
  SET r2.niveau = a.after_niveau, r2.actif = true,
      r2.description = a.after_description, r2.updatedAt = datetime()
)
FOREACH (_ IN CASE WHEN a.type = "TECHNO_CREATE" THEN [1] ELSE [] END |
  MERGE (t:Techno {nom: a.techno}) SET t.type = a.typeTechno
  MERGE (cat:TechnoCategory {nom: a.category})
  MERGE (t)-[:APPARTIENT_A]->(cat)
)
FOREACH (_ IN CASE WHEN a.type = "PERSON_DELETE" THEN [1] ELSE [] END |
  DETACH DELETE p
)

SET a.status = "VALIDATED", a.manager = $manager,
    a.decisionAt = datetime(), a.decisionComment = $comment
RETURN 1 AS closed_count
```

**Pour ajouter un nouveau type d'`AuditEvent`**, c'est ici — dans
`backend/routers/historique.py`, fonction `decide_competence_request` —
qu'il faut ajouter un nouveau bloc `FOREACH (_ IN CASE WHEN a.type =
"MON_NOUVEAU_TYPE" THEN [1] ELSE [] END | <action Cypher>)`.

### 4.3 Cas particulier : `QUESTIONNAIRE_REQUEST`

Ce type ne suit pas le bloc ci-dessus : les compétences soumises sont
stockées sous forme de **chaîne JSON** dans la propriété `a.data` de
l'`AuditEvent` (sérialisées par `json.dumps` côté `questionnaire.py` à la
création). À la validation, `historique.py` désérialise ce JSON
(`json.loads`) et exécute une requête `MERGE`/`SET` **en boucle Python**,
une fois par compétence soumise — voir le code de
`decide_competence_request` dans `backend/routers/historique.py` pour le
détail exact.

### 4.4 Exceptions qui mutent directement le graphe (hors workflow)

Deux routes ne créent **pas** d'`AuditEvent` de type `PROPOSED` et
modifient le graphe immédiatement :

- `PUT /personnes/{nom}/competences` (`personnes.py::upsert_person_competence`)
  — upsert direct d'une compétence, sans passer par une validation.
- `DELETE /personnes/{nom}` (`personnes.py::delete_personne`) — suppression
  immédiate et définitive d'une personne, **sans** page de confirmation
  dédiée à ce comportement dans l'interface actuelle (à distinguer de `POST
  /personnes/{nom}/suppression`, qui crée elle une *demande* de suppression
  soumise à validation).

Ce point est **volontaire** dans le code actuel mais mérite d'être gardé en
tête pour toute évolution qui chercherait à rendre la validation
systématique (voir §10).

---

## 5. Backend — détail fichier par fichier

Tous les fichiers sont dans `backend/`. Le serveur ASGI (Uvicorn) charge
`main:app` comme point d'entrée (voir `backend/Dockerfile`,
`CMD ["python", "-m", "uvicorn", "main:app", ...]`).

### 5.1 `main.py`

Crée l'application FastAPI et l'assemble :
- Lit `CORS_ORIGINS` (variable d'environnement, CSV) et construit la liste
  `origins` passée au middleware `CORSMiddleware` (valeurs de repli codées
  en dur si la variable est vide : `localhost:5500`, `127.0.0.1:5500`,
  `localhost:8080`, `127.0.0.1:8080`).
- Définit un `lifespan` (context manager async) qui appelle
  `database.connect()` au démarrage et `database.disconnect()` à l'arrêt —
  **c'est le seul endroit où la connexion Neo4j est ouverte/fermée**.
- Monte chacun des routers de `backend/routers/` via
  `app.include_router(...)`.
- Expose `GET /health`, qui exécute `RETURN 1 AS ok` sur Neo4j et renvoie
  `{"ok": true/false, "neo4j_uri": ...}` — utilisé par le `healthcheck`
  Docker du service `backend` (voir §7).

**Pour ajouter un nouveau router** : créer le fichier dans
`backend/routers/`, l'importer en haut de `main.py`, puis ajouter
`app.include_router(mon_router.router)`.

### 5.2 `database.py`

Couche d'accès unique à Neo4j :
- Lit `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` depuis l'environnement
  (valeurs par défaut : `bolt://localhost:7687` / `neo4j` / `neo4j`).
- `connect()` : crée le driver (`GraphDatabase.driver(...)`) et vérifie la
  connectivité (`driver.verify_connectivity()`).
- `disconnect()` : ferme proprement le driver.
- `run_read(cypher, params)` : ouvre une session, exécute la requête en
  lecture (`session.run`), retourne une liste de dictionnaires
  (`record.data()`), traduit toute `Neo4jError` en `HTTPException(500)`.
- `run_write(cypher, params)` : identique mais dans une transaction
  d'écriture explicite (`session.execute_write`), garantissant un commit
  atomique.

**Toutes les requêtes Cypher du projet passent par `run_read`/`run_write`
et sont paramétrées** (`$param`, jamais de concaténation de chaîne dans le
Cypher) — c'est la protection native contre l'injection Cypher, à
conserver impérativement pour tout nouveau code.

### 5.3 `models.py`

Schémas Pydantic utilisés pour valider les corps de requête (`response_model`
et paramètres de type `BaseModel` dans les signatures des routes). Points
notables :
- `NiveauType = conint(ge=1, le=3)` : contraint tout niveau de compétence
  entre 1 et 3 au niveau de la validation — modifier cette ligne pour
  changer l'échelle de niveau si un jour ce besoin apparaît (impacte aussi
  la logique métier ailleurs, voir §9).
- `DecisionPayload.decision` est un `Literal["VALIDATED", "REJECTED"]` —
  toute autre valeur est rejetée automatiquement par FastAPI/Pydantic avant
  d'atteindre le code métier.
- `UserCreate.role` / `UserRoleUpdate.role` sont des
  `Literal["ADMIN", "USER"]` — pour ajouter un rôle, modifier ces deux
  `Literal` (et adapter la logique de `auth_deps.py`/`users.py` en
  conséquence).

### 5.4 `utils.py`

- `CAPGEMINI_EMAIL_REGEX` : expression régulière qui définit le format
  d'email accepté (`prenom.nom@capgemini.com`, avec tirets optionnels dans
  prénom/nom). **C'est ici qu'il faut modifier le format attendu** si le
  domaine ou la convention de nommage change un jour.
- `validate_capgemini_email(email)` : normalise (minuscule, espaces
  retirés) puis valide l'email contre la regex — **sauf** si la valeur est
  exactement `"admin"`, cas particulier laissé volontairement pour
  permettre l'amorçage du tout premier compte administrateur (voir le
  guide d'installation, section 6.2). Lève une `HTTPException(400)` sinon.
- `make_cle(techno, domaine, version)` : construit la clé unique
  `"techno|domaine|version"` utilisée comme identifiant du nœud `Contexte`.
  **Toute évolution du modèle de `Contexte` doit repartir de cette
  fonction**, utilisée dans plusieurs routers.
- `normalize_email(email)` : minuscule + `strip()`, utilisée
  systématiquement avant toute comparaison d'email en base.
- `empty_to_none(value)` : convertit une chaîne vide (`""`, provenant
  typiquement d'un filtre de formulaire non renseigné côté frontend) en
  `None`, pour que les clauses `WHERE $param IS NULL OR ...` des requêtes
  Cypher fonctionnent correctement.
- `get_user(x_user: str = Header(None))` : dépendance FastAPI (`Depends`)
  qui exige la simple **présence** du header HTTP `X-User` (sans vérifier
  qu'il correspond à un compte réel — voir §8 pour la distinction avec
  `auth_deps.get_current_user_record`). Utilisée sur les routes qui ont
  seulement besoin de savoir « qui a fait la demande » à des fins de trace
  (champ `auteur` d'un `AuditEvent`), sans exiger un rôle particulier.

### 5.5 `auth_deps.py`

Dépendances d'autorisation, appelées explicitement (pas via `Depends(...)`
dans la signature, mais appelées directement dans le corps des fonctions de
route avec le header `x_user` en paramètre) :
- `get_current_user_record(x_user)` : vérifie que l'email correspond à un
  `User` **actif** en base, lève `HTTPException(401)` sinon. Retourne
  `{email, role, active}`.
- `require_admin(x_user)` : appelle `get_current_user_record` puis vérifie
  `role == "ADMIN"`, lève `HTTPException(403)` sinon.
- `count_active_admins()` : compte les `User {role: "ADMIN", active: true}`
  — utilisée par `users.py` pour empêcher la suppression/rétrogradation du
  dernier administrateur.

**Pour protéger une nouvelle route par le rôle admin**, reprendre le
pattern utilisé dans `backend/routers/users.py` :

```python
from fastapi import Header
from auth_deps import require_admin

@router.get("/ma-route")
def ma_route(x_user: Optional[str] = Header(None)):
    require_admin(x_user)
    ...
```

### 5.6 `security.py`

**Module non branché dans l'application actuelle** — aucun `import
security` n'existe ailleurs dans le code (`main.py` ni aucun router ne
l'utilise). C'est un scaffolding JWT complet, prêt à l'emploi si le besoin
de renforcer l'authentification apparaît :
- Bascule `DEV_AUTH` (variable d'environnement) : si `true` (valeur par
  défaut), `get_current_user()` retourne un utilisateur simulé sans
  vérifier de token ; si `false`, exige et valide un token JWT `Bearer`
  (bibliothèque `python-jose`).
- `CurrentUser` (modèle Pydantic), `get_current_user()` (dépendance
  FastAPI), `require_manager()` (vérification de rôle) — écrits pour un
  usage avec `Depends(get_current_user)` dans les signatures de route, à la
  place du couple actuel `get_user`/`require_admin`.

**Pour activer ce module** : remplacer, route par route, les dépendances
`get_user`/`auth_deps.require_admin` par `security.get_current_user` (et
adapter la vérification de rôle), puis mettre en place un vrai mécanisme
d'émission de token (actuellement absent — `POST /auth/login` renvoie un
`UserOut`, pas un token).

### 5.7 `routers/` — détail par fichier

Chaque fichier est un `APIRouter` monté dans `main.py`. Toutes les requêtes
Cypher sont paramétrées.

#### `routers/auth.py` — préfixe `/auth`

| Méthode | Route | Comportement |
|---|---|---|
| `POST` | `/auth/login` | Valide le format de l'email (`validate_capgemini_email`), cherche un `User` avec cet email, ce mot de passe **exact** (comparaison en clair) et `active: true`. Retourne `{email, role, active}` ou `401`. |

#### `routers/users.py` — préfixe `/users`, tout réservé `ADMIN`

| Méthode | Route | Comportement |
|---|---|---|
| `GET` | `/users` | Liste tous les comptes. |
| `POST` | `/users` | Crée un compte (email validé, mot de passe obligatoire, rejette les doublons avec `409`). |
| `PUT` | `/users/{email}/role` | Change le rôle ; refuse (`409`) si cela reviendrait à rétrograder le dernier admin actif. |
| `DELETE` | `/users/{email}` | Supprime le compte ; même protection du dernier admin. |

#### `routers/personnes.py` — préfixe `/personnes` (le plus volumineux, ~370 lignes)

| Méthode | Route | Comportement |
|---|---|---|
| `GET` | `/personnes` | Liste tous les noms de `Personne`. |
| `POST` | `/personnes` | Crée un `AuditEvent PERSON_CREATE` (`PROPOSED`) — ne crée **pas** directement la `Personne` (voir §10, limite connue). |
| `POST` | `/personnes/{nom}/competences/demandes` | Crée un `AuditEvent COMPETENCE_REQUEST` (`PROPOSED`) ; fonctionne même si la `Personne` n'existe pas encore ; crée/relie au besoin le `Contexte`, `Techno` (doit déjà exister), `Domaine`, `Version` (`MERGE`, création si absents). |
| `POST` | `/personnes/{nom}/suppression` | Crée un `AuditEvent PERSON_DELETE` (`PROPOSED`) — demande de suppression soumise à validation. |
| `DELETE` | `/personnes/{nom}` | Suppression **immédiate** et définitive (`DETACH DELETE`), hors workflow. |
| `GET` | `/personnes/{nom}/competences` | Compétences réelles (validées) d'une personne, filtrables par techno/domaine/version. |
| `PUT` | `/personnes/{nom}/competences` | Upsert **direct** d'une compétence (hors workflow, voir §4.4). |
| `DELETE` | `/personnes/{nom}/competences` | Supprime la relation `COMPETENCE` immédiatement ; trace un `AuditEvent COMPETENCE_DELETE` avec `status: "REJECTED"` d'emblée (pas de validation à faire, juste une trace). |
| `GET` | `/personnes/{nom}/demandes` | Liste les `COMPETENCE_REQUEST` en attente (`PROPOSED`) pour cette personne. |

#### `routers/ref.py` — préfixe `/ref`

| Méthode | Route | Comportement |
|---|---|---|
| `GET` | `/ref/technos` | Liste les `Techno`, filtrable par `category`. |
| `POST` | `/ref/technos` | Crée un `AuditEvent TECHNO_CREATE` (`PROPOSED`) — passe par validation. |
| `GET` / `POST` | `/ref/domaines` | `GET` liste ; **`POST` crée directement** (`MERGE`), hors workflow — pas d'UI dédiée, voir §9.1. |
| `GET` / `POST` | `/ref/versions` | Idem `domaines`. |
| `GET` | `/ref/niveaux` | Retourne la constante `[1, 2, 3]` (pas de lecture en base). |
| `GET` | `/ref/techno-categories` | Liste les `TechnoCategory`. |

#### `routers/contextes.py` — préfixe `/contextes`

| Méthode | Route | Comportement |
|---|---|---|
| `POST` | `/contextes` | Crée/récupère un `Contexte` à partir d'un triplet techno/domaine/version déjà existants (`404` sinon). |
| `GET` | `/contextes` | Liste les contextes, filtrable par catégorie/techno/domaine/version. |
| `DELETE` | `/contextes/{cle}` | Supprime un contexte **uniquement** s'il n'est référencé par aucune relation `COMPETENCE` (sinon `409`). |

#### `routers/competences.py` — préfixe `/competences`

| Méthode | Route | Comportement |
|---|---|---|
| `GET` | `/competences/contexte` | Vue « qui a quoi » : toutes les compétences (personne, techno, catégorie, domaine, version, niveau...) filtrables — alimente notamment la page Recherche. |

#### `routers/historique.py` — préfixe `/historique` (cœur du workflow)

| Méthode | Route | Comportement |
|---|---|---|
| `GET` | `/historique` | Liste les `AuditEvent`, filtrable par personne/techno/statut/type/période (`from`/`to`), triés par date décroissante, limité (`limit`, max 500). |
| `PUT` | `/historique/{event_id}/decision` | Applique une décision `VALIDATED`/`REJECTED` — voir §4 pour le détail complet. |

#### `routers/graph.py` (pas de préfixe)

| Méthode | Route | Comportement |
|---|---|---|
| `GET` | `/graph?personne=...` | Construit un objet `{nodes, edges}` au format attendu par la librairie `vis-network`, à partir des compétences réelles de la personne — utilisé par `profils.html`. |

#### `routers/questionnaire.py` (pas de préfixe)

| Méthode | Route | Comportement |
|---|---|---|
| `POST` | `/questionnaire` | Crée un seul `AuditEvent QUESTIONNAIRE_REQUEST` (`PROPOSED`) contenant toutes les compétences soumises, sérialisées en JSON dans `data`. |

---

## 6. Frontend — détail fichier par fichier

Tous les fichiers sont dans `frontend/`, servis tels quels par Nginx (voir
§7.2). Chaque page protégée (tout sauf `login.html`) inclut `common.js`
avant son propre `<script>` :

```html
<script src="common.js"></script>
<script>
  // logique spécifique à la page — currentUser, currentRole
  // et API_BASE_URL sont déjà disponibles globalement grâce à common.js
</script>
```

### 6.1 `common.js`

Chargé par toutes les pages sauf `login.html`. Responsabilités :
- Calcule `API_BASE_URL` (voir §1.1 pour la logique exacte).
- Lit `sessionStorage.currentUser` / `currentRole` ; si absent, redirige
  immédiatement vers `login.html` (**garde de connexion** — c'est la seule
  protection côté frontend, purement cosmétique : la vraie protection est
  faite côté API par `auth_deps.py`, voir §8).
- Affiche le badge utilisateur (`#user-badge`) si l'élément existe dans la
  page.
- Masque tous les éléments de classe CSS `.admin-only` si `currentRole !==
  "ADMIN"`.
- Définit trois fonctions globales `showAlert()`, `showConfirm()`,
  `showPrompt()` qui remplacent les `alert()`/`confirm()`/`prompt()`
  natifs du navigateur par des boîtes de dialogue stylées cohérentes avec
  `style.css` (implémentées comme des `Promise`, avec la même sémantique
  d'usage que leurs équivalents natifs). **Toute nouvelle page doit utiliser
  ces fonctions plutôt que les natives**, pour rester cohérente
  visuellement avec le reste de l'application.

### 6.2 `style.css`

Feuille de style unique (environ 1000 lignes) partagée par toutes les
pages. Définit notamment les classes utilisées par les dialogues de
`common.js` (`.modal-backdrop`, `.dialog-box`, `.dialog-title`,
`.dialog-message`, `.dialog-actions`), les boutons (`.btn`,
`.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`), les cartes
(`.card`), et la mise en page générale (`header`, `nav`, `main`, `footer`,
`.topbar`, `.user-area`, `.pill`). **Toute nouvelle page doit réutiliser
ces classes existantes** plutôt que d'introduire des styles ad hoc, pour
garder une interface cohérente.

### 6.3 Pages HTML

| Fichier | Rôle | Endpoints API appelés |
|---|---|---|
| `login.html` | Connexion (email + mot de passe). Ne charge **pas** `common.js` (logique de session dupliquée localement puisque cette page précède justement l'existence d'une session). | `POST /auth/login` |
| `index.html` | Accueil, liens d'accès rapide vers les pages principales. | *(aucun)* |
| `profils.html` | Sélection d'une personne, tableau de ses compétences, visualisation graphe (`vis-network`), demandes de modification/suppression de compétence. | `GET /personnes`, `GET /personnes/{nom}`, `GET /personnes/{nom}/competences`, `POST /personnes/{nom}/competences/demandes`, `GET /graph` |
| `recherche.html` | Recherche multicritère de profils. | `GET /ref/techno-categories`, `GET /ref/domaines`, `GET /ref/versions`, `GET /ref/technos`, `GET /competences/contexte` |
| `gestion.html` | Création de personnes, création de technologies (demandes), soumission de demandes de compétence. | `GET`/`POST /personnes`, `GET /ref/techno-categories`, `GET /ref/domaines`, `GET /ref/versions`, `POST /ref/technos`, `POST /personnes/{nom}/competences/demandes` |
| `questionnaire.html` | Auto-déclaration groupée de compétences. | `GET /personnes`, `POST /questionnaire` |
| `validation.html` | Liste des demandes en attente, actions Valider/Rejeter. **Réservée ADMIN** (masquée dans la nav, mais voir §8 pour la vraie protection). | `GET /historique`, `PUT /historique/{id}/decision` |
| `utilisateurs.html` | CRUD des comptes utilisateurs. **Réservée ADMIN.** | `GET`/`POST /users`, `PUT /users/{email}/role`, `DELETE /users/{email}` |
| `synthese.html` | Vue de couverture d'équipe par techno/contexte. | `GET /ref/techno-categories`, `GET /ref/domaines`, `GET /contextes`, `GET /competences/contexte`, `GET /ref/technos` |
| `historique.html` | Historique filtrable des événements. | `GET /personnes`, `GET /ref/technos`, `GET /historique` |

**Pour ajouter une nouvelle page** : dupliquer la structure d'une page
existante proche du besoin (header + `<nav>` avec les mêmes liens + `<main>`
+ inclusion de `common.js`), ajouter le lien correspondant dans la balise
`<nav>` de **toutes** les pages existantes (il n'y a pas de composant de
navigation partagé — chaque page a sa propre copie du `<nav>`, à répliquer
manuellement), et ajouter la classe `admin-only` sur le lien si la page
doit être réservée aux administrateurs (en gardant à l'esprit que cela ne
protège que l'affichage, pas l'accès réel — voir §8).

---

## 7. Infrastructure Docker — détail fichier par fichier

### 7.1 `docker-compose.yml` (racine)

Définit les 4 services, un réseau bridge unique `app-network`, et deux
volumes nommés `neo4j_data`/`neo4j_logs` (persistance des données et logs
Neo4j, indépendante du cycle de vie des conteneurs).

Ordre de démarrage garanti par les `healthcheck` + `depends_on: condition:
service_healthy` : `neo4j` → `backend` → `frontend` (`service_started`
seulement) → `proxy`.

Variables d'environnement injectées dans les conteneurs (voir le guide
d'installation, section 4, pour le détail de chacune) : `NEO4J_USER`,
`NEO4J_PASSWORD`, `CORS_ORIGINS`, `DEV_AUTH` (service `backend`) ; `NEO4J_AUTH`
(dérivé de `NEO4J_USER`/`NEO4J_PASSWORD`, service `neo4j`).

Ports publiés vers l'hôte : `80` (`proxy`), `8000` (`backend`), `7474` et
`7687` (`neo4j`). Le service `frontend` ne publie **aucun** port : il n'est
joignable que depuis les autres conteneurs du réseau `app-network` (par le
`proxy`), jamais directement depuis l'hôte.

### 7.2 `backend/Dockerfile`

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Image minimale (`slim`), dépendances installées avant la copie du code
(profite du cache Docker : tant que `requirements.txt` ne change pas, la
couche d'installation des dépendances n'est pas reconstruite lors d'un
changement de code applicatif seul). Pas de rechargement à chaud
(`--reload`) : tout changement de code nécessite un rebuild/redémarrage du
conteneur (`docker compose up -d --build backend`).

### 7.3 `frontend/Dockerfile` + `frontend/default.conf`

```dockerfile
FROM nginx:1.27-alpine
COPY . /usr/share/nginx/html
COPY default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Copie l'intégralité du dossier `frontend/` (HTML/CSS/JS) tel quel dans la
racine web de Nginx. La configuration `default.conf` sert les fichiers
statiques (`try_files $uri $uri/ /index.html`) et proxifie `/api/` vers
`http://backend:8000/` — cette dernière règle n'est en pratique pas
sollicitée en développement local (le frontend appelle directement le port
`8000`, voir §1.1) mais reste cohérente avec le comportement de production.

### 7.4 `proxy/Dockerfile` + `proxy/nginx.conf`

```dockerfile
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

`proxy/nginx.conf` route `/api/` vers `http://backend:8000/` et tout le
reste (`/`) vers `http://frontend:80/`, en propageant les en-têtes
`Host`, `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` — **c'est le
seul service exposé publiquement en usage serveur cible** (port 80).

### 7.5 Scripts (`scripts/`)

- `init_server.sh` : copie `.env.example` vers `.env` s'il n'existe pas
  encore, puis lance `docker compose up --build -d`. Pensé pour un premier
  déploiement serveur (voir le guide d'installation, section 9.6).
- `backup_neo4j.sh` / `restore_neo4j.sh` : encapsulent `neo4j-admin
  database dump`/`load` via `docker exec`/`docker cp` sur le conteneur
  `cartographie-neo4j` (nom fixé par `container_name` dans
  `docker-compose.yml` — si ce nom est modifié, ces scripts doivent être
  mis à jour en conséquence). Détail complet dans le guide d'utilisation et
  d'administration, section D.

---

## 8. Authentification et autorisation en détail

### 8.1 Flux actuel

1. `login.html` envoie `POST /auth/login` avec `{email, password}`.
2. `auth.py::login` vérifie qu'un `User` avec cet email, ce mot de passe
   **exact** (comparaison de chaîne en clair) et `active: true` existe.
3. Si oui, le frontend stocke `sessionStorage.currentUser = email` et
   `sessionStorage.currentRole = role` — **c'est toute la « session »**, il
   n'y a ni cookie, ni token, ni expiration côté serveur.
4. Chaque appel API ultérieur envoie l'email dans un header HTTP
   **`X-User`** (voir le code de chaque page, ex. `headers: {"X-User":
   currentUser}` dans les appels `fetch`).
5. Côté backend, deux niveaux de vérification possibles selon la route :
   - `utils.get_user` : exige juste la **présence** du header (pas de
     vérification que l'utilisateur existe réellement) — utilisé quand
     seule la traçabilité (`auteur`) importe.
   - `auth_deps.get_current_user_record` / `auth_deps.require_admin` :
     vérifient que l'email correspond à un compte **actif** en base, et,
     pour `require_admin`, que son rôle est `ADMIN`.

### 8.2 Limites connues (acceptées pour ce contexte d'usage interne)

- Le header `X-User` **n'est pas signé** : le backend fait confiance à la
  valeur envoyée par le client, sans preuve cryptographique d'identité. Un
  utilisateur techniquement outillé pourrait théoriquement forger ce header
  pour usurper une autre identité.
- Les mots de passe sont stockés **en clair** dans Neo4j (pas de hachage).
- Le masquage des liens `.admin-only` côté frontend (`common.js`) est une
  simple aide visuelle : la vraie protection contre un accès non autorisé
  est faite **côté API**, par `auth_deps.require_admin` sur chaque route
  sensible — c'est cette protection côté serveur qui fait foi.

Ces choix sont **assumés** pour un usage strictement interne à une équipe
de confiance, et documentés comme tels dès l'origine du projet.

### 8.3 Piste d'évolution déjà préparée

`backend/security.py` contient un scaffolding JWT complet (voir §5.6),
prêt à être branché si le besoin de renforcer l'authentification apparaît
(ouverture au-delà de l'équipe interne, exigence de sécurité accrue). Voir
le §5.6 pour la marche à suivre.

---

## 9. Cookbook — comment réaliser les évolutions les plus courantes

### 9.1 Ajouter une page frontend permettant de créer un Domaine/une Version

Actuellement, seule l'API permet de créer un `Domaine` ou une `Version`
(`POST /ref/domaines`, `POST /ref/versions` dans `backend/routers/ref.py`
— routes déjà existantes et fonctionnelles, simplement non exposées dans
l'interface). Pour combler ce manque :
1. Dans `frontend/gestion.html`, ajouter un formulaire similaire à celui
   des technologies (voir le bloc JS autour de `API_BASE_URL}/ref/technos`
   dans ce fichier).
2. Appeler `POST /ref/domaines` (ou `/versions`) avec `{"nom": "..."}`.
3. Rafraîchir les listes déroulantes concernées après création (mêmes
   fonctions `fetchJson`/`fill` déjà utilisées dans le fichier pour les
   listes existantes).

### 9.2 Ajouter un nouveau champ à une compétence

1. Ajouter le champ dans `backend/models.py`, classes `CompetenceUpsert`,
   `CompetenceOut`, `CompetenceRequest` (et `DecisionPayload`/`AuditEvent`
   si le champ doit transiter par le workflow de validation).
2. Adapter les requêtes Cypher concernées dans `backend/routers/
   personnes.py` (`upsert_person_competence`, `create_competence_request`,
   `get_person_competences`) pour lire/écrire ce nouveau champ sur la
   relation `COMPETENCE`.
3. Si le champ doit apparaître dans le workflow de validation, adapter le
   bloc `FOREACH` de `backend/routers/historique.py` (voir §4.2) pour
   propager `a.after_<champ>` vers `r2.<champ>`.
4. Adapter les formulaires et l'affichage dans `frontend/profils.html`,
   `frontend/gestion.html`, `frontend/questionnaire.html` selon les pages
   concernées.

### 9.3 Ajouter un nouveau rôle (au-delà de `ADMIN`/`USER`)

1. `backend/models.py` : étendre les `Literal["ADMIN", "USER"]` de
   `UserCreate.role` et `UserRoleUpdate.role`.
2. `backend/auth_deps.py` : ajouter une nouvelle fonction de garde
   (`require_xxx`) sur le modèle de `require_admin`, ou adapter
   `require_admin` si le nouveau rôle doit hériter des mêmes droits.
3. Appliquer cette garde sur les routes concernées (voir §5.5 pour le
   pattern).
4. `frontend/common.js` : adapter la condition `currentRole !== "ADMIN"`
   qui pilote le masquage `.admin-only` si le nouveau rôle doit voir
   d'autres pages que `USER` mais pas toutes celles d'`ADMIN`.

### 9.4 Changer l'échelle des niveaux de compétence (actuellement 1 à 3)

1. `backend/models.py` : modifier `NiveauType = conint(ge=1, le=3)`.
2. `backend/routers/ref.py`, route `GET /ref/niveaux` : adapter la liste
   codée en dur `[1, 2, 3]`.
3. Vérifier tout affichage codé en dur de « niveau 1 à 3 » côté frontend
   (formulaires de sélection dans `gestion.html`, `questionnaire.html`,
   `profils.html`).

### 9.5 Ajouter un nouveau type d'`AuditEvent`

Voir §4.2 — ajouter un bloc `FOREACH (_ IN CASE WHEN a.type = "MON_TYPE"
THEN [1] ELSE [] END | ...)` dans `historique.py::decide_competence_request`,
et créer la route qui génère ce nouvel `AuditEvent` avec `status:
"PROPOSED"` (suivre le pattern de `personnes.py::create_person_delete_request`
comme modèle le plus simple).

---

## 10. Limites connues et dette technique

Cette section recense honnêtement les points connus, pour éviter que de
futures évolutions ne les redécouvrent par surprise :

- **`PERSON_CREATE` sans effet câblé à la validation** : contrairement aux
  autres types d'`AuditEvent`, `historique.py` ne contient pas de bloc
  `FOREACH` dédié à `PERSON_CREATE` — or `personnes.py::create_personne`
  crée bien un `AuditEvent PERSON_CREATE`. En pratique, la ligne `MERGE
  (p:Personne {nom: a.personne})` présente en tête du bloc Cypher partagé
  (§4.2) s'exécute pour **tous** les types d'event (elle n'est pas dans un
  `FOREACH` conditionné), ce qui crée effectivement la personne au passage
  — mais ce comportement n'est pas explicite dans le code et mérite d'être
  vérifié avant toute modification de ce bloc.
- **Pas de type `TECHNO_DELETE`/`DOMAINE_DELETE`/`VERSION_DELETE`** : ces
  entités référentielles ne peuvent pas être supprimées via le workflow
  (seul `DELETE /contextes/{cle}` existe, avec sa propre logique). Un
  nettoyage du référentiel nécessite une intervention directe en base
  (Neo4j Browser).
- **Deux routes mutent directement le graphe hors workflow**
  (`PUT /personnes/{nom}/competences`, `DELETE /personnes/{nom}`) — voir
  §4.4.
- **Pas de page pour créer `Domaine`/`Version`** — voir §9.1.
- **Authentification simplifiée** (header non signé, mots de passe en
  clair) — voir §8.2, choix assumé pour ce contexte, avec une piste
  d'évolution déjà préparée (§8.3).
- **Aucun test automatisé, aucune CI/CD** — toute modification doit être
  vérifiée manuellement (voir §1.4).
- **Fichiers dupliqués dans le dépôt**, sans impact fonctionnel mais à
  connaître pour éviter de modifier la mauvaise copie : `frontend/
  default.conf` et une éventuelle copie `nginx.conf` du même dossier
  peuvent coexister avec un contenu identique ; vérifier laquelle est
  réellement référencée par `frontend/Dockerfile` (`default.conf`) avant
  toute modification de la configuration Nginx du frontend.
- **`backend/security.py` non branché** — voir §5.6 et §8.3.
