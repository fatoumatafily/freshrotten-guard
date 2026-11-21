"""Chargement sécurisé des modèles et inférence.

* Vérification d'empreinte SHA-256 de chaque fichier **avant** chargement.
* ``keras.saving.load_model(..., safe_mode=True)`` : refuse les couches Lambda
  et toute désérialisation de code arbitraire.
* Les modèles sont chargés **une seule fois** (au démarrage de l'API).
* Les logits (avant softmax) sont recalculés à partir de la dernière couche
  Dense : ils servent au score d'énergie, mais ne sont **jamais** exposés par
  l'API publique (protection contre l'extraction du modèle).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import keras
import numpy as np

from .config import EMPREINTES_PAR_DEFAUT, Parametres

journal = logging.getLogger("frg.inference")

FICHIERS_MODELES = {
    "base": "FreshRotten_model.keras",
    "robuste": "FreshRotten_model_robuste.keras",
}
FICHIER_POIDS_GARDIEN = "mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5"


class IntegriteCompromise(RuntimeError):
    """Empreinte SHA-256 inattendue : le fichier a été altéré ou remplacé."""


def sha256_fichier(chemin: Path) -> str:
    """Empreinte SHA-256 d'un fichier, lue par blocs."""
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def verifier_integrite(chemin: Path, attendue: str | None = None) -> str:
    """Lève :class:`IntegriteCompromise` si l'empreinte ne correspond pas."""
    attendue = attendue or EMPREINTES_PAR_DEFAUT.get(chemin.name)
    if attendue is None:
        raise IntegriteCompromise(f"Aucune empreinte de référence pour {chemin.name}")
    obtenue = sha256_fichier(chemin)
    if obtenue != attendue:
        raise IntegriteCompromise(
            f"Empreinte invalide pour {chemin.name} : attendue {attendue[:12]}…, obtenue {obtenue[:12]}…"
        )
    return obtenue


@dataclass(frozen=True)
class InfoClasses:
    """Contenu de ``model/classes.json``."""

    classes: list[str]
    taille: tuple[int, int]

    @staticmethod
    def charger(dossier: Path) -> InfoClasses:
        data = json.loads((dossier / "classes.json").read_text(encoding="utf-8"))
        return InfoClasses(list(data["classes"]), tuple(data["img_size"]))  # type: ignore[arg-type]

    def fruit_et_etat(self, indice: int) -> tuple[str, str]:
        fruit, etat = self.classes[indice].split("_")
        return fruit, etat


class ModeleFruit:
    """Un CNN FreshRotten chargé, avec accès aux logits."""

    def __init__(self, nom: str, modele: keras.Model) -> None:
        self.nom = nom
        self.keras = modele
        derniere = modele.layers[-1]
        self._corps = keras.Model(modele.inputs, modele.layers[-2].output)
        self._w, self._b = (np.asarray(v) for v in derniere.get_weights())

    def logits(self, x: np.ndarray) -> np.ndarray:
        """Logits ``(n, 6)`` (avant softmax). Usage interne uniquement."""
        h = np.asarray(self._corps(x, training=False))
        return h @ self._w + self._b

    def probabilites(self, x: np.ndarray) -> np.ndarray:
        """Probabilités ``(n, 6)``."""
        return np.asarray(self.keras(x, training=False))


class Gardien:
    """MobileNetV2 pré-entraîné ImageNet : empreinte sémantique + classes ImageNet."""

    def __init__(self, chemin_poids: Path) -> None:
        reseau = keras.applications.MobileNetV2(weights=None, include_top=True)
        reseau.load_weights(str(chemin_poids))
        self._reseau = keras.Model(reseau.input, [reseau.layers[-2].output, reseau.output])

    def analyser(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Renvoie (empreintes ``(n, 1280)``, probabilités ImageNet ``(n, 1000)``)."""
        emb, probas = self._reseau(x, training=False)
        return np.asarray(emb), np.asarray(probas)


@dataclass
class Modeles:
    """Ensemble des modèles chargés au démarrage."""

    info: InfoClasses
    fruits: dict[str, ModeleFruit]
    gardien: Gardien
    empreintes: dict[str, str]
    actif: str

    @property
    def modele_actif(self) -> ModeleFruit:
        return self.fruits[self.actif]


def charger_modeles(params: Parametres) -> Modeles:
    """Vérifie l'intégrité puis charge les deux CNN et le gardien (une seule fois)."""
    dossier = params.dossier_modeles
    info = InfoClasses.charger(dossier)
    empreintes: dict[str, str] = {}
    fruits: dict[str, ModeleFruit] = {}
    for nom, fichier in FICHIERS_MODELES.items():
        chemin = dossier / fichier
        if params.verifier_empreintes:
            empreintes[fichier] = verifier_integrite(chemin)
        modele = keras.saving.load_model(chemin, safe_mode=True, compile=False)
        fruits[nom] = ModeleFruit(nom, modele)
        journal.info("Modèle %s chargé (%s)", nom, fichier)

    chemin_gardien = params.dossier_poids_gardien / FICHIER_POIDS_GARDIEN
    if not chemin_gardien.exists():
        # Premier lancement : téléchargement officiel Keras, puis vérification d'empreinte.
        chemin_gardien = Path(
            keras.utils.get_file(
                FICHIER_POIDS_GARDIEN,
                "https://storage.googleapis.com/tensorflow/keras-applications/mobilenet_v2/"
                + FICHIER_POIDS_GARDIEN,
                cache_subdir="models",
                file_hash=EMPREINTES_PAR_DEFAUT[FICHIER_POIDS_GARDIEN],
            )
        )
    if params.verifier_empreintes:
        empreintes[FICHIER_POIDS_GARDIEN] = verifier_integrite(chemin_gardien)
    gardien = Gardien(chemin_gardien)
    journal.info("Gardien MobileNetV2 chargé")
    return Modeles(info, fruits, gardien, empreintes, params.modele_actif)
