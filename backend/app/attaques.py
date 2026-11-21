"""Attaques adversariales — enveloppe fine autour de ``model/attaques.py``.

Les fonctions ``fgsm`` et ``pgd`` d'origine sont **réutilisées telles quelles**
(chargées depuis ``model/attaques.py``, sans copie ni modification). Ce module
ajoute seulement la validation des paramètres et un point d'entrée unique.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Literal

import numpy as np

from .config import parametres
from .inference import ModeleFruit

TypeAttaque = Literal["fgsm", "pgd", "pgd_ciblee"]
EPSILON_MAX = 0.1


@lru_cache
def module_origine(dossier: Path | None = None) -> ModuleType:
    """Charge ``model/attaques.py`` comme module (sans le copier)."""
    chemin = (dossier or parametres().dossier_modeles) / "attaques.py"
    spec = importlib.util.spec_from_file_location("frg_attaques_origine", chemin)
    if spec is None or spec.loader is None:
        raise ImportError(f"Impossible de charger {chemin}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclass
class ResultatAttaque:
    x_adv: np.ndarray  # (1, 128, 128, 3) dans [0, 1]
    perturbation: np.ndarray  # x_adv - x


def attaquer(
    modele: ModeleFruit,
    x: np.ndarray,
    type_attaque: TypeAttaque,
    epsilon: float,
    indice_vrai: int,
    indice_cible: int | None = None,
    nb_classes: int = 6,
    etapes: int = 10,
) -> ResultatAttaque:
    """Génère une image adverse contre ``modele`` (attaque en boîte blanche).

    ``indice_vrai`` : classe de référence (en pratique la prédiction du modèle
    attaqué sur l'image propre). ``indice_cible`` : classe visée pour PGD ciblée.
    """
    if not 0.0 <= epsilon <= EPSILON_MAX:
        raise ValueError(f"epsilon doit être dans [0, {EPSILON_MAX}]")
    orig = module_origine()
    if epsilon == 0.0:
        x_adv = np.array(x, copy=True)
    elif type_attaque == "fgsm":
        x_adv = orig.fgsm(modele.keras, x, orig.one_hot(indice_vrai, nb_classes), epsilon)
    elif type_attaque == "pgd":
        x_adv = orig.pgd(modele.keras, x, orig.one_hot(indice_vrai, nb_classes), epsilon, steps=etapes)
    elif type_attaque == "pgd_ciblee":
        if indice_cible is None:
            raise ValueError("Une classe cible est requise pour PGD ciblée")
        x_adv = orig.pgd(modele.keras, x, orig.one_hot(indice_cible, nb_classes), epsilon, steps=etapes, cible=True)
    else:  # pragma: no cover — garanti par la validation Pydantic
        raise ValueError(f"Attaque inconnue : {type_attaque}")
    x_adv = np.asarray(x_adv, dtype="float32")
    return ResultatAttaque(x_adv, x_adv - x)
