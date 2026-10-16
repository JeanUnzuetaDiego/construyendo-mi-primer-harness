#!/usr/bin/env bash
# El semáforo del taller. Uso:  bash .taller/verificar.sh 0|1|2|3|4|5|6|7|retos|todo
# Un proyecto recién creado sale en ROJO: un objeto ausente es un fallo, no un caso omitido.
command -v python3 >/dev/null 2>&1 || { echo "Falta python3."; exit 2; }
exec python3 "$(cd "$(dirname "$0")" && pwd)/lib/verificar.py" "$@"
