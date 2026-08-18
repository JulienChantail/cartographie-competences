# Guide d'utilisation et d'administration

Ce document couvre deux publics :

- **Partie A** — les utilisateurs de l'application (équipe DBA) : comment
  s'en servir au quotidien.
- **Parties B à H** — les administrateurs applicatifs et/ou serveur :
  comment administrer les comptes, sauvegarder/restaurer les données,
  gérer les images Docker et réaliser les mises à jour (dont Neo4j) en
  gardant l'environnement fonctionnel.

Pour l'installation initiale, voir le
[guide d'installation](GUIDE_INSTALLATION.md). Pour le détail technique du
code, voir le [guide d'architecture](GUIDE_ARCHITECTURE.md).

Sommaire :

- [A. Utilisation de l'application](#a-utilisation-de-lapplication)
  - [A.1 Connexion](#a1-connexion)
  - [A.2 Pages disponibles](#a2-pages-disponibles)
  - [A.3 Le workflow demande / validation](#a3-le-workflow-demande--validation)
  - [A.4 Bon à savoir](#a4-bon-à-savoir)
- [B. Administration des comptes et des données](#b-administration-des-comptes-et-des-données)
- [C. Supervision et vérifications de bon fonctionnement](#c-supervision-et-vérifications-de-bon-fonctionnement)
- [D. Sauvegarde et restauration de la base Neo4j](#d-sauvegarde-et-restauration-de-la-base-neo4j)
- [E. Gestion des images et conteneurs Docker](#e-gestion-des-images-et-conteneurs-docker)
- [F. Procédures de mise à jour](#f-procédures-de-mise-à-jour)
- [G. Maintenance courante](#g-maintenance-courante)
- [H. Incidents et dépannage administrateur](#h-incidents-et-dépannage-administrateur)

---

## A. Utilisation de l'application

### A.1 Connexion

Ouvrir l'application (`http://localhost` en local, ou l'URL du serveur en
production, ex. `http://cartographie-dba`) puis se connecter avec :

- **Email** au format `prenom.nom@capgemini.com`
- **Mot de passe** fourni par un administrateur

Une fois connecté, le nom et le rôle (`ADMIN` ou `USER`) apparaissent en
haut à droite. Deux actions y sont toujours disponibles :

- **Changer d'utilisateur** : revient à l'écran de connexion.
- **Déconnexion** : ferme la session en cours (la session est stockée dans
  le navigateur — `sessionStorage` — et disparaît à la fermeture de
  l'onglet).

Les rôles conditionnent l'accès à certaines pages : les liens marqués comme
réservés aux administrateurs sont automatiquement masqués pour les comptes
`USER` (mais voir l'encart de sécurité en fin de section B — ce masquage
est côté affichage uniquement, la protection réelle est faite côté API).

### A.2 Pages disponibles

| Page | Rôle |
|---|---|
| **Accueil** | Point d'entrée avec accès rapide aux pages principales. |
| **Profils** | Consulter les compétences d'une personne : sélectionner un nom pour afficher son tableau de compétences (techno / domaine / version / niveau) et une visualisation graphique. Permet aussi de **demander** une modification ou une suppression de compétence existante — la demande part en attente de validation, elle n'est pas appliquée immédiatement. |
| **Recherche** | Trouver les profils correspondant à des critères donnés (technologie, domaine, version...) — utile pour identifier rapidement qui maîtrise quoi. |
| **Gestion** | Trois actions : ajouter une personne (demande de création), ajouter une nouvelle technologie au référentiel (catégorie + type + nom, demande de création), soumettre une demande de compétence pour une personne existante. |
| **Questionnaire** | Auto-déclaration groupée : une personne renseigne plusieurs compétences en une fois, soumises en un seul lot à validation. |
| **Validation** *(réservé ADMIN)* | Liste des demandes en attente. Pour chacune : **Valider** (applique le changement dans le graphe) ou **Rejeter** (aucun impact, juste tracé dans l'historique), avec un commentaire optionnel. |
| **Utilisateurs** *(réservé ADMIN)* | Gestion des comptes : création, changement de rôle (`ADMIN` ↔ `USER`), suppression. Le dernier compte `ADMIN` actif ne peut pas être rétrogradé ni supprimé. |
| **Synthèse** | Vue d'ensemble de la couverture de l'équipe : qui maîtrise quoi, utile pour identifier les zones de risque (compétence portée par une seule personne) ou de redondance. |
| **Historique** | Liste de tous les événements (créations, demandes, décisions), filtrable par personne, techno, statut, type et période. |

### A.3 Le workflow demande / validation

```
Utilisateur                          Administrateur
────────────                         ─────────────────
Soumet une demande       ──────▶     Consulte "Validation"
(Gestion / Profils /                 │
Questionnaire)                       ├─▶ Valide  → compétence mise à jour dans le graphe
                                      └─▶ Rejette → rien ne change dans le graphe
                                          (tracé dans "Historique" dans les deux cas)
```

**Exception** : la suppression d'une **personne** (bouton dédié, distinct
de la demande de suppression) et l'upsert direct d'une compétence via
certains flux d'administration s'appliquent **immédiatement**, sans passer
par ce circuit — voir le [guide d'architecture](GUIDE_ARCHITECTURE.md#4-le-workflow-de-demande--validation-en-détail)
pour le détail exact des routes concernées.

### A.4 Bon à savoir

- Un niveau de compétence va de **1** (notions) à **3** (expert).
- La version d'une technologie est optionnelle dans certains formulaires
  (valeur `N/A` si non renseignée).
- Toute demande reste visible dans l'historique, validée ou non — rien
  n'est jamais silencieusement perdu.

---

## B. Administration des comptes et des données

### B.1 Rôles

Deux rôles existent : `USER` et `ADMIN`. Seul un `ADMIN` peut : valider ou
rejeter des demandes, gérer les comptes utilisateurs. Un compte inactif
(`active: false`) ne peut plus se connecter mais son historique reste
conservé.

### B.2 Créer, modifier, désactiver un compte

Depuis la page **Utilisateurs** (réservée aux `ADMIN`) :
- **Créer** un compte : email au format `prenom.nom@capgemini.com` +
  mot de passe + rôle initial.
- **Changer le rôle** d'un compte existant (`ADMIN` ↔ `USER`).
- **Supprimer** un compte.

**Protection intégrée** : il est impossible de rétrograder ou de supprimer
le **dernier** compte `ADMIN` actif — l'application refuse l'opération
(erreur explicite) pour éviter de se retrouver sans aucun administrateur.
Pour retirer les droits d'un dernier admin, créer d'abord un second compte
`ADMIN`.

### B.3 Réinitialiser le mot de passe d'un compte (perte de mot de passe)

Il n'existe pas de fonction « mot de passe oublié » dans l'application.
Deux méthodes :

1. **Un autre administrateur recrée le mot de passe** : il n'y a pas de
   fonction dédiée « réinitialiser » dans l'interface — le plus simple est
   de le faire directement en base via Neo4j Browser (`http://<hôte>:7474`) :

   ```cypher
   MATCH (u:User {email: "prenom.nom@capgemini.com"})
   SET u.password = "NouveauMotDePasseTemporaire!"
   RETURN u;
   ```

   Communiquer ce mot de passe temporaire à la personne concernée par un
   canal sécurisé, en lui demandant de le considérer comme définitif (il
   n'existe pas de mécanisme de changement de mot de passe en libre-service
   dans l'interface actuelle — un administrateur doit repasser par cette
   procédure pour tout changement ultérieur).

2. Si **aucun** compte `ADMIN` n'est plus accessible (cas extrême), la
   même requête Cypher peut être exécutée directement sans passer par
   l'application, en se connectant à Neo4j Browser avec les identifiants
   `NEO4J_USER`/`NEO4J_PASSWORD` du fichier `.env` du serveur.

> Rappel : les mots de passe sont stockés **en clair** dans Neo4j (choix
> assumé pour ce contexte d'usage interne, voir le guide d'architecture).
> Traiter l'accès à Neo4j Browser et au fichier `.env` avec la même
> vigilance que des identifiants de production.

### B.4 Ajouter des données de référence (domaines, versions)

Comme détaillé dans le guide d'installation, il n'existe pas de page dans
l'interface pour créer un nouveau **Domaine** ou une nouvelle **Version** —
seules les technologies (`Techno`) sont créables via la page Gestion. Pour
ajouter un domaine ou une version après l'installation initiale, utiliser
l'API directement :

```powershell
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d "{\"nom\": \"Nouveau domaine\"}"
curl -X POST http://localhost:8000/ref/versions -H "Content-Type: application/json" -d "{\"nom\": \"Nouvelle version\"}"
```

*(Remplacer `localhost:8000` par l'URL réelle du backend si exécuté depuis
un poste distinct du serveur.)* Ces deux appels créent directement la
donnée en base, sans passer par le workflow de validation (comportement
volontaire de ces deux routes, voir le guide d'architecture).

---

## C. Supervision et vérifications de bon fonctionnement

### C.1 État des services

```bash
docker compose ps
```

Les 4 services doivent apparaître `Up`, avec `neo4j` et `backend` marqués
`(healthy)`.

### C.2 Santé applicative

```bash
curl http://localhost:8000/health
# -> {"ok":true,"neo4j_uri":"bolt://neo4j:7687"}
```

### C.3 Logs

```bash
docker compose logs -f              # tous les services, en continu
docker compose logs -f backend      # un seul service
docker compose logs --tail=200 neo4j  # les 200 dernières lignes, sans suivre
```

### C.4 Espace disque

Les données Neo4j grossissent avec le temps (volumes `neo4j_data` et
`neo4j_logs`). Vérifier périodiquement l'espace disque disponible sur le
serveur (`df -h`) et la taille des volumes Docker :

```bash
docker system df -v
```

---

## D. Sauvegarde et restauration de la base Neo4j

### D.1 Sauvegarde

Le script `scripts/backup_neo4j.sh` automatise une sauvegarde à froid via
`neo4j-admin database dump` :

```bash
./scripts/backup_neo4j.sh
```

Contenu du script, pour référence :

```bash
#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$(pwd)/backups"
mkdir -p "$BACKUP_DIR"

CONTAINER_NAME="cartographie-neo4j"
BACKUP_PATH="$BACKUP_DIR/neo4j_backup_${TIMESTAMP}"

mkdir -p "$BACKUP_PATH"

docker exec "$CONTAINER_NAME" sh -c 'mkdir -p /var/lib/neo4j/backups && /bin/neo4j-admin database dump --to=/var/lib/neo4j/backups/neo4j_backup'

docker cp "$CONTAINER_NAME:/var/lib/neo4j/backups/neo4j_backup" "$BACKUP_PATH"

echo "Sauvegarde créée dans $BACKUP_PATH"
```

Le résultat est déposé dans `./backups/neo4j_backup_<horodatage>/` (dossier
créé automatiquement à la racine du projet, au niveau où la commande est
lancée). **Ce script fonctionne base en ligne comme hors ligne** — `dump`
prend un instantané cohérent sans nécessiter l'arrêt du conteneur.

> Le dossier `backups/` n'est pas synchronisé ailleurs par défaut : pour une
> vraie stratégie de sauvegarde de production, copier régulièrement son
> contenu vers un stockage externe au serveur (autre machine, stockage
> réseau, solution de sauvegarde de l'entreprise).

**Planification automatique (recommandé en production)** : ajouter une
tâche `cron` sur le serveur pour exécuter la sauvegarde quotidiennement,
par exemple tous les jours à 2h du matin :

```bash
crontab -e
```

Ajouter la ligne (adapter le chemin absolu vers le projet) :

```
0 2 * * * cd /chemin/vers/Projet_cartographie_competences && ./scripts/backup_neo4j.sh >> /var/log/cartographie_backup.log 2>&1
```

Penser à purger périodiquement les sauvegardes trop anciennes dans
`backups/` pour éviter de saturer le disque.

### D.2 Restauration

```bash
./scripts/restore_neo4j.sh backups/neo4j_backup_YYYYMMDD_HHMMSS
```

Contenu du script, pour référence :

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_SOURCE=${1:-}
if [ -z "$BACKUP_SOURCE" ]; then
  echo "Usage: $0 <chemin_backup>"
  exit 1
fi

CONTAINER_NAME="cartographie-neo4j"

docker cp "$BACKUP_SOURCE" "$CONTAINER_NAME:/var/lib/neo4j/backups/"

docker exec "$CONTAINER_NAME" sh -c 'neo4j-admin database load --from=/var/lib/neo4j/backups/neo4j_backup --overwrite=true'

echo "Restauration lancée depuis $BACKUP_SOURCE"
```

**Important** : contrairement à la sauvegarde, `neo4j-admin database load
--overwrite=true` **remplace entièrement** la base courante par le contenu
du dump — toute donnée créée depuis la sauvegarde restaurée est perdue.
Toujours effectuer une sauvegarde de l'état courant (D.1) **avant** de
restaurer un ancien dump, au cas où la restauration devrait elle-même être
annulée.

Après une restauration, vérifier que l'application redevient cohérente :

```bash
docker compose restart backend
curl http://localhost:8000/health
```

---

## E. Gestion des images et conteneurs Docker

### E.1 Vue d'ensemble des images utilisées

| Service | Image / origine | Construite localement ? |
|---|---|---|
| `neo4j` | `neo4j:2026.03` (image officielle, Docker Hub) | Non — image téléchargée telle quelle |
| `backend` | Construite depuis `backend/Dockerfile` (base `python:3.12-slim`) | Oui |
| `frontend` | Construite depuis `frontend/Dockerfile` (base `nginx:1.27-alpine`) | Oui |
| `proxy` | Construite depuis `proxy/Dockerfile` (base `nginx:1.27-alpine`) | Oui |

### E.2 Commandes de référence

```bash
docker compose images               # images utilisées par chaque service, avec taille
docker images                       # toutes les images présentes sur la machine
docker compose build                # reconstruit les images backend/frontend/proxy sans redémarrer
docker compose build --no-cache backend   # reconstruction complète sans cache (en cas de doute sur le cache)
docker compose pull neo4j           # télécharge la dernière image correspondant au tag fixé dans docker-compose.yml
docker compose up -d                # (re)crée les conteneurs nécessaires, sans forcer un rebuild
docker compose up -d --build        # reconstruit puis (re)crée tous les conteneurs
docker compose up -d --build backend  # ne reconstruit/redémarre que le service backend
```

### E.3 Nettoyage

```bash
docker compose down                 # arrête et supprime les conteneurs (conserve les volumes nommés, donc les données Neo4j)
docker image prune -f               # supprime les images Docker devenues orphelines (ex. anciennes versions après rebuild)
docker system prune -f              # nettoyage plus large (conteneurs arrêtés, réseaux et images inutilisés — ne touche pas les volumes nommés utilisés)
```

`docker system prune` ne supprime **jamais** les volumes nommés (donc pas
les données Neo4j) sauf si l'option `--volumes` est explicitement ajoutée —
à ne surtout pas faire sans une sauvegarde préalable.

---

## F. Procédures de mise à jour

Principe général applicable à **toute** mise à jour (changement de version
d'une image, d'une dépendance Python, etc.) :

1. **Sauvegarder** la base Neo4j (section D.1) avant toute opération.
2. Faire la mise à jour sur un environnement de test si possible avant de
   la reproduire sur le serveur de production.
3. Mettre à jour **un service à la fois**, vérifier qu'il repasse
   `(healthy)` avant de passer au suivant.
4. Vérifier `docker compose logs` du service concerné après redémarrage.
5. Conserver le numéro de version précédent (tag d'image, ou commit Git)
   pour pouvoir revenir en arrière rapidement en cas de problème.

### F.1 Mettre à jour le backend (dépendances Python, code applicatif)

1. Mettre à jour les fichiers concernés (`backend/requirements.txt` pour
   une dépendance, code des `routers/` pour une évolution fonctionnelle —
   voir le guide d'architecture pour savoir où intervenir).
2. Reconstruire et redémarrer uniquement ce service :

   ```bash
   docker compose up -d --build backend
   ```

3. Vérifier :

   ```bash
   docker compose ps
   curl http://localhost:8000/health
   docker compose logs --tail=100 backend
   ```

4. En cas de problème, revenir au code précédent (`git checkout` sur le
   commit antérieur, ou restauration manuelle des fichiers) puis répéter
   l'étape 2.

### F.2 Mettre à jour le frontend ou le proxy (image Nginx de base)

Le tag de l'image de base (`nginx:1.27-alpine`) est fixé dans
`frontend/Dockerfile` et `proxy/Dockerfile`. Pour monter de version :

1. Modifier la ligne `FROM nginx:1.27-alpine` dans le(s) `Dockerfile`
   concerné(s) avec le nouveau tag souhaité (consulter les notes de version
   officielles de l'image `nginx` sur Docker Hub avant de monter une
   version majeure).
2. Reconstruire et redémarrer :

   ```bash
   docker compose up -d --build frontend
   docker compose up -d --build proxy
   ```

3. Vérifier que l'application reste accessible (`curl http://localhost/`)
   et que la navigation fonctionne dans le navigateur.

### F.3 Mettre à jour Neo4j — procédure complète

C'est la mise à jour la plus sensible du projet : Neo4j peut introduire des
changements de format de stockage ou de comportement entre versions
majeures, et une erreur peut rendre la base illisible. **Ne jamais sauter
cette procédure, même pour une mise à jour mineure.**

#### Étape 1 — Préparation

1. Identifier la version cible et **lire les notes de version officielles
   Neo4j** (guide de migration entre la version actuelle — `2026.03`, visible
   dans `docker-compose.yml` — et la version cible), en particulier toute
   mention de changement de format de stockage ou de procédures Cypher
   dépréciées/supprimées qui pourraient affecter les requêtes du backend
   (voir `backend/routers/` et `backend/database.py` dans le guide
   d'architecture pour la liste des requêtes Cypher utilisées par
   l'application).
2. **Sauvegarder** la base actuelle :

   ```bash
   ./scripts/backup_neo4j.sh
   ```

   Vérifier que le dossier `backups/neo4j_backup_<horodatage>/` a bien été
   créé et n'est pas vide.
3. Noter le tag d'image actuel (`neo4j:2026.03` dans `docker-compose.yml`)
   quelque part en dehors du projet (pour pouvoir revenir en arrière même
   si le fichier est déjà modifié).

#### Étape 2 — Test si possible

Si un environnement de test est disponible (même un simple clone du projet
sur un autre poste), y restaurer la sauvegarde de l'étape 1
(voir section D.2 du présent guide et section 8 du guide d'installation),
appliquer la procédure ci-dessous, et valider que l'application fonctionne
normalement avant de toucher à la production.

#### Étape 3 — Mise à jour de l'image

1. Modifier le tag de l'image dans `docker-compose.yml` :

   ```yaml
   services:
     neo4j:
       image: neo4j:2026.03   # ← remplacer par le tag cible
   ```

2. Télécharger la nouvelle image et redémarrer **uniquement** le service
   `neo4j` :

   ```bash
   docker compose pull neo4j
   docker compose up -d neo4j
   ```

3. Suivre les logs du démarrage — Neo4j peut effectuer une migration
   automatique du format de stockage au premier démarrage sur une nouvelle
   version majeure, ce qui peut prendre du temps selon la taille de la
   base :

   ```bash
   docker compose logs -f neo4j
   ```

   Attendre un message confirmant que la base est démarrée et prête
   (`Started.` dans les logs Neo4j), puis vérifier l'état de santé :

   ```bash
   docker compose ps
   ```

   `neo4j` doit repasser `(healthy)`.

#### Étape 4 — Vérification applicative

1. Vérifier que le backend, qui dépend de `neo4j` via `depends_on:
   condition: service_healthy`, redémarre proprement s'il a redémarré
   entretemps, ou qu'il reste connecté sinon :

   ```bash
   docker compose restart backend
   curl http://localhost:8000/health
   ```

2. Se connecter à l'application et vérifier manuellement quelques
   fonctionnalités clés : connexion, consultation d'un profil, page
   Synthèse, soumission puis validation d'une demande simple.
3. Vérifier l'absence d'erreurs inhabituelles dans les logs du backend :

   ```bash
   docker compose logs --tail=200 backend
   ```

#### Étape 5 — En cas de problème (retour arrière)

Si la nouvelle version pose problème (erreurs Cypher, service qui ne
démarre plus, données inaccessibles) :

1. Arrêter neo4j :

   ```bash
   docker compose stop neo4j
   ```

2. Revenir au tag d'image précédent dans `docker-compose.yml`.
3. Si le format de stockage a déjà été migré par la nouvelle version (ce
   qui peut le rendre incompatible avec l'ancienne image), **ne pas**
   redémarrer directement l'ancienne image sur le même volume : restaurer
   plutôt la sauvegarde de l'étape 1 sur un volume propre, en suivant la
   procédure de restauration à froid décrite dans le guide d'installation
   (section 8), avec l'ancien tag d'image.
4. Redémarrer et vérifier comme à l'étape 4.

> **Règle d'or** : une sauvegarde `neo4j-admin database dump` réalisée
> **avant** la mise à jour reste lisible par l'ancienne version de Neo4j
> qui l'a produite, même si la mise à jour a modifié le volume en place —
> c'est le filet de sécurité ultime de cette procédure. Ne jamais faire une
> mise à jour de Neo4j sans cette sauvegarde préalable.

### F.4 Mettre à jour Docker Compose / Docker Engine lui-même

Ces mises à jour se font au niveau du système d'exploitation du serveur
(gestionnaire de paquets, ou Docker Desktop côté poste de développement),
indépendamment du projet. Vérifier après mise à jour que :

```bash
docker compose version
docker compose ps
```

fonctionnent toujours normalement, et redémarrer la stack si nécessaire.

---

## G. Maintenance courante

```bash
docker compose restart               # redémarre tous les services
docker compose restart backend       # redémarre un seul service
docker compose logs -f               # consulter les logs en continu
docker system prune -f               # nettoyer les conteneurs arrêtés / images non utilisées (ne touche pas les volumes)
```

Vérification de routine recommandée (hebdomadaire en production) :

```bash
docker compose ps                    # tous les services Up et healthy
curl http://localhost:8000/health    # API opérationnelle
docker system df -v                  # espace disque utilisé par Docker
```

---

## H. Incidents et dépannage administrateur

| Symptôme | Cause probable | Action |
|---|---|---|
| Un service reste `unhealthy` après un redémarrage | Erreur de démarrage (config, dépendance, réseau) | `docker compose logs <service>` pour lire l'erreur exacte |
| L'application est inaccessible depuis les postes utilisateurs mais fonctionne en local sur le serveur | Pare-feu, DNS, ou port 80 non exposé | Vérifier la configuration réseau/pare-feu du serveur (section 9.7 du guide d'installation) |
| Un utilisateur a oublié son mot de passe | — | Voir section B.3 |
| Les listes déroulantes Domaine/Version sont vides après une réinstallation | Base neuve non peuplée | Voir section B.4 et section 6.3 du guide d'installation |
| Une demande validée n'apparaît pas dans le profil de la personne | Erreur applicative lors de la validation, ou personne mal orthographiée entre la demande et le référentiel | Consulter la page Historique pour retrouver l'événement, vérifier son détail ; en dernier recours, consulter les logs backend au moment de la validation |
| Espace disque saturé sur le serveur | Volumes Neo4j (données + logs) ou sauvegardes accumulées dans `backups/` | Purger les anciennes sauvegardes, vérifier `docker system df -v`, envisager l'archivage des logs Neo4j |
| Besoin de repartir d'un état antérieur suite à une mauvaise manipulation | — | Restaurer la dernière sauvegarde saine (section D.2), après avoir sauvegardé l'état courant par précaution |
| `docker compose up` échoue après modification de `docker-compose.yml` | Erreur de syntaxe YAML | `docker compose config` affiche la configuration résolue et signale les erreurs de syntaxe avant de tenter un démarrage |

Pour toute anomalie non couverte ici touchant au comportement du code
(pas à l'infrastructure), se référer au
[guide d'architecture](GUIDE_ARCHITECTURE.md) pour localiser le fichier
responsable de la fonctionnalité concernée.
