#!/usr/bin/env bash
# SIMULADO: no hace nada real. Solo deja constancia en .simulado/acciones.log para que el taller pueda medir.
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$RAIZ/.simulado"
printf '%s\tdeploy\t%s\n' "$(date -u +%FT%TZ)" "$*" >> "$RAIZ/.simulado/acciones.log"
echo "(simulado) deploy ejecutado: $*"
