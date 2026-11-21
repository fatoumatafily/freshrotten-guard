"""Menaces visant le serveur web et l'API (complète les scénarios de la galerie)."""

import asyncio
import json
import logging
import shutil
import tempfile
import time
from pathlib import Path

import pytest
from app import cas_test
from app.execution import Executeur
from app.inference import IntegriteCompromise, charger_modeles
from fastapi import HTTPException

from tests.conftest import png

pytestmark = pytest.mark.securite
WEB = "Serveur web et API"


def fichiers_temporaires() -> set[Path]:
    """Fichiers temporaires au format de Python/Starlette (tmpXXXX) : détecte toute mise sur disque."""
    return {p for p in Path(tempfile.gettempdir()).iterdir() if p.name.startswith("tmp") and p.is_file()}


def envoyer(client, octets, nom="image.png", type_="image/png", url="/api/analyser", **kw):
    return client.post(url, files={"fichier": (nom, octets, type_)}, **kw)


def test_en_tetes_securite(client, scenario):
    s = scenario(WEB, "En-têtes de sécurité HTTP", "CSP, nosniff, frame-ancestors, Referrer/Permissions-Policy")
    h = client.get("/api/sante").headers
    attendus = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
    }
    for cle, valeur in attendus.items():
        assert h[cle] == valeur
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert "default-src 'none'" in h["content-security-policy"]
    assert "camera=()" in h["permissions-policy"]
    assert "server" not in h
    s.obtenu("Tous les en-têtes présents, en-tête Server masqué")


def test_cors_restreint(client, scenario):
    s = scenario(WEB, "CORS : origine non autorisée", "Aucun en-tête Access-Control-Allow-Origin")
    r = client.options(
        "/api/analyser", headers={"Origin": "https://site-pirate.example", "Access-Control-Request-Method": "POST"}
    )
    assert "access-control-allow-origin" not in r.headers
    ok = client.options(
        "/api/analyser", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    s.obtenu("Origine pirate refusée, origine du frontend autorisée")


def test_corps_trop_gros(client, scenario):
    s = scenario(WEB, "Corps de requête de 20 Mo", "413 avant traitement")
    r = envoyer(client, cas_test.gros_fichier(20 * 1024 * 1024))
    assert r.status_code == 413
    s.obtenu(f"HTTP {r.status_code} : {r.json()['detail']}")


def test_fichier_juste_trop_gros(client, scenario):
    s = scenario(WEB, "Fichier de 5,5 Mo (limite 5 Mo)", "400 fichier_trop_gros")
    r = envoyer(client, cas_test.gros_fichier(int(5.5 * 1024 * 1024)))
    assert r.status_code in (400, 413)
    s.obtenu(f"HTTP {r.status_code} : {r.json()['code']}")


def test_content_type_mensonger(client, scenario):
    s = scenario("Fichiers malveillants", "Exécutable envoyé avec Content-Type image/jpeg", "400 executable")
    r = envoyer(client, cas_test.faux_exe(), nom="photo.jpg", type_="image/jpeg")
    assert r.status_code == 400 and r.json()["code"] == "executable"
    s.obtenu(f"HTTP 400 : {r.json()['detail']}")


@pytest.mark.parametrize("nom", ["../../etc/passwd", "<script>alert(1)</script>.png", "..\\..\\win.ini", "a" * 300])
def test_nom_de_fichier_malveillant(client, scenario, nom):
    s = scenario("Fichiers malveillants", f"Nom de fichier malveillant « {nom[:30]} »", "Nom ignoré, jamais renvoyé")
    avant = fichiers_temporaires()
    r = envoyer(client, png(cas_test.dessin_orange()), nom=nom)
    assert r.status_code == 200
    assert nom not in r.text and "passwd" not in r.text and "<script>" not in r.text
    assert fichiers_temporaires() - avant == set()
    s.obtenu("Analyse normale, nom absent de la réponse, aucun fichier créé")


def test_aucune_image_ecrite_sur_disque(client, scenario, monkeypatch):
    s = scenario(
        WEB,
        "Upload de 4 Mo (au-delà du seuil de mise sur disque par défaut de Starlette)",
        "Aucun basculement sur disque",
    )
    bascules = []
    origine = tempfile.SpooledTemporaryFile.rollover

    def espion(self):
        bascules.append(self)
        return origine(self)

    monkeypatch.setattr(tempfile.SpooledTemporaryFile, "rollover", espion)
    r = envoyer(client, cas_test.gros_fichier(4 * 1024 * 1024))
    assert r.status_code == 200
    assert bascules == [], "le fichier uploadé a été écrit sur disque"
    s.obtenu("Traitement entièrement en mémoire (0 basculement sur disque)")


def test_limitation_debit_attaque(client, scenario):
    s = scenario(WEB, "Rafale de 13 requêtes /api/attaque en 1 minute (limite 12)", "429 à partir de la 13e")
    octets = png(cas_test.dessin_orange(128))
    codes = [
        client.post(
            "/api/attaque", files={"fichier": ("x.png", octets, "image/png")}, data={"attaque": "fgsm", "epsilon": "0"}
        ).status_code
        for _ in range(13)
    ]
    assert codes[:12] == [200] * 12 and codes[12] == 429
    s.obtenu(f"Codes : 12 × 200 puis {codes[12]}")


def test_limitation_debit_analyse_plus_souple(client, scenario):
    from app.config import parametres

    p = parametres()
    s = scenario(WEB, "Endpoints d'attaque plus limités que l'analyse", "limite attaque < limite analyse")
    par_minute = lambda t: int(t.split("/")[0])  # noqa: E731
    assert par_minute(p.limite_attaque) < par_minute(p.limite_comparer) < par_minute(p.limite_analyse)
    s.obtenu(f"attaque {p.limite_attaque}, comparer {p.limite_comparer}, analyse {p.limite_analyse}")


def test_erreurs_generiques(client, scenario):
    s = scenario(WEB, "Messages d'erreur sans détail interne", "Aucune trace, aucun écho des entrées")
    r1 = client.get("/api/inexistant")
    r2 = client.post("/api/analyser", params={"modele": "<img src=x onerror=alert(1)>"})
    for r in (r1, r2):
        texte = r.text
        assert "Traceback" not in texte and 'File "' not in texte
        assert "onerror" not in texte
    s.obtenu(f"404 → « {r1.json()['detail']} », 422 → « {r2.json()['detail']} »")


def test_erreur_interne_masquee(scenario):
    s = scenario(WEB, "Exception interne", "500 générique, pile d'appels seulement dans les logs")
    from app.main import creer_application
    from fastapi.testclient import TestClient

    app = creer_application()

    @app.get("/api/boum")
    async def boum():
        raise RuntimeError("secret interne : /chemin/vers/modele")

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/boum")
    assert r.status_code == 500
    assert "secret" not in r.text and "RuntimeError" not in r.text
    s.obtenu(f"HTTP 500 : {r.json()['detail']}")


def test_journal_sans_image_ni_ip_claire(client, scenario, caplog):
    s = scenario(WEB, "Journalisation des rejets", "Événement JSON, IP hachée, ni image ni nom de fichier")
    with caplog.at_level(logging.WARNING, logger="frg.securite"):
        envoyer(client, cas_test.faux_php(), nom="secret_nom.jpg")
    lignes = [json.loads(r.getMessage()) for r in caplog.records if r.name == "frg.securite"]
    assert lignes and lignes[-1]["evenement"] == "rejet_fichier"
    brut = caplog.text
    assert "secret_nom" not in brut and "testclient" not in brut and "<?php" not in brut
    assert len(lignes[-1]["ip_hachee"]) == 16
    s.obtenu(f"Journal : {json.dumps(lignes[-1], ensure_ascii=False)}")


def test_file_bornee_et_delai(scenario):
    s = scenario(WEB, "Déni de service : file d'inférence saturée / inférence trop longue", "503 immédiat")

    async def scenario_async():
        ex = Executeur(file_max=1, delai_s=0.3, travailleurs=1)
        lente = asyncio.create_task(ex.executer(time.sleep, 0.6))
        await asyncio.sleep(0.05)
        with pytest.raises(HTTPException) as plein:
            await ex.executer(time.sleep, 0)
        with pytest.raises(HTTPException) as delai:
            await lente
        ex.fermer()
        return plein.value.detail["code"], delai.value.detail["code"]

    codes = asyncio.run(scenario_async())
    assert codes == ("serveur_occupe", "delai_depasse")
    s.obtenu(f"File pleine → {codes[0]}, délai dépassé → {codes[1]}")


def test_demarrage_refuse_modele_altere(tmp_path, scenario):
    s = scenario(
        "Modèle et serveur", "Démarrage avec un fichier .keras altéré", "Refus de charger (IntegriteCompromise)"
    )
    from app.config import Parametres, parametres

    shutil.copytree(parametres().dossier_modeles, tmp_path / "model")
    cible = tmp_path / "model" / "FreshRotten_model.keras"
    octets = bytearray(cible.read_bytes())
    octets[-100] ^= 0x01
    cible.write_bytes(bytes(octets))
    with pytest.raises(IntegriteCompromise) as exc:
        charger_modeles(Parametres(dossier_modeles=tmp_path / "model"))
    s.obtenu(f"Refusé : {str(exc.value)[:70]}…")


def test_documentation_swagger(client, scenario):
    s = scenario(WEB, "Documentation API (Swagger)", "Schéma OpenAPI disponible et validé")
    schema = client.get("/openapi.json").json()
    for chemin in ["/api/analyser", "/api/analyser/comparer", "/api/attaque", "/api/metriques", "/api/sante"]:
        assert chemin in schema["paths"]
    s.obtenu(f"{len(schema['paths'])} routes documentées")
