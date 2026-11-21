"""Menaces sur l'authentification."""

import base64
import json
import time

import pytest
from app import cas_test
from app.auth import emettre_jeton, hacher_mot_de_passe, lire_jeton, verifier_mot_de_passe

from tests.conftest import IDENTIFIANT_TEST, MOT_DE_PASSE_TEST, png

pytestmark = pytest.mark.securite
AUTH = "Authentification"
PROTEGEES = [
    ("post", "/api/analyser"),
    ("post", "/api/attaque"),
    ("get", "/api/metriques"),
    ("get", "/api/scenarios"),
    ("post", "/api/analyser/comparer"),
    ("get", "/api/rapport-securite"),
]


def sans_jeton(client, methode, url, jeton=None):
    en_tetes = {"Authorization": f"Bearer {jeton}"} if jeton else {"Authorization": ""}
    kw = {"files": {"fichier": ("x.png", png(cas_test.dessin_orange(64)), "image/png")}} if methode == "post" else {}
    return getattr(client, methode)(url, headers=en_tetes, **kw)


def test_routes_protegees_sans_jeton(client, scenario):
    s = scenario(AUTH, "Accès aux routes sans être connecté", "401 sur toutes les routes protégées")
    codes = {url: sans_jeton(client, m, url).status_code for m, url in PROTEGEES}
    assert set(codes.values()) == {401}, codes
    assert client.get("/api/sante", headers={"Authorization": ""}).status_code == 200
    s.obtenu(f"{len(codes)} routes → 401 ; /api/sante reste publique")


def test_mauvais_mot_de_passe_message_generique(client, scenario):
    s = scenario(AUTH, "Mauvais mot de passe / identifiant inconnu", "Même message générique (pas d'énumération)")
    r1 = client.post("/api/auth/connexion", json={"identifiant": IDENTIFIANT_TEST, "mot_de_passe": "faux"})
    r2 = client.post("/api/auth/connexion", json={"identifiant": "inconnu", "mot_de_passe": "faux"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()
    s.obtenu(f"401 : « {r1.json()['detail']} » dans les deux cas")


def test_force_brute_limitee(client, scenario):
    s = scenario(AUTH, "Force brute : 6 tentatives en 1 minute", "429 à la 6e tentative")
    codes = [
        client.post("/api/auth/connexion", json={"identifiant": "x", "mot_de_passe": f"essai{i}"}).status_code
        for i in range(6)
    ]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    s.obtenu(f"Codes : {codes}")


def test_jeton_falsifie(client, scenario):
    s = scenario(AUTH, "Jeton falsifié (identité modifiée, signature conservée)", "401")
    _, jeton = emettre_jeton(IDENTIFIANT_TEST)
    charge, signature = jeton.split(".")
    donnees = json.loads(base64.urlsafe_b64decode(charge + "=="))
    donnees["sub"] = "admin"
    falsifie = base64.urlsafe_b64encode(json.dumps(donnees).encode()).rstrip(b"=").decode() + "." + signature
    assert sans_jeton(client, "get", "/api/metriques", falsifie).status_code == 401
    assert sans_jeton(client, "get", "/api/metriques", "nimportequoi").status_code == 401
    s.obtenu("Signature invalide → 401 ; jeton mal formé → 401")


def test_jeton_expire(client, scenario, monkeypatch):
    s = scenario(AUTH, "Jeton expiré", "401")
    _, jeton = emettre_jeton(IDENTIFIANT_TEST)
    reel = time.time
    monkeypatch.setattr(time, "time", lambda: reel() + 9 * 3600)
    assert lire_jeton(jeton) is None
    monkeypatch.setattr(time, "time", reel)
    assert lire_jeton(jeton) is not None
    s.obtenu("Refusé après 8 h, accepté avant")


def test_mots_de_passe_haches(scenario, caplog, client):
    s = scenario(AUTH, "Stockage et journalisation des mots de passe", "Empreinte scrypt salée ; jamais en clair")
    e1, e2 = hacher_mot_de_passe("secret-123456"), hacher_mot_de_passe("secret-123456")
    assert e1 != e2 and e1.startswith("scrypt$") and "secret" not in e1
    assert verifier_mot_de_passe("secret-123456", e1) and not verifier_mot_de_passe("autre", e1)
    client.post("/api/auth/connexion", json={"identifiant": IDENTIFIANT_TEST, "mot_de_passe": "MotDePasseEspion"})
    assert "MotDePasseEspion" not in caplog.text
    s.obtenu("Sel aléatoire (2 empreintes différentes), mot de passe absent des journaux")


def test_connexion_valide(client, scenario):
    s = scenario(AUTH, "Connexion avec le bon mot de passe", "Jeton valable, accès aux routes")
    r = client.post("/api/auth/connexion", json={"identifiant": IDENTIFIANT_TEST, "mot_de_passe": MOT_DE_PASSE_TEST})
    jeton = r.json()["jeton"]
    assert (
        client.get("/api/auth/moi", headers={"Authorization": f"Bearer {jeton}"}).json()["identifiant"]
        == IDENTIFIANT_TEST
    )
    s.obtenu(f"Jeton émis, expiration dans {(r.json()['expire_le'] - time.time()) / 3600:.0f} h")
