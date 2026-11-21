"""Crée l'empreinte (scrypt) d'un compte FreshRotten Guard.

Le mot de passe est saisi sans écho (ou généré aléatoirement) ; seule son
empreinte est écrite. Exemple ::

    python scripts/creer_compte.py jury            # demande le mot de passe
    python scripts/creer_compte.py jury --generer  # génère un mot de passe fort

Copiez ensuite la ligne FRG_COMPTES affichée dans votre fichier .env (local)
ou dans les secrets du Space Hugging Face.
"""

from __future__ import annotations

import argparse
import getpass
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.auth import hacher_mot_de_passe


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("identifiant")
    ap.add_argument("--generer", action="store_true", help="Génère un mot de passe aléatoire fort")
    args = ap.parse_args()
    if args.generer:
        mot_de_passe = secrets.token_urlsafe(12)
        print(f"Mot de passe généré (à noter, il ne sera plus affiché) : {mot_de_passe}")
    else:
        mot_de_passe = getpass.getpass("Mot de passe : ")
        if len(mot_de_passe) < 10:
            sys.exit("Mot de passe trop court (10 caractères minimum).")
        if getpass.getpass("Confirmation : ") != mot_de_passe:
            sys.exit("Les mots de passe ne correspondent pas.")
    print("FRG_COMPTES=" + json.dumps({args.identifiant: hacher_mot_de_passe(mot_de_passe)}))


if __name__ == "__main__":
    main()
