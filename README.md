# FreshRotten Guard

Classification **frais / pourri** de pommes, bananes et oranges, avec des défenses de
sécurité de l'IA : rejet des images hors domaine, résistance aux attaques adversariales
et validation stricte des fichiers. Aucune image n'est stockée : tout est traité en mémoire.

- **Backend** : FastAPI + TensorFlow/Keras (`backend/`)
- **Frontend** : React 19 + Vite + Tailwind (`frontend/`)
- **Modèles** : deux CNN 128×128 entraînés de zéro (`model/`)

| Modèle | Précision propre | Sous FGSM ε=0,03 | Sous PGD ε=0,03 |
|---|---|---|---|
| Base (`FreshRotten_model.keras`) | 99,7 % | 29,5 % | 0,4 % |
| Robuste, entraînement adversarial (`FreshRotten_model_robuste.keras`) | 96,2 % | 84,2 % | 79,6 % |

## Démarrage rapide

Prérequis : Python 3.11 ou 3.12, Node.js 20+.

```bash
make install        # crée .venv et installe les dépendances backend + frontend
cp .env.example .env
make dev            # backend http://127.0.0.1:8000/docs, application http://127.0.0.1:5173
```

Si le port 8000 est déjà pris : `BACKEND_PORT=8001 make dev`.
Sous Windows : `powershell -ExecutionPolicy Bypass -File .\dev.ps1`.

Au premier lancement, le backend télécharge les poids ImageNet de MobileNetV2 (~14 Mo,
empreinte SHA-256 vérifiée) dans `~/.keras/models`.

## L'application

| Onglet | Rôle |
|---|---|
| Webcam | Analyse en direct de la zone de visée, verdict lissé, bouton « Figer » |
| Analyser une image | Upload, purification d'entrée optionnelle, comparaison base / robuste |
| Laboratoire de sécurité | Attaques FGSM / PGD / PGD ciblée, galerie de scénarios, tableau de bord, rapport de sécurité |
| À propos | Fonctionnement et limites |

## Les défenses

1. **Fichiers** (`securite_fichiers.py`) : octets magiques, JPEG/PNG/WebP seulement, refus des
   SVG, GIF, images animées, polyglottes, bombes de décompression ; métadonnées supprimées ;
   traitement entièrement en mémoire.
2. **Hors domaine** (`ood.py`), en 6 couches calibrées : qualité de l'image, détection de
   visages, gardien MobileNetV2 (distance de Mahalanobis au dataset), autre fruit vu par
   ImageNet, incertitude du CNN (confiance, entropie, énergie), cohérence gardien / CNN.
3. **Adversarial** : modèle robuste par défaut, purification optionnelle (JPEG, 5 bits,
   médian) et détection de manipulation par *feature squeezing* (`defenses.py`).
4. **Modèle et serveur** : empreinte SHA-256 des modèles vérifiée avant chargement,
   `safe_mode` Keras, probabilités arrondies et logits jamais exposés, limitation de débit,
   file d'inférence bornée (503), en-têtes de sécurité, erreurs sans détail interne,
   journaux JSON avec IP hachée.

## Configuration

Toutes les variables sont préfixées par `FRG_` (voir `.env.example`, lues depuis `.env` à la
racine). Une variable laissée vide prend sa valeur par défaut. Les seuils hors domaine ne se
règlent pas à la main : ils sont produits par `scripts/calibrer_seuils.py`.

## Commandes

| Commande | Effet |
|---|---|
| `make test` | Tests unitaires backend (pytest) et frontend (vitest) |
| `make test-securite` | Suite de sécurité ; régénère `backend/artefacts/rapport_securite.{md,json}` |
| `make lint` | Ruff, ESLint, TypeScript |
| `make audit` | Vulnérabilités connues des dépendances (pip-audit, npm audit) |
| `make cas-test DATASET=…` | Cas de test sur disque + une photo de démo par classe |
| `make robustesse DATASET=…` | `backend/artefacts/robustesse.json` (tableau de bord) |
| `make calibrer DATASET=…` | Recalibre les seuils hors domaine (long) |

## Données (non versionnées)

Le dataset Kaggle *Fruits fresh and rotten for classification* (`train/` et `test/`, 6
sous-dossiers `freshapples`, `rottenbanana`…) n'est pas dans le dépôt. Il sert à :

- `make cas-test DATASET=chemin/vers/dataset` : copie une photo par classe dans
  `tests/data/fruits/`. **Sans ces photos, 21 scénarios du Laboratoire sont indisponibles**
  (contrôles sur fruits valides, attaques, robustesse naturelle).
- `make robustesse` : sans `robustesse.json`, la section « Robustesse naturelle » du tableau
  de bord ne s'affiche pas.

Vous pouvez aussi déposer de vraies photos hors domaine dans `tests/data/reelles/<categorie>/` :
elles apparaissent dans la galerie et servent à la calibration.

## Déploiement

- **Backend** : Space Hugging Face (SDK Docker) avec `python scripts/deployer_hf.py --origine
  https://votre-frontend` (nécessite `hf auth login`). Image locale :
  `docker build -f backend/Dockerfile -t freshrotten-guard .`
- **Frontend** : `npm run build` avec `VITE_API_URL=https://<space>.hf.space`.

## Structure

```
backend/app/        API FastAPI, inférence, défenses, attaques, scénarios
backend/artefacts/  seuils calibrés, statistiques du gardien, rapports
backend/tests/      tests unitaires et suite de sécurité (tests/securite)
frontend/src/       application React
model/              modèles .keras, classes.json, resultats.json, attaques.py, figures
scripts/            calibration, cas de test, robustesse, déploiement
```
