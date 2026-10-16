#!/usr/bin/env bash
# Puente: traduce el JSON de la herramienta y llama a after-edit.sh.
#   Claude Code (PostToolUse) manda {"tool_input":{"file_path":...}}   ·   Cursor (afterFileEdit) manda {"file_path":...}
# exit 2 en PostToolUse = el stderr llega al agente. Con exit 0 el agente NUNCA lo ve: sería como no tener el hook.
AQUI="$(cd "$(dirname "$0")" && pwd)"
FILE=$(python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
    print((d.get("tool_input") or {}).get("file_path") or d.get("file_path") or "")
except Exception:
    print("")' 2>/dev/null)
[ -n "$FILE" ] || exit 0
OUT=$(bash "$AQUI/after-edit.sh" "$FILE" 2>&1)
[ -n "$OUT" ] || exit 0
echo "$OUT" >&2
exit 2
