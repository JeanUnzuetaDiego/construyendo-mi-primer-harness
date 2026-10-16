#!/usr/bin/env bash
# Envoltorio de la guardia. Si no hay python3 FALLA CERRADO (exit 2): una guardia ausente no es una guardia que dice «sí».
AQUI="$(cd "$(dirname "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "BLOQUEADO por el harness [guardia]: falta python3; la guardia no puede evaluar nada." >&2
  exit 2
fi
exec python3 "$AQUI/guardia.py"
