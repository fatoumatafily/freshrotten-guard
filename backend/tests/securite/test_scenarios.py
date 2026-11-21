"""Tous les scénarios de la galerie du Laboratoire, exécutés comme tests.

Les scénarios « Robustesse naturelle » et « Manipulation des couleurs » sont
informatifs : un échec y décrit une limite connue (cf. SECURITY.md) et ne fait
pas échouer la suite (xfail non strict).
"""

import pytest
from app import scenarios as scen

INFORMATIFS = {"Robustesse naturelle", "Manipulation des couleurs"}


@pytest.fixture(scope="module")
def ctx(client):
    return client.app.state.ctx


@pytest.mark.securite
@pytest.mark.parametrize("identifiant", list(scen.SCENARIOS))
def test_scenario(ctx, scenario, identifiant):
    d = scen.SCENARIOS[identifiant]
    s = scenario(d.categorie, d.titre, d.attendu)
    if not d.disponible():
        s.obtenu("Indisponible (image de démonstration absente)")
        pytest.skip("tests/data/fruits absent : lancez scripts/generer_cas_test.py --dataset dataset")
    res = scen.executer(ctx, identifiant)
    s.obtenu(res.obtenu, **res.details)
    if d.categorie in INFORMATIFS and not res.reussi:
        s.obtenu(res.obtenu, limite_connue=True)
        pytest.xfail("limite connue documentée dans SECURITY.md")
    assert res.reussi, res.obtenu
