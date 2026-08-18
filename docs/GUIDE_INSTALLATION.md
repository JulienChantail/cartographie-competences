# Guide d'installation

Ce document permet d'installer l'application **de zéro** : sur un poste de
développement totalement vierge, puis sur un serveur de production. Il ne
suppose aucune connaissance préalable du projet. Suivre les sections dans
l'ordre.

Sommaire :

1. [Vue d'ensemble de ce qui va être installé](#1-vue-densemble-de-ce-qui-va-être-installé)
2. [Prérequis poste de développement](#2-prérequis-poste-de-développement)
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
| `proxy` | Reverse proxy Nginx — **point d'entrée unique de l'application** | `80` |

Une seule commande (`docker compose up --build -d`) construit et démarre les
4 conteneurs. Aucune autre installation logicielle (Python, Node.js, Neo4j
en local, etc.) n'est nécessaire sur la machine : **tout tourne dans
Docker**.

---

## 2. Prérequis poste de développement

# Installation de Docker sur Ubuntu 24.04

## Vérification de l'init system

```bash
ps -p 1 -o comm=
```

**Résultat :**

```text
systemd
```

---

## Vérification du dépôt Neo4j

```bash
grep -R neo4j /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null
```

**Résultat :**

```text
/etc/apt/sources.list.d/neo4j.list:deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable/
```

---

## Désactivation temporaire du dépôt Neo4j

```bash
sudo mv /etc/apt/sources.list.d/neo4j.list \
           /etc/apt/sources.list.d/neo4j.list.disabled
```

---

## Mise à jour des dépôts

```bash
sudo apt update
```

**Résultat :**

```text
16 packages can be upgraded. Run 'apt list --upgradable' to see them.
```

Aucune erreur liée au dépôt Neo4j après sa désactivation.

---

## Installation de Docker

```bash
sudo apt install -y docker.io docker-compose
```

### Points notables

- `docker-compose` était déjà installé :
  ```text
  docker-compose version 1.29.2
  ```

- Installation de :
  ```text
  docker.io 29.1.3-0ubuntu3~24.04.2
  ```

- Suppression automatique du paquet :
  ```text
  podman-docker
  ```

---

## Vérification des versions installées

```bash
docker --version
docker-compose --version
```

**Résultat :**

```text
Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2
docker-compose version 1.29.2, build unknown
```

---

## Activation du service Docker

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

---

## Vérification de l'état du service

```bash
sudo systemctl status docker
```

**Résultat :**

```text
docker.service - Docker Application Container Engine
Loaded: loaded (/usr/lib/systemd/system/docker.service; enabled)
Active: active (running)
```

✅ Le service Docker est démarré et opérationnel.

---

## Ajout de l'utilisateur au groupe Docker

```bash
sudo usermod -aG docker $USER
```

> Cette commande permet d'utiliser Docker sans `sudo` après une nouvelle connexion à la session (ou un redémarrage du shell).

---

## État final

| Élément | Statut |
|----------|----------|
| systemd | ✅ Présent |
| Dépôt Neo4j | ✅ Désactivé temporairement |
| apt update | ✅ OK |
| Docker | ✅ Installé |
| Docker Compose | ✅ Disponible |
| Service Docker | ✅ Actif |
| Groupe docker | ✅ Utilisateur ajouté |

### Validation rapide

```bash
docker ps
docker run hello-world
```

Si ces commandes s'exécutent correctement, l'installation Docker est pleinement fonctionnelle.

## Vérification des droits Docker

Après l'installation de Docker, l'utilisateur courant doit appartenir au groupe `docker` afin de pouvoir exécuter les commandes Docker sans utiliser `sudo`.

### Ajouter l'utilisateur au groupe Docker

```bash
sudo usermod -aG docker $USER
```

### Vérifier l'appartenance au groupe

Fermer puis rouvrir la session (ou redémarrer WSL), puis vérifier :

```bash
groups
```

Le groupe `docker` doit apparaître dans la liste.

Exemple :

```text
utilisateur adm sudo docker
```

### Tester l'accès à Docker

```bash
docker ps
```

Si la commande fonctionne sans erreur de permission, la configuration est correcte.

### Dépannage

Si la commande renvoie :

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

vérifier que :

```bash
grep docker /etc/group
```

contient bien l'utilisateur courant.

Exemple :

```text
docker:x:110:root,utilisateur
```

Si ce n'est pas le cas :

```bash
sudo usermod -aG docker $USER
```

Puis redémarrer la session.

### Cas particulier WSL

Sous WSL, l'ajout à un groupe Linux n'est généralement pris en compte qu'après un redémarrage de l'instance WSL :

```powershell
wsl --shutdown
```

Puis relancer le terminal Ubuntu et vérifier de nouveau :

```bash
groups
docker ps
```
## 3. Récupération du projet

### Option A — via Git (recommandé)

```powershell
git clone <url-du-dépôt-git> Projet_cartographie_competences
cd Projet_cartographie_competences
```

*(Remplacer `<url-du-dépôt-git>` par l'URL réelle du dépôt Git de
l'entreprise. Si le projet n'est pas encore versionné avec Git, voir
l'option B.)*

### Option B — par copie de fichiers

Copier l'intégralité du dossier `Projet_cartographie_competences/` sur la
machine cible (clé USB, partage réseau, archive `.zip`, etc.), puis ouvrir
un terminal dans ce dossier.

Dans les deux cas, **vérifier que le dossier obtenu contient bien** un
fichier `docker-compose.yml` à sa racine, ainsi que les dossiers `backend/`,
`frontend/`, `proxy/`, `scripts/` et `docs/`. C'est ce dossier qui sert de
référence pour toutes les commandes de ce guide (on l'appelle « la racine du
projet »).

---

## 4. Configuration des variables d'environnement

Le projet fournit un modèle `.env.example` à la racine. Docker Compose lit
automatiquement un fichier nommé `.env` placé au même endroit — **il faut le
créer** avant le premier démarrage :

```powershell
cp .env.example .env
```

Contenu du modèle :

```env
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CORS_ORIGINS=http://localhost,http://localhost:8080,http://127.0.0.1:8080,http://cartographie-dba
DEV_AUTH=true
```

| Variable | Rôle | Valeur par défaut | À changer ? |
|---|---|---|---|
| `NEO4J_USER` | Identifiant de connexion à Neo4j (utilisé par le conteneur `neo4j` pour créer le compte, et par `backend` pour s'y connecter). | `neo4j` | Peut rester `neo4j` (nom d'utilisateur système standard de Neo4j). |
| `NEO4J_PASSWORD` | Mot de passe du compte Neo4j ci-dessus. | `password` | **Oui, impérativement**, dès qu'on sort d'un usage strictement local et jetable (voir §9 pour la production). |
| `CORS_ORIGINS` | Liste (séparée par des virgules, sans espace) des origines autorisées à appeler l'API depuis un navigateur. | `http://localhost:8080,http://127.0.0.1:8080,http://cartographie-dba` | À adapter selon l'URL réelle d'accès (voir remarque ci-dessous et §9). |
| `DEV_AUTH` | Bascule interne réservée au module `security.py` (non branché dans l'application actuellement, voir le guide d'architecture). | `true` | Laisser `true` tant que `security.py` n'est pas activé. Sans effet sur le fonctionnement actuel. |

**Remarque importante sur `CORS_ORIGINS` et l'URL de l'API** : le fichier
`frontend/common.js` (et `frontend/login.html`) détermine dynamiquement
l'URL de l'API à appeler :

```js
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "/api";
```

- Si l'application est ouverte via `http://localhost` ou `http://127.0.0.1`
  (poste de développement), le frontend appelle **directement** l'API sur
  le port `8000` exposé par le conteneur `backend`. Il faut donc que
  `http://localhost:8000` (ou `http://127.0.0.1:8000`) figure dans
  `CORS_ORIGINS`, sans quoi le navigateur bloquera les requêtes (erreur
  CORS visible dans la console développeur).
- Pour tout autre nom d'hôte (serveur de production, nom de domaine
  interne), le frontend appelle `/api/...`, c'est-à-dire l'URL relative
  au domaine courant — la requête passe alors par le `proxy` Nginx (port
  80), qui la redirige vers `backend:8000` en interne. Dans ce cas,
  `CORS_ORIGINS` a moins d'importance puisque la requête part du même
  domaine que la page, mais il est recommandé d'y inclure l'URL publique
  finale par cohérence.

Modifier `.env` avec un éditeur de texte selon les besoins, puis
l'enregistrer. Le fichier `.env` **ne doit jamais être commité dans Git**
(il est déjà exclu par les règles d'ignore du projet) car il peut contenir
des secrets (mot de passe Neo4j).

---

## 5. Premier démarrage

Depuis la racine du projet (là où se trouve `docker-compose.yml`) :

```powershell
docker-compose up --build -d
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

```powershell
docker-compose logs -f
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

```powershell
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

1. Ouvrir **http://localhost:7474** dans le navigateur (Neo4j Browser).
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
   > près : la valeur littérale `admin` est explicitement acceptée comme
   > cas particulier, précisément pour permettre ce genre d'amorçage. Ce
   > compte `admin` sert uniquement à démarrer : voir l'étape 6.4 pour le
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
avec `curl` (ou tout client HTTP, y compris directement via la
documentation interactive `http://localhost:8000/docs`) :

```powershell
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d "{\"nom\": \"Run MCO\"}"
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d "{\"nom\": \"Build\"}"
curl -X POST http://localhost:8000/ref/domaines -H "Content-Type: application/json" -d "{\"nom\": \"Architecture\"}"
curl -X POST http://localhost:8000/ref/versions -H "Content-Type: application/json" -d "{\"nom\": \"N/A\"}"
```

*(Adapter les noms de domaines à l'organisation réelle de l'équipe — ceux
ci-dessus sont ceux utilisés historiquement dans ce projet. La version
`N/A` correspond à la valeur utilisée quand le champ « version » est laissé
vide dans le formulaire de la page Gestion.)*

Les **catégories de technologies** (`TechnoCategory`) et les
**technologies** (`Techno`) elles-mêmes n'ont pas besoin d'être pré-créées
en base : elles se créent normalement depuis la page **Gestion** de
l'application (section « Ajouter une compétence au référentiel »), via le
workflow de demande/validation habituel (voir le guide d'utilisation et
d'administration).

### 6.4 Se connecter et finaliser l'amorçage

1. Ouvrir **http://localhost**.
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

```powershell
docker compose ps
```

Les 4 services (`cartographie-neo4j`, `cartographie-backend`,
`cartographie-frontend`, `cartographie-proxy`) doivent être `Up`, et
`neo4j`/`backend` `(healthy)`.

```powershell
curl http://localhost:8000/health
```

Réponse attendue :

```json
{"ok":true,"neo4j_uri":"bolt://neo4j:7687"}
```

Puis dans le navigateur :
- **http://localhost** → page de connexion de l'application.
- **http://localhost:8000/docs** → documentation interactive de l'API
  (Swagger UI généré automatiquement par FastAPI), utile pour tester des
  appels sans passer par l'interface.
- **http://localhost:7474** → Neo4j Browser.

---

## 8. Restaurer une sauvegarde Neo4j existante (option alternative à l'étape 6)

Si une sauvegarde Neo4j (`.dump`, produite par `scripts/backup_neo4j.sh` —
voir le guide d'utilisation et d'administration) est disponible et doit
remplacer une base vide plutôt que de repartir de zéro :

```powershell
# 1. Arrêter neo4j (le chargement d'un dump exige la base hors ligne)
docker compose stop neo4j

# 2. Charger le dump sur le volume de données via un conteneur temporaire
docker run --rm `
  -v projet_cartographie_competences_neo4j_data:/data `
  -v "C:\chemin\vers\dossier\contenant\le\dump:/dumps" `
  neo4j:2026.03 `
  neo4j-admin database load neo4j --from-path=/dumps --overwrite-destination=true

# 3. Redémarrer neo4j
docker compose start neo4j
```

*(sous macOS/Linux, remplacer les retours à la ligne PowerShell `` ` `` par
`\`.)*

> Le tag de l'image `neo4j:2026.03` dans `docker-compose.yml` doit être
> **égal ou supérieur** à la version Neo4j qui a produit le dump — un dump
> plus récent que l'image cible ne peut pas être chargé.

Le nom exact du volume Docker (préfixé par le nom du dossier du projet) se
vérifie avec :

```powershell
docker volume ls
```

Si le script `scripts/restore_neo4j.sh` est utilisé à la place (restauration
**dans un conteneur `neo4j` déjà démarré**, différent de la méthode
ci-dessus qui restaure sur un volume à froid), se référer au guide
d'utilisation et d'administration, section sauvegarde/restauration.

Après restauration, se connecter avec un compte administrateur déjà présent
dans le dump — les étapes 6.2 et 6.3 ne sont alors pas nécessaires.

---

## 9. Déploiement sur un serveur de production

### 9.1 Prérequis serveur

- Un serveur **Linux** (Ubuntu ou Debian récent recommandé).
- Accès `sudo` ou root sur ce serveur.
- Un accès réseau (interne à l'entreprise, ou externe selon le contexte)
  vers ce serveur depuis les postes des utilisateurs.
- Idéalement, un nom d'hôte/DNS interne clair (ex. `cartographie-dba`)
  plutôt qu'une adresse IP brute — voir §9.5.

### 9.2 Installation de Docker sur le serveur

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
```

Vérifier :

```bash
docker version
docker compose version
```

### 9.3 Transfert du projet sur le serveur

Transférer l'intégralité du dossier du projet sur le serveur (via `git
clone`, `scp`, `rsync`, ou tout autre moyen conforme aux pratiques de
l'entreprise). Structure attendue une fois sur le serveur :

```
Projet_cartographie_competences/
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
cd Projet_cartographie_competences
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

### 9.6 Démarrage de la stack

```bash
docker compose up --build -d
```

Ou, en utilisant le script fourni qui automatise la copie de `.env` et le
démarrage :

```bash
./scripts/init_server.sh
```

Contenu de ce script, pour référence :

```bash
#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose up --build -d

echo "Stack démarrée."
echo "Frontend: http://localhost"
echo "Backend: http://localhost:8000/docs"
echo "Neo4j Browser: http://localhost:7474"
```

*(Le message affiché mentionne `localhost` car le script est générique ; sur
le serveur, remplacer mentalement par son nom DNS réel.)*

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
utilisées pour Neo4j Browser et `curl` (sauf si ces commandes sont exécutées
directement sur le serveur, auquel cas `localhost` reste valide car les
commandes s'exécutent alors sur la machine qui héberge les conteneurs).

### 9.9 Vérification finale

```bash
docker compose ps
curl http://localhost/            # via le proxy, doit répondre (page HTML)
curl http://localhost:8000/health # accès direct au backend
```

Puis, depuis un poste utilisateur, ouvrir l'URL choisie (ex.
`http://cartographie-dba`) dans un navigateur et vérifier que la page de
connexion s'affiche et qu'une connexion aboutit.

---

## 10. Commandes utiles

```powershell
docker compose ps                   # état des 4 conteneurs
docker compose logs -f              # suivre les logs de tous les services
docker compose logs -f backend      # suivre les logs d'un seul service
docker compose restart backend      # redémarrer un seul service
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
| `docker : terme non reconnu` | Docker Desktop pas installé, ou PATH pas rafraîchi | Réinstaller Docker Desktop, ou fermer/rouvrir le terminal |
| `request returned 500 Internal Server Error ... dockerDesktopLinuxEngine` | Docker Desktop encore en train de démarrer | Attendre que l'icône baleine soit stable puis réessayer |
| `wsl : la virtualisation n'est pas activée` | Fonctionnalité Windows « Virtual Machine Platform » désactivée, ou virtualisation désactivée au BIOS | `wsl --install --no-distribution` (terminal admin) puis redémarrer ; vérifier aussi le BIOS |
| Erreur CORS dans la console du navigateur (« has been blocked by CORS policy ») | L'origine utilisée pour ouvrir l'application n'est pas listée dans `CORS_ORIGINS` | Ajouter l'origine exacte (protocole + hostname + port) dans `.env`, puis `docker compose up -d --build backend` |
| `backend` reste `unhealthy` indéfiniment | Neo4j pas encore prêt, ou mauvais identifiants `NEO4J_USER`/`NEO4J_PASSWORD` | `docker compose logs backend` pour voir l'erreur exacte ; vérifier la cohérence entre `.env` et les identifiants attendus par Neo4j |
| Page de connexion accessible mais listes déroulantes vides sur la page Gestion | Base Neo4j vide, section 6.3 non réalisée | Exécuter les appels `curl` de la section 6.3 |
| Impossible de se connecter avec `admin` / mot de passe défini | Faute de frappe dans la requête Cypher de la section 6.2, ou compte `active: false` | Rouvrir Neo4j Browser, `MATCH (u:User {email:"admin"}) RETURN u;` pour vérifier l'existence et les valeurs exactes du nœud |
| `docker compose up` échoue avec un conflit de port (`port is already allocated`) | Un autre service utilise déjà le port 80, 8000, 7474 ou 7687 sur la machine | Arrêter le service en conflit, ou modifier la correspondance de ports dans `docker-compose.yml` (partie gauche du `"hôte:conteneur"`) |
| Le dump ne se charge pas (`Store copy failed` ou erreur de version) | Version de l'image `neo4j` inférieure à la version ayant produit le dump | Adapter le tag de l'image `neo4j` dans `docker-compose.yml` à une version égale ou supérieure, puis relancer |

Pour tout problème persistant, consulter les journaux détaillés :

```powershell
docker compose logs --tail=200 neo4j
docker compose logs --tail=200 backend
docker compose logs --tail=200 proxy
```
