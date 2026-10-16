#!/usr/bin/env python3
"""Puntúa la SALIDA de tu subagente revisor contra defectos sembrados: ¿encontró los reales, inventó citas, respetó el formato?
No necesita IA: lee un texto. Tu IA genera la revisión; este script la VERIFICA (el agente propone, el harness verifica)."""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REV = os.path.join(os.path.dirname(AQUI), "revision")
CASO = os.path.join(REV, "caso")
if len(sys.argv) < 2:
    sys.exit("Uso: bash .taller/puntuar-revision.sh <archivo-con-la-salida-del-revisor>   (prueba con .taller/revision/muestra-buena.txt)")
try:
    texto = open(sys.argv[1], encoding="utf-8").read()
except OSError:
    sys.exit("No puedo leer %s" % sys.argv[1])

esperados = []
for l in open(os.path.join(REV, "esperados.txt"), encoding="utf-8"):
    m = re.match(r"^(\S+):(\d+)\s*\|\s*(.*)$", l.strip())
    if m:
        esperados.append((m.group(1), int(m.group(2)), m.group(3)))
largos = {f: len(open(os.path.join(CASO, f), encoding="utf-8").read().split("\n")) - 1 for f in os.listdir(CASO)}

hallazgos, mal_formato = [], []
lineas = [l for l in texto.split("\n") if l.strip()]
for l in lineas:
    m = re.match(r"^\[(BLOQ|MAYOR|MENOR)\]\s+(\S+?):(\d+)\s*[—\-–:]\s*(\S.*)$", l.strip())
    if m:
        hallazgos.append((m.group(1), os.path.basename(m.group(2)), int(m.group(3)), m.group(4)))
    elif l.strip().startswith("["):
        mal_formato.append(l.strip()[:70])

inventadas = [(f, n) for _, f, n, _ in hallazgos if f not in largos or n < 1 or n > largos[f]]
validas = [h for h in hallazgos if (h[1], h[2]) not in inventadas]
usados, encontrados = set(), []
for f, n, desc in esperados:  # primero coincidencias exactas, luego ±1; cada cita se usa una sola vez
    for tol in (0, 1):
        hit = next((i for i, h in enumerate(validas) if i not in usados and h[1] == f and abs(h[2] - n) <= tol), None)
        if hit is not None:
            usados.add(hit); encontrados.append((f, n, desc)); break
faltan = [e for e in esperados if e not in encontrados]
veredicto = re.search(r"Veredicto:\s*(APRUEBA|REQUIERE CAMBIOS)", texto)
hay_bloq = any(h[0] == "BLOQ" for h in hallazgos)
coherente = bool(veredicto) and not (hay_bloq and veredicto.group(1) == "APRUEBA")
cabe = len(lineas) <= 30

print("Revisión puntuada contra %d defectos sembrados\n" % len(esperados))
print("  hallazgos reales encontrados: %d/%d" % (len(encontrados), len(esperados)))
for f, n, d in faltan:
    print("      · faltó %s:%d — %s" % (f, n, d))
print("  citas INVENTADAS (archivo o línea que no existe): %d" % len(inventadas))
for f, n in inventadas:
    print("      · %s:%d  %s" % (f, n, "el archivo no existe en el caso" if f not in largos else "el archivo solo tiene %d líneas" % largos[f]))
print("  formato [BLOQ]/[MAYOR]/[MENOR] archivo:línea — …: %s" % ("ok" if not mal_formato else "%d línea(s) mal formadas" % len(mal_formato)))
print("  línea de Veredicto: %s" % ("sí" if veredicto else "FALTA"))
print("  veredicto coherente (no aprueba con un [BLOQ] abierto): %s" % ("sí" if coherente else "NO"))
print("  longitud: %d líneas (máximo 30): %s" % (len(lineas), "ok" if cabe else "se pasa"))
puntos = 6 * len(encontrados) / max(1, len(esperados)) + (2 if not inventadas else 0) + (1 if not mal_formato and hallazgos else 0) + (1 if coherente and cabe else 0)
print("\n  PUNTAJE: %.1f/10" % puntos)
print("  " + ("Un revisor que cita lo que no abrió es ruido: arregla tu prompt para que SOLO cite lo que leyó." if inventadas else "Sin citas inventadas."))
sys.exit(0 if puntos >= 9 else 1)
