"""Limitation de débit par adresse IP (slowapi).

Les endpoints d'attaque, coûteux, sont bien plus limités que l'analyse.
Derrière un proxy inverse, configurez uvicorn avec ``--proxy-headers`` et
``--forwarded-allow-ips`` pour que l'IP réelle du client soit utilisée.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import parametres

limiteur = Limiter(key_func=get_remote_address, headers_enabled=False, default_limits=["600/minute"])
LIMITE_ANALYSE = parametres().limite_analyse
LIMITE_COMPARER = parametres().limite_comparer
LIMITE_ATTAQUE = parametres().limite_attaque
LIMITE_SCENARIOS = parametres().limite_scenarios
