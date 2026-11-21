"""Point d'entrée FastAPI de FreshRotten Guard.

Lancement : ``uvicorn app.main:app`` depuis ``backend/``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.formparsers import MultiPartParser

from . import ood
from .api.limites import limiteur
from .api.middlewares import EnTetesSecurite, LimiteTailleCorps
from .api.routes import routeur
from .config import parametres
from .execution import Executeur
from .inference import charger_modeles
from .journal import configurer_journalisation, evenement
from .service import Contexte

VERSION = "1.0.0"
journal = logging.getLogger("frg.api")


@asynccontextmanager
async def cycle_de_vie(app: FastAPI) -> AsyncIterator[None]:
    """Charge les modèles **une seule fois** au démarrage (et vérifie leur intégrité)."""
    configurer_journalisation()
    params = parametres()
    modeles = charger_modeles(params)
    stats = ood.StatsGardien.charger(params.fichier_stats_ood)
    seuils = ood.Seuils.charger(params.fichier_seuils)
    if stats is None or not seuils.calibre:
        journal.warning("Seuils hors domaine NON CALIBRÉS : lancez scripts/calibrer_seuils.py")
    app.state.ctx = Contexte(modeles=modeles, params=params, gardien=stats, seuils=seuils)
    app.state.executeur = Executeur(params.file_max, params.delai_inference_s)
    app.state.version = VERSION
    journal.info("FreshRotten Guard prêt (modèle actif : %s)", params.modele_actif)
    yield
    app.state.executeur.fermer()


def creer_application() -> FastAPI:
    params = parametres()
    # Starlette place les fichiers > 1 Mo dans un fichier temporaire SUR DISQUE.
    # On relève ce seuil au-dessus de la taille maximale acceptée : tout reste
    # en mémoire (la taille du corps est de toute façon bornée par LimiteTailleCorps).
    MultiPartParser.spool_max_size = params.taille_max_octets + 128 * 1024
    app = FastAPI(
        title="FreshRotten Guard",
        version=VERSION,
        description=(
            "Classification **frais / pourri** (pomme, banane, orange) avec défenses de sécurité de l'IA : "
            "détection hors domaine, résistance adversariale, validation stricte des fichiers. "
            "Aucune image n'est stockée."
        ),
        lifespan=cycle_de_vie,
        docs_url="/docs" if params.documentation_api else None,
        redoc_url=None,
        openapi_url="/openapi.json" if params.documentation_api else None,
    )
    app.state.limiter = limiteur

    # Ordre : le dernier ajouté est le plus externe.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=params.origines_cors,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
        max_age=600,
    )
    # Marge de 64 Ko pour l'enveloppe multipart autour du fichier.
    app.add_middleware(LimiteTailleCorps, limite=params.taille_max_octets + 64 * 1024)
    app.add_middleware(EnTetesSecurite)

    @app.exception_handler(RateLimitExceeded)
    async def trop_de_requetes(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        evenement("limite_debit", request.client.host if request.client else None, chemin=request.url.path)
        return JSONResponse(
            {"detail": "Trop de requêtes : réessayez dans quelques instants.", "code": "limite_debit"},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(RequestValidationError)
    async def parametres_invalides(request: Request, exc: RequestValidationError) -> JSONResponse:
        # On ne renvoie que le nom des champs fautifs, jamais la valeur reçue.
        champs = sorted({str(e["loc"][-1]) for e in exc.errors() if e.get("loc")})
        return JSONResponse(
            {"detail": "Paramètres invalides.", "code": "parametres_invalides", "champs": champs},
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def erreur_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(exc.detail, status_code=exc.status_code, headers=exc.headers)
        messages = {404: "Ressource introuvable.", 405: "Méthode non autorisée."}
        return JSONResponse(
            {"detail": messages.get(exc.status_code, "Requête refusée."), "code": f"http_{exc.status_code}"},
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def erreur_interne(request: Request, exc: Exception) -> JSONResponse:
        # Détails (pile d'appels) uniquement dans les journaux serveur.
        journal.exception("Erreur interne sur %s", request.url.path)
        return JSONResponse({"detail": "Erreur interne du serveur.", "code": "erreur_interne"}, status_code=500)

    app.include_router(routeur)
    return app


app = creer_application()
