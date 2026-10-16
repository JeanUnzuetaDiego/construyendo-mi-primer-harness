#!/usr/bin/env bash
# Corre después de CADA edición del agente. OBSERVA y avisa; nunca modifica archivos. Cuesta 0 tokens.
# Cada aviso lleva la línea ofensora (N:texto) y termina en «>> AVISO»: el agente necesita saber DÓNDE y QUÉ HACER.
FILE="${1:-}"
[ -f "$FILE" ] || exit 0

DINERO='(double|float)[[:space:]]+[a-z_]*(monto|neto|importe|descuento|bonus|afp|sueldo|salario)'
TASA='new BigDecimal\("0\.[0-9]+"\)|[^0-9A-Za-z_.]0\.[0-9][0-9]+[^0-9]'
aviso() { echo ">> AVISO [$FILE]: $1"; }

case "$FILE" in
  *.java)
    grep -nEi "$DINERO" "$FILE"     && aviso "usa BigDecimal para dinero, nunca double ni float."
    grep -n 'System\.out' "$FILE"   && aviso "usa el logger, no System.out."
    grep -nE "$TASA" "$FILE"        && aviso "una tasa escrita en el código es un valor de negocio hardcodeado: sácala de la configuración."
    ;;
  *.ts|*.tsx)
    grep -n 'console\.log' "$FILE"  && aviso "quita console.log; usa el logger del proyecto."
    grep -nE ': *any([^A-Za-z0-9_]|$)' "$FILE" && aviso "evita any: declara el tipo."
    ;;
esac
exit 0
