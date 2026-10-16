#!/usr/bin/env bash
# Busca lecciones por su SEÑAL: la frase que estás a punto de decir.
# Uso:  bash harness/lecciones.sh "los tests están verdes"      ·      bash harness/lecciones.sh --listar
AQUI="$(cd "$(dirname "$0")" && pwd)"
if [ "${1:-}" = "--listar" ]; then
  for f in "$AQUI"/lecciones/L-*.md; do [ -f "$f" ] && printf '%s  %s\n' "$(grep -m1 '^id:' "$f" | sed 's/^id: *//')" "$(grep -m1 '^titulo:' "$f" | sed 's/^titulo: *//')"; done
  exit 0
fi
[ $# -ge 1 ] || { echo "Uso: bash harness/lecciones.sh \"<la frase que ibas a decir>\""; exit 2; }
FRASE="$*"; HALLADAS=0
for f in "$AQUI"/lecciones/L-*.md; do
  [ -f "$f" ] || continue
  SENAL=$(grep -m1 '^senal:' "$f" | sed 's/^senal: *//')
  if printf '%s' "$SENAL" | grep -qiF -- "$FRASE"; then
    echo "$(grep -m1 '^id:' "$f" | sed 's/^id: *//') — $(grep -m1 '^titulo:' "$f" | sed 's/^titulo: *//')"
    echo "  señal : $SENAL"
    echo "  ficha : ${f#"$AQUI"/}"
    HALLADAS=$((HALLADAS + 1))
  fi
done
if [ "$HALLADAS" -eq 0 ]; then
  echo "Sin coincidencias para: $FRASE"
  echo "¿Es una lección nueva? cp harness/lecciones/_PLANTILLA.md harness/lecciones/L-NN-<slug>.md"
  exit 1
fi
