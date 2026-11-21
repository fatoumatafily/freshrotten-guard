"""Configuration centralisée de FreshRotten Guard.

Toutes les valeurs sont lisibles depuis l'environnement (préfixe ``FRG_``) ou un
fichier ``.env``. Aucun secret n'est codé en dur : le sel de hachage des IP est
généré aléatoirement au démarrage s'il n'est pas fourni.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RACINE_PROJET = Path(__file__).resolve().parents[2]

# Empreintes SHA-256 attendues des fichiers modèles (vérifiées au démarrage).
EMPREINTES_PAR_DEFAUT: dict[str, str] = {
    "FreshRotten_model.keras": "219baea2f4b3b4b37399aba4502b2d33b820baf40df581585ca68b2fb001206a",
    "FreshRotten_model_robuste.keras": "3d244ef84305b2ddb67fc93e0095ff3bf7acc0e27a7eb8283536e9e72104d25c",
    # Poids ImageNet officiels de MobileNetV2 (format .h5, non couvert par safe_mode).
    "mobilenet_v2_weights_tf_dim_ordering_tf_kernels_1.0_224.h5": (
        "3e195a2857356cfc092cbbb460beb2a5bce279015d7792598b8d3d9e451902e3"
    ),
}


class Parametres(BaseSettings):
    """Paramètres de l'application (surchargés par variables d'environnement)."""

    model_config = SettingsConfigDict(
        env_prefix="FRG_", env_file=RACINE_PROJET / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Modèles -----------------------------------------------------------
    dossier_modeles: Path = RACINE_PROJET / "model"
    dossier_artefacts: Path = RACINE_PROJET / "backend" / "artefacts"
    modele_actif: Literal["robuste", "base"] = "robuste"
    verifier_empreintes: bool = True
    # Dossier des poids du gardien ImageNet (cache Keras par défaut).
    dossier_poids_gardien: Path = Path.home() / ".keras" / "models"

    # --- Fichiers ----------------------------------------------------------
    taille_max_octets: int = Field(default=5 * 1024 * 1024, ge=1024, le=50 * 1024 * 1024)
    pixels_max: int = Field(default=40_000_000, ge=10_000)
    dimension_max: int = Field(default=8000, ge=64)
    dimension_min: int = Field(default=32, ge=8)

    # --- Web ---------------------------------------------------------------
    origines_cors: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    limite_analyse: str = "240/minute"
    limite_comparer: str = "60/minute"
    limite_attaque: str = "12/minute"
    limite_scenarios: str = "30/minute"
    delai_inference_s: float = Field(default=15.0, gt=0)
    file_max: int = Field(default=8, ge=1, le=256)
    decimales_probabilites: int = Field(default=3, ge=1, le=6)
    sel_hachage_ip: str = Field(default_factory=lambda: secrets.token_hex(16))
    documentation_api: bool = True

    # --- Authentification ---------------------------------------------------
    authentification: bool = True
    # {"identifiant": "scrypt$..."} — généré par scripts/creer_compte.py, jamais de mot de passe en clair.
    comptes: dict[str, str] = Field(default_factory=dict)
    # Clé de signature des jetons. Si absente : générée au démarrage (sessions perdues au redémarrage).
    secret_session: str = Field(default_factory=lambda: secrets.token_hex(32))
    duree_session_min: int = Field(default=480, ge=5, le=7 * 24 * 60)
    limite_connexion: str = "5/minute"

    # --- Défenses ----------------------------------------------------------
    purification_par_defaut: bool = False
    detection_manipulation: bool = True

    @property
    def fichier_seuils(self) -> Path:
        return self.dossier_artefacts / "seuils.json"

    @property
    def fichier_stats_ood(self) -> Path:
        return self.dossier_artefacts / "stats_gardien.npz"


@lru_cache
def parametres() -> Parametres:
    """Instance unique des paramètres."""
    return Parametres()
