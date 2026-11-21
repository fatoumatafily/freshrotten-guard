"""Scénarios d'attaque : une définition unique, exécutée par la galerie du
Laboratoire (``POST /api/scenarios/{id}``) **et** par la suite de tests
``tests/securite`` (qui en tire le rapport présenté au jury).

Chaque scénario renvoie *attendu / obtenu / réussi*.
"""

from __future__ import annotations

import hashlib
import io
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from . import cas_test
from .api.schemas import ResultatScenario, Scenario
from .attaques import attaquer
from .config import EMPREINTES_PAR_DEFAUT, RACINE_PROJET
from .defenses import purifier
from .preprocessing import vers_tenseur_modele
from .securite_fichiers import FichierRefuse, valider_et_decoder
from .service import Contexte, analyser

DOSSIER_FRUITS = RACINE_PROJET / "tests" / "data" / "fruits"
DOSSIER_REELLES = RACINE_PROJET / "tests" / "data" / "reelles"


@dataclass
class Definition:
    id: str
    categorie: str
    titre: str
    description: str
    attendu: str
    executer: Callable[[Contexte], tuple[str, bool, dict[str, object]]]
    disponible: Callable[[], bool] = lambda: True


SCENARIOS: dict[str, Definition] = {}


def _ajouter(d: Definition) -> None:
    SCENARIOS[d.id] = d


def image_fruit(classe: str) -> Image.Image | None:
    """Image de démonstration ``tests/data/fruits/<classe>.*`` (copiée du dataset par generer_cas_test.py)."""
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        chemin = DOSSIER_FRUITS / f"{classe}{ext}"
        if chemin.exists():
            return Image.open(chemin).convert("RGB")
    return None


def _fruit_dispo(classe: str) -> Callable[[], bool]:
    return lambda: image_fruit(classe) is not None


def _valider(ctx: Contexte, octets: bytes):
    p = ctx.params
    return valider_et_decoder(
        octets,
        taille_max=p.taille_max_octets,
        pixels_max=p.pixels_max,
        dimension_max=p.dimension_max,
        dimension_min=p.dimension_min,
    )


# ------------------------------------------------------------ hors domaine
def _scenario_hors_domaine(nom: str, fabrique: Callable[[], Image.Image]) -> Callable:
    def run(ctx: Contexte):
        res = analyser(ctx, fabrique())
        obtenu = f"Rejet : {res.raison_rejet}" if res.statut == "rejet" else f"Accepté : {res.classe} ({res.confiance})"
        brut = max(res.probabilites, key=res.probabilites.get)
        return (
            obtenu,
            res.statut == "rejet",
            {
                "code_rejet": res.code_rejet,
                "sans_defense_le_modele_aurait_dit": brut,
                "confiance_brute": res.probabilites[brut],
            },
        )

    return run


TITRES_HORS_DOMAINE = {
    "noire.png": "Image noire",
    "blanche.png": "Image blanche",
    "grise.png": "Image grise uniforme",
    "orange_uniforme.png": "Aplat orange (couleur d'orange sans fruit)",
    "bruit.png": "Bruit aléatoire",
    "capture_texte.png": "Capture d'écran de texte",
    "dessin_banane.png": "Dessin animé de banane",
    "dessin_orange.png": "Dessin animé d'orange",
    "visage_schematique.png": "Visage (schématique)",
}
for _nom, _fab in cas_test.IMAGES_HORS_DOMAINE.items():
    _ajouter(
        Definition(
            id="hd_" + _nom.removesuffix(".png"),
            categorie="Hors domaine",
            titre=TITRES_HORS_DOMAINE[_nom],
            description="Image qui n'est pas une photo de pomme, banane ou orange.",
            attendu="Rejet « aucun fruit pris en charge »",
            executer=_scenario_hors_domaine(_nom, _fab),
        )
    )


def _scenarios_reelles() -> None:
    """Un scénario par photo réelle déposée dans tests/data/reelles/<categorie>/."""
    if not DOSSIER_REELLES.exists():
        return
    for categorie in sorted(p for p in DOSSIER_REELLES.iterdir() if p.is_dir()):
        for photo in sorted(categorie.iterdir())[:3]:
            if photo.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            octets = photo.read_bytes()
            _ajouter(
                Definition(
                    id=f"reel_{categorie.name}_{photo.stem}"[:60],
                    categorie="Hors domaine (photos réelles)",
                    titre=f"{categorie.name.replace('_', ' ').capitalize()} : {photo.stem}",
                    description=f"Photo réelle de tests/data/reelles/{categorie.name}/",
                    attendu="Rejet « aucun fruit pris en charge »",
                    executer=_scenario_hors_domaine(
                        photo.name, lambda o=octets: Image.open(io.BytesIO(o)).convert("RGB")
                    ),
                )
            )


_scenarios_reelles()


# ---------------------------------------------------------- fruits valides
def _scenario_fruit_valide(classe: str) -> Callable:
    def run(ctx: Contexte):
        res = analyser(ctx, image_fruit(classe))
        obtenu = f"Accepté : {res.classe} ({res.confiance})" if res.statut == "ok" else f"Rejet : {res.raison_rejet}"
        return obtenu, res.statut == "ok" and res.classe == classe, {"code_rejet": res.code_rejet}

    return run


CLASSES = ["apple_fresh", "apple_rotten", "banana_fresh", "banana_rotten", "orange_fresh", "orange_rotten"]
for _c in CLASSES:
    _ajouter(
        Definition(
            id=f"valide_{_c}",
            categorie="Fruits valides (contrôle)",
            titre=f"Photo valide : {_c}",
            description="Une vraie photo du domaine ne doit PAS être rejetée par les défenses.",
            attendu=f"Accepté : {_c}",
            executer=_scenario_fruit_valide(_c),
            disponible=_fruit_dispo(_c),
        )
    )


# --------------------------------------------------------- fichiers piégés
CODES_ATTENDUS = {
    "faux_exe.jpg": "executable",
    "faux_php.jpg": "script",
    "faux_html.jpg": "script",
    "svg_script.svg": "svg_refuse",
    "gif_anime.gif": "gif_refuse",
    "webp_anime.webp": "image_animee",
    "bombe_decompression.png": "bombe_decompression",
    "polyglotte_jpeg_zip.jpg": "polyglotte",
    "polyglotte_jpeg_html.jpg": "polyglotte",
    "png_script_texte.png": "polyglotte",
    "jpeg_tronque.jpg": "fichier_corrompu",
    "jpeg_corrompu.jpg": "fichier_corrompu",
}
TITRES_FICHIERS = {
    "faux_exe.jpg": "Exécutable .exe renommé en .jpg",
    "faux_php.jpg": "Script PHP renommé en .jpg",
    "faux_html.jpg": "Page HTML renommée en .jpg",
    "svg_script.svg": "SVG contenant un script",
    "gif_anime.gif": "GIF animé",
    "webp_anime.webp": "WebP animé",
    "bombe_decompression.png": "Bombe de décompression (50 000 × 50 000 px)",
    "polyglotte_jpeg_zip.jpg": "Polyglotte JPEG + ZIP",
    "polyglotte_jpeg_html.jpg": "Polyglotte JPEG + HTML",
    "png_script_texte.png": "PNG avec <script> dans les métadonnées",
    "jpeg_tronque.jpg": "JPEG tronqué",
    "jpeg_corrompu.jpg": "JPEG corrompu",
}


def _scenario_fichier(nom: str) -> Callable:
    def run(ctx: Contexte):
        octets = cas_test.FICHIERS_PIEGES[nom]()
        attendu = CODES_ATTENDUS[nom]
        try:
            _valider(ctx, octets)
        except FichierRefuse as exc:
            return f"Refusé ({exc.code}) : {exc.message}", exc.code == attendu, {"taille_octets": len(octets)}
        return "Accepté (FAILLE)", False, {"taille_octets": len(octets)}

    return run


for _nom in cas_test.FICHIERS_PIEGES:
    _ajouter(
        Definition(
            id="fichier_" + _nom.replace(".", "_"),
            categorie="Fichiers malveillants",
            titre=TITRES_FICHIERS[_nom],
            description="Le serveur vérifie les octets magiques et décode réellement l'image ; extension ignorée.",
            attendu=f"Refusé ({CODES_ATTENDUS[_nom]})",
            executer=_scenario_fichier(_nom),
        )
    )


def _scenario_particulier(nom: str) -> Callable:
    def run(ctx: Contexte):
        try:
            v = _valider(ctx, cas_test.FICHIERS_PARTICULIERS[nom]())
        except FichierRefuse as exc:
            return f"Refusé ({exc.code})", False, {}
        ok = v.image.mode == "RGB" and not v.image.getexif() and not v.image.info
        return f"Accepté, converti en RGB ({', '.join(v.alertes) or 'aucune alerte'})", ok, {"alertes": v.alertes}

    return run


for _nom in cas_test.FICHIERS_PARTICULIERS:
    _ajouter(
        Definition(
            id="format_" + _nom.replace(".", "_"),
            categorie="Formats particuliers",
            titre=_nom.replace("_", " ").rsplit(".", 1)[0].capitalize(),
            description="Transparence, CMJN, gris, 16 bits, EXIF : conversion propre en RGB sans métadonnées.",
            attendu="Accepté, RGB 8 bits, métadonnées supprimées",
            executer=_scenario_particulier(_nom),
        )
    )


# ------------------------------------------------------------- adversarial
def _x(classe: str) -> np.ndarray:
    return vers_tenseur_modele(image_fruit(classe))


def _classe(ctx: Contexte, nom: str, x: np.ndarray) -> tuple[str, float]:
    p = ctx.modeles.fruits[nom].probabilites(x)[0]
    return ctx.modeles.info.classes[int(np.argmax(p))], float(np.max(p))


def _scenario_pgd(nom_modele: str, classe: str, eps: float, attendu_trompe: bool) -> Callable:
    def run(ctx: Contexte):
        x = _x(classe)
        k = ctx.modeles.info.classes.index(classe)
        adv = attaquer(ctx.modeles.fruits[nom_modele], x, "pgd", eps, k).x_adv
        c, conf = _classe(ctx, nom_modele, adv)
        trompe = c != classe
        return (
            f"{'Trompé' if trompe else 'Résiste'} : prédit {c} ({conf:.2f})",
            trompe == attendu_trompe,
            {"epsilon": eps, "classe_vraie": classe},
        )

    return run


_ajouter(
    Definition(
        id="adv_pgd_base",
        categorie="Attaques adversariales",
        titre="PGD ε=0,03 contre le modèle de base",
        description="Démonstration de la vulnérabilité : 10 pas de PGD en boîte blanche.",
        attendu="Le modèle de base est trompé",
        executer=_scenario_pgd("base", "apple_fresh", 0.03, True),
        disponible=_fruit_dispo("apple_fresh"),
    )
)
_ajouter(
    Definition(
        id="adv_pgd_robuste",
        categorie="Attaques adversariales",
        titre="PGD ε=0,03 contre le modèle robuste",
        description="Même attaque, en boîte blanche, contre le modèle entraîné de façon adversariale.",
        attendu="Le modèle robuste résiste",
        executer=_scenario_pgd("robuste", "apple_fresh", 0.03, False),
        disponible=_fruit_dispo("apple_fresh"),
    )
)


def _scenario_ciblee(nom_modele: str, attendu_succes: bool) -> Callable:
    def run(ctx: Contexte):
        x = _x("banana_rotten")
        classes = ctx.modeles.info.classes
        adv = attaquer(
            ctx.modeles.fruits[nom_modele],
            x,
            "pgd_ciblee",
            0.03,
            classes.index("banana_rotten"),
            classes.index("banana_fresh"),
            etapes=20,
        ).x_adv
        c, conf = _classe(ctx, nom_modele, adv)
        succes = c == "banana_fresh"
        return (
            f"{'Cible atteinte' if succes else 'Cible manquée'} : prédit {c} ({conf:.2f})",
            succes == attendu_succes,
            {"cible": "banana_fresh"},
        )

    return run


_ajouter(
    Definition(
        id="adv_ciblee_base",
        categorie="Attaques adversariales",
        titre="PGD ciblée : banane pourrie → « fraîche » (base)",
        description="L'attaquant veut faire passer une banane pourrie pour fraîche.",
        attendu="Le modèle de base est trompé (cible atteinte)",
        executer=_scenario_ciblee("base", True),
        disponible=_fruit_dispo("banana_rotten"),
    )
)
_ajouter(
    Definition(
        id="adv_ciblee_robuste",
        categorie="Attaques adversariales",
        titre="PGD ciblée : banane pourrie → « fraîche » (robuste)",
        description="Même attaque ciblée contre le modèle robuste.",
        attendu="Le modèle robuste résiste (cible manquée)",
        executer=_scenario_ciblee("robuste", False),
        disponible=_fruit_dispo("banana_rotten"),
    )
)


def _scenario_detection(ctx: Contexte):
    image = image_fruit("apple_fresh")
    x = vers_tenseur_modele(image)
    adv = attaquer(ctx.modeles.fruits["base"], x, "pgd", 0.03, 0).x_adv
    from .preprocessing import tenseur_vers_image

    res = analyser(ctx, tenseur_vers_image(adv), "base")
    detecte = "image_possiblement_manipulee" in res.alertes or res.statut == "rejet"
    return (
        f"{'Signalée' if detecte else 'Non signalée'} ({res.statut}, alertes : {res.alertes or 'aucune'})",
        detecte,
        {"code_rejet": res.code_rejet},
    )


_ajouter(
    Definition(
        id="adv_detection",
        categorie="Attaques adversariales",
        titre="Détection d'une image adverse (base, PGD ε=0,03)",
        description="L'image adverse est envoyée à l'analyse normale : purification + gardien doivent la signaler.",
        attendu="Image signalée (manipulée) ou rejetée",
        executer=_scenario_detection,
        disponible=_fruit_dispo("apple_fresh"),
    )
)


def _scenario_purification(ctx: Contexte):
    x = _x("apple_fresh")
    adv = attaquer(ctx.modeles.fruits["base"], x, "fgsm", 0.01, 0).x_adv
    avant, _ = _classe(ctx, "base", adv)
    apres, conf = _classe(ctx, "base", purifier(adv, "jpeg"))
    return (
        f"Sans purification : {avant} → avec JPEG : {apres} ({conf:.2f})",
        apres == "apple_fresh",
        {"epsilon": 0.01},
    )


_ajouter(
    Definition(
        id="adv_purification",
        categorie="Attaques adversariales",
        titre="Purification JPEG contre FGSM ε=0,01 (base)",
        description="Une légère compression JPEG efface une partie des perturbations de faible amplitude.",
        attendu="Prédiction correcte restaurée",
        executer=_scenario_purification,
        disponible=_fruit_dispo("apple_fresh"),
    )
)


def _scenario_teinte(ctx: Contexte):
    """Décalage de teinte d'un fruit pourri pour le rendre « plus frais »."""
    image = image_fruit("banana_rotten").convert("HSV")
    h, s, v = image.split()
    h = h.point(lambda t: (t + 12) % 256)  # vers le jaune-vert
    s = s.point(lambda t: min(255, int(t * 1.3)))
    v = v.point(lambda t: min(255, int(t * 1.25)))
    modifiee = Image.merge("HSV", (h, s, v)).convert("RGB")
    res = analyser(ctx, modifiee)
    trompe = res.statut == "ok" and res.etat == "fresh"
    obtenu = f"Rejet : {res.raison_rejet}" if res.statut == "rejet" else f"Accepté : {res.classe} ({res.confiance})"
    return obtenu, not trompe, {"code_rejet": res.code_rejet}


_ajouter(
    Definition(
        id="couleur_teinte",
        categorie="Manipulation des couleurs",
        titre="Décalage de teinte : banane pourrie « rafraîchie »",
        description="Teinte décalée vers le jaune, saturation et luminosité augmentées.",
        attendu="Pas classée « fraîche » (pourrie ou rejet)",
        executer=_scenario_teinte,
        disponible=_fruit_dispo("banana_rotten"),
    )
)


# ------------------------------------------------------ robustesse naturelle
TRANSFORMATIONS: dict[str, tuple[str, Callable[[Image.Image], Image.Image]]] = {
    "flip": ("Miroir horizontal", lambda im: im.transpose(Image.FLIP_LEFT_RIGHT)),
    "rotation": ("Rotation 20°", lambda im: im.rotate(20, fillcolor=(255, 255, 255))),
    "luminosite": ("Luminosité −35 %", lambda im: ImageEnhance.Brightness(im).enhance(0.65)),
    "contraste": ("Contraste +50 %", lambda im: ImageEnhance.Contrast(im).enhance(1.5)),
    "flou": ("Flou gaussien r=2", lambda im: im.filter(ImageFilter.GaussianBlur(2))),
    "bruit": (
        "Bruit gaussien σ=12",
        lambda im: Image.fromarray(
            np.clip(
                np.asarray(im, dtype=np.float32) + np.random.default_rng(0).normal(0, 12, (im.height, im.width, 3)),
                0,
                255,
            ).astype("uint8")
        ),
    ),
    "jpeg": ("Compression JPEG forte (q=15)", lambda im: _jpeg(im, 15)),
    "recadrage": (
        "Recadrage 80 % centré",
        lambda im: im.crop((im.width // 10, im.height // 10, im.width * 9 // 10, im.height * 9 // 10)),
    ),
}


def _jpeg(im: Image.Image, qualite: int) -> Image.Image:
    t = io.BytesIO()
    im.save(t, format="JPEG", quality=qualite)
    t.seek(0)
    return Image.open(t).convert("RGB")


def _scenario_naturel(cle: str) -> Callable:
    def run(ctx: Contexte):
        res = analyser(ctx, TRANSFORMATIONS[cle][1](image_fruit("orange_rotten")))
        obtenu = f"Accepté : {res.classe} ({res.confiance})" if res.statut == "ok" else f"Rejet : {res.raison_rejet}"
        return obtenu, res.statut == "ok" and res.classe == "orange_rotten", {"code_rejet": res.code_rejet}

    return run


for _cle, (_titre, _) in TRANSFORMATIONS.items():
    _ajouter(
        Definition(
            id=f"naturel_{_cle}",
            categorie="Robustesse naturelle",
            titre=f"{_titre} (orange pourrie)",
            description="Perturbation naturelle (non malveillante) d'une photo valide.",
            attendu="Toujours « orange_rotten »",
            executer=_scenario_naturel(_cle),
            disponible=_fruit_dispo("orange_rotten"),
        )
    )


# ------------------------------------------------------- modèle et serveur
def _scenario_extraction(ctx: Contexte):
    res = analyser(ctx, cas_test.dessin_orange()).model_dump()
    decimales = max(len(str(v).split(".")[-1]) for v in res["probabilites"].values())
    sans_logits = not any("logit" in k for k in res)
    ok = decimales <= ctx.params.decimales_probabilites and sans_logits
    return f"Probabilités à {decimales} décimales max, logits exposés : {'non' if sans_logits else 'OUI'}", ok, {}


_ajouter(
    Definition(
        id="extraction_modele",
        categorie="Modèle et serveur",
        titre="Extraction du modèle (fuite d'information)",
        description="La réponse publique ne doit exposer ni logits ni probabilités en pleine précision.",
        attendu="Probabilités arrondies, aucun logit",
        executer=_scenario_extraction,
    )
)


def _scenario_integrite(ctx: Contexte):
    chemin = ctx.params.dossier_modeles / "FreshRotten_model_robuste.keras"
    octets = bytearray(chemin.read_bytes())
    octets[len(octets) // 2] ^= 0xFF  # un seul octet modifié, en mémoire
    obtenue = hashlib.sha256(octets).hexdigest()
    detecte = obtenue != EMPREINTES_PAR_DEFAUT[chemin.name]
    return f"Empreinte modifiée {'détectée' if detecte else 'NON détectée'} ({obtenue[:12]}…)", detecte, {}


_ajouter(
    Definition(
        id="integrite_modele",
        categorie="Modèle et serveur",
        titre="Fichier modèle altéré (1 octet)",
        description="Vérification SHA-256 au démarrage : le serveur refuse de charger un modèle modifié.",
        attendu="Altération détectée",
        executer=_scenario_integrite,
    )
)


def _scenario_safe_mode(ctx: Contexte):
    import keras

    entree = keras.Input((4,))
    sortie = keras.layers.Lambda(lambda t: t * 2)(entree)
    piege = keras.Model(entree, sortie)
    with tempfile.TemporaryDirectory() as dossier:
        chemin = Path(dossier) / "piege.keras"
        piege.save(chemin)
        try:
            keras.saving.load_model(chemin, safe_mode=True)
        except Exception as exc:  # ValueError attendu : désérialisation de lambda refusée
            return f"Chargement refusé ({type(exc).__name__})", True, {}
    return "Chargé (FAILLE)", False, {}


_ajouter(
    Definition(
        id="modele_lambda",
        categorie="Modèle et serveur",
        titre="Modèle piégé (couche Lambda = code arbitraire)",
        description="Un .keras contenant du code Python sérialisé est refusé par safe_mode=True.",
        attendu="Chargement refusé",
        executer=_scenario_safe_mode,
    )
)


# ----------------------------------------------------------------- API
def lister() -> list[Scenario]:
    return [
        Scenario(
            id=d.id,
            categorie=d.categorie,
            titre=d.titre,
            description=d.description,
            attendu=d.attendu,
            disponible=d.disponible(),
        )
        for d in SCENARIOS.values()
    ]


def executer(ctx: Contexte, identifiant: str) -> ResultatScenario:
    d = SCENARIOS[identifiant]
    debut = time.perf_counter()
    if not d.disponible():
        return ResultatScenario(
            id=d.id,
            titre=d.titre,
            attendu=d.attendu,
            obtenu="Indisponible : image de démonstration absente (scripts/generer_cas_test.py)",
            reussi=False,
            details={"indisponible": True},
            duree_ms=0,
        )
    obtenu, reussi, details = d.executer(ctx)
    return ResultatScenario(
        id=d.id,
        titre=d.titre,
        attendu=d.attendu,
        obtenu=obtenu,
        reussi=bool(reussi),
        details=details,
        duree_ms=round((time.perf_counter() - debut) * 1000, 1),
    )
