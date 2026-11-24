"""Tests fonctionnels de l'API."""

import pytest
from app import cas_test
from app.scenarios import image_fruit
from PIL import Image

from tests.conftest import png


def envoyer(client, octets, url="/api/analyser", nom="image.png", **params):
    return client.post(url, files={"fichier": (nom, octets, "image/png")}, params=params)


def test_sante(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    data = r.json()
    assert data["modeles"] == {"base": True, "robuste": True, "gardien": True}
    assert data["modele_actif"] == "robuste"
    assert data["empreintes_verifiees"] is True


def test_metriques(client):
    data = client.get("/api/metriques").json()
    assert data["entrainement"]["modele_defendu"]["accuracy_pgd"] == pytest.approx(0.7957, abs=1e-3)


def test_bruit_rejete_alors_que_le_modele_seul_dirait_banane(client):
    r = envoyer(client, png(cas_test.image_bruit()))
    assert r.status_code == 200
    data = r.json()
    assert data["statut"] == "rejet"
    assert data["fruit"] is None and data["raison_rejet"]
    assert len(data["probabilites"]) == 6


@pytest.mark.parametrize("classe", ["apple_fresh", "banana_rotten", "orange_fresh"])
def test_fruit_valide_accepte(client, classe):
    image = image_fruit(classe)
    if image is None:
        pytest.skip("tests/data/fruits absent : lancez scripts/generer_cas_test.py --dataset dataset")
    data = envoyer(client, png(image)).json()
    assert data["statut"] == "ok", data
    assert data["classe"] == classe
    assert data["fruit"] == classe.split("_")[0] and data["etat"] == classe.split("_")[1]


def test_comparer_deux_modeles(client):
    data = envoyer(client, png(cas_test.dessin_orange()), url="/api/analyser/comparer").json()
    assert data["base"]["modele"] == "base" and data["robuste"]["modele"] == "robuste"


def test_purification_parametre(client):
    data = envoyer(client, png(cas_test.dessin_orange()), purification="jpeg").json()
    assert data["purification"] == "jpeg"


def test_parametre_invalide(client):
    r = envoyer(client, png(cas_test.dessin_orange()), modele="inexistant")
    assert r.status_code == 422
    assert r.json()["code"] == "parametres_invalides"


def test_attaque_pgd(client):
    image = image_fruit("apple_fresh") or cas_test.dessin_orange()
    r = client.post(
        "/api/attaque",
        files={"fichier": ("x.png", png(image), "image/png")},
        data={"attaque": "pgd", "epsilon": "0.03"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert set(data["modeles"]) == {"base", "robuste"}
    for m in data["modeles"].values():
        assert m["image_attaquee"].startswith("data:image/png;base64,")
        assert m["norme_linf"] <= 0.03 + 1e-6


@pytest.mark.parametrize("eps", ["-0.1", "0.5", "abc"])
def test_attaque_epsilon_borne(client, eps):
    r = client.post(
        "/api/attaque",
        files={"fichier": ("x.png", png(cas_test.dessin_orange()), "image/png")},
        data={"attaque": "fgsm", "epsilon": eps},
    )
    assert r.status_code == 422


def test_attaque_type_ferme(client):
    r = client.post(
        "/api/attaque",
        files={"fichier": ("x.png", png(cas_test.dessin_orange()), "image/png")},
        data={"attaque": "deepfool", "epsilon": "0.01"},
    )
    assert r.status_code == 422


def test_attaque_ciblee_exige_cible(client):
    r = client.post(
        "/api/attaque",
        files={"fichier": ("x.png", png(cas_test.dessin_orange()), "image/png")},
        data={"attaque": "pgd_ciblee", "epsilon": "0.01"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "cible_requise"


def test_image_attaquee_reuploadable(client):
    """L'image téléchargée depuis le Laboratoire doit être acceptée par l'analyse normale (format)."""
    import base64

    image = image_fruit("apple_fresh") or cas_test.dessin_orange()
    data = client.post(
        "/api/attaque",
        files={"fichier": ("x.png", png(image), "image/png")},
        data={"attaque": "fgsm", "epsilon": "0.02"},
    ).json()
    octets = base64.b64decode(data["modeles"]["base"]["image_attaquee"].split(",", 1)[1])
    assert Image.open(__import__("io").BytesIO(octets)).size == (128, 128)
    assert envoyer(client, octets).status_code == 200


def test_scenarios_liste(client):
    data = client.get("/api/scenarios").json()
    assert len(data) > 30
    assert {"id", "categorie", "titre", "attendu", "disponible"} <= set(data[0])


def test_variable_vide_garde_la_valeur_par_defaut(monkeypatch):
    """« FRG_SEL_HACHAGE_IP= » vide ne doit pas donner un sel vide (IP hachées devinables)."""
    from app.config import Parametres

    monkeypatch.setenv("FRG_SEL_HACHAGE_IP", "")
    sel = Parametres().sel_hachage_ip
    assert len(sel) == 32
