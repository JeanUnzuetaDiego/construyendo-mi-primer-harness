#!/usr/bin/env bash
# Ataca tu guardia con un corpus de comandos. Uso:  bash .taller/red-team.sh [archivo-con-tus-ataques.txt]
# Con un archivo (una orden por línea) puedes atacar la guardia de tu pareja: cada línea debería ser bloqueada.
command -v python3 >/dev/null 2>&1 || { echo "Falta python3."; exit 2; }
exec python3 "$(cd "$(dirname "$0")" && pwd)/lib/redteam.py" "$@"
