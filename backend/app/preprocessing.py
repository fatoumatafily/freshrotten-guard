"""Prétraitement des images — **source unique de vérité**.

Le CNN FreshRotten a été entraîné avec : conversion RGB → redimensionnement
128×128 en ``NEAREST`` → pixels / 255. Toute différence fausse les prédictions,
donc *toutes* les entrées (upload, webcam, attaques, tests, calibration) passent
par :func:`vers_tenseur_modele`. Un test vérifie que cette fonction donne
exactement le même résultat que ``charger_image`` de ``model/attaques.py``.

Le gardien ImageNet (MobileNetV2) a son propre prétraitement, lui aussi
centralisé ici (:func:`vers_tenseur_gardien`).
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

TAILLE_MODELE: tuple[int, int] = (128, 128)
TAILLE_GARDIEN: tuple[int, int] = (224, 224)


def vers_tenseur_modele(image: Image.Image, taille: tuple[int, int] = TAILLE_MODELE) -> np.ndarray:
    """Image PIL → tableau ``(1, 128, 128, 3)`` float32 dans [0, 1] (identique à l'entraînement)."""
    img = image.convert("RGB").resize(tuple(taille), Image.NEAREST)
    x = np.asarray(img, dtype="float32") / 255.0
    return np.expand_dims(x, axis=0)


def vers_tenseur_gardien(image: Image.Image) -> np.ndarray:
    """Image PIL → tableau ``(1, 224, 224, 3)`` au format attendu par MobileNetV2 ([-1, 1])."""
    img = image.convert("RGB").resize(TAILLE_GARDIEN, Image.BILINEAR)
    x = np.asarray(img, dtype="float32") / 127.5 - 1.0
    return np.expand_dims(x, axis=0)


def tenseur_vers_image(x: np.ndarray) -> Image.Image:
    """Tableau ``(1, H, W, 3)`` ou ``(H, W, 3)`` dans [0, 1] → image PIL RGB 8 bits."""
    if x.ndim == 4:
        x = x[0]
    return Image.fromarray(np.clip(np.rint(x * 255.0), 0, 255).astype("uint8"), mode="RGB")


def image_vers_png(image: Image.Image) -> bytes:
    """Encode une image en PNG (sans perte, sans métadonnées), en mémoire."""
    tampon = io.BytesIO()
    image.save(tampon, format="PNG", optimize=False)
    return tampon.getvalue()
