"""Calibration des seuils de détection hors domaine (OOD) de FreshRotten Guard.

Méthode (aucune valeur arbitraire) :

* **Ajustement du gardien** : empreintes MobileNetV2 de N images *d'entraînement*
  par classe → ACP + Gaussiennes par classe (covariance partagée régularisée).
* **Choix des seuils** sur la moitié A du jeu de *test* (images valides) :
  chaque seuil est le quantile qui ne rejette qu'une petite fraction cible
  d'images valides (taux de faux rejets visé, paramétrable).
* **Évaluation** sur la moitié B du test (jamais vue pendant le choix) et sur
  des images invalides : CIFAR-100 (personnes, animaux, véhicules, autres
  fruits…), images synthétiques (bruit, uniformes, texte, dessins) et, si
  présentes, vraies photos de ``tests/data/reelles/<categorie>/``.

Sorties dans ``backend/artefacts/`` : ``seuils.json``, ``stats_gardien.npz``,
``rapport_calibration.md``.

Exemple ::

    python scripts/calibrer_seuils.py --dataset dataset --cifar ~/.keras/datasets/cifar-100-python
"""

from __future__ import annotations

import argparse
import json
import pickle
import random
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "backend"))

from app import cas_test, ood  # noqa: E402
from app.config import parametres  # noqa: E402
from app.defenses import divergence_l1, purifier  # noqa: E402
from app.inference import Modeles, charger_modeles  # noqa: E402
from app.preprocessing import vers_tenseur_gardien, vers_tenseur_modele  # noqa: E402

DOSSIERS = {  # nom de dossier du dataset Kaggle → indice de classe (ordre de classes.json)
    "freshapples": 0,
    "rottenapples": 1,
    "freshbanana": 2,
    "rottenbanana": 3,
    "freshoranges": 4,
    "rottenoranges": 5,
}
CIFAR_GROUPES = {
    "personnes": ["baby", "boy", "girl", "man", "woman"],
    "animaux": [
        "bear",
        "camel",
        "cattle",
        "chimpanzee",
        "elephant",
        "fox",
        "kangaroo",
        "leopard",
        "lion",
        "rabbit",
        "raccoon",
        "squirrel",
        "tiger",
        "wolf",
        "hamster",
        "mouse",
        "skunk",
        "otter",
    ],
    "vehicules": ["bicycle", "bus", "motorcycle", "pickup_truck", "streetcar", "tank", "tractor", "train"],
    "autres_fruits_legumes": ["pear", "sweet_pepper", "mushroom"],
    "objets_scenes": [
        "bottle",
        "bowl",
        "clock",
        "cup",
        "keyboard",
        "lamp",
        "plate",
        "telephone",
        "television",
        "chair",
        "couch",
        "table",
        "road",
        "forest",
        "sea",
        "mountain",
    ],
}
FRR_QUALITE = 0.0025  # par contrôle de qualité
PLANCHERS = {
    "luminosite_min": 0.12,
    "contraste_min": 0.04,
    "nettete_min": 5.0,
    "luminosite_max": 0.97,
    "couleurs_min": 600,
}


# --------------------------------------------------------------- mesures
def mesurer(modeles: Modeles, images: list[Image.Image], etiquette: str, cache: Path | None) -> dict[str, np.ndarray]:
    """Calcule pour chaque image : empreinte, probas ImageNet, qualité, visages, logits/probas des 2 CNN."""
    if cache and (cache / f"{etiquette}.npz").exists():
        with np.load(cache / f"{etiquette}.npz", allow_pickle=False) as d:
            res = dict(d)
        if "C" not in res:  # mesure ajoutée après coup : calcul rapide, sans réseau
            res["C"] = np.array([ood.compter_couleurs(im) for im in images])
            np.savez(cache / f"{etiquette}.npz", **res)
        return res
    sortie: dict[str, list[np.ndarray]] = {k: [] for k in ["E", "PI", "Q", "H", "LB", "PB", "LR", "PR", "DB", "DR"]}
    t0 = time.time()
    for i in range(0, len(images), 32):
        lot = images[i : i + 32]
        xg = np.concatenate([vers_tenseur_gardien(im) for im in lot])
        xm = np.concatenate([vers_tenseur_modele(im) for im in lot])
        xp = np.concatenate([purifier(xm[j : j + 1], "median") for j in range(len(lot))])
        e, p = modeles.gardien.analyser(xg)
        sortie["E"].append(e)
        sortie["PI"].append(p)
        for nom, cle in [("base", "B"), ("robuste", "R")]:
            m = modeles.fruits[nom]
            probas = m.probabilites(xm)
            sortie["L" + cle].append(m.logits(xm))
            sortie["P" + cle].append(probas)
            pp = m.probabilites(xp)
            sortie["D" + cle].append(np.array([divergence_l1(a, b) for a, b in zip(probas, pp, strict=True)]))
        for im in lot:
            q = ood.mesurer_qualite(im)
            sortie["Q"].append(np.array([[q["luminosite"], q["contraste"], q["nettete"]]]))
            sortie["H"].append(np.array([ood.compter_visages(im)]))
        print(f"  {etiquette}: {min(i + 32, len(images))}/{len(images)} ({time.time() - t0:.0f} s)", flush=True)
    res = {k: np.concatenate(v) for k, v in sortie.items()}
    res["C"] = np.array([ood.compter_couleurs(im) for im in images])
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        np.savez(cache / f"{etiquette}.npz", **res)
    return res


def charger_dossier(dossier: Path, n_par_classe: int | None, graine: int) -> tuple[list[Path], np.ndarray]:
    rng = random.Random(graine)
    chemins, y = [], []
    for nom, k in DOSSIERS.items():
        fichiers = sorted((dossier / nom).iterdir())
        if n_par_classe:
            fichiers = rng.sample(fichiers, min(n_par_classe, len(fichiers)))
        chemins += fichiers
        y += [k] * len(fichiers)
    return chemins, np.array(y)


def ouvrir(chemins: list[Path]) -> list[Image.Image]:
    return [Image.open(c).convert("RGB") for c in chemins]


def charger_cifar(dossier: Path, n_par_groupe: int, graine: int) -> dict[str, list[Image.Image]]:
    """Images du jeu de test CIFAR-100 (32×32, agrandies en 224×224 bicubique)."""
    with open(dossier / "meta", "rb") as f:
        noms = pickle.load(f, encoding="latin1")["fine_label_names"]  # noqa: S301 — jeu public officiel
    with open(dossier / "test", "rb") as f:
        d = pickle.load(f, encoding="latin1")  # noqa: S301
    x = d["data"].reshape(-1, 3, 32, 32).transpose(0, 2, 3, 1)
    y = np.array(d["fine_labels"])
    rng = np.random.default_rng(graine)
    groupes = {}
    for groupe, classes in CIFAR_GROUPES.items():
        idx = np.flatnonzero(np.isin(y, [noms.index(c) for c in classes]))
        idx = rng.choice(idx, min(n_par_groupe, len(idx)), replace=False)
        groupes[f"cifar_{groupe}"] = [Image.fromarray(x[i]).resize((224, 224), Image.BICUBIC) for i in idx]
    return groupes


def charger_reelles(dossier: Path) -> dict[str, list[Image.Image]]:
    groupes: dict[str, list[Image.Image]] = {}
    if not dossier.exists():
        return groupes
    for sous in sorted(p for p in dossier.iterdir() if p.is_dir()):
        ims = [
            Image.open(f).convert("RGB")
            for f in sorted(sous.iterdir())
            if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        if ims:
            groupes[f"reelles_{sous.name}"] = ims
    return groupes


# ------------------------------------------------------------- décisions
def signaux(m: dict[str, np.ndarray], stats: ood.StatsGardien) -> list[ood.SignalGardien]:
    d = stats.distances(m["E"])
    autres = list(ood.IMAGENET_AUTRES_FRUITS)
    res = []
    for i in range(len(d)):
        k = int(np.argmin(d[i]))
        pa = m["PI"][i, autres]
        j = int(np.argmax(pa))
        res.append(
            ood.SignalGardien(
                distance=float(d[i, k]),
                fruit_proche=ood.FRUITS[k // 2],
                classe_proche=k,
                proba_autre_fruit=float(pa[j]),
                autre_fruit=ood.IMAGENET_AUTRES_FRUITS[autres[j]],
                proba_fruits_pris_en_charge=float(m["PI"][i, list(ood.IMAGENET_FRUITS_PRIS_EN_CHARGE)].sum()),
                visages=int(m["H"][i]),
                qualite={
                    "luminosite": float(m["Q"][i, 0]),
                    "contraste": float(m["Q"][i, 1]),
                    "nettete": float(m["Q"][i, 2]),
                    "couleurs": float(m["C"][i]),
                },
            )
        )
    return res


def decisions(m, sig, seuils, classes, nom_modele):
    cle = "B" if nom_modele == "base" else "R"
    return [ood.decider(m["L" + cle][i], m["P" + cle][i], sig[i], seuils, classes, nom_modele) for i in range(len(sig))]


def taux_rejet_par_couche(decs: list[ood.Decision]) -> dict[str, float]:
    noms = [c.nom for c in decs[0].controles if c.nom != "manipulation"]
    return {n: float(np.mean([not next(c for c in d.controles if c.nom == n).reussi for d in decs])) for n in noms}


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", type=Path, required=True, help="Dossier contenant train/ et test/ (6 sous-dossiers)")
    ap.add_argument("--cifar", type=Path, help="Dossier cifar-100-python (négatifs réels, optionnel)")
    ap.add_argument("--reelles", type=Path, default=RACINE / "tests" / "data" / "reelles")
    ap.add_argument("--par-classe-train", type=int, default=250)
    ap.add_argument("--par-groupe-cifar", type=int, default=200)
    ap.add_argument("--frr-gardien", type=float, default=0.02, help="Faux rejets visés pour la distance du gardien")
    ap.add_argument("--frr-incertitude", type=float, default=0.005, help="Faux rejets visés par seuil d'incertitude")
    ap.add_argument("--frr-autre-fruit", type=float, default=0.005)
    ap.add_argument("--dim", type=int, default=512, help="Dimensions conservées par l'ACP du gardien")
    ap.add_argument("--cache", type=Path, help="Dossier de cache des mesures (accélère les relances)")
    ap.add_argument("--graine", type=int, default=0)
    args = ap.parse_args()

    params = parametres()
    sortie = params.dossier_artefacts
    sortie.mkdir(parents=True, exist_ok=True)
    print("Chargement des modèles…")
    modeles = charger_modeles(params)
    classes = modeles.info.classes

    print("Mesures sur les images valides…")
    ch_tr, y_tr = charger_dossier(args.dataset / "train", args.par_classe_train, args.graine)
    m_tr = mesurer(modeles, ouvrir(ch_tr), "train", args.cache)
    ch_te, y_te = charger_dossier(args.dataset / "test", None, args.graine)
    m_te = mesurer(modeles, ouvrir(ch_te), "test", args.cache)
    rng = np.random.default_rng(args.graine)
    perm = rng.permutation(len(y_te))
    idx_a, idx_b = np.sort(perm[: len(perm) // 2]), np.sort(perm[len(perm) // 2 :])
    sel = lambda m, idx: {k: v[idx] for k, v in m.items()}  # noqa: E731
    m_a, m_b = sel(m_te, idx_a), sel(m_te, idx_b)
    y_a, y_b = y_te[idx_a], y_te[idx_b]

    print("Mesures sur les images invalides…")
    negatifs: dict[str, list[Image.Image]] = {
        "synthetiques": [f() for f in cas_test.IMAGES_HORS_DOMAINE.values()]
        + [cas_test.image_bruit(256, g) for g in range(20)],
    }
    if args.cifar and args.cifar.exists():
        negatifs.update(charger_cifar(args.cifar, args.par_groupe_cifar, args.graine))
    negatifs.update(charger_reelles(args.reelles))
    m_neg = {nom: mesurer(modeles, ims, nom, args.cache) for nom, ims in negatifs.items()}

    # 1) Gardien : ajustement sur le train uniquement.
    stats = ood.StatsGardien.ajuster(m_tr["E"], y_tr, dim=args.dim)
    dist_a = stats.distances(m_a["E"]).min(1)

    # 2) Seuils (moitié A du test).
    q = m_a["Q"]
    seuils = ood.Seuils(
        luminosite_min=min(float(np.quantile(q[:, 0], FRR_QUALITE)), PLANCHERS["luminosite_min"]),
        luminosite_max=max(float(np.quantile(q[:, 0], 1 - FRR_QUALITE)), PLANCHERS["luminosite_max"]),
        contraste_min=min(float(np.quantile(q[:, 1], FRR_QUALITE)), PLANCHERS["contraste_min"]),
        nettete_min=min(float(np.quantile(q[:, 2], FRR_QUALITE)), PLANCHERS["nettete_min"]),
        couleurs_min=int(min(float(np.quantile(m_a["C"], FRR_QUALITE)), PLANCHERS["couleurs_min"])),
        distance_max=float(np.quantile(dist_a, 1 - args.frr_gardien)),
        autre_fruit_min=max(
            0.5,
            float(np.quantile(m_a["PI"][:, list(ood.IMAGENET_AUTRES_FRUITS)].max(1), 1 - args.frr_autre_fruit)),
        ),
        visage_actif=True,
        calibre=True,
    )
    for nom, cle in [("base", "B"), ("robuste", "R")]:
        probas, logits = m_a["P" + cle], m_a["L" + cle]
        seuils.modeles[nom] = ood.SeuilsModele(
            confiance_min=float(np.quantile(probas.max(1), args.frr_incertitude)),
            entropie_max=float(np.quantile([ood.entropie(p) for p in probas], 1 - args.frr_incertitude)),
            energie_max=float(np.quantile([ood.energie(lg) for lg in logits], 1 - args.frr_incertitude)),
        )
    # Détection de manipulation : divergence brut / purifié sur images propres (1 % de fausses alertes).
    seuils.divergence_manipulation = float(np.quantile(np.concatenate([m_a["DR"], m_a["DB"]]), 0.99))

    # 3) Évaluation (moitié B + négatifs).
    sig_b = signaux(m_b, stats)
    rapport: dict[str, object] = {
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "methode": "Seuils choisis sur la moitié A du test, évalués sur la moitié B (jamais vue)",
        "images_valides": {"train_gardien": len(y_tr), "test_A": len(y_a), "test_B": len(y_b)},
        "frr_cibles": {
            "gardien": args.frr_gardien,
            "incertitude": args.frr_incertitude,
            "autre_fruit": args.frr_autre_fruit,
            "qualite": FRR_QUALITE,
        },
        "modeles": {},
    }
    for nom in ("robuste", "base"):
        decs_b = decisions(m_b, sig_b, seuils, classes, nom)
        acceptes = np.array([not d.rejet for d in decs_b])
        cle = "B" if nom == "base" else "R"
        pred = m_b["P" + cle].argmax(1)
        par_neg = {}
        for groupe, m in m_neg.items():
            decs = decisions(m, signaux(m, stats), seuils, classes, nom)
            codes: dict[str, int] = {}
            for d in decs:
                codes[d.code or "accepte"] = codes.get(d.code or "accepte", 0) + 1
            par_neg[groupe] = {
                "n": len(decs),
                "fausses_acceptations": float(np.mean([not d.rejet for d in decs])),
                "rejet_par_couche": taux_rejet_par_couche(decs),
                "raisons": codes,
            }
        rapport["modeles"][nom] = {
            "taux_faux_rejets": float(1 - acceptes.mean()),
            "rejet_par_couche_valides": taux_rejet_par_couche(decs_b),
            "precision_sans_filtre": float((pred == y_b).mean()),
            "faux_rejets_sur_bien_classees": float(1 - acceptes[pred == y_b].mean()),
            "erreurs_du_modele_interceptees": float(1 - acceptes[pred != y_b].mean()) if (pred != y_b).any() else 1.0,
            "precision_sur_acceptes": float((pred[acceptes] == y_b[acceptes]).mean()),
            "negatifs": par_neg,
        }
        print(
            f"[{nom}] faux rejets = {1 - acceptes.mean():.3f} ; "
            + " ; ".join(f"{g}: FA={v['fausses_acceptations']:.3f}" for g, v in par_neg.items())
        )

    d_b = stats.distances(m_b["E"])
    rapport["gardien_identifie_bon_fruit"] = float((d_b.argmin(1) // 2 == y_b // 2).mean())
    rapport["visages_faux_positifs_valides"] = float((m_b["H"] > 0).mean())
    seuils.rapport = rapport
    seuils.enregistrer(params.fichier_seuils)
    stats.enregistrer(params.fichier_stats_ood)
    ecrire_rapport_md(seuils, sortie / "rapport_calibration.md")
    print(f"Écrit : {params.fichier_seuils}, {params.fichier_stats_ood}, {sortie / 'rapport_calibration.md'}")


def ecrire_rapport_md(seuils: ood.Seuils, chemin: Path) -> None:
    r = seuils.rapport
    lignes = [
        "# Rapport de calibration des seuils hors domaine",
        "",
        f"Généré le {r['date']} par `scripts/calibrer_seuils.py`. {r['methode']}.",
        "",
        f"Images valides : {json.dumps(r['images_valides'])}. Taux de faux rejets visés : {json.dumps(r['frr_cibles'])}.",
        "",
        "## Seuils retenus",
        "",
        "| Seuil | Valeur |",
        "|---|---|",
    ]
    s = asdict(seuils)
    for k in [
        "luminosite_min",
        "luminosite_max",
        "contraste_min",
        "nettete_min",
        "distance_max",
        "autre_fruit_min",
        "divergence_manipulation",
    ]:
        lignes.append(f"| `{k}` | {s[k]:.4g} |")
    for nom, sm in s["modeles"].items():
        for k, v in sm.items():
            lignes.append(f"| `{nom}.{k}` | {v:.4g} |")
    lignes += [
        "",
        f"Le gardien identifie le bon fruit dans **{r['gardien_identifie_bon_fruit']:.1%}** des images valides "
        f"(moitié B). Faux positifs du détecteur de visages sur fruits : {r['visages_faux_positifs_valides']:.2%}.",
        "",
    ]
    for nom, m in r["modeles"].items():
        lignes += [
            f"## Modèle {nom}",
            "",
            f"* **Taux de faux rejets** (images valides rejetées) : **{m['taux_faux_rejets']:.1%}**",
            f"  * dont images que le modèle classait **correctement** : {m['faux_rejets_sur_bien_classees']:.1%} ; "
            f"**erreurs du modèle interceptées** : {m['erreurs_du_modele_interceptees']:.1%}",
            f"* Précision sans filtre : {m['precision_sans_filtre']:.1%} — sur les images acceptées : "
            f"{m['precision_sur_acceptes']:.1%}",
            "",
            "| Jeu d'images invalides | n | Fausses acceptations | Raison principale du rejet |",
            "|---|---|---|---|",
        ]
        for g, v in m["negatifs"].items():
            raisons = {k: n for k, n in v["raisons"].items() if k != "accepte"}
            principale = max(raisons, key=raisons.get) if raisons else "—"
            lignes.append(f"| {g} | {v['n']} | **{v['fausses_acceptations']:.1%}** | {principale} |")
        lignes += [
            "",
            "Taux de rejet par couche (seule) :",
            "",
            "| Couche | Valides (faux rejets) | " + " | ".join(m["negatifs"]) + " |",
            "|---|---|" + "---|" * len(m["negatifs"]),
        ]
        for couche, v in m["rejet_par_couche_valides"].items():
            lignes.append(
                f"| {couche} | {v:.1%} | "
                + " | ".join(f"{m['negatifs'][g]['rejet_par_couche'][couche]:.1%}" for g in m["negatifs"])
                + " |"
            )
        lignes.append("")
    lignes += [
        "## Limites",
        "",
        "* Les images CIFAR-100 font 32×32 pixels (agrandies) : elles sont floues, la couche « netteté » en rejette "
        "une partie. Ajoutez de vraies photos dans `tests/data/reelles/<categorie>/` puis relancez.",
        "* Le dataset a des fonds assez homogènes : une photo de fruit très différente (fond chargé, plusieurs "
        "fruits) peut être rejetée par prudence (faux rejet) plutôt que mal classée.",
    ]
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
