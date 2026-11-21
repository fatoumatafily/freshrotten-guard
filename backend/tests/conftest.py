"""Configuration pytest commune : client HTTP partagé (modèles chargés une seule fois)."""

import io
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def client():
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app, base_url="http://localhost") as c:
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
