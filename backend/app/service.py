"""Orchestration de l'analyse : image validée → défenses → prédiction → réponse."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from PIL import Image

from . import ood
from .api.schemas import Controle, ResultatAnalyse
from .config import Parametres
from .defenses import MethodePurification, divergence_l1, purifier
from .inference import Modeles
from .preprocessing import vers_tenseur_gardien, vers_tenseur_modele

SEUIL_DIVERGENCE_MANIPULATION = 0.6  # remplacé par la valeur calibrée si disponible


@dataclass
class Contexte:
    """Tout ce dont l'analyse a besoin, chargé une fois au démarrage."""

    modeles: Modeles
    params: Parametres
    gardien: ood.StatsGardien
    seuils: ood.Seuils


def arrondir(probas: np.ndarray, classes: list[str], decimales: int) -> dict[str, float]:
    """Probabilités arrondies : limite l'information exploitable pour copier le modèle."""
    return {c: round(float(p), decimales) for c, p in zip(classes, probas, strict=True)}


def analyser(
    ctx: Contexte,
    image: Image.Image,
    nom_modele: str | None = None,
    purification: MethodePurification | None = None,
    alertes_fichier: list[str] | None = None,
    signal_gardien: ood.SignalGardien | None = None,
) -> ResultatAnalyse:
    """Analyse complète d'une image déjà validée (RGB, sans métadonnées).

    ``signal_gardien`` permet de réutiliser le calcul du gardien (comparaison
    des deux modèles) : il ne dépend pas du modèle FreshRotten choisi.
    """
    debut = time.perf_counter()
    nom = nom_modele or ctx.modeles.actif
    modele = ctx.modeles.fruits[nom]
    info = ctx.modeles.info
    alertes = list(alertes_fichier or [])
    decimales = ctx.params.decimales_probabilites

    x = vers_tenseur_modele(image, info.taille)
    x_brut = x
    if purification:
        x = purifier(x, purification)

    if signal_gardien is None:
        signal_gardien = ood.signal_gardien(ctx.modeles.gardien, ctx.gardien, vers_tenseur_gardien(image), image)
    logits = modele.logits(x)[0]
    probas = modele.probabilites(x)[0]
    decision = ood.decider(logits, probas, signal_gardien, ctx.seuils, info.classes, nom)

    # Détection de manipulation (feature squeezing) : brut vs purifié.
    if ctx.params.detection_manipulation:
        reference = x_brut if purification else purifier(x_brut, "median")
        p_ref = modele.probabilites(reference)[0]
        ecart = divergence_l1(probas, p_ref)
        seuil = ctx.seuils.divergence_manipulation or SEUIL_DIVERGENCE_MANIPULATION
        if ecart > seuil:
            alertes.append("image_possiblement_manipulee")
        decision.controles.append(
            Controle(
                nom="manipulation",
                reussi=ecart <= seuil,
                valeur=round(ecart, 3),
                seuil=round(seuil, 3),
                message="Prédiction stable après purification"
                if ecart <= seuil
                else "La prédiction change fortement après purification : image possiblement manipulée",
            )
        )

    indice = int(np.argmax(probas))
    fruit, etat = info.fruit_et_etat(indice)
    commun = dict(
        modele=nom,
        probabilites=arrondir(probas, info.classes, decimales),
        alertes=alertes,
        controles=decision.controles,
        purification=purification,
        duree_ms=round((time.perf_counter() - debut) * 1000, 1),
    )
    if decision.rejet:
        return ResultatAnalyse(statut="rejet", raison_rejet=decision.message, code_rejet=decision.code, **commun)
    return ResultatAnalyse(
        statut="ok",
        fruit=fruit,
        etat=etat,
        classe=info.classes[indice],
        confiance=round(float(probas[indice]), decimales),
        **commun,
    )
