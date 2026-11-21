"""Collecte des résultats de la suite de sécurité et génération du rapport.

Chaque test appelle la fixture ``scenario(menace, attendu)`` puis
``scenario.obtenu(...)`` ; à la fin de la session, le rapport est écrit dans
``backend/artefacts/rapport_securite.md`` et ``rapport_securite.json`` (affiché
dans la page Laboratoire via ``GET /api/rapport-securite``).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pytest

SORTIE = Path(__file__).resolve().parents[2] / "artefacts"
_RESULTATS: list[Ligne] = []


@dataclass
class Ligne:
    id: str
    categorie: str
    menace: str
    attendu: str
    obtenu: str = "—"
    reussi: bool = False
    duree_ms: float = 0.0
    details: dict = field(default_factory=dict)


class Enregistreur:
    def __init__(self, ligne: Ligne) -> None:
        self.ligne = ligne

    def obtenu(self, texte: str, **details) -> None:
        self.ligne.obtenu = texte
        self.ligne.details.update(details)


@pytest.fixture
def scenario(request):
    debut = time.perf_counter()
    lignes: list[Ligne] = []

    def fabrique(categorie: str, menace: str, attendu: str) -> Enregistreur:
        ligne = Ligne(request.node.name, categorie, menace, attendu)
        lignes.append(ligne)
        return Enregistreur(ligne)

    yield fabrique
    for ligne in lignes:
        ligne.duree_ms = round((time.perf_counter() - debut) * 1000, 1)
        ligne.reussi = getattr(request.node, "_frg_reussi", False)
        _RESULTATS.append(ligne)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultat = yield
    rapport = resultat.get_result()
    if rapport.when == "call":
        item._frg_reussi = rapport.passed


def pytest_sessionfinish(session, exitstatus):
    if not _RESULTATS:
        return
    SORTIE.mkdir(parents=True, exist_ok=True)
    total, ok = len(_RESULTATS), sum(r.reussi for r in _RESULTATS)
    donnees = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "reussis": ok,
        "limites_connues": sum(bool(r.details.get("limite_connue")) for r in _RESULTATS),
        "resultats": [asdict(r) for r in _RESULTATS],
    }
    (SORTIE / "rapport_securite.json").write_text(json.dumps(donnees, indent=2, ensure_ascii=False), "utf-8")
    lignes = [
        "# Rapport de la suite de tests de sécurité — FreshRotten Guard",
        "",
        f"Généré le {donnees['date']} par `make test-securite`. **{ok}/{total} scénarios réussis.**",
        "",
    ]
    categories: dict[str, list[Ligne]] = {}
    for r in _RESULTATS:
        categories.setdefault(r.categorie, []).append(r)
    for cat, rs in categories.items():
        lignes += [f"## {cat}", "", "| Scénario | Attendu | Obtenu | Résultat |", "|---|---|---|---|"]
        for r in rs:
            obtenu = r.obtenu.replace("|", r"\|").replace("\n", " ")
            etat = "✅" if r.reussi else ("⚠️ limite connue" if r.details.get("limite_connue") else "❌")
            lignes.append(f"| {r.menace} | {r.attendu} | {obtenu} | {etat} |")
        lignes.append("")
    (SORTIE / "rapport_securite.md").write_text("\n".join(lignes), "utf-8")
    print(f"\nRapport de sécurité : {SORTIE / 'rapport_securite.md'} ({ok}/{total})")
