"""Authentification : mots de passe hachés (scrypt) et jetons de session signés (HMAC-SHA256).

* Les comptes sont fournis par configuration (``FRG_COMPTES``), sous la forme
  ``{"identifiant": "scrypt$…"}`` ; aucun mot de passe en clair n'existe côté
  serveur. Générer une empreinte : ``python scripts/creer_compte.py``.
* Le jeton est ``base64url(charge).base64url(signature)`` ; la charge contient
  l'identifiant et la date d'expiration. Il est envoyé dans l'en-tête
  ``Authorization: Bearer …`` (pas de cookie : frontend et API sont sur deux
  domaines différents).
* Comparaisons à temps constant, et vérification factice pour un identifiant
  inconnu : le temps de réponse ne révèle pas quels comptes existent.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import parametres

N, R, P, LONGUEUR = 2**14, 8, 1, 32


def _b64(octets: bytes) -> str:
    return base64.urlsafe_b64encode(octets).rstrip(b"=").decode("ascii")


def _deb64(texte: str) -> bytes:
    return base64.urlsafe_b64decode(texte + "=" * (-len(texte) % 4))


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    sel = secrets.token_bytes(16)
    empreinte = hashlib.scrypt(mot_de_passe.encode(), salt=sel, n=N, r=R, p=P, dklen=LONGUEUR)
    return f"scrypt${N}${R}${P}${_b64(sel)}${_b64(empreinte)}"


# Empreinte factice : utilisée quand l'identifiant n'existe pas (temps de réponse constant).
_EMPREINTE_FACTICE = hacher_mot_de_passe(secrets.token_urlsafe(16))


def verifier_mot_de_passe(mot_de_passe: str, empreinte: str) -> bool:
    try:
        algo, n, r, p, sel, attendu = empreinte.split("$")
        if algo != "scrypt":
            return False
        calcule = hashlib.scrypt(
            mot_de_passe.encode(), salt=_deb64(sel), n=int(n), r=int(r), p=int(p), dklen=len(_deb64(attendu))
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calcule, _deb64(attendu))


def authentifier(identifiant: str, mot_de_passe: str) -> bool:
    empreinte = parametres().comptes.get(identifiant)
    valide = verifier_mot_de_passe(mot_de_passe, empreinte or _EMPREINTE_FACTICE)
    return valide and empreinte is not None


@dataclass
class Session:
    identifiant: str
    expire_le: int


def _signer(charge: bytes) -> bytes:
    return hmac.new(parametres().secret_session.encode(), charge, hashlib.sha256).digest()


def emettre_jeton(identifiant: str) -> tuple[Session, str]:
    expire = int(time.time()) + parametres().duree_session_min * 60
    charge = json.dumps({"sub": identifiant, "exp": expire}, separators=(",", ":")).encode()
    return Session(identifiant, expire), f"{_b64(charge)}.{_b64(_signer(charge))}"


def lire_jeton(jeton: str) -> Session | None:
    try:
        partie_charge, partie_signature = jeton.split(".")
        charge = _deb64(partie_charge)
        if not hmac.compare_digest(_signer(charge), _deb64(partie_signature)):
            return None
        donnees = json.loads(charge)
        identifiant, expire = str(donnees["sub"]), int(donnees["exp"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if expire < time.time() or identifiant not in parametres().comptes:
        return None  # expiré, ou compte supprimé depuis
    return Session(identifiant, expire)


_porteur = HTTPBearer(auto_error=False, description="Jeton obtenu via POST /api/auth/connexion")
NON_AUTHENTIFIE = HTTPException(
    401,
    {"detail": "Authentification requise.", "code": "non_authentifie"},
    headers={"WWW-Authenticate": "Bearer"},
)


async def exiger_session(
    request: Request, identifiants: HTTPAuthorizationCredentials | None = Depends(_porteur)
) -> Session:
    """Dépendance FastAPI : refuse (401) toute requête sans jeton valide."""
    if not parametres().authentification:
        return Session("anonyme", 0)
    if identifiants is None:
        raise NON_AUTHENTIFIE
    session = lire_jeton(identifiants.credentials)
    if session is None:
        raise NON_AUTHENTIFIE
    request.state.session = session
    return session
