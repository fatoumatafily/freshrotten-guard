"""Défenses d'entrée contre les perturbations adverses.

* **Purification** : transformations légères qui « cassent » une perturbation
  de faible amplitude (compression JPEG, réduction de profondeur de couleur,
  filtre médian). Elles s'appliquent sur l'entrée 128×128 déjà prétraitée,
  car c'est à cette résolution que vit la perturbation.
* **Détection** : si la prédiction change fortement entre l'image brute et
  l'image purifiée, l'image est signalée « possiblement manipulée »
  (principe de *feature squeezing*, Xu et al., 2018).
"""

from __future__ import annotations

import io
from typing import Literal

import numpy as np
from PIL import Image, ImageFilter

from .preprocessing import tenseur_vers_image, vers_tenseur_modele

MethodePurification = Literal["jpeg", "bits", "median"]
METHODES: tuple[MethodePurification, ...] = ("jpeg", "bits", "median")


def purifier(x: np.ndarray, methode: MethodePurification = "jpeg") -> np.ndarray:
    """Applique une purification à un tenseur ``(1, 128, 128, 3)`` et renvoie un tenseur de même forme."""
    if methode == "bits":
        # 5 bits par canal (32 niveaux) : efface les variations de ±1/255 à ±4/255.
        niveaux = 31.0
        return (np.round(x * niveaux) / niveaux).astype("float32")
    image = tenseur_vers_image(x)
    if methode == "jpeg":
        tampon = io.BytesIO()
        image.save(tampon, format="JPEG", quality=75)
        tampon.seek(0)
        image = Image.open(tampon)
        image.load()
    elif methode == "median":
        image = image.filter(ImageFilter.MedianFilter(size=3))
    else:  # pragma: no cover
        raise ValueError(f"Méthode inconnue : {methode}")
    return vers_tenseur_modele(image, taille=(x.shape[2], x.shape[1]))


def divergence_l1(p: np.ndarray, q: np.ndarray) -> float:
    """Distance L1 entre deux distributions de probabilités (entre 0 et 2)."""
    return float(np.abs(np.asarray(p).ravel() - np.asarray(q).ravel()).sum())
