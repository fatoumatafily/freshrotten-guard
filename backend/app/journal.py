"""Journalisation de sécurité.

On journalise les rejets et les attaques détectées (type, horodatage, IP
**hachée** avec un sel secret), mais **jamais** les images, ni leur nom de
fichier, ni l'IP en clair.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from .config import parametres

journal_securite = logging.getLogger("frg.securite")


def hacher_ip(ip: str | None) -> str:
    """HMAC-SHA256 tronqué de l'IP : permet de corréler sans identifier."""
    sel = parametres().sel_hachage_ip.encode()
    return hmac.new(sel, (ip or "inconnue").encode(), hashlib.sha256).hexdigest()[:16]


def evenement(type_: str, ip: str | None, **details: object) -> None:
    """Écrit un événement de sécurité structuré (JSON, une ligne)."""
    interdits = {"image", "octets", "nom_fichier", "filename"}
    propre = {k: v for k, v in details.items() if k not in interdits}
    ligne = {
        "horodatage": datetime.now(UTC).isoformat(timespec="seconds"),
        "evenement": type_,
        "ip_hachee": hacher_ip(ip),
        **propre,
    }
    journal_securite.warning(json.dumps(ligne, ensure_ascii=False, default=str))


def configurer_journalisation() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    # Les journaux d'accès d'uvicorn ne contiennent ni corps ni nom de fichier.
    logging.getLogger("multipart").setLevel(logging.WARNING)
