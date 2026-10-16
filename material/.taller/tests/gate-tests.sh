#!/usr/bin/env bash
# Pruebas de la compuerta (harness/scripts/gate.sh): ¿quién vigila al vigilante?
# Cada prueba arma un repo temporal y comprueba el COMPORTAMIENTO de la compuerta que tú escribiste.
set -u
RAIZ="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "Ejecuta esto dentro del proyecto."; exit 2; }
cd "$RAIZ" || exit 2
for f in harness/scripts/gate.sh harness/hooks/after-edit.sh; do
  [ -f "$f" ] || { echo "Falta $f (el hook es del bloque 2; la compuerta, del 4)."; exit 2; }
done

PASS=0; FAIL=0; TMPS=""
ok()  { echo "  [OK] $1"; PASS=$((PASS + 1)); }
bad() { echo "  [X]  $1"; FAIL=$((FAIL + 1)); }

# Repo temporal con remoto y una base (origin/main). $1 = "sinlint" para no copiar el hook.
nuevo_repo() {
  local T; T=$(mktemp -d); TMPS="$TMPS $T"
  git init -q --bare "$T/remoto.git"
  git init -q "$T/repo"
  (
    cd "$T/repo" || exit 1
    git symbolic-ref HEAD refs/heads/main
    git config user.email t@t.t; git config user.name t
    mkdir -p back harness/hooks harness/scripts
    cp "$RAIZ/harness/scripts/gate.sh" harness/scripts/
    [ "${1:-}" = "sinlint" ] || cp "$RAIZ/harness/hooks/after-edit.sh" harness/hooks/
    printf 'package x;\npublic class Ok { }\n' > back/Ok.java
    git add -A; git commit -qm base
    git remote add origin "$T/remoto.git"; git push -q origin main 2>/dev/null
  )
  echo "$T"
}
gate() { ( cd "$1/repo" && bash harness/scripts/gate.sh origin/main >/dev/null 2>&1 ); }

echo "Pruebas de la compuerta (harness/scripts/gate.sh)"

T=$(nuevo_repo); gate "$T"; RC=$?
if [ "$RC" -ne 0 ]; then ok "T1 sin cambios no sale en verde"; else bad "T1 sin cambios SALE EN VERDE"; fi

T=$(nuevo_repo)
( cd "$T/repo" && echo '// cambio' >> back/Ok.java && printf 'public class Nueva {\n  private double montoX;\n}\n' > back/Nueva.java )
gate "$T"; RC=$?
if [ "$RC" -ne 0 ]; then ok "T2 el archivo nuevo bloquea"; else bad "T2 archivo NUEVO sin evaluar"; fi

T=$(nuevo_repo)
( cd "$T/repo" && echo '// cambio' >> back/Ok.java )
gate "$T"; RC=$?
if [ "$RC" -eq 0 ]; then ok "T3 un cambio limpio pasa"; else bad "T3 un cambio limpio NO pasa"; fi

T=$(nuevo_repo)
( cd "$T/repo" && printf 'public class Ok {\n  private double montoBruto;\n}\n' > back/Ok.java )
gate "$T"; RC=$?
if [ "$RC" -ne 0 ]; then ok "T4 archivo modificado bloquea"; else bad "T4 archivo modificado PASA"; fi

T=$(nuevo_repo)
( cd "$T/repo" && printf 'public class MiBoleta {\n  private double montoX;\n}\n' > "back/Mi Boleta.java" )
gate "$T"; RC=$?
if [ "$RC" -ne 0 ]; then ok "T5 nombre con espacios bloquea"; else bad "T5 nombre con espacios SIN evaluar"; fi

T=$(nuevo_repo sinlint)
( cd "$T/repo" && echo '// cambio' >> back/Ok.java )
gate "$T"; RC=$?
if [ "$RC" -ne 0 ]; then ok "T6 sin linter no hay verde"; else bad "T6 sin linter SALE EN VERDE"; fi

# shellcheck disable=SC2086
rm -rf $TMPS
echo "Resultado: $PASS bien, $FAIL en rojo"
[ "$FAIL" -eq 0 ]
