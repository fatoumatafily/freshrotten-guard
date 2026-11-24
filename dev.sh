#!/usr/bin/env bash
# Lance FreshRotten Guard en local (Linux / macOS, sans Docker) : backend + frontend.
# Usage : ./dev.sh            (backend :8000, frontend :5173)
#         BACKEND_PORT=8001 ./dev.sh   si le port 8000 est déjà pris
set -euo pipefail
racine="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
export TF_CPP_MIN_LOG_LEVEL=2

if [ ! -x "$racine/.venv/bin/python" ]; then
  echo "Environnement Python absent : lancez d'abord « make install »." >&2
  exit 1
fi

(cd "$racine/backend" && exec "$racine/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT") &
pid_backend=$!
(cd "$racine/frontend" && VITE_API_PROXY="http://127.0.0.1:$BACKEND_PORT" exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT" --strictPort) &
pid_frontend=$!
trap 'kill $pid_backend $pid_frontend 2>/dev/null' EXIT INT TERM

echo "Backend : http://127.0.0.1:$BACKEND_PORT/docs  -  Application : http://127.0.0.1:$FRONTEND_PORT"
echo "(premier lancement : téléchargement des poids MobileNetV2, ~14 Mo)"
wait -n
