#!/usr/bin/env bash
# Puntúa la salida de tu subagente revisor contra defectos sembrados. Uso:  bash .taller/puntuar-revision.sh <archivo>
# Practica sin IA con:  bash .taller/puntuar-revision.sh .taller/revision/muestra-con-alucinacion.txt
command -v python3 >/dev/null 2>&1 || { echo "Falta python3."; exit 2; }
exec python3 "$(cd "$(dirname "$0")" && pwd)/lib/puntuar_revision.py" "$@"
