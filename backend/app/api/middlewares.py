"""Middlewares ASGI de sécurité : en-têtes HTTP et limite de taille du corps."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# CSP stricte pour l'API (aucune ressource active). Swagger (/docs) a besoin de
# charger ses scripts depuis un CDN : il a sa propre politique, plus permissive.
CSP_API = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
CSP_DOCS = (
    "default-src 'none'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
)

EN_TETES_COMMUNS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
    (b"cross-origin-opener-policy", b"same-origin"),
    (b"cross-origin-resource-policy", b"same-site"),
    (b"cache-control", b"no-store"),
]


class EnTetesSecurite:
    """Ajoute les en-têtes de sécurité à toutes les réponses HTTP."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chemin: str = scope.get("path", "")
        csp = CSP_DOCS if chemin.startswith(("/docs", "/redoc")) else CSP_API

        async def envoyer(message: Message) -> None:
            if message["type"] == "http.response.start":
                en_tetes = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"server"]
                en_tetes += [*EN_TETES_COMMUNS, (b"content-security-policy", csp.encode())]
                message["headers"] = en_tetes
            await send(message)

        await self.app(scope, receive, envoyer)


class LimiteTailleCorps:
    """Refuse (413) tout corps de requête dépassant ``limite`` octets.

    Vérifie l'en-tête Content-Length **et** compte réellement les octets reçus
    (un client peut mentir ou utiliser l'encodage « chunked »).
    """

    def __init__(self, app: ASGIApp, limite: int) -> None:
        self.app = app
        self.limite = limite

    async def _refuser(self, send: Send) -> None:
        corps = json.dumps({"detail": "Requête trop volumineuse.", "code": "requete_trop_grosse"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(corps)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": corps})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for nom, valeur in scope.get("headers", []):
            if nom == b"content-length":
                try:
                    if int(valeur) > self.limite:
                        await self._refuser(send)
                        return
                except ValueError:
                    await self._refuser(send)
                    return
        recus = 0
        reponse_commencee = False

        async def recevoir() -> Message:
            nonlocal recus
            message = await receive()
            if message["type"] == "http.request":
                recus += len(message.get("body", b""))
                if recus > self.limite:
                    raise CorpsTropGros
            return message

        async def envoyer(message: Message) -> None:
            nonlocal reponse_commencee
            if message["type"] == "http.response.start":
                reponse_commencee = True
            await send(message)

        try:
            await self.app(scope, recevoir, envoyer)
        except CorpsTropGros:
            if not reponse_commencee:
                await self._refuser(send)


class CorpsTropGros(Exception):
    """Levée quand le flux reçu dépasse la limite."""
