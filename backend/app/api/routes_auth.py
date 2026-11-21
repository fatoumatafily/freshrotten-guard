"""Routes d'authentification."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import Session, authentifier, emettre_jeton, exiger_session
from ..config import parametres
from ..journal import evenement
from .limites import limiteur

routeur_auth = APIRouter(prefix="/api/auth", tags=["Authentification"])


class DemandeConnexion(BaseModel):
    identifiant: str = Field(min_length=1, max_length=64)
    mot_de_passe: str = Field(min_length=1, max_length=256)


class ReponseConnexion(BaseModel):
    jeton: str
    identifiant: str
    expire_le: int = Field(description="Horodatage Unix d'expiration")


class ReponseMoi(BaseModel):
    identifiant: str
    expire_le: int


@routeur_auth.post("/connexion", response_model=ReponseConnexion)
@limiteur.limit(parametres().limite_connexion)
async def connexion(request: Request, demande: DemandeConnexion) -> ReponseConnexion:
    """Échange identifiant + mot de passe contre un jeton de session (5 essais / minute / IP)."""
    if not authentifier(demande.identifiant, demande.mot_de_passe):
        # Jamais le mot de passe dans les journaux ; l'identifiant est tronqué.
        evenement(
            "connexion_refusee", request.client.host if request.client else None, identifiant=demande.identifiant[:32]
        )
        raise HTTPException(401, {"detail": "Identifiant ou mot de passe incorrect.", "code": "identifiants_invalides"})
    session, jeton = emettre_jeton(demande.identifiant)
    evenement("connexion_reussie", request.client.host if request.client else None, identifiant=session.identifiant)
    return ReponseConnexion(jeton=jeton, identifiant=session.identifiant, expire_le=session.expire_le)


@routeur_auth.get("/moi", response_model=ReponseMoi)
async def moi(session: Session = Depends(exiger_session)) -> ReponseMoi:
    """Vérifie le jeton et renvoie l'utilisateur connecté."""
    return ReponseMoi(identifiant=session.identifiant, expire_le=session.expire_le)
