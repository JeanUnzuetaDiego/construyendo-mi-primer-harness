#!/usr/bin/env bash
# El agente de caos (simulado) y el medidor. Uso:  bash .taller/prueba.sh antes | despues | comparar   (--help para más)
command -v python3 >/dev/null 2>&1 || { echo "Falta python3."; exit 2; }
exec python3 "$(cd "$(dirname "$0")" && pwd)/lib/prueba.py" "$@"
