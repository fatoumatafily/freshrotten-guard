"""Exécution bornée des inférences (protection contre le déni de service).

* **File bornée** : au-delà de ``file_max`` requêtes en attente ou en cours,
  le serveur répond immédiatement 503 au lieu d'accumuler du travail.
* **Délai maximal** : une inférence qui dépasse ``delai_s`` renvoie 503.
* Les calculs TensorFlow tournent dans un pool de threads dédié et de taille
  fixe, pour ne jamais bloquer la boucle asynchrone.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from fastapi import HTTPException

T = TypeVar("T")


class Executeur:
    def __init__(self, file_max: int, delai_s: float, travailleurs: int = 2) -> None:
        self.file_max = file_max
        self.delai_s = delai_s
        self._en_cours = 0
        self._pool = ThreadPoolExecutor(max_workers=travailleurs, thread_name_prefix="frg-inference")

    async def executer(self, fonction: Callable[..., T], *args: object, delai_s: float | None = None) -> T:
        if self._en_cours >= self.file_max:
            raise HTTPException(
                503, {"detail": "Serveur occupé : réessayez dans un instant.", "code": "serveur_occupe"}
            )
        self._en_cours += 1
        try:
            boucle = asyncio.get_running_loop()
            futur = boucle.run_in_executor(self._pool, lambda: fonction(*args))
            return await asyncio.wait_for(futur, timeout=delai_s or self.delai_s)
        except TimeoutError as exc:
            raise HTTPException(503, {"detail": "Analyse trop longue : réessayez.", "code": "delai_depasse"}) from exc
        finally:
            self._en_cours -= 1

    def fermer(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
