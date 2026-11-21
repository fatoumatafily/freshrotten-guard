"""Schémas Pydantic des réponses et paramètres de l'API (documentés dans Swagger)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Statut = Literal["ok", "rejet"]
Etat = Literal["fresh", "rotten"]
Fruit = Literal["apple", "banana", "orange"]
NomModele = Literal["base", "robuste"]
TypeAttaque = Literal["fgsm", "pgd", "pgd_ciblee"]
NomClasse = Literal["apple_fresh", "apple_rotten", "banana_fresh", "banana_rotten", "orange_fresh", "orange_rotten"]


class Controle(BaseModel):
    """Résultat d'une couche de défense (affiché dans le détail du verdict)."""

    nom: str
    reussi: bool
    valeur: float | None = None
    seuil: float | None = None
    message: str


class ResultatAnalyse(BaseModel):
    """Réponse de ``POST /api/analyser``."""

    statut: Statut
    modele: NomModele
    fruit: Fruit | None = None
    etat: Etat | None = None
    classe: NomClasse | None = None
    confiance: float | None = Field(default=None, ge=0, le=1)
    probabilites: dict[str, float] = Field(default_factory=dict, description="Arrondies (anti-extraction)")
    raison_rejet: str | None = Field(default=None, description="Message lisible si statut = rejet")
    code_rejet: str | None = None
    alertes: list[str] = Field(default_factory=list)
    controles: list[Controle] = Field(default_factory=list)
    purification: str | None = None
    duree_ms: float


class ResultatComparaison(BaseModel):
    """Réponse de ``POST /api/analyser/comparer``."""

    base: ResultatAnalyse
    robuste: ResultatAnalyse


ModeAttaque = Literal["boite_blanche", "transfert"]


class PredictionAttaque(BaseModel):
    classe: NomClasse
    confiance: float
    probabilites: dict[str, float]


class ResultatModeleAttaque(BaseModel):
    """Ce que voit un modèle : avant / après attaque."""

    propre: PredictionAttaque
    attaquee: PredictionAttaque
    trompe: bool = Field(description="La prédiction a changé par rapport à l'image propre")
    cible_atteinte: bool | None = Field(default=None, description="PGD ciblée : la classe visée est obtenue")
    manipulation_detectee: bool = Field(description="Détection par purification (feature squeezing)")
    prediction_purifiee: PredictionAttaque = Field(description="Prédiction après purification JPEG")
    image_attaquee: str = Field(description="Image adverse PNG 128×128 (data URL, téléchargeable)")
    perturbation: str = Field(description="Perturbation amplifiée pour être visible (data URL)")
    norme_linf: float


class ResultatAttaque(BaseModel):
    """Réponse de ``POST /api/attaque``."""

    attaque: TypeAttaque
    epsilon: float
    cible: NomClasse | None
    mode: ModeAttaque = Field(
        description="boite_blanche : chaque modèle est attaqué avec ses propres gradients ; "
        "transfert : l'image est fabriquée contre le modèle de base et montrée aux deux"
    )
    image_originale: str = Field(description="Entrée 128×128 telle que vue par le modèle (data URL)")
    modeles: dict[NomModele, ResultatModeleAttaque]
    duree_ms: float


class EtatSante(BaseModel):
    statut: Literal["ok", "degrade"]
    modeles: dict[str, bool]
    modele_actif: NomModele
    empreintes_verifiees: bool
    seuils_calibres: bool
    version: str


class Scenario(BaseModel):
    id: str
    categorie: str
    titre: str
    description: str
    attendu: str
    disponible: bool = True


class ResultatScenario(BaseModel):
    id: str
    titre: str
    attendu: str
    obtenu: str
    reussi: bool
    details: dict[str, object] = Field(default_factory=dict)
    duree_ms: float


class Erreur(BaseModel):
    """Erreur générique renvoyée au client (jamais de trace d'exécution)."""

    detail: str
    code: str
