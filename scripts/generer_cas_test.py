"""Génère les cas de test de sécurité sur disque (pour inspection / démo manuelle).

* ``tests/data/generes/fichiers_pieges/`` : faux .exe/.php/.html, SVG, GIF animé,
  bombe de décompression, polyglottes, fichiers tronqués/corrompus.
* ``tests/data/generes/formats_particuliers/`` : transparence, CMJN, 16 bits, EXIF.
* ``tests/data/generes/hors_domaine/`` : noir, blanc, bruit, texte, dessins, visage.
* ``tests/data/generes/adverses/`` : images attaquées (PGD/FGSM) prêtes à réuploader.
* ``tests/data/fruits/<classe>.png`` (avec ``--dataset``) : une photo de démonstration
  par classe, copiée du jeu de **test** (première image, par ordre alphabétique,
  correctement classée et acceptée par les défenses).

Exemple ::

    python scripts/generer_cas_test.py --dataset dataset
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend"))

from app import cas_test  # noqa: E402

DONNEES = RACINE / "tests" / "data"
DOSSIERS = {
    "apple_fresh": "freshapples",
    "apple_rotten": "rottenapples",
    "banana_fresh": "freshbanana",
    "banana_rotten": "rottenbanana",
    "orange_fresh": "freshoranges",
    "orange_rotten": "rottenoranges",
}


def ecrire_cas_synthetiques() -> None:
    sortie = DONNEES / "generes"
    for sous, cas in [
        ("fichiers_pieges", cas_test.FICHIERS_PIEGES),
        ("formats_particuliers", cas_test.FICHIERS_PARTICULIERS),
    ]:
        (sortie / sous).mkdir(parents=True, exist_ok=True)
        for nom, fabrique in cas.items():
            (sortie / sous / nom).write_bytes(fabrique())
    (sortie / "hors_domaine").mkdir(parents=True, exist_ok=True)
    for nom, fabrique in cas_test.IMAGES_HORS_DOMAINE.items():
        fabrique().save(sortie / "hors_domaine" / nom)
    print(f"Cas synthétiques écrits dans {sortie}")


def copier_fruits(dataset: Path) -> None:
    from app import ood
    from app.attaques import attaquer
    from app.config import parametres
    from app.preprocessing import tenseur_vers_image, vers_tenseur_modele
    from app.service import Contexte, analyser

    params = parametres()
    from app.inference import charger_modeles

    ctx = Contexte(
        modeles=charger_modeles(params),
        params=params,
        gardien=ood.StatsGardien.charger(params.fichier_stats_ood),
        seuils=ood.Seuils.charger(params.fichier_seuils),
    )
    if not ctx.seuils.calibre:
        print("Attention : seuils non calibrés, lancez d'abord scripts/calibrer_seuils.py")
    (DONNEES / "fruits").mkdir(parents=True, exist_ok=True)
    adverses = DONNEES / "generes" / "adverses"
    adverses.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    for classe, dossier in DOSSIERS.items():
        for chemin in sorted((dataset / "test" / dossier).iterdir())[:200]:
            image = Image.open(chemin).convert("RGB")
            base = analyser(ctx, image, "base")
            robuste = analyser(ctx, image, "robuste")
            if base.classe == classe and robuste.classe == classe and robuste.statut == "ok" and base.statut == "ok":
                shutil.copyfile(chemin, DONNEES / "fruits" / f"{classe}.png")
                print(f"{classe}: {chemin.name} (confiance robuste {robuste.confiance})")
                x = vers_tenseur_modele(image)
                k = ctx.modeles.info.classes.index(classe)
                for eps in (0.01, 0.03):
                    adv = attaquer(ctx.modeles.fruits["base"], x, "pgd", eps, k).x_adv
                    tenseur_vers_image(adv).save(adverses / f"{classe}_pgd_base_eps{eps}.png")
                break
        else:
            print(f"{classe}: aucune image satisfaisante trouvée")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, help="Dossier du dataset (train/ et test/) pour copier des fruits de démo")
    args = ap.parse_args()
    ecrire_cas_synthetiques()
    if args.dataset:
        copier_fruits(args.dataset)


if __name__ == "__main__":
    main()
