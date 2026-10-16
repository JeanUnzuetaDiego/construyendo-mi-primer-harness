#!/usr/bin/env bash
# ¿En qué fase estás? Nadie la declara: se deduce de hechos observables (la rama, el expediente, el árbol de git).
# Cuesta 0 tokens y no opina.
set -uo pipefail
RAIZ="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "No es un repositorio git."; exit 2; }
cd "$RAIZ" || exit 2
PRODUCTO_DIRS="back web"; RAMAS_LARGAS="main master develop"
# shellcheck disable=SC1091
[ -f harness/config.env ] && . harness/config.env

RAMA=$(git branch --show-current 2>/dev/null)
RF=$(printf '%s' "$RAMA" | grep -oE 'RF-[A-Z]{3}-[0-9]+' | head -1)
EXP="work/${RF:-_}/expediente.md"
SUCIO=$(git status --porcelain | wc -l | tr -d ' ')
sig() { echo "SIGUIENTE: $*"; }

echo "rama: ${RAMA:-(detached)} | ${RF:--} | sin commitear: $SUCIO"
echo "--------------------------------------------------"

salud() {
  local c h g p
  c=falta; [ -f "${CONSTITUCION:-AGENTS.md}" ] && c=ok
  h=falta; [ -f harness/hooks/after-edit.sh ] && h=ok
  g=falta; grep -q PreToolUse .claude/settings.json 2>/dev/null && g=ok
  p=falta; [ "$(git config core.hooksPath)" = ".githooks" ] && p=ok
  echo
  echo "harness: constitucion $c · hook $h · guardia $g · pre-push $p   (detalle: bash harness/doctor.sh)"
}

for l in $RAMAS_LARGAS; do
  if [ "$RAMA" = "$l" ]; then
    echo "FASE 1 — rama de trabajo. Estás en '$RAMA', una rama larga."
    sig "git checkout -b feat/RF-XXX-NNN-descripcion"; salud; exit 0
  fi
done
if [ -z "$RF" ]; then
  echo "FASE 0/1 — la rama no declara un RF-XXX-NNN."
  sig "git branch -m feat/RF-XXX-NNN-descripcion"; salud; exit 0
fi
if [ ! -f "requisitos/$RF.md" ]; then
  echo "FASE 0 — $RF no existe en requisitos/."
  sig "usa un requisito que exista: ls requisitos/"; salud; exit 1
fi
if [ ! -f "$EXP" ]; then
  echo "FASE 2 — leer el requisito. No hay expediente."
  sig "mkdir -p work/$RF && crea work/$RF/expediente.md con '## Fase 2' y '## Fase 3'"; salud; exit 0
fi

CRIT=$(awk '/^## Fase 2/{f=1;next} /^## /{f=0} f && /^> /{sub(/^> */,""); print}' "$EXP")
if [ -z "$CRIT" ]; then
  echo "FASE 2 — el expediente no tiene criterios."
  sig "copia criterios de requisitos/$RF.md con '> ' delante"; salud; exit 0
fi
MAL=0
while IFS= read -r c; do
  if ! grep -qF -- "$c" "requisitos/$RF.md"; then echo "  [X] PARAFRASEADO: $c"; MAL=1; fi
done <<< "$CRIT"
if [ "$MAL" -eq 1 ]; then
  echo "FASE 2 — no literal: parafrasear es inventar."
  sig "copia el texto exacto del requisito"; salud; exit 1
fi

RUTAS=$(awk '/^## Fase 3/{f=1;next} /^## /{f=0} f && /^- /{sub(/^- */,""); print}' "$EXP")
if [ -z "$RUTAS" ]; then
  echo "FASE 3 — declara los archivos a tocar (máx. 8)."
  sig "agrega '- ruta' bajo '## Fase 3'"; salud; exit 0
fi
N=0; INV=0
while IFS= read -r r; do
  N=$((N + 1))
  if [ ! -f "$r" ]; then echo "  [X] RUTA INVENTADA: $r"; INV=1; fi
done <<< "$RUTAS"
if [ "$INV" -eq 1 ]; then
  echo "FASE 3 — la ruta no existe: no se deduce."
  sig "corrige las rutas (ls -R back web)"; salud; exit 1
fi
if [ "$N" -gt 8 ]; then
  echo "FASE 3 — $N archivos; el máximo es 8. Parte la tarea."; salud; exit 1
fi

if [ "$SUCIO" -eq 0 ]; then
  echo "FASE 4 — implementar. Alcance: $N archivo(s)."
  sig "edita el primero; el hook te avisará"
else
  echo "FASE 6 — verificar. Hay $SUCIO archivo(s) modificado(s)."
  echo "  La compuerta comprueba; el agente no opina:"
  sig "bash harness/scripts/gate.sh   # y comprueba 'Archivos a evaluar: N' > 0"
fi
salud
echo
echo "Recuerda: la persona aprueba o rechaza cada artefacto. Un rechazo REPITE la fase."
