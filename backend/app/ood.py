"""Détection « hors domaine » : refuser ce qui n'est pas une pomme, une banane ou une orange.

Le CNN FreshRotten finit par un softmax sur 6 classes : il répond *toujours*
un fruit, même pour du bruit (testé : bruit → « banana_rotten » à 100 %).
On ajoute donc plusieurs couches indépendantes, de la moins chère à la plus
chère, chacune calibrée par ``scripts/calibrer_seuils.py`` :

1. **Qualité** : image trop sombre, trop claire, presque uniforme, trop floue,
   ou dessin / image de synthèse (trop peu de couleurs distinctes).
2. **Personne** : détecteur de visages (OpenCV Haar) → rejet direct.
3. **Gardien sémantique** : les empreintes MobileNetV2 (ImageNet) de l'image
   doivent être proches de celles du dataset (distance de Mahalanobis à la
   classe la plus proche). Le top-1 ImageNet seul ne suffit pas : une pomme
   pourrie y est vue comme « bagel », une banane pourrie comme « slug ».
4. **Autre fruit** : si ImageNet voit nettement un fruit non pris en charge
   (fraise, citron, ananas, grenade…), rejet.
5. **Incertitude** du CNN : confiance max, entropie, score d'énergie.
6. **Cohérence** : le fruit vu par le gardien doit être celui prédit par le CNN.

Pourquoi combiner ? Chaque couche a des angles morts : la confiance du CNN est
élevée sur du bruit ; la distance du gardien ne voit pas la différence entre
une pomme fraîche et une pomme pourrie mal prédite ; la qualité ne détecte pas
une photo nette de voiture. Ensemble, elles se couvrent mutuellement.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .api.schemas import Controle
from .inference import Gardien

# Indices ImageNet (ILSVRC-2012) utiles.
IMAGENET_FRUITS_PRIS_EN_CHARGE = {948: "Granny_Smith", 950: "orange", 954: "banana"}
IMAGENET_AUTRES_FRUITS = {
    949: "fraise",
    951: "citron",
    952: "figue",
    953: "ananas",
    955: "jacquier",
    956: "pomme-cannelle",
    957: "grenade",
    943: "concombre",
    945: "poivron",
    988: "gland",
    990: "marron d'Inde",
}
FRUITS = ("apple", "banana", "orange")


# --------------------------------------------------------------- seuils
@dataclass
class SeuilsModele:
    """Seuils d'incertitude propres à un modèle FreshRotten."""

    confiance_min: float = 0.0
    entropie_max: float = 10.0
    energie_max: float = 1e9


@dataclass
class Seuils:
    """Tous les seuils. Valeurs par défaut *permissives* : seule la calibration les rend utiles."""

    luminosite_min: float = 0.05
    luminosite_max: float = 0.98
    contraste_min: float = 0.02
    nettete_min: float = 1.0
    couleurs_min: int = 0
    distance_max: float = float("inf")
    autre_fruit_min: float = 1.01
    visage_actif: bool = True
    modeles: dict[str, SeuilsModele] = field(default_factory=dict)
    divergence_manipulation: float | None = None
    calibre: bool = False
    rapport: dict[str, object] = field(default_factory=dict)

    @staticmethod
    def charger(chemin: Path) -> Seuils:
        if not chemin.exists():
            return Seuils()
        data = json.loads(chemin.read_text(encoding="utf-8"))
        modeles = {k: SeuilsModele(**v) for k, v in data.pop("modeles", {}).items()}
        return Seuils(modeles=modeles, **data)

    def enregistrer(self, chemin: Path) -> None:
        chemin.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------- gardien (stats)
@dataclass
class StatsGardien:
    """Statistiques des empreintes MobileNetV2 du dataset (ACP + Gaussiennes par classe)."""

    moyenne: np.ndarray  # (D,)
    projection: np.ndarray  # (D, d)
    centres: np.ndarray  # (6, d)
    precision: np.ndarray  # (d, d) inverse de la covariance partagée régularisée

    @staticmethod
    def ajuster(empreintes: np.ndarray, etiquettes: np.ndarray, dim: int = 512, retrait: float = 0.01) -> StatsGardien:
        moyenne = empreintes.mean(0)
        _, _, vt = np.linalg.svd(empreintes - moyenne, full_matrices=False)
        projection = vt[:dim].T
        z = (empreintes - moyenne) @ projection
        centres = np.stack([z[etiquettes == k].mean(0) for k in range(int(etiquettes.max()) + 1)])
        cov = np.cov((z - centres[etiquettes]).T)
        # Régularisation (shrinkage) : covariance estimée sur peu d'images par dimension.
        cov = (1 - retrait) * cov + retrait * np.trace(cov) / cov.shape[0] * np.eye(cov.shape[0])
        return StatsGardien(moyenne, projection, centres, np.linalg.inv(cov))

    def distances(self, empreintes: np.ndarray) -> np.ndarray:
        """Distances de Mahalanobis (au carré) ``(n, 6)`` aux centres de classe."""
        z = (empreintes - self.moyenne) @ self.projection
        return np.stack([(((z - c) @ self.precision) * (z - c)).sum(1) for c in self.centres], 1)

    def enregistrer(self, chemin: Path) -> None:
        np.savez_compressed(
            chemin,
            moyenne=self.moyenne.astype("float32"),
            projection=self.projection.astype("float32"),
            centres=self.centres.astype("float32"),
            precision=self.precision.astype("float32"),
        )

    @staticmethod
    def charger(chemin: Path) -> StatsGardien | None:
        if not chemin.exists():
            return None
        with np.load(chemin, allow_pickle=False) as d:  # allow_pickle=False : aucun objet Python
            return StatsGardien(d["moyenne"], d["projection"], d["centres"], d["precision"])


# ------------------------------------------------------------- mesures
def mesurer_qualite(image: Image.Image) -> dict[str, float]:
    """Luminosité, contraste (écart-type), netteté (variance du Laplacien) et nombre de couleurs distinctes.

    Une photo compte des milliers de couleurs distinctes (bruit du capteur, dégradés) ; un dessin,
    un aplat ou une capture d'écran de texte, quelques dizaines à quelques centaines.
    """
    gris = np.asarray(image.convert("L").resize((256, 256), Image.BILINEAR), dtype=np.float32)
    return {
        "luminosite": float(gris.mean() / 255.0),
        "contraste": float(gris.std() / 255.0),
        "nettete": float(cv2.Laplacian(gris, cv2.CV_32F).var()),
        "couleurs": float(compter_couleurs(image)),
    }


def compter_couleurs(image: Image.Image) -> int:
    """Nombre de couleurs RGB distinctes sur l'image réduite en 128×128 (NEAREST : aucune couleur inventée)."""
    pixels = np.asarray(image.convert("RGB").resize((128, 128), Image.NEAREST), dtype=np.uint32).reshape(-1, 3)
    return int(np.unique((pixels[:, 0] << 16) | (pixels[:, 1] << 8) | pixels[:, 2]).size)


@lru_cache
def _detecteur_visages() -> cv2.CascadeClassifier:
    return cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def compter_visages(image: Image.Image) -> int:
    """Nombre de visages de face (taille minimale : 1/5 du plus petit côté, pour limiter les faux positifs)."""
    gris = np.asarray(image.convert("L"), dtype=np.uint8)
    cote = min(gris.shape)
    if cote > 640:  # accélère sans perdre les visages de taille utile
        echelle = 640 / cote
        gris = cv2.resize(gris, None, fx=echelle, fy=echelle, interpolation=cv2.INTER_AREA)
        cote = min(gris.shape)
    mini = max(32, cote // 5)
    visages = _detecteur_visages().detectMultiScale(gris, scaleFactor=1.1, minNeighbors=8, minSize=(mini, mini))
    return len(visages)


def entropie(probas: np.ndarray) -> float:
    p = np.clip(probas, 1e-12, 1.0)
    return float(-(p * np.log(p)).sum())


def energie(logits: np.ndarray) -> float:
    """Score d'énergie (Liu et al., 2020) : −logsumexp(logits). Plus il est élevé, plus l'entrée est atypique."""
    m = float(np.max(logits))
    return float(-(m + np.log(np.exp(logits - m).sum())))


@dataclass
class SignalGardien:
    """Tout ce que le gardien a vu (indépendant du modèle FreshRotten)."""

    distance: float
    fruit_proche: str
    classe_proche: int
    proba_autre_fruit: float
    autre_fruit: str | None
    proba_fruits_pris_en_charge: float
    visages: int
    qualite: dict[str, float]


def signal_gardien(
    gardien: Gardien, stats: StatsGardien | None, x_gardien: np.ndarray, image: Image.Image
) -> SignalGardien:
    """Exécute le gardien (MobileNetV2 + visages + qualité) sur une image."""
    empreinte, probas_in = gardien.analyser(x_gardien)
    probas_in = probas_in[0]
    if stats is not None:
        d = stats.distances(empreinte)[0]
        k = int(np.argmin(d))
        distance = float(d[k])
    else:
        k, distance = 0, 0.0
    autres = {nom: float(probas_in[i]) for i, nom in IMAGENET_AUTRES_FRUITS.items()}
    autre_nom, autre_p = max(autres.items(), key=lambda t: t[1])
    return SignalGardien(
        distance=distance,
        fruit_proche=FRUITS[k // 2],
        classe_proche=k,
        proba_autre_fruit=autre_p,
        autre_fruit=autre_nom,
        proba_fruits_pris_en_charge=float(sum(probas_in[i] for i in IMAGENET_FRUITS_PRIS_EN_CHARGE)),
        visages=compter_visages(image),
        qualite=mesurer_qualite(image),
    )


# ------------------------------------------------------------ décision
@dataclass
class Decision:
    rejet: bool
    code: str | None
    message: str | None
    controles: list[Controle]


MESSAGES = {
    "trop_sombre": "Image trop sombre : éclairez davantage le fruit.",
    "trop_claire": "Image trop claire ou surexposée.",
    "uniforme": "Image presque uniforme : aucun objet visible.",
    "trop_floue": "Image trop floue : stabilisez l'appareil ou faites la mise au point.",
    "dessin": "Dessin ou image de synthèse détecté : seules les photos de fruits sont analysées.",
    "personne": "Une personne a été détectée : ce n'est pas un fruit pris en charge.",
    "hors_domaine": "Ce n'est pas un fruit pris en charge (pomme, banane ou orange).",
    "autre_fruit": "Fruit non pris en charge détecté ({fruit}). Seules les pommes, bananes et oranges sont analysées.",
    "incertain": "Prédiction trop incertaine : le modèle n'est pas assez sûr de lui.",
    "incoherent": "Résultat incohérent entre le gardien et le modèle : image ambiguë.",
}


def decider(
    logits: np.ndarray,
    probas: np.ndarray,
    signal: SignalGardien,
    seuils: Seuils,
    classes: list[str],
    nom_modele: str = "robuste",
) -> Decision:
    """Applique toutes les couches et renvoie la décision (la première couche en échec donne la raison)."""
    controles: list[Controle] = []
    echecs: list[tuple[str, dict[str, str]]] = []

    def controle(nom: str, ok: bool, valeur: float, seuil: float, msg_ok: str, code: str, **fmt: str) -> None:
        controles.append(
            Controle(
                nom=nom,
                reussi=ok,
                valeur=round(float(valeur), 4),
                seuil=round(float(seuil), 4) if np.isfinite(seuil) else None,
                message=msg_ok if ok else MESSAGES[code].format(**fmt),
            )
        )
        if not ok:
            echecs.append((code, fmt))

    q = signal.qualite
    controle(
        "luminosite_min",
        q["luminosite"] >= seuils.luminosite_min,
        q["luminosite"],
        seuils.luminosite_min,
        "Luminosité suffisante",
        "trop_sombre",
    )
    controle(
        "luminosite_max",
        q["luminosite"] <= seuils.luminosite_max,
        q["luminosite"],
        seuils.luminosite_max,
        "Pas de surexposition",
        "trop_claire",
    )
    controle(
        "contraste",
        q["contraste"] >= seuils.contraste_min,
        q["contraste"],
        seuils.contraste_min,
        "Image non uniforme",
        "uniforme",
    )
    controle(
        "nettete",
        q["nettete"] >= seuils.nettete_min,
        q["nettete"],
        seuils.nettete_min,
        "Netteté suffisante",
        "trop_floue",
    )
    couleurs = q.get("couleurs", float("inf"))
    controle(
        "couleurs",
        couleurs >= seuils.couleurs_min,
        couleurs if np.isfinite(couleurs) else 0,
        seuils.couleurs_min,
        "Image photographique (couleurs variées)",
        "dessin",
    )
    if seuils.visage_actif:
        controle("personne", signal.visages == 0, signal.visages, 0, "Aucun visage détecté", "personne")
    controle(
        "gardien_distance",
        signal.distance <= seuils.distance_max,
        signal.distance,
        seuils.distance_max,
        "Le gardien reconnaît un fruit du domaine",
        "hors_domaine",
    )
    controle(
        "autre_fruit",
        signal.proba_autre_fruit < seuils.autre_fruit_min,
        signal.proba_autre_fruit,
        seuils.autre_fruit_min,
        "Aucun autre fruit détecté",
        "autre_fruit",
        fruit=signal.autre_fruit or "?",
    )

    sm = seuils.modeles.get(nom_modele, SeuilsModele())
    conf = float(np.max(probas))
    controle("confiance", conf >= sm.confiance_min, conf, sm.confiance_min, "Confiance suffisante", "incertain")
    ent = entropie(probas)
    controle("entropie", ent <= sm.entropie_max, ent, sm.entropie_max, "Entropie faible", "incertain")
    en = energie(logits)
    controle("energie", en <= sm.energie_max, en, sm.energie_max, "Score d'énergie normal", "incertain")

    fruit_modele = classes[int(np.argmax(probas))].split("_")[0]
    coherent = fruit_modele == signal.fruit_proche
    controles.append(
        Controle(
            nom="coherence",
            reussi=coherent,
            message=f"Gardien et modèle voient tous deux : {fruit_modele}"
            if coherent
            else f"Le gardien voit « {signal.fruit_proche} », le modèle prédit « {fruit_modele} »",
        )
    )
    if not coherent:
        echecs.append(("incoherent", {}))

    if echecs:
        code, fmt = echecs[0]
        return Decision(True, code, MESSAGES[code].format(**fmt), controles)
    return Decision(False, None, None, controles)
