# Guide d'utilisation et d'administration

Ce document couvre deux publics :

- **Partie A** — les utilisateurs de l'application (équipe DBA) : comment
  s'en servir au quotidien.
- **Parties B à I** — les administrateurs applicatifs et/ou serveur :
  comment administrer les comptes, sauvegarder/restaurer les données,
  gérer les images Docker, réaliser les mises à jour (dont Neo4j) en
  gardant l'environnement fonctionnel, et localiser/explorer les données
  stockées.

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
- [I. Localisation et exploration des données](#i-localisation-et-exploration-des-données)
  - [I.1 Où sont physiquement stockées les données](#i1-où-sont-physiquement-stockées-les-données)
  - [I.2 Retrouver et inspecter le volume Docker](#i2-retrouver-et-inspecter-le-volume-docker)
  - [I.3 Se connecter à Neo4j depuis le serveur](#i3-se-connecter-à-neo4j-depuis-le-serveur)
  - [I.4 Exploration de la base Neo4j](#i4-exploration-de-la-base-neo4j)
  - [I.5 Où sont stockés les événements d'audit](#i5-où-sont-stockés-les-événements-daudit)
  - [I.6 Sauvegarder et vérifier qu'une sauvegarde est exploitable](#i6-sauvegarder-et-vérifier-quune-sauvegarde-est-exploitable)

---

## A. Utilisation de l'application

### A.1 Connexion

Ouvrir l'application (`http://localhost:8088` en local — port hôte
actuellement publié par le service `proxy`, à vérifier avec `docker compose
ps` en cas de doute —, ou l'URL du serveur en production, ex.
`http://cartographie-dba` ou `http://deserve.corp.capgemini.com/cartographie/`)
puis se connecter avec :

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

> **Mise à jour importante** : les scripts `backup_neo4j.sh` et
> `restore_neo4j.sh` utilisaient une syntaxe `neo4j-admin` obsolète
> (`--to=`/`--from=`/`--overwrite=`, héritée de Neo4j 4.x) qui **ne
> fonctionne plus du tout** sur la version `2026.03` réellement utilisée
> par ce projet (`neo4j-admin` refuse l'argument et affiche son aide). Les
> scripts ont été corrigés et **testés de bout en bout** (sauvegarde,
> restauration sur un volume neuf, relecture des données) — voir ci-dessous
> pour la procédure à jour.

### D.0 Ce qu'il faut savoir avant de sauvegarder

- L'image utilisée (`neo4j:2026.03`, voir `docker-compose.yml`) est
  l'**édition Community** de Neo4j. Contrairement à l'édition Enterprise,
  elle ne permet pas de sauvegarder une base **pendant qu'elle est montée
  dans un serveur Neo4j en cours d'exécution** (`neo4j-admin database dump`
  échoue avec `The database is in use` tant que le conteneur `neo4j`
  tourne, et les commandes Cypher `STOP DATABASE`/`START DATABASE` sont
  refusées en Community). **La sauvegarde comme la restauration
  nécessitent donc un arrêt bref du conteneur `neo4j`** (quelques secondes
  en pratique pour dumper les deux bases — mesuré sur une base de test :
  moins d'une seconde pour ~260 Mo de données). Les deux scripts
  automatisent cet arrêt/redémarrage.
- Les deux scripts sauvegardent/restaurent **deux bases Neo4j distinctes** :
  `neo4j` (toutes les données métier : `Personne`, `Techno`, `Contexte`,
  `AuditEvent`, `User`... — voir section I ci-dessous) et `system` (le
  catalogue interne de Neo4j : comptes/rôles Neo4j, registre des bases).
  Les deux sont utiles pour une reprise fidèle du serveur.

### D.1 Sauvegarde

```bash
./scripts/backup_neo4j.sh
```

Ce que fait le script (voir `scripts/backup_neo4j.sh` pour le détail
exact) :

1. Résout automatiquement le volume de données et l'image du conteneur
   `cartographie-neo4j` en cours d'exécution (`docker inspect`).
2. Arrête ce conteneur (`docker stop`).
3. Démarre un conteneur temporaire, basé sur la **même image** et monté sur
   le **même volume**, qui exécute `neo4j-admin database dump "*"
   --to-path=... --overwrite-destination=true` (le motif `"*"` dumpe en un
   seul appel toutes les bases présentes, ici `system` et `neo4j`).
4. Copie les fichiers `system.dump` et `neo4j.dump` produits vers
   `./backups/neo4j_backup_<horodatage>/` sur la machine hôte.
5. **Redémarre systématiquement `cartographie-neo4j`** à la fin, y compris
   si une étape a échoué en cours de route (`trap ... EXIT` dans le
   script) — la base ne reste jamais arrêtée par accident.

> Le dossier `backups/` n'est pas synchronisé ailleurs par défaut (et est
> exclu de Git via `.gitignore`) : pour une vraie stratégie de sauvegarde
> de production, copier régulièrement son contenu vers un stockage externe
> au serveur (autre machine, stockage réseau, solution de sauvegarde de
> l'entreprise).

**Planification automatique (recommandé en production)** : ajouter une
tâche `cron` sur le serveur pour exécuter la sauvegarde quotidiennement,
par exemple tous les jours à 2h du matin (heure creuse, compte tenu de la
brève coupure évoquée en D.0) :

```bash
crontab -e
```

Ajouter la ligne (adapter le chemin absolu vers le projet) :

```
0 2 * * * cd /opt/cartographie-competences && ./scripts/backup_neo4j.sh >> /var/log/cartographie_backup.log 2>&1
```

Penser à purger périodiquement les sauvegardes trop anciennes dans
`backups/` pour éviter de saturer le disque.

### D.2 Restauration

```bash
./scripts/restore_neo4j.sh backups/neo4j_backup_YYYYMMDD_HHMMSS
```

Le dossier passé en argument doit contenir `neo4j.dump` et/ou
`system.dump` (produits par D.1). Le script suit le même principe que la
sauvegarde : arrêt de `cartographie-neo4j`, restauration via un conteneur
temporaire sur le même volume (`neo4j-admin database load "*"
--from-path=... --overwrite-destination=true`), puis redémarrage
systématique du conteneur.

**Important** : `--overwrite-destination=true` **remplace entièrement** la
base courante par le contenu du dump — toute donnée créée depuis la
sauvegarde restaurée est perdue. Toujours effectuer une sauvegarde de
l'état courant (D.1) **avant** de restaurer un ancien dump, au cas où la
restauration devrait elle-même être annulée.

> Si le dump de la base `system` provient d'une **autre** installation
> Neo4j que celle sur laquelle il est rechargé (ex. copie d'un poste de
> développement vers un autre), `neo4j-admin` affiche un avertissement
> (« this system database dump may contain unwanted metadata for the DBMS
> it was taken from »). C'est attendu et sans conséquence pour un usage de
> ce projet (restauration d'une copie de la base de données métier à des
> fins de développement ou de reprise après incident sur le même serveur),
> mais à garder en tête avant de l'utiliser dans un autre contexte.

Après une restauration, vérifier que l'application redevient cohérente :

```bash
docker compose ps                    # cartographie-neo4j doit repasser (healthy)
curl http://localhost:8000/health
```

### D.3 Procédure validée (résumé du test effectué)

La procédure ci-dessus a été testée intégralement en conditions réelles :
sauvegarde d'une base peuplée (12 personnes, 34 technologies) avec
`backup_neo4j.sh`, restauration de ce dump sur un volume Docker neuf, puis
relecture des données (`MATCH (p:Personne) RETURN count(p)`) confirmant
que les 12 personnes et l'intégralité du référentiel étaient bien
présentes après restauration — avant application au conteneur réel de
travail, restauré avec succès également. C'est cette procédure, et non
l'ancienne syntaxe `--to=`/`--from=`, qui doit être suivie désormais.

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

> **Si l'application devient inaccessible via `proxy` après un rebuild**
> (page blanche, erreur 502/504, alors que `curl http://localhost:8000/health`
> direct au backend fonctionne) : redémarrer `proxy` — `docker compose
> restart proxy`. Nginx résout le nom `backend` (ou `frontend`) en adresse
> IP au démarrage et peut garder en cache une IP devenue obsolète après
> qu'un conteneur a été recréé (`up -d --build`change son IP interne). Ce
> problème de résolution DNS Docker a déjà été observé en exploitation —
> le réflexe `docker compose restart proxy` après un rebuild de `backend`
> ou `frontend` évite ce désagrément.

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

3. Vérifier que l'application reste accessible (`curl http://localhost:8088/`)
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

---

## I. Localisation et exploration des données

Objectif de cette section : qu'un nouvel administrateur comprenne en moins
de 10 minutes où sont les données, comment les consulter, comment les
sauvegarder et comment les restaurer — sans avoir à lire tout le reste du
guide.

### I.1 Où sont physiquement stockées les données

**Toutes** les données métier de l'application — profils (`Personne`),
compétences (`COMPETENCE`, `Contexte`), référentiel (`Techno`,
`TechnoCategory`, `Domaine`, `Version`), comptes (`User`) et historique des
demandes/décisions (`AuditEvent`) — sont stockées dans **une seule base
Neo4j** (label par label, voir I.4), elle-même stockée sur disque via un
**volume Docker nommé**, complètement indépendant du cycle de vie des
conteneurs (un `docker compose down` sans `-v`, ou un `docker compose up
-d --build`, ne touche jamais à ce volume).

Sur le serveur DESERVE :

| Élément | Valeur |
|---|---|
| Conteneur | `cartographie-neo4j` |
| Volume Docker | `cartographie-competences_neo4j_data` |
| Chemin réel sur le serveur (hors conteneur) | `/var/lib/docker/volumes/cartographie-competences_neo4j_data/_data` |
| Point de montage dans le conteneur | `/data` |

Le nom du volume est dérivé automatiquement par Docker Compose du nom du
dossier du projet sur le serveur (`/opt/cartographie-competences`, préfixe
`cartographie-competences` une fois les caractères non alphanumériques
normalisés) et du nom logique `neo4j_data` déclaré dans
`docker-compose.yml`. **Sur un autre poste** (ex. un poste de
développement où le dossier du projet ne s'appelle pas pareil), ce nom de
volume sera différent — voir I.2 pour le retrouver dans tous les cas.

Il existe un second volume, `..._neo4j_logs` (monté sur `/logs`), qui ne
contient que les journaux du serveur Neo4j — pas de données applicatives.

### I.2 Retrouver et inspecter le volume Docker

```bash
# État des 4 services (confirme que cartographie-neo4j tourne)
docker compose ps

# Détail du conteneur Neo4j : image, volumes montés, état de santé, réseau...
docker inspect cartographie-neo4j

# Lister tous les volumes Docker de la machine
docker volume ls

# Retrouver précisément le nom du volume de données monté sur /data
# (fonctionne quel que soit le nom réel du dossier du projet)
docker inspect cartographie-neo4j --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{"\n"}}{{end}}'

# Détail du volume : chemin réel sur disque (clé "Mountpoint"), date de création...
docker volume inspect cartographie-competences_neo4j_data
```

`docker volume inspect` renvoie notamment un champ `"Mountpoint"` — c'est
le chemin exact indiqué dans le tableau de I.1
(`/var/lib/docker/volumes/<nom_du_volume>/_data`). **Ne jamais modifier ces
fichiers directement** avec un éditeur de texte ou un outil autre que
Neo4j lui-même (risque de corruption de la base) : ce chemin sert
uniquement à la sauvegarde/restauration bas niveau (voir I.6) ou au
diagnostic (espace disque utilisé, présence des fichiers attendue...).

### I.3 Se connecter à Neo4j depuis le serveur

Deux façons de consulter la base directement (sans passer par
l'application ni par Neo4j Browser dans un navigateur) :

```bash
# Ouvrir un shell dans le conteneur (exploration de fichiers, logs internes...)
docker exec -it cartographie-neo4j bash

# Ouvrir une session Cypher interactive (requêtes sur les données)
docker exec -it cartographie-neo4j cypher-shell -u neo4j -p <password>
```

Remplacer `<password>` par la valeur de `NEO4J_PASSWORD` du fichier `.env`
du serveur (voir le guide d'installation, section 4). Une fois connecté
via `cypher-shell`, toute requête Cypher standard fonctionne (voir I.4
pour des exemples prêts à l'emploi) ; `:exit` pour quitter.

Alternative avec interface graphique : **Neo4j Browser**, accessible à
`http://<hôte>:7474` si ce port est exposé et atteignable depuis le poste
utilisé (voir le guide d'installation, section 9.7, sur les restrictions
de pare-feu recommandées en production — ce port ne devrait être ouvert
qu'à un réseau d'administration restreint).

### I.4 Exploration de la base Neo4j

Requêtes de base pour comprendre rapidement ce que contient la base,
utilisables aussi bien dans `cypher-shell` que dans Neo4j Browser :

```cypher
// Labels (types de nœuds) présents dans la base
CALL db.labels();

// Types de relations présents
CALL db.relationshipTypes();

// Nombre de nœuds par label — vue d'ensemble rapide du volume de données
MATCH (n)
RETURN labels(n), count(*);

// Liste des comptes applicatifs et de leur rôle
MATCH (u:User)
RETURN u.email, u.role;

// Nombre de personnes cartographiées
MATCH (p:Personne)
RETURN count(p);

// Nombre de technologies référencées
MATCH (t:Techno)
RETURN count(t);
```

Pour aller plus loin, voici les principaux labels du modèle de données
(détail complet, y compris les relations, dans le
[guide d'architecture, section 2](GUIDE_ARCHITECTURE.md#2-modèle-de-données-neo4j)) :

| Label | Contenu |
|---|---|
| `Personne` | Membres de l'équipe DBA cartographiés |
| `Techno` / `TechnoCategory` | Référentiel des technologies et leurs catégories |
| `Domaine` / `Version` | Référentiel des domaines d'usage et versions |
| `Contexte` | Triplet unique techno/domaine/version, pivot des compétences |
| `User` | Comptes applicatifs (email, mot de passe **en clair**, rôle) |
| `AuditEvent` | Historique de toutes les demandes et décisions (voir I.5) |

### I.5 Où sont stockés les événements d'audit

Les événements d'audit (`AuditEvent` : demandes de création/modification/
suppression de compétence, de personne, de technologie, et leurs
décisions) sont des **nœuds Neo4j comme les autres**, dans la **même** base
`neo4j` que le reste des données métier — il n'existe **pas** de stockage
séparé (pas de fichier de log applicatif dédié, pas de base distincte).
Ils sont donc automatiquement inclus dans toute sauvegarde de la base
`neo4j` (voir D.1/I.6), et consultables :

- via l'application, page **Historique** ;
- via l'API, `GET /historique` ;
- directement en Cypher :

  ```cypher
  MATCH (a:AuditEvent)
  RETURN a.type, a.status, count(*)
  ORDER BY a.type, a.status;
  ```

### I.6 Sauvegarder et vérifier qu'une sauvegarde est exploitable

La procédure de sauvegarde/restauration complète (scripts
`scripts/backup_neo4j.sh` / `scripts/restore_neo4j.sh`, syntaxe
`neo4j-admin` correcte pour la version `2026.03`) est documentée en détail
à la [section D](#d-sauvegarde-et-restauration-de-la-base-neo4j) — ce
paragraphe se concentre sur la question « comment savoir qu'une sauvegarde
est réellement utilisable, sans attendre un incident pour le découvrir ».

Après une sauvegarde (`./scripts/backup_neo4j.sh`), vérifier qu'elle est
exploitable **sans toucher à la base de production** :

1. Vérifier que les fichiers `neo4j.dump` (et `system.dump`) existent et
   ont une taille cohérente avec la base (ni vide, ni anormalement petite
   par rapport à la sauvegarde précédente) :

   ```bash
   ls -la backups/neo4j_backup_<horodatage>/
   ```

2. `neo4j-admin` peut lire les métadonnées d'un dump sans le charger, via
   `--info`, ce qui confirme que le fichier n'est pas corrompu :

   ```bash
   docker run --rm -v <chemin_absolu_du_dossier_de_sauvegarde>:/dumps \
     neo4j:2026.03 \
     neo4j-admin database load neo4j --from-path=/dumps --info
   ```

   Une sortie affichant le nombre de fichiers et la taille du dump (sans
   message d'erreur) confirme que l'archive est lisible.

3. Pour une vérification complète (recommandé avant une mise à jour Neo4j
   ou après un premier changement de procédure), restaurer le dump sur un
   **volume Docker jetable** distinct du volume de production, démarrer un
   conteneur Neo4j temporaire dessus, et vérifier quelques comptages
   (`MATCH (p:Personne) RETURN count(p)` par exemple) contre ce qui est
   attendu, puis supprimer ce volume temporaire. C'est exactement la
   méthode utilisée pour valider la correction des scripts de ce projet —
   voir D.3.
