"""Configuration pytest commune : client HTTP partagé (modèles chargés une seule fois)."""

import io
import json
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Compte de test (créé avant tout import de l'application ; jamais utilisé en production).
IDENTIFIANT_TEST, MOT_DE_PASSE_TEST = "testeur", "mot-de-passe-de-test-42"
from app.auth import hacher_mot_de_passe  # noqa: E402

os.environ["FRG_COMPTES"] = json.dumps({IDENTIFIANT_TEST: hacher_mot_de_passe(MOT_DE_PASSE_TEST)})
os.environ["FRG_AUTHENTIFICATION"] = "true"


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app, base_url="http://localhost") as c:
        r = c.post("/api/auth/connexion", json={"identifiant": IDENTIFIANT_TEST, "mot_de_passe": MOT_DE_PASSE_TEST})
        assert r.status_code == 200, r.text
        c.headers["Authorization"] = f"Bearer {r.json()['jeton']}"
        yield c


@pytest.fixture(autouse=True)
def _reinitialiser_limites():
    """Chaque test démarre avec des compteurs de débit vierges."""
    from app.api.limites import limiteur

    limiteur.reset()
    yield


def png(image) -> bytes:
    t = io.BytesIO()
    image.save(t, format="PNG")
    return t.getvalue()
