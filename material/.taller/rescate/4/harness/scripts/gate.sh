#!/usr/bin/env bash
# Compuerta v2: evalúa también los archivos nuevos y los nombres con espacios, y NUNCA sale en verde si no evaluó nada.
BASE="${1:-origin/main}"
RAIZ="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "No es un repositorio git."; exit 2; }
cd "$RAIZ" || exit 2

LINT="harness/hooks/after-edit.sh"
# Un objeto ausente es un fallo, no un caso omitido: sin linter no hay compuerta.
[ -f "$LINT" ] || { echo "FALTA $LINT: la compuerta no puede evaluar nada. Esto NO es verde."; exit 2; }
git rev-parse --verify -q "$BASE" >/dev/null || { echo "Base inexistente: $BASE. Esto NO es verde."; exit 2; }

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
# Modificados, agregados, renombrados y copiados (-z: separados por NUL, soporta espacios) + los nuevos que git aún no conoce.
{ git diff --name-only --diff-filter=ACMR -z "$BASE" --; git ls-files -z --others --exclude-standard; } > "$TMP"
N=$(tr -cd '\0' < "$TMP" | wc -c | tr -d ' ')
if [ "$N" -eq 0 ]; then
  echo "SIN CAMBIOS QUE EVALUAR — esto NO es verde: no se evaluó nada."
  exit 2
fi
echo "Archivos a evaluar: $N"

FALLO=0
while IFS= read -r -d '' f; do
  case "$f" in
    *.java|*.ts|*.tsx)
      OUT=$(bash "$LINT" "$f" 2>&1)
      if printf '%s' "$OUT" | grep -q 'AVISO'; then
        echo "[X] $f"
        printf '%s\n' "$OUT"
        FALLO=1
      fi ;;
  esac
done < "$TMP"

if [ "$FALLO" -eq 0 ]; then echo "GATE OK"; else echo "GATE FALLO"; fi
exit $FALLO
