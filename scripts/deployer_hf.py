"""Publie le backend sur un Space Hugging Face (SDK Docker).

Prérequis : ``hf auth login`` avec un jeton « Write » (le jeton n'est jamais lu
ni affiché par ce script : huggingface_hub l'utilise directement).

Exemple ::

    python scripts/deployer_hf.py --origine https://freshrotten-guard.vercel.app

Le Space contient uniquement ce qui est nécessaire à l'exécution : Dockerfile,
``model/``, ``backend/app``, ``backend/artefacts`` et les dépendances. Ni le
dataset, ni les tests, ni l'environnement local ne sont envoyés.
"""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

RACINE = Path(__file__).resolve().parents[1]
ENTETE_README = """---
title: FreshRotten Guard API
emoji: 🍌
colorFrom: green
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: API frais/pourri avec défenses de sécurité de l'IA
---

# FreshRotten Guard — API

Backend FastAPI de FreshRotten Guard (classification frais / pourri de pommes,
bananes et oranges, avec détection hors domaine, défenses adversariales et
validation stricte des fichiers). Documentation interactive : `/docs`.

Aucune image n'est stockée : tout est traité en mémoire.
"""


def lire_env(chemin: Path) -> dict[str, str]:
    """Lit un fichier .env simple (CLE=valeur), sans l'afficher."""
    valeurs: dict[str, str] = {}
    if chemin.exists():
        for ligne in chemin.read_text(encoding="utf-8").splitlines():
            if "=" in ligne and not ligne.lstrip().startswith("#"):
                cle, valeur = ligne.split("=", 1)
                valeurs[cle.strip()] = valeur.strip()
    return valeurs


def preparer(dossier: Path) -> None:
    ignorer = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    shutil.copy(RACINE / "backend" / "Dockerfile", dossier / "Dockerfile")
    shutil.copytree(RACINE / "model", dossier / "model", ignore=ignorer)
    (dossier / "backend").mkdir()
    for element in ["app", "artefacts"]:
        shutil.copytree(RACINE / "backend" / element, dossier / "backend" / element, ignore=ignorer)
    for fichier in ["requirements.txt", "pyproject.toml"]:
        shutil.copy(RACINE / "backend" / fichier, dossier / "backend" / fichier)
    (dossier / "README.md").write_text(ENTETE_README, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space", default="freshrotten-guard", help="Nom du Space")
    ap.add_argument("--origine", action="append", default=[], help="Origine(s) autorisée(s) par CORS (frontend)")
    args = ap.parse_args()

    api = HfApi()
    utilisateur = api.whoami()["name"]
    depot = f"{utilisateur}/{args.space}"
    api.create_repo(depot, repo_type="space", space_sdk="docker", exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        preparer(Path(tmp))
        api.upload_folder(
            folder_path=tmp,
            repo_id=depot,
            repo_type="space",
            commit_message="Déploiement du backend FreshRotten Guard",
            delete_patterns=["*"],  # le Space reflète exactement l'état local
        )

    origines = args.origine or ["http://localhost:5173"]
    api.add_space_variable(depot, "FRG_ORIGINES_CORS", json.dumps(origines))
    api.add_space_variable(depot, "FRG_MODELE_ACTIF", "robuste")
    # Secrets générés ici, jamais affichés : sel de hachage des IP et clé de signature des sessions.
    api.add_space_secret(depot, "FRG_SEL_HACHAGE_IP", secrets.token_hex(32))
    api.add_space_secret(depot, "FRG_SECRET_SESSION", secrets.token_hex(32))
    # Comptes : uniquement les EMPREINTES scrypt, lues dans le .env local.
    comptes = lire_env(RACINE / ".env").get("FRG_COMPTES")
    if comptes and json.loads(comptes):
        api.add_space_secret(depot, "FRG_COMPTES", comptes)
        print(f"Comptes transmis (empreintes) : {', '.join(json.loads(comptes))}")
    else:
        print("ATTENTION : aucun compte dans .env (scripts/creer_compte.py) : personne ne pourra se connecter.")

    sous_domaine = depot.replace("/", "-").replace("_", "-").lower()
    print(f"Space : https://huggingface.co/spaces/{depot}")
    print(f"API   : https://{sous_domaine}.hf.space  (construction en cours, quelques minutes)")
    print(f"CORS  : {origines}")


if __name__ == "__main__":
    main()
