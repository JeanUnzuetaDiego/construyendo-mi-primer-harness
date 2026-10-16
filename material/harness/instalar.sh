#!/usr/bin/env bash
# Lleva tu harness a otro repo sin pisar nada suyo. Por defecto solo muestra el plan.
# Uso:  bash harness/instalar.sh <carpeta-del-repo-destino> [--aplicar] [--cursor] [--forzar]
command -v python3 >/dev/null 2>&1 || { echo "Falta python3."; exit 2; }
exec python3 "$(cd "$(dirname "$0")" && pwd)/instalar.py" "$@"
