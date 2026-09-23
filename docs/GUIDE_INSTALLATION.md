# Guide d'installation

Ce document permet d'installer l'application **de zéro** : sur un poste
Windows totalement vierge, puis sur un serveur de production. Il ne suppose
aucune connaissance préalable du projet. Suivre les sections dans l'ordre.

**Docker Desktop n'est pas utilisé** (interdit en environnement Capgemini
pour raisons de sécurité) : Docker tourne directement en ligne de commande
dans une distribution Linux sous WSL2. Sauf mention contraire, **toutes les
commandes `docker`, `docker compose`, `git` et `curl` de ce guide s'exécutent
dans le terminal Ubuntu (WSL)**, pas dans PowerShell — PowerShell sert
uniquement à installer WSL lui-même et à ouvrir des URL dans le navigateur.

Sommaire :

1. [Vue d'ensemble de ce qui va être installé](#1-vue-densemble-de-ce-qui-va-être-installé)
2. [Prérequis poste de développement (WSL2 + Docker)](#2-prérequis-poste-de-développement-wsl2--docker)
3. [Récupération du projet](#3-récupération-du-projet)
4. [Configuration des variables d'environnement](#4-configuration-des-variables-denvironnement)
5. [Premier démarrage](#5-premier-démarrage)
6. [Initialisation de la base Neo4j (obligatoire sur une base vide)](#6-initialisation-de-la-base-neo4j-obligatoire-sur-une-base-vide)
7. [Vérifications post-installation](#7-vérifications-post-installation)
8. [Restaurer une sauvegarde Neo4j existante (option alternative à l'étape 6)](#8-restaurer-une-sauvegarde-neo4j-existante-option-alternative-à-létape-6)
9. [Déploiement sur un serveur de production](#9-déploiement-sur-un-serveur-de-production)
10. [Commandes utiles](#10-commandes-utiles)
11. [Dépannage](#11-dépannage)

---

## 1. Vue d'ensemble de ce qui va être installé

L'application est constituée de **4 conteneurs Docker** qui communiquent
entre eux, décrits dans le fichier `docker-compose.yml` à la racine du
projet :

| Service | Rôle | Port exposé sur la machine hôte |
|---|---|---|
| `neo4j` | Base de données (moteur de graphe) | `7474` (interface Neo4j Browser), `7687` (protocole Bolt utilisé par l'API) |
| `backend` | API FastAPI (Python) | `8000` |
| `frontend` | Pages HTML statiques, servies par Nginx | *(aucun port publié directement, accessible uniquement via `proxy`)* |
| `proxy` | Reverse proxy Nginx — **point d'entrée unique de l'application** | `8088` (mappé vers le port `80` du conteneur — voir la remarque ci-dessous) |

> **Port du proxy** : `docker-compose.yml` publie le port `80` interne du
> conteneur `proxy` sur le port **`8088`** de la machine hôte (`"8088:80"`).
> Ce n'est donc **pas** le port `80` standard qu'il faut utiliser pour
> accéder à l'application depuis un navigateur en local — voir
> `docker compose ps` pour vérifier le mapping réel à tout moment. Le reste
> de ce guide utilise `http://localhost:8088`.

Une seule commande (`docker compose up --build -d`) construit et démarre les
4 conteneurs. Aucune autre installation logicielle (Python, Node.js, Neo4j en
local, etc.) n'est nécessaire : **tout tourne dans Docker**, y compris en
développement.

**Sur un poste Windows**, Docker Engine tourne dans une distribution Linux
WSL2 (voir §2) — il n'y a pas de `docker` disponible directement dans
PowerShell. **Sur un serveur Linux** (§9), Docker tourne nativement, sans
particularité.

---

## 2. Prérequis poste de développement (WSL2 + Docker)

### 2.1 Installer WSL2

Ouvrir **PowerShell en administrateur** et lancer :

```powershell
wsl --install -d Ubuntu-24.04
```

Cette commande active les fonctionnalités Windows nécessaires (plateforme de
machine virtuelle, sous-système Windows pour Linux), installe le noyau WSL2
et télécharge la distribution **Ubuntu 24.04 LTS**. Sur un poste réellement
vierge, un **redémarrage** est demandé une fois — après redémarrage,
relancer la même commande si l'installation ne se termine pas
automatiquement.

Au premier lancement, une fenêtre de terminal Ubuntu s'ouvre et demande de
créer un **nom d'utilisateur et un mot de passe UNIX** (indépendants du
compte Windows) : c'est cet utilisateur qui sera utilisé pour tout le reste
de ce guide. Ce terminal Ubuntu est accessible ensuite à tout moment via le
menu Démarrer (« Ubuntu 24.04 LTS ») ou la commande `wsl` dans PowerShell.

> **Machine déjà utilisée avec Docker Desktop** : si une distribution
> `docker-desktop` apparaît dans `wsl -l -v`, elle est indépendante de la
> distribution `Ubuntu-24.04` installée ci-dessus et n'interfère pas avec
> elle — Docker Desktop n'a de toute façon pas sa place dans ce projet (voir
> l'introduction de ce guide) et peut être ignoré ou désinstallé.

### 2.2 Installer Docker Engine et Docker Compose dans Ubuntu

Dans le terminal **Ubuntu (WSL)**, installer Docker depuis le dépôt officiel
Docker (et non le paquet `docker.io`/`docker-compose` d'Ubuntu, plus ancien
et dont la commande `docker-compose` — avec un tiret — est incompatible avec
la syntaxe `docker compose` — avec un espace — utilisée partout ailleurs
dans ce guide) :

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

ARCH=$(dpkg --print-architecture)
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Activer et démarrer le service Docker (WSL2 avec Ubuntu 24.04 utilise
`systemd`, ce qui permet des services au démarrage comme sur un vrai
serveur Linux) :

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

Autoriser l'utilisateur courant à exécuter `docker` sans `sudo` :

```bash
sudo usermod -aG docker $USER
```

**Fermer puis rouvrir le terminal Ubuntu** (l'appartenance à un nouveau
groupe Linux n'est prise en compte qu'à la prochaine connexion), puis
vérifier :

```bash
docker --version
docker compose version
docker ps
```

La dernière commande doit s'exécuter sans erreur de permission (pas de
`permission denied ... docker.sock`) et sans `sudo`. Si l'erreur persiste
après avoir rouvert le terminal, forcer un redémarrage complet de WSL depuis
PowerShell puis rouvrir le terminal Ubuntu :

```powershell
wsl --shutdown
```

### 2.3 Particularité WSL à connaître : l'arrêt automatique en l'absence de terminal

Contrairement à Docker Desktop (qui maintient une machine virtuelle active
en permanence via un service Windows), **une distribution WSL s'arrête
automatiquement environ une minute après la fermeture du dernier terminal
qui y est ouvert**, ce qui arrête aussi Docker et les 4 conteneurs avec
elle.

Ce n'est pas gênant en pratique : `docker-compose.yml` définit chaque
service avec `restart: unless-stopped`, donc rouvrir un terminal Ubuntu (ou
exécuter n'importe quelle commande `wsl ...` depuis PowerShell) relance
automatiquement Docker et les conteneurs — compter **15 à 30 secondes**
avant que `docker compose ps` ne réaffiche les 4 services `Up`/`healthy` et
que l'application ne soit de nouveau accessible dans le navigateur. Il est
normal d'observer, pendant cette fenêtre, un redémarrage isolé du conteneur
`backend` (il tente de se connecter à Neo4j avant que celui-ci soit prêt) :
il se stabilise de lui-même.

Pour garder l'application en permanence disponible sans laisser de terminal
ouvert (utile sur un poste de développement partagé ou pour une démo), garder
au moins un terminal Ubuntu ouvert en arrière-plan, ou désactiver cet arrêt
automatique dans `%UserProfile%\.wslconfig` :

```ini
[wsl2]
vmIdleTimeout=-1
```

(nécessite `wsl --shutdown` puis réouverture pour prendre effet). Cette
particularité ne concerne que WSL en développement — sur le serveur de
production (§9), Docker est un service Linux standard, toujours actif.

---

## 3. Récupération du projet

Toutes les commandes ci-dessous s'exécutent dans le terminal **Ubuntu
(WSL)**. Travailler dans le système de fichiers Linux (`~/...`) plutôt que
dans `/mnt/c/...` (l'arborescence Windows vue depuis WSL) : les accès
disque y sont nettement plus rapides, ce qui accélère sensiblement les
`docker compose build`.

### Option A — via Git (recommandé)

```bash
cd ~
git clone <url-du-dépôt-git> cartographie-competences
cd cartographie-competences
```

*(Remplacer `<url-du-dépôt-git>` par l'URL réelle du dépôt Git de
l'entreprise. `git` est déjà installé par défaut sur Ubuntu 24.04.)*

### Option B — par copie de fichiers

Copier l'intégralité du dossier du projet dans le système de fichiers Linux,
par exemple depuis un partage réseau déjà monté sous `/mnt/...`, ou depuis
Windows via l'explorateur de fichiers en naviguant vers `\\wsl$\Ubuntu-24.04\home\<utilisateur>\`.

Dans les deux cas, **vérifier que le dossier obtenu contient bien** un
fichier `docker-compose.yml` à sa racine, ainsi que les dossiers `backend/`,
`frontend/`, `proxy/`, `scripts/` et `docs/`. C'est ce dossier qui sert de
référence pour toutes les commandes de ce guide (on l'appelle « la racine du
projet »).

### Workflow Git cible

Le développement ne se fait **pas directement sur le serveur DESERVE**. Le
circuit cible est :

```
PC local (développement, WSL)
    │  git push
    ▼
GitLab (dépôt de référence de l'entreprise)
    │  git pull
    ▼
Serveur DESERVE (/opt/cartographie-competences)
    │  docker compose up -d --build
    ▼
Application en production
```

En pratique, pendant une phase de transition, un dépôt GitHub personnel peut
servir de relais intermédiaire pour développer depuis un poste personnel
(`PC perso → push → GitHub → pull sur PC pro → push → GitLab`) — GitHub
n'est alors qu'un canal de transport temporaire, GitLab restant la source de
vérité de l'entreprise. Dans tous les cas, la mise à jour du serveur suit
toujours le même schéma : `git pull` sur le serveur, puis redémarrage des
conteneurs concernés (voir le guide d'utilisation et d'administration,
section F, pour la procédure de mise à jour détaillée).

### Environnement de développement local du backend (optionnel, hors Docker)

Le backend peut aussi tourner **directement dans WSL, hors conteneur**,
pratique pour un cycle de rechargement plus rapide que
`docker compose up -d --build backend` à chaque changement. Neo4j reste, lui,
lancé via Docker (`docker compose up -d neo4j`) ; comme les deux tournent
dans la même distribution WSL, le backend le joint simplement sur
`localhost:7687`.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Le backend lit aussi un .env local via python-dotenv (voir backend/database.py) :
# au minimum NEO4J_URI=bolt://localhost:7687 si Neo4j tourne dans Docker avec
# le port 7687 publié sur l'hôte (cas par défaut, voir §1).
python -m uvicorn main:app --reload --port 8000
```

*(`python3` et `venv` sont installés par défaut sur Ubuntu 24.04 ; sinon :
`sudo apt-get install -y python3-venv`.)*

Le dossier `backend/.venv/` est un environnement Python local **qui ne doit
jamais être commité** (déjà exclu par `.gitignore`) : chaque poste de
développement crée le sien avec les commandes ci-dessus.

---

## 4. Configuration des variables d'environnement

Le projet fournit un modèle `.env.example` à la racine. Docker Compose lit
automatiquement un fichier nommé `.env` placé au même endroit — **il faut le
créer** avant le premier démarrage :

```bash
cp .env.example .env
```

Contenu du modèle :

```env
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CORS_ORIGINS=http://localhost,http://localhost:8088,http://127.0.0.1:8088,http://localhost:8080,http://127.0.0.1:8080,http://cartographie-dba
DEV_AUTH=true
```

| Variable | Rôle | Valeur par défaut | À changer ? |
|---|---|---|---|
| `NEO4J_USER` | Identifiant de connexion à Neo4j (utilisé par le conteneur `neo4j` pour créer le compte, et par `backend` pour s'y connecter). | `neo4j` | Peut rester `neo4j` (nom d'utilisateur système standard de Neo4j). |
| `NEO4J_PASSWORD` | Mot de passe du compte Neo4j ci-dessus. | `password` | **Oui, impérativement**, dès qu'on sort d'un usage strictement local et jetable (voir §9 pour la production). |
| `CORS_ORIGINS` | Liste (séparée par des virgules, sans espace) des origines autorisées à appeler l'API depuis un navigateur. | voir ci-dessus | À adapter selon l'URL réelle d'accès (voir remarque ci-dessous et §9). |
| `DEV_AUTH` | Bascule interne réservée au module `security.py` (non branché dans l'application actuellement, voir le guide d'architecture). | `true` | Laisser `true` tant que `security.py` n'est pas activé. Sans effet sur le fonctionnement actuel. |

**Remarque importante sur `CORS_ORIGINS` et l'URL de l'API** : le fichier
`frontend/common.js` (et `frontend/login.html`) détermine dynamiquement
l'URL de l'API à appeler :

```js
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "/cartographie/api";
```

- Si l'application est ouverte via `http://localhost` ou `http://127.0.0.1`
  (poste de développement — dans le navigateur **Windows**, atteignant les
  conteneurs WSL grâce au transfert automatique de ports de WSL2), le
  frontend appelle **directement** l'API sur le port `8000` exposé par le
  conteneur `backend`. La page elle-même n'est accessible que via le
  `proxy` (le service `frontend` ne publie aucun port — voir §1), donc
  l'URL réelle à ouvrir est `http://localhost:8088` (port hôte publié par
  `proxy`). C'est cette origine (`http://localhost:8088`, pas `:8000`) que
  le navigateur envoie comme `Origin` sur les appels API : il faut donc que
  `http://localhost:8088` (ou `http://127.0.0.1:8088`) figure dans
  `CORS_ORIGINS`, sans quoi le navigateur bloquera les requêtes (erreur
  CORS visible dans la console développeur, y compris sur `POST
  /auth/login` depuis la page de connexion).
- Pour tout autre nom d'hôte (serveur de production, nom de domaine
  interne), le frontend appelle `/cartographie/api/...`, c'est-à-dire une
  URL relative au domaine courant. Dans ce cas, `CORS_ORIGINS` a moins
  d'importance puisque la requête part du même domaine que la page, mais il
  est recommandé d'y inclure l'URL publique finale par cohérence.

  > **Pour un déploiement serveur (§9)** : ce préfixe `/cartographie` n'est
  > pas routé par `proxy/nginx.conf` ni `frontend/default.conf` (qui ne
  > connaissent que `/api/`) — c'est le reverse-proxy externe en place sur
  > le serveur DESERVE qui le prend en charge en amont (voir §9.5). Voir le
  > guide d'architecture, §1.1, pour le détail.

Modifier `.env` avec un éditeur de texte selon les besoins (`nano .env`
depuis le terminal Ubuntu, par exemple), puis l'enregistrer. Le fichier
`.env` **ne doit jamais être commité dans Git** (il est déjà exclu par les
règles d'ignore du projet) car il peut contenir des secrets (mot de passe
Neo4j).

---

## 5. Premier démarrage

Depuis la racine du projet, dans le terminal **Ubuntu (WSL)** :

```bash
docker compose up --build -d
```

Détail de la commande :
- `up` : crée et démarre les conteneurs.
- `--build` : force la reconstruction des images `backend`, `frontend` et
  `proxy` à partir de leurs `Dockerfile` (utile au premier lancement, et à
  chaque fois que le code de ces services a changé).
- `-d` : démarre en arrière-plan (« detached »), rend la main immédiatement
  dans le terminal.

Le premier lancement peut prendre plusieurs minutes : téléchargement de
l'image `neo4j:2026.03` (plusieurs centaines de Mo) et des images de base
Python/Nginx, puis installation des dépendances Python.

Suivre la progression si besoin :

```bash
docker compose logs -f
```

*(`Ctrl+C` pour quitter le suivi des logs — cela n'arrête pas les
conteneurs.)*

---

## 6. Initialisation de la base Neo4j (obligatoire sur une base vide)

**Cette étape est indispensable la toute première fois**, sur une base
Neo4j qui vient d'être créée : sans elle, l'application démarre mais reste
inutilisable (impossible de se connecter, listes déroulantes vides). Si une
sauvegarde Neo4j existante doit être restaurée à la place (reprise d'un
environnement déjà peuplé), passer directement à la section 8 et ignorer
cette section 6.

### 6.1 Attendre que les services soient prêts

```bash
docker compose ps
```

Les colonnes `STATUS` de `neo4j` et `backend` doivent afficher
`(healthy)`. Si `backend` est encore `(unhealthy)` ou `starting`, patienter
quelques secondes et relancer la commande — `backend` attend que `neo4j`
soit lui-même prêt avant de démarrer (voir le guide d'architecture pour le
détail de cet ordre de démarrage).

### 6.2 Créer le tout premier compte administrateur

L'application n'a **aucun mécanisme d'auto-inscription** : tous les comptes
sont créés via la page « Utilisateurs », réservée aux administrateurs. Il y
a donc un problème d'amorçage pour le tout premier compte, qu'il faut créer
directement en base via l'interface Neo4j Browser.

1. Ouvrir **http://localhost:7474** dans le navigateur **Windows** (accès
   direct aux conteneurs WSL grâce au transfert automatique de ports de
   WSL2, aucune configuration supplémentaire requise).
2. Se connecter avec :
   - **Username** : la valeur de `NEO4J_USER` dans `.env` (par défaut `neo4j`)
   - **Password** : la valeur de `NEO4J_PASSWORD` dans `.env` (par défaut `password`)
3. Dans la barre de requête, exécuter (bouton ▷ ou `Ctrl+Entrée`) :

   ```cypher
   CREATE (u:User {
     email: "admin",
     password: "Admin123!",
     role: "ADMIN",
     active: true,
     createdAt: datetime(),
     createdBy: "bootstrap-installation"
   })
   ```

   > **Pourquoi l'email `"admin"` et pas une adresse `@capgemini.com` ?**
   > Le backend exige normalement un email au format
   > `prenom.nom@capgemini.com` (voir `backend/utils.py`), à une exception
   > près : la valeur littérale `admin` est explicitement acceptée comme cas
   > particulier, précisément pour permettre ce genre d'amorçage. Ce compte
   > `admin` sert uniquement à démarrer : voir l'étape 6.4 pour le
   > remplacer par de vrais comptes nominatifs.

4. Vérifier la création :

   ```cypher
   MATCH (u:User) RETURN u;
   ```

   Un nœud `User` avec `role: "ADMIN"` doit apparaître.

### 6.3 Peupler les données de référence minimales (Domaine / Version)

Les listes déroulantes « Domaine » et « Version » des pages **Gestion** et
**Questionnaire** sont alimentées par les nœuds `Domaine` et `Version`
existants en base — il n'existe **aucune page de l'interface** pour en
créer de nouveaux (contrairement aux technologies, créables depuis la page
Gestion). Sur une base vide, ces listes sont donc vides et bloquent la
saisie. Il faut créer au moins un `Domaine` et une `Version` via l'API,
depuis le terminal **Ubuntu (WSL)** avec `curl` (ou via la documentation
interactive `http://localhost:8000/docs` dans le navigateur) :

```bash
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d '{"nom": "Run MCO"}'
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d '{"nom": "Build"}'
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d '{"nom": "Architecture"}'
curl -X POST http://localhost:8000/ref/versions -H "Content-Type: application/json" -d '{"nom": "N/A"}'
```

*(Adapter les noms de domaines à l'organisation réelle de l'équipe — ceux
ci-dessus sont ceux utilisés historiquement dans ce projet. La version
`N/A` correspond à la valeur utilisée quand le champ « version » est laissé
vide dans le formulaire de la page Gestion.)*

> **Ne pas exécuter ces commandes `curl` dans PowerShell** : `curl` y est un
> alias de `Invoke-WebRequest`, qui ne comprend pas la syntaxe `-d` ci-dessus
> et échoue avec une erreur `ParameterBindingException`. Rester dans le
> terminal Ubuntu (WSL), qui utilise le vrai `curl`.

Les **catégories de technologies** (`TechnoCategory`) et les
**technologies** (`Techno`) elles-mêmes n'ont pas besoin d'être pré-créées
en base : elles se créent normalement depuis la page **Gestion** de
l'application (section « Ajouter une compétence au référentiel »), via le
workflow de demande/validation habituel (voir le guide d'utilisation et
d'administration).

### 6.4 Se connecter et finaliser l'amorçage

1. Ouvrir **http://localhost:8088** dans le navigateur Windows (port hôte
   publié par le service `proxy`, voir §1).
2. Se connecter avec l'email `admin` et le mot de passe défini à l'étape 6.2.
3. Aller sur la page **Utilisateurs** et créer les comptes nominatifs réels
   de l'équipe (format `prenom.nom@capgemini.com`), avec le rôle `ADMIN`
   pour au moins une personne.
4. Une fois qu'**un second compte `ADMIN` nominatif** existe, il est
   possible de supprimer le compte `admin` de bootstrap depuis la page
   Utilisateurs (l'application interdit la suppression du dernier
   administrateur actif — voir le guide d'utilisation et d'administration —
   donc cette suppression n'est possible qu'après création d'un second
   admin).

---

## 7. Vérifications post-installation

Depuis le terminal Ubuntu (WSL) :

```bash
docker compose ps
```

Les 4 services (`cartographie-neo4j`, `cartographie-backend`,
`cartographie-frontend`, `cartographie-proxy`) doivent être `Up`, et
`neo4j`/`backend` `(healthy)`.

```bash
curl http://localhost:8000/health
```

Réponse attendue :

```json
{"ok":true,"neo4j_uri":"bolt://neo4j:7687"}
```

Puis, dans le navigateur **Windows** (accès direct grâce au transfert de
ports WSL2, aucune configuration réseau supplémentaire) :
- **http://localhost:8088** → page de connexion de l'application.
- **http://localhost:8000/docs** → documentation interactive de l'API
  (Swagger UI généré automatiquement par FastAPI), utile pour tester des
  appels sans passer par l'interface.
- **http://localhost:7474** → Neo4j Browser.

---

## 8. Restaurer une sauvegarde Neo4j existante (option alternative à l'étape 6)

Si une sauvegarde Neo4j (produite par `scripts/backup_neo4j.sh` — voir le
guide d'utilisation et d'administration) est disponible et doit remplacer
une base vide plutôt que de repartir de zéro, une fois la stack démarrée
(§5), depuis la racine du projet dans le terminal Ubuntu (WSL) :

```bash
./scripts/restore_neo4j.sh backups/neo4j_backup_20260916_140957
```

*(remplacer le chemin par le dossier de sauvegarde réel, contenant
`neo4j.dump` et/ou `system.dump` — voir `backups/` ou l'emplacement où la
sauvegarde a été transférée sur cette machine)*

Le script arrête brièvement `cartographie-neo4j` (édition Community : le
chargement d'un dump exige la base hors ligne), charge le dump, puis
redémarre le conteneur automatiquement — compter 15 à 30 secondes après la
fin du script avant que `docker compose ps` n'affiche `neo4j` de nouveau
`healthy`.

> Le tag de l'image `neo4j:2026.03` dans `docker-compose.yml` doit être
> **égal ou supérieur** à la version Neo4j qui a produit le dump — un dump
> plus récent que l'image cible ne peut pas être chargé.

Après restauration, se connecter avec un compte administrateur déjà présent
dans le dump — les étapes 6.2 et 6.3 ne sont alors pas nécessaires.

---

## 9. Déploiement sur un serveur de production

### 9.1 Prérequis serveur

- Un serveur **Linux** (Ubuntu récent recommandé — les commandes ci-dessous
  sont écrites pour Ubuntu).
- Accès `sudo` ou root sur ce serveur.
- Un accès réseau (interne à l'entreprise, ou externe selon le contexte)
  vers ce serveur depuis les postes des utilisateurs.
- Idéalement, un nom d'hôte/DNS interne clair (ex. `cartographie-dba`)
  plutôt qu'une adresse IP brute — voir §9.5.

Contrairement au poste de développement (§2), il n'y a ici ni WSL ni
Docker Desktop à installer : Docker tourne comme un service Linux standard,
toujours actif, indépendamment de toute session ouverte.

### 9.2 Installation de Docker sur le serveur

Même méthode que dans WSL (§2.2 — dépôt officiel Docker, pas le paquet
`docker.io` d'Ubuntu) :

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

ARCH=$(dpkg --print-architecture)
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
```

Fermer puis rouvrir la session SSH (nouveau groupe pris en compte à la
reconnexion), puis vérifier :

```bash
docker --version
docker compose version
docker ps
```

### 9.3 Transfert du projet sur le serveur

Transférer l'intégralité du dossier du projet sur le serveur (via `git
clone`, `scp`, `rsync`, ou tout autre moyen conforme aux pratiques de
l'entreprise). Structure attendue une fois sur le serveur :

```
cartographie-competences/
├── docker-compose.yml
├── .env.example
├── backend/
├── frontend/
├── proxy/
├── scripts/
└── docs/
```

### 9.4 Configuration de l'environnement de production

```bash
cd cartographie-competences
cp .env.example .env
```

Éditer `.env` (`nano .env` ou équivalent) et **impérativement** :

```env
NEO4J_USER=neo4j
NEO4J_PASSWORD=<mot-de-passe-fort-et-unique>
CORS_ORIGINS=http://cartographie-dba
DEV_AUTH=true
```

- `NEO4J_PASSWORD` : ne jamais laisser la valeur par défaut `password` en
  production.
- `CORS_ORIGINS` : remplacer par l'URL réelle d'accès au serveur (nom
  DNS interne, éventuellement plusieurs origines séparées par des virgules
  si l'application est accessible par plusieurs noms). Ne pas laisser les
  valeurs `localhost`/`127.0.0.1` de développement.

### 9.5 Choix de l'URL d'accès

L'objectif est que les utilisateurs finaux accèdent à l'application via une
URL propre (`http://cartographie-dba`), **sans avoir à connaître d'adresse
IP ni de numéro de port**. Deux approches possibles, à mettre en place côté
infrastructure serveur (hors du périmètre de ce projet) :

- **DNS interne** : faire pointer l'enregistrement `cartographie-dba` (ou
  le nom choisi) vers l'adresse IP du serveur, auprès de l'équipe
  infrastructure/réseau.
- **Fichier hosts local** (solution de secours, à l'échelle d'un poste
  uniquement, pas d'un déploiement multi-utilisateurs) : ajouter une ligne
  `<ip-serveur> cartographie-dba` dans `C:\Windows\System32\drivers\etc\hosts`
  (Windows) ou `/etc/hosts` (macOS/Linux).

Le reverse proxy `proxy` (Nginx, service Docker de ce projet) écoute sur le
port **80** standard : aucune configuration supplémentaire n'est nécessaire
côté application pour qu'une URL sans port fonctionne, à condition que le
DNS ou le fichier hosts pointe vers le serveur et que le port 80 y soit
accessible (voir §9.7 pour le pare-feu).

> **HTTPS** : la configuration fournie sert du **HTTP simple** sur le port
> 80. Pour une exposition au-delà d'un réseau interne de confiance, mettre
> en place du HTTPS est fortement recommandé (certificat, terminaison TLS
> en amont du `proxy` Nginx ou dans sa configuration) — cette mise en place
> dépend de l'infrastructure cible (reverse proxy d'entreprise existant,
> certificat interne, Let's Encrypt...) et n'est pas fournie nativement par
> ce projet à ce stade.

> **Préfixe `/cartographie/` (déploiement DESERVE actuel)** : sur le
> serveur DESERVE, l'application est accédée via un chemin
> (`http://deserve.corp.capgemini.com/cartographie/`, voir le guide
> d'utilisation et d'administration, section A.1) plutôt qu'un sous-domaine
> dédié — le frontend appelle d'ailleurs en dur `/cartographie/api/...`
> pour toute origine autre que `localhost` (voir §4 ci-dessus et le guide
> d'architecture, §1.1). Ce préfixe n'est pas routé par `proxy/nginx.conf`
> ni `frontend/default.conf` (qui ne connaissent que `/api/`) : c'est le
> reverse-proxy externe à ce projet, déjà en place sur le serveur DESERVE
> devant ce `proxy` Docker (configuration hors du périmètre de ce dépôt),
> qui le prend en charge. Pour tout nouveau serveur de production, reproduire
> cette même prise en charge côté reverse-proxy externe.

### 9.6 Démarrage de la stack

```bash
docker compose up --build -d
```

Ou, en utilisant le script fourni qui automatise la copie de `.env` et le
démarrage :

```bash
./scripts/init_server.sh
```

### 9.7 Pare-feu / exposition réseau

Seul le port **80** (le `proxy`) doit être accessible depuis les postes des
utilisateurs finaux. Les ports `7474`, `7687` (Neo4j) et `8000` (API
backend) sont utiles pour l'administration et le débogage mais ne doivent
**pas** être exposés publiquement sur un serveur de production — les
restreindre au réseau interne / à l'accès administrateur via le pare-feu du
serveur (`ufw`, `iptables`, groupe de sécurité cloud...), par exemple avec
`ufw` :

```bash
sudo ufw allow 80/tcp
sudo ufw allow from <plage-ip-admin> to any port 7474 proto tcp
sudo ufw allow from <plage-ip-admin> to any port 7687 proto tcp
sudo ufw allow from <plage-ip-admin> to any port 8000 proto tcp
```

*(Adapter selon les outils déjà en place sur l'infrastructure de
l'entreprise — la configuration du pare-feu système dépasse le périmètre de
ce projet.)*

### 9.8 Première initialisation en production

Répéter la section 6 (création du premier compte `admin`, données de
référence) **ou** la section 8 (restauration d'une sauvegarde) selon le
cas, en remplaçant `localhost` par le nom du serveur / son IP dans les URL
utilisées pour Neo4j Browser (sauf si ces commandes sont exécutées
directement sur le serveur, auquel cas `localhost` reste valide car les
commandes s'exécutent alors sur la machine qui héberge les conteneurs).

### 9.9 Vérification finale

```bash
docker compose ps
curl http://localhost:8088/       # via le proxy (port hôte publié, voir §1), doit répondre (page HTML)
curl http://localhost:8000/health # accès direct au backend
```

Puis, depuis un poste utilisateur, ouvrir l'URL choisie (ex.
`http://cartographie-dba`) dans un navigateur et vérifier que la page de
connexion s'affiche et qu'une connexion aboutit.

---

## 10. Commandes utiles

```bash
docker compose ps                   # état des 4 conteneurs
docker compose logs -f              # suivre les logs de tous les services
docker compose logs -f backend      # suivre les logs d'un seul service
docker compose up -d --build backend  # reconstruire et redémarrer un seul service après un changement de code
docker compose restart proxy        # à faire après tout rebuild de backend/frontend : Nginx peut
                                     # garder en cache l'ancienne IP du conteneur et renvoyer des 502 sinon
docker compose down                 # tout arrêter (conserve les données Neo4j)
docker compose down -v              # tout arrêter ET supprimer les volumes (⚠ perte définitive des données Neo4j)
```

Pour la gestion des images Docker au quotidien (mises à jour de version,
notamment Neo4j), voir le
[guide d'utilisation et d'administration](GUIDE_UTILISATION_ADMINISTRATION.md).

---

## 11. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `wsl : la virtualisation n'est pas activée` | Fonctionnalité Windows « Virtual Machine Platform » désactivée, ou virtualisation désactivée au BIOS | `wsl --install` depuis un terminal PowerShell **administrateur**, puis redémarrer ; vérifier aussi que la virtualisation est activée au BIOS |
| Une commande `curl ... -d ...` échoue avec `Invoke-WebRequest : Impossible de lier le paramètre « Headers »` | La commande a été lancée dans PowerShell, où `curl` est un alias vers `Invoke-WebRequest` (syntaxe incompatible) | Relancer la même commande dans le terminal **Ubuntu (WSL)**, qui utilise le vrai `curl` |
| `docker ps` renvoie `permission denied ... docker.sock` | L'utilisateur vient d'être ajouté au groupe `docker` mais le terminal actuel utilise encore l'ancienne session | Fermer et rouvrir le terminal Ubuntu ; si ça persiste, `wsl --shutdown` depuis PowerShell puis rouvrir |
| L'application (ou Neo4j Browser) ne répond plus après un moment sans terminal WSL ouvert | Comportement normal de WSL2 : la distribution s'arrête après ~1 minute sans terminal attaché (voir §2.3) | Ouvrir un terminal Ubuntu (ou toute commande `wsl ...`) pour relancer WSL, puis patienter 15 à 30 s que les conteneurs redeviennent `healthy` (`docker compose ps`) |
| `cartographie-backend` redémarre une fois juste après la réouverture d'un terminal WSL | Le backend a démarré avant que Neo4j ne soit prêt (l'ordre de démarrage de `depends_on` n'est respecté qu'au premier `docker compose up`, pas lors d'une reprise automatique de WSL) | Normal, se stabilise seul en quelques secondes grâce à `restart: unless-stopped` |
| Erreur CORS dans la console du navigateur (« has been blocked by CORS policy ») | L'origine utilisée pour ouvrir l'application n'est pas listée dans `CORS_ORIGINS` | Ajouter l'origine exacte (protocole + hostname + port) dans `.env`, puis `docker compose up -d --build backend` |
| `backend` reste `unhealthy` indéfiniment | Neo4j pas encore prêt, ou mauvais identifiants `NEO4J_USER`/`NEO4J_PASSWORD` | `docker compose logs backend` pour voir l'erreur exacte ; vérifier la cohérence entre `.env` et les identifiants attendus par Neo4j |
| Page de connexion accessible mais listes déroulantes vides sur la page Gestion | Base Neo4j vide, section 6.3 non réalisée | Exécuter les appels `curl` de la section 6.3 (dans le terminal Ubuntu, pas PowerShell) |
| Impossible de se connecter avec `admin` / mot de passe défini | Faute de frappe dans la requête Cypher de la section 6.2, ou compte `active: false` | Rouvrir Neo4j Browser, `MATCH (u:User {email:"admin"}) RETURN u;` pour vérifier l'existence et les valeurs exactes du nœud |
| 502 sur le frontend juste après un `docker compose up -d --build backend` (ou `frontend`) | Nginx (`proxy`) a mis en cache l'ancienne IP du conteneur reconstruit | `docker compose restart proxy` |
| `docker compose up` échoue avec un conflit de port (`port is already allocated`) | Un autre service utilise déjà le port 80, 8000, 7474 ou 7687 sur la machine | Arrêter le service en conflit, ou modifier la correspondance de ports dans `docker-compose.yml` (partie gauche du `"hôte:conteneur"`) |
| Le dump ne se charge pas (`Store copy failed` ou erreur de version) | Version de l'image `neo4j` inférieure à la version ayant produit le dump | Adapter le tag de l'image `neo4j` dans `docker-compose.yml` à une version égale ou supérieure, puis relancer |

Pour tout problème persistant, consulter les journaux détaillés :

```bash
docker compose logs --tail=200 neo4j
docker compose logs --tail=200 backend
docker compose logs --tail=200 proxy
```
