#!/usr/bin/env bash
# Compuerta v1 — ¡TIENE DEFECTOS! Encuéntralos con:  bash .taller/tests/gate-tests.sh
BASE="${1:-origin/main}"
FILES=$(git diff --name-only "$BASE")

if [ -z "$FILES" ]; then
  echo "Sin cambios que evaluar."
  exit 0
fi
echo "Archivos a evaluar: $(printf '%s\n' "$FILES" | wc -l | tr -d ' ')"

FALLO=0
for f in $FILES; do
  case "$f" in
    *.java|*.ts|*.tsx)
      OUT=$(bash harness/hooks/after-edit.sh "$f")
      if printf '%s' "$OUT" | grep -q 'AVISO'; then
        echo "[X] $f"
        printf '%s\n' "$OUT"
        FALLO=1
      fi ;;
  esac
done

if [ "$FALLO" -eq 0 ]; then echo "GATE OK"; else echo "GATE FALLO"; fi
exit $FALLO
