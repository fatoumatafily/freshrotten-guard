"""Routes HTTP de l'API (documentées automatiquement dans Swagger : ``/docs``)."""

import base64
import json
import time
from typing import Annotated, Literal

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile

from .. import scenarios as scen
from ..attaques import EPSILON_MAX, attaquer
from ..defenses import divergence_l1, purifier
from ..journal import evenement
from ..preprocessing import image_vers_png, tenseur_vers_image, vers_tenseur_gardien, vers_tenseur_modele
from ..securite_fichiers import FichierRefuse, ImageValidee, valider_et_decoder
from ..service import Contexte, analyser, arrondir
from .limites import LIMITE_ANALYSE, LIMITE_ATTAQUE, LIMITE_COMPARER, LIMITE_SCENARIOS, limiteur
from .schemas import (
    EtatSante,
    ModeAttaque,
    NomClasse,
    NomModele,
    PredictionAttaque,
    ResultatAnalyse,
    ResultatAttaque,
    ResultatComparaison,
    ResultatModeleAttaque,
    ResultatScenario,
    Scenario,
    TypeAttaque,
)

routeur = APIRouter(prefix="/api")
# Une attaque ciblée doit atteindre UNE classe précise : 20 pas au lieu de 10 (mesuré : 10 pas
# ne suffisent pas toujours contre le modèle de base à ε = 0,03).
ETAPES_CIBLEE = 20
Purification = Literal["jpeg", "bits", "median"]
REPONSES_ERREUR = {
    400: {"description": "Fichier refusé (format, taille, contenu suspect…)"},
    413: {"description": "Requête trop volumineuse"},
    422: {"description": "Paramètres invalides"},
    429: {"description": "Trop de requêtes"},
    503: {"description": "Serveur occupé ou délai dépassé"},
}


def _ctx(request: Request) -> Contexte:
    return request.app.state.ctx


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _lire_et_valider(request: Request, fichier: UploadFile) -> ImageValidee:
    """Lit le fichier **en mémoire** (jamais sur disque) et le valide. Le nom fourni est ignoré."""
    ctx = _ctx(request)
    limite = ctx.params.taille_max_octets
    morceaux, total = [], 0
    while bloc := await fichier.read(256 * 1024):
        total += len(bloc)
        if total > limite:
            evenement("rejet_fichier", _ip(request), code="fichier_trop_gros")
            raise HTTPException(400, {"detail": "Fichier trop volumineux.", "code": "fichier_trop_gros"})
        morceaux.append(bloc)
    octets = b"".join(morceaux)
    try:
        return await request.app.state.executeur.executer(
            lambda: valider_et_decoder(
                octets,
                taille_max=limite,
                pixels_max=ctx.params.pixels_max,
                dimension_max=ctx.params.dimension_max,
                dimension_min=ctx.params.dimension_min,
            )
        )
    except FichierRefuse as exc:
        evenement("rejet_fichier", _ip(request), code=exc.code, taille=len(octets))
        raise HTTPException(400, {"detail": exc.message, "code": exc.code}) from exc


def _journaliser_resultat(request: Request, res: ResultatAnalyse, source: str) -> None:
    if res.statut == "rejet":
        evenement("rejet_hors_domaine", _ip(request), code=res.code_rejet, modele=res.modele, source=source)
    if "image_possiblement_manipulee" in res.alertes:
        evenement("manipulation_detectee", _ip(request), modele=res.modele, source=source)


# ------------------------------------------------------------------ analyse
@routeur.post("/analyser", response_model=ResultatAnalyse, responses=REPONSES_ERREUR, tags=["Analyse"])
@limiteur.limit(LIMITE_ANALYSE)
async def route_analyser(
    request: Request,
    fichier: Annotated[UploadFile, File(description="Image JPEG, PNG ou WebP (5 Mo max)")],
    modele: Annotated[NomModele | None, Query(description="Modèle à utiliser (défaut : robuste)")] = None,
    purification: Annotated[Purification | None, Query(description="Purification d'entrée optionnelle")] = None,
    source: Annotated[Literal["upload", "webcam"], Query()] = "upload",
) -> ResultatAnalyse:
    """Analyse une image : **frais / pourri**, ou rejet motivé si l'image est hors domaine."""
    image = await _lire_et_valider(request, fichier)
    ctx = _ctx(request)
    res = await request.app.state.executeur.executer(analyser, ctx, image.image, modele, purification, image.alertes)
    _journaliser_resultat(request, res, source)
    return res


@routeur.post("/analyser/comparer", response_model=ResultatComparaison, responses=REPONSES_ERREUR, tags=["Analyse"])
@limiteur.limit(LIMITE_COMPARER)
async def route_comparer(
    request: Request,
    fichier: Annotated[UploadFile, File()],
    purification: Annotated[Purification | None, Query()] = None,
) -> ResultatComparaison:
    """Analyse la même image avec le modèle de base **et** le modèle robuste."""
    image = await _lire_et_valider(request, fichier)
    ctx = _ctx(request)

    def deux_modeles() -> ResultatComparaison:
        from .. import ood

        signal = ood.signal_gardien(ctx.modeles.gardien, ctx.gardien, vers_tenseur_gardien(image.image), image.image)
        return ResultatComparaison(
            base=analyser(ctx, image.image, "base", purification, image.alertes, signal),
            robuste=analyser(ctx, image.image, "robuste", purification, image.alertes, signal),
        )

    res = await request.app.state.executeur.executer(deux_modeles)
    _journaliser_resultat(request, res.robuste, "comparer")
    return res


# ------------------------------------------------------------------ attaque
def _data_url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _prediction(ctx: Contexte, nom: str, x: np.ndarray) -> tuple[PredictionAttaque, np.ndarray]:
    p = ctx.modeles.fruits[nom].probabilites(x)[0]
    classes = ctx.modeles.info.classes
    i = int(np.argmax(p))
    dec = ctx.params.decimales_probabilites
    return PredictionAttaque(
        classe=classes[i], confiance=round(float(p[i]), dec), probabilites=arrondir(p, classes, dec)
    ), p


def executer_attaque(
    ctx: Contexte,
    x: np.ndarray,
    type_attaque: TypeAttaque,
    epsilon: float,
    cible: str | None,
    mode: str,
) -> ResultatAttaque:
    """Génère l'attaque et évalue les deux modèles (fonction pure, réutilisée par les scénarios)."""
    debut = time.perf_counter()
    classes = ctx.modeles.info.classes
    indice_cible = classes.index(cible) if cible else None
    seuil = ctx.seuils.divergence_manipulation or 0.6

    propres = {nom: _prediction(ctx, nom, x) for nom in ("base", "robuste")}
    images_adv: dict[str, np.ndarray] = {}
    for nom in ("base", "robuste"):
        source = nom if mode == "boite_blanche" else "base"
        if source not in images_adv:
            vrai = int(np.argmax(propres[source][1]))
            images_adv[source] = attaquer(
                ctx.modeles.fruits[source],
                x,
                type_attaque,
                epsilon,
                vrai,
                indice_cible,
                len(classes),
                etapes=ETAPES_CIBLEE if type_attaque == "pgd_ciblee" else 10,
            ).x_adv
        images_adv[nom] = images_adv[source]

    resultats = {}
    for nom in ("base", "robuste"):
        x_adv = images_adv[nom]
        pred_adv, p_adv = _prediction(ctx, nom, x_adv)
        pred_pur, _ = _prediction(ctx, nom, purifier(x_adv, "jpeg"))
        _, p_med = _prediction(ctx, nom, purifier(x_adv, "median"))
        delta = x_adv - x
        amplitude = max(float(np.abs(delta).max()), 1e-8)
        resultats[nom] = ResultatModeleAttaque(
            propre=propres[nom][0],
            attaquee=pred_adv,
            trompe=pred_adv.classe != propres[nom][0].classe,
            cible_atteinte=(pred_adv.classe == cible) if cible else None,
            manipulation_detectee=divergence_l1(p_adv, p_med) > seuil,
            prediction_purifiee=pred_pur,
            image_attaquee=_data_url(image_vers_png(tenseur_vers_image(x_adv))),
            perturbation=_data_url(image_vers_png(tenseur_vers_image(delta / (2 * amplitude) + 0.5))),
            norme_linf=round(float(np.abs(delta).max()), 4),
        )
    return ResultatAttaque(
        attaque=type_attaque,
        epsilon=epsilon,
        cible=cible,
        mode=mode,
        image_originale=_data_url(image_vers_png(tenseur_vers_image(x))),
        modeles=resultats,
        duree_ms=round((time.perf_counter() - debut) * 1000, 1),
    )


@routeur.post("/attaque", response_model=ResultatAttaque, responses=REPONSES_ERREUR, tags=["Laboratoire"])
@limiteur.limit(LIMITE_ATTAQUE)
async def route_attaque(
    request: Request,
    fichier: Annotated[UploadFile, File()],
    attaque: Annotated[TypeAttaque, Form()],
    epsilon: Annotated[float, Form(ge=0.0, le=EPSILON_MAX, description="Amplitude L∞ de la perturbation")],
    cible: Annotated[NomClasse | None, Form(description="Classe visée (PGD ciblée uniquement)")] = None,
    mode: Annotated[ModeAttaque, Form()] = "boite_blanche",
) -> ResultatAttaque:
    """Attaque adversariale (FGSM, PGD, PGD ciblée) et comparaison **base vs robuste**."""
    if attaque == "pgd_ciblee" and cible is None:
        raise HTTPException(422, {"detail": "Choisissez une classe cible pour PGD ciblée.", "code": "cible_requise"})
    if attaque != "pgd_ciblee":
        cible = None
    image = await _lire_et_valider(request, fichier)
    ctx = _ctx(request)
    x = vers_tenseur_modele(image.image, ctx.modeles.info.taille)
    evenement("attaque_laboratoire", _ip(request), attaque=attaque, epsilon=epsilon, mode=mode)
    return await request.app.state.executeur.executer(
        executer_attaque, ctx, x, attaque, epsilon, cible, mode, delai_s=ctx.params.delai_inference_s * 2
    )


# ------------------------------------------------------------- informations
def _lire_json(chemin) -> dict | None:
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else None


@routeur.get("/metriques", tags=["Laboratoire"])
async def route_metriques(request: Request) -> dict:
    """Métriques d'entraînement (``resultats.json``), robustesse naturelle, purification et calibration."""
    ctx = _ctx(request)
    artefacts = ctx.params.dossier_artefacts
    return {
        "entrainement": _lire_json(ctx.params.dossier_modeles / "resultats.json"),
        "robustesse": _lire_json(artefacts / "robustesse.json"),
        "calibration": ctx.seuils.rapport or None,
    }


@routeur.get("/rapport-securite", tags=["Laboratoire"])
async def route_rapport(request: Request) -> dict:
    """Dernier rapport de la suite de tests de sécurité (``make test-securite``)."""
    rapport = _lire_json(_ctx(request).params.dossier_artefacts / "rapport_securite.json")
    if rapport is None:
        raise HTTPException(404, {"detail": "Aucun rapport : lancez « make test-securite ».", "code": "pas_de_rapport"})
    return rapport


@routeur.get("/sante", response_model=EtatSante, tags=["Service"])
async def route_sante(request: Request) -> EtatSante:
    """État du service et des modèles chargés (sans détail sensible)."""
    ctx = _ctx(request)
    modeles = {**{nom: True for nom in ctx.modeles.fruits}, "gardien": ctx.modeles.gardien is not None}
    calibre = ctx.seuils.calibre and ctx.gardien is not None
    return EtatSante(
        statut="ok" if calibre else "degrade",
        modeles=modeles,
        modele_actif=ctx.modeles.actif,
        empreintes_verifiees=bool(ctx.modeles.empreintes),
        seuils_calibres=calibre,
        version=request.app.state.version,
    )


# ------------------------------------------------------------- scénarios
@routeur.get("/scenarios", response_model=list[Scenario], tags=["Laboratoire"])
async def route_scenarios() -> list[Scenario]:
    """Liste des scénarios d'attaque de la galerie."""
    return scen.lister()


@routeur.post("/scenarios/{identifiant}", response_model=ResultatScenario, tags=["Laboratoire"])
@limiteur.limit(LIMITE_SCENARIOS)
async def route_executer_scenario(request: Request, identifiant: str) -> ResultatScenario:
    """Exécute un scénario et renvoie **attendu / obtenu / réussi**."""
    if identifiant not in scen.SCENARIOS:
        raise HTTPException(404, {"detail": "Scénario inconnu.", "code": "scenario_inconnu"})
    return await request.app.state.executeur.executer(
        scen.executer, _ctx(request), identifiant, delai_s=_ctx(request).params.delai_inference_s * 3
    )
