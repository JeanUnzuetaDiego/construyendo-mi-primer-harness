#!/usr/bin/env bash
# ¿Tu harness está vivo? Prueba cada pieza con canarios. Uso:  bash harness/doctor.sh [carpeta-del-repo]
command -v python3 >/dev/null 2>&1 || { echo "Falta python3."; exit 2; }
exec python3 "$(cd "$(dirname "$0")" && pwd)/doctor.py" "$@"
