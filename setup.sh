#!/usr/bin/env bash
# Crea el proyecto de práctica del taller «Construyendo mi primer Harness».
# Uso:  bash setup.sh [carpeta]        (por defecto: ~/taller-harness/mi-primer-harness)
# Requisitos: bash, git (2.22 o más) y python3 (3.8 o más). No hace falta internet ni ninguna herramienta de IA.
set -e
AQUI=$(cd "$(dirname "$0")" && pwd)
DEST="${1:-$HOME/taller-harness/mi-primer-harness}"
REMOTO="${DEST}-remoto.git"

falta() { echo "FALTA $1. $2"; exit 1; }
command -v git >/dev/null     || falta git "Instálalo y vuelve a correr setup.sh."
command -v python3 >/dev/null || falta python3 "Hace falta 3.8 o más (los hooks leen JSON con python3)."
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || falta "python3 >= 3.8" "Tienes $(python3 --version 2>&1)."
if [ -e "$DEST" ]; then
  echo "Ya existe $DEST. Bórralo o elige otra carpeta:  bash setup.sh <carpeta>"
  exit 1
fi

mkdir -p "$DEST"
cp -R "$AQUI/material/." "$DEST/"
[ -f "$AQUI/GUIA-PARTICIPANTE.md" ] && cp "$AQUI/GUIA-PARTICIPANTE.md" "$DEST/GUIA.md"
chmod +x "$DEST"/bin/* "$DEST"/harness/*.sh "$DEST"/harness/hooks/*.sh "$DEST"/harness/scripts/*.sh \
         "$DEST"/.githooks/pre-push "$DEST"/.taller/*.sh "$DEST"/.taller/tests/*.sh 2>/dev/null || true

git init -q "$DEST"
cd "$DEST"
git symbolic-ref HEAD refs/heads/main
git config user.name "Participante del taller"
git config user.email "taller@example.com"
git add -A
git commit -qm "Proyecto base del taller"
git init -q --bare "$REMOTO"
git -C "$REMOTO" symbolic-ref HEAD refs/heads/main
git remote add origin "$REMOTO"
git push -q -u origin main 2>/dev/null
git checkout -q -b feat/RF-DEM-001-boleta
git branch --show-current >/dev/null 2>&1 || falta "git 2.22 o más" "Tu git no soporta 'git branch --show-current'."

echo "Listo. Proyecto en: $DEST   (rama feat/RF-DEM-001-boleta)"
echo
echo "Siguiente:"
echo "  cd $DEST"
echo "  bash .taller/verificar.sh 0      # el arranque: tiene que salir en verde"
echo "  bash .taller/verificar.sh todo   # y esto en ROJO: todavía no construiste nada"
echo "  abre GUIA.md"
