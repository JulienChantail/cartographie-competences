# Cartographie des compétences DBA

Application web interne permettant à une équipe DBA de cartographier les
compétences de ses membres : suivi des compétences par personne (technologie
/ domaine / version / niveau), recherche de profils, workflow de demande et
de validation des changements, historique des décisions, questionnaire
d'auto-évaluation et synthèse de la couverture d'équipe.

## Fonctionnalités principales

- **Gestion des profils** : création de personnes, consultation de leurs compétences, visualisation en graphe.
- **Recherche de profils** par critères (technologie, domaine, version, niveau).
- **Workflow de demande / validation** : toute création ou modification de compétence passe par une demande (`AuditEvent`) qu'un administrateur valide ou rejette avant qu'elle ne s'applique réellement dans la base.
- **Questionnaire d'auto-évaluation** : une personne déclare plusieurs compétences en une seule fois.
- **Historique** complet des demandes et décisions, filtrable.
- **Synthèse d'équipe** : vue de couverture des compétences.
- **Gestion des utilisateurs et des rôles** (`ADMIN` / `USER`), avec protection du dernier compte administrateur.

## Stack technique

| Composant           | Technologie                                     |
|----------------------|--------------------------------------------------|
| Backend              | Python 3.12 / FastAPI 0.115                        |
| Base de données      | Neo4j 2026.03 (base de graphe)                       |
| Driver Neo4j         | `neo4j` 5.24 (protocole Bolt)                          |
| Frontend             | HTML / CSS / JavaScript natif (aucun framework, aucun build) |
| Reverse proxy        | Nginx (point d'entrée unique, port 80)                   |
| Conteneurisation     | Docker / Docker Compose (4 services)                       |

Aucune base de données relationnelle, aucun framework JS (React/Vue/Angular),
aucun système de build (npm/webpack) : le frontend est constitué de pages
HTML statiques servies telles quelles.

## Démarrage rapide (poste de développement)

Prérequis : Docker Desktop installé et démarré (voir le guide d'installation
pour le détail complet, notamment sous Windows/WSL2).

```powershell
docker compose up --build -d
```

Puis ouvrir **http://localhost** dans le navigateur.

Pour une installation complète depuis un poste totalement vierge (y compris
la création du tout premier compte administrateur et le peuplement des
données de référence), et pour la mise en production sur un serveur, suivre
impérativement le [guide d'installation](docs/GUIDE_INSTALLATION.md) — le
simple `docker compose up` ci-dessus ne suffit pas à obtenir une application
utilisable sur une base Neo4j vide.

## Documentation

Toute la documentation du projet est centralisée dans le dossier
[`docs/`](docs/), en trois guides complémentaires :

| Guide | Contenu | Public |
|---|---|---|
| [Guide d'installation](docs/GUIDE_INSTALLATION.md) | Installer et configurer l'application de zéro sur un poste de développement, puis la déployer sur un serveur de production. | Toute personne devant (re)monter l'environnement. |
| [Guide d'utilisation et d'administration](docs/GUIDE_UTILISATION_ADMINISTRATION.md) | Fonctionnement de l'application au quotidien, administration (utilisateurs, validations, sauvegardes), gestion des images Docker et procédures de mise à jour (dont Neo4j). | Utilisateurs finaux et administrateurs applicatifs/serveur. |
| [Guide d'architecture](docs/GUIDE_ARCHITECTURE.md) | Architecture globale puis détail fichier par fichier du code (backend et frontend), pour savoir où et comment intervenir lors d'une évolution. | Développeurs amenés à faire évoluer le code. |

## Structure du dépôt

```
Projet_cartographie_competences/
├── README.md                 # ce fichier
├── docker-compose.yml         # orchestration des 4 services (neo4j, backend, frontend, proxy)
├── .env.example                # modèle des variables d'environnement (à copier en .env)
│
├── backend/                    # API FastAPI (Python)
│   ├── main.py                   # point d'entrée : CORS, cycle de vie, montage des routes
│   ├── database.py                # connexion Neo4j, fonctions run_read / run_write
│   ├── models.py                   # schémas de données (Pydantic)
│   ├── utils.py                     # fonctions transverses (validation email, etc.)
│   ├── auth_deps.py                  # vérification d'identité et de rôle
│   ├── security.py                    # scaffolding JWT (préparé, non branché)
│   ├── requirements.txt                # dépendances Python
│   ├── Dockerfile                       # image Docker du backend
│   └── routers/                          # une route FastAPI par domaine métier
│
├── frontend/                   # pages HTML statiques + JS partagé
│   ├── *.html                    # une page par fonctionnalité
│   ├── common.js                   # session, garde de connexion, dialogues
│   ├── style.css                     # feuille de style unique
│   └── Dockerfile                      # image Docker (Nginx statique)
│
├── proxy/                      # reverse proxy Nginx, point d'entrée unique (port 80)
│   ├── nginx.conf
│   └── Dockerfile
│
├── scripts/                    # scripts d'exploitation
│   ├── init_server.sh             # bootstrap d'un serveur (copie .env + démarrage)
│   ├── backup_neo4j.sh             # sauvegarde de la base Neo4j
│   └── restore_neo4j.sh             # restauration d'une sauvegarde
│
└── docs/                       # documentation (les 3 guides listés ci-dessus)
```

Le détail complet et commenté de chaque fichier est dans le
[guide d'architecture](docs/GUIDE_ARCHITECTURE.md).

## Statut sécurité

Application à **usage interne exclusivement** (pas d'exposition à des
utilisateurs externes) :

- Le contrôle d'accès repose sur un header `X-User` transmis par le
  frontend, non signé cryptographiquement.
- Les mots de passe sont stockés **en clair** dans Neo4j.
- Un scaffolding JWT existe (`backend/security.py`) mais n'est pas branché
  dans l'application ; il est prêt à être activé si le besoin de renforcer
  l'authentification apparaît.

Ces choix sont assumés pour ce contexte d'usage restreint. Le détail complet
des limites et de la piste d'évolution est décrit dans le
[guide d'architecture](docs/GUIDE_ARCHITECTURE.md#8-authentification-et-autorisation-en-détail).
