#!/usr/bin/env bash
# Punto de rescate: pone tu proyecto en el estado «solución» de UN bloque para que puedas seguir.
# Uso:  bash .taller/saltar.sh 1|2|3|4|5|6        (queda anotado: ese bloque cuenta la mitad de los puntos)
N="${1:-}"
case "$N" in 1|2|3|4|5|6) ;; *) echo "Uso: bash .taller/saltar.sh 1|2|3|4|5|6"; exit 2 ;; esac
RAIZ="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "Ejecuta esto dentro del proyecto."; exit 2; }
cd "$RAIZ" || exit 2
SRC=".taller/rescate/$N"
[ -d "$SRC" ] || { echo "No hay punto de rescate para el bloque $N."; exit 1; }
cp -R "$SRC/." .
mkdir -p .taller/estado && echo "$N" >> .taller/estado/rescates
chmod +x harness/hooks/*.sh harness/scripts/*.sh 2>/dev/null
echo "Rescate del bloque $N aplicado ($(find "$SRC" -type f | wc -l | tr -d ' ') archivo(s))."
echo "Queda anotado: el verificador cuenta ese bloque con la mitad de los puntos. Comprueba con:  bash .taller/verificar.sh $N"
