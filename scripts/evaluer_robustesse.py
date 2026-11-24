"""Mesure la robustesse naturelle et l'effet de la purification → ``backend/artefacts/robustesse.json``.

Ce fichier alimente la section « Robustesse naturelle » et le tableau
« Coût et effet de la purification » du tableau de bord (page Laboratoire,
``GET /api/metriques``). Sans lui, ces deux blocs ne s'affichent pas.

* **Transformations naturelles** : précision des deux modèles (sans filtre hors
  domaine) sur des images de test transformées (miroir, rotation, flou, bruit…),
  les mêmes que les scénarios « Robustesse naturelle » de la galerie.
* **Purification** : précision sur images propres et sous PGD ε = 0,03
  (attaque en boîte blanche contre chaque modèle, l'attaquant ignore la purification).

Exemple ::

    python scripts/evaluer_robustesse.py --dataset dataset --par-classe 50
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend"))

from app.attaques import module_origine  # noqa: E402
from app.config import parametres  # noqa: E402
from app.defenses import METHODES, purifier  # noqa: E402
from app.inference import charger_modeles  # noqa: E402
from app.preprocessing import vers_tenseur_modele  # noqa: E402
from app.scenarios import TRANSFORMATIONS  # noqa: E402

DOSSIERS = {  # nom de dossier du dataset Kaggle → indice de classe (ordre de classes.json)
    "freshapples": 0,
    "rottenapples": 1,
    "freshbanana": 2,
    "rottenbanana": 3,
    "freshoranges": 4,
    "rottenoranges": 5,
}
TITRES_PURIFICATION = {
    "aucune": "Aucune",
    "jpeg": "Compression JPEG (q = 75)",
    "bits": "Réduction de profondeur (5 bits)",
    "median": "Filtre médian 3×3",
}
EPS_PGD = 0.03
LOT = 32


def echantillon(dossier: Path, n_par_classe: int, graine: int) -> tuple[list[Path], np.ndarray]:
    rng = random.Random(graine)
    chemins, y = [], []
    for nom, k in DOSSIERS.items():
        fichiers = sorted((dossier / nom).iterdir())
        fichiers = rng.sample(fichiers, min(n_par_classe, len(fichiers)))
        chemins += fichiers
        y += [k] * len(fichiers)
    return chemins, np.array(y)


def tenseurs(images: list[Image.Image]) -> np.ndarray:
    return np.concatenate([vers_tenseur_modele(im) for im in images])


def predire(modele, x: np.ndarray) -> np.ndarray:
    return np.concatenate([modele.probabilites(x[i : i + LOT]).argmax(1) for i in range(0, len(x), LOT)])


def purifier_lot(x: np.ndarray, methode: str) -> np.ndarray:
    if methode == "aucune":
        return x
    return np.concatenate([purifier(x[i : i + 1], methode) for i in range(len(x))])


def pgd_lot(modele, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    orig = module_origine()
    sorties = []
    for i in range(0, len(x), LOT):
        y_oh = np.eye(6, dtype="float32")[y[i : i + LOT]]
        sorties.append(np.asarray(orig.pgd(modele.keras, x[i : i + LOT], y_oh, EPS_PGD, steps=10), dtype="float32"))
    return np.concatenate(sorties)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, required=True, help="Dossier contenant test/ (6 sous-dossiers)")
    ap.add_argument("--par-classe", type=int, default=50, help="Images de test par classe")
    ap.add_argument("--graine", type=int, default=0)
    args = ap.parse_args()

    params = parametres()
    modeles = charger_modeles(params)
    chemins, y = echantillon(args.dataset / "test", args.par_classe, args.graine)
    images = [Image.open(c).convert("RGB") for c in chemins]
    print(f"{len(images)} images de test chargées")

    transformations = {}
    for cle, (titre, transformer) in TRANSFORMATIONS.items():
        x = tenseurs([transformer(im) for im in images])
        transformations[cle] = {
            "titre": titre,
            **{nom: round(float((predire(m, x) == y).mean()), 4) for nom, m in modeles.fruits.items()},
        }
        print(f"  {titre:<32} base {transformations[cle]['base']:.1%}  robuste {transformations[cle]['robuste']:.1%}")

    x_propre = tenseurs(images)
    x_pgd = {nom: pgd_lot(m, x_propre, y) for nom, m in modeles.fruits.items()}
    purification = {}
    for methode in ("aucune", *METHODES):
        ligne: dict[str, object] = {"titre": TITRES_PURIFICATION[methode]}
        for nom, m in modeles.fruits.items():
            ligne[f"propre_{nom}"] = round(float((predire(m, purifier_lot(x_propre, methode)) == y).mean()), 4)
            ligne[f"pgd_{nom}"] = round(float((predire(m, purifier_lot(x_pgd[nom], methode)) == y).mean()), 4)
        purification[methode] = ligne
        print(f"  {ligne['titre']:<32} {ligne}")

    sortie = params.dossier_artefacts / "robustesse.json"
    sortie.write_text(
        json.dumps(
            {
                "date": time.strftime("%Y-%m-%d %H:%M"),
                "n_images": len(images),
                "transformations": transformations,
                "purification": purification,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"Écrit : {sortie}")


if __name__ == "__main__":
    main()
