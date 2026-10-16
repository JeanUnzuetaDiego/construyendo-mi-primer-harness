#!/usr/bin/env bash
# Adaptador de Cursor para la guardia (hook beforeShellExecution).  EXPERIMENTAL: según la documentación, sin probar en tu Cursor.
# Cursor y Claude Code hablan protocolos distintos:
#   Claude Code: exit 2 bloquea y el stderr se lo lee el agente.
#   Cursor     : espera un JSON {"permission": ...} en stdout; sin JSON válido BLOQUEA TODO.
# El núcleo (guardia.sh) es el mismo; este archivo solo traduce.
#
# Por qué devuelve "ask" y no "allow" cuando la guardia no tiene objeción: «allow» puede saltarse la confirmación
# del usuario y convertir tu guardia en un auto-aprobador de todo lo que no bloquea. Comprueba en tu versión de
# Cursor qué hace cada valor antes de cambiarlo.
AQUI="$(cd "$(dirname "$0")" && pwd)"
CARGA=$(cat)
ERR=$(printf '%s' "$CARGA" | bash "$AQUI/guardia.sh" 2>&1 >/dev/null)
RC=$?
if [ "$RC" -eq 0 ]; then
  printf '{"permission":"ask"}\n'
else
  MSG=$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$ERR")
  printf '{"permission":"deny","user_message":%s,"agent_message":%s}\n' "$MSG" "$MSG"
fi
exit 0
