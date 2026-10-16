#!/usr/bin/env python3
"""instalar: lleva TU harness a otro repositorio sin pisar nada suyo.
Por defecto solo MUESTRA el plan (modo prueba). Con --aplicar escribe. Nunca hace commit.
  --aplicar   escribe los cambios         --cursor   conecta también Cursor (EXPERIMENTAL, sin probar en tu Cursor)
  --forzar    sobrescribe archivos del harness que en el destino son distintos"""
import filecmp
import json
import os
import shutil
import subprocess
import sys

H = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.dirname(H)
args = [a for a in sys.argv[1:] if not a.startswith("--")]
APLICAR, CURSOR, FORZAR = "--aplicar" in sys.argv, "--cursor" in sys.argv, "--forzar" in sys.argv
if not args:
    sys.exit("Uso: bash harness/instalar.sh <carpeta-del-repo-destino> [--aplicar] [--cursor] [--forzar]")
DEST = os.path.abspath(args[0])
if not os.path.isdir(DEST):
    sys.exit("No existe la carpeta destino: %s" % DEST)
if os.path.realpath(DEST) == os.path.realpath(ORIGEN):
    sys.exit("El destino es este mismo proyecto.")
if not os.path.isdir(os.path.join(DEST, ".git")):
    sys.exit("El destino no es un repositorio git (falta .git). Haz 'git init' primero.")

acciones, pendientes, avisos = [], [], []


def linea(simbolo, ruta, nota=""):
    print("  %s %-44s %s" % (simbolo, ruta, nota))


def copiar(rel, ejecutable=False):
    o, d = os.path.join(ORIGEN, rel), os.path.join(DEST, rel)
    if not os.path.isfile(d):
        linea("+", rel, "nuevo")
        acciones.append(lambda o=o, d=d: (os.makedirs(os.path.dirname(d), exist_ok=True), shutil.copy2(o, d)))
    elif filecmp.cmp(o, d, shallow=False):
        linea("=", rel, "igual")
    elif FORZAR:
        linea("≈", rel, "difiere: se sobrescribe (--forzar)")
        acciones.append(lambda o=o, d=d: shutil.copy2(o, d))
    else:
        linea("!", rel, "difiere del tuyo: NO se toca (usa --forzar para sobrescribir)")
        avisos.append("%s es distinto en el destino y no se sobrescribió." % rel)


def leer_json(ruta):
    if not os.path.isfile(ruta):
        return {}
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except ValueError as e:
        sys.exit("%s no es JSON válido (%s). No lo toco: arréglalo y vuelve a correr." % (ruta, e))


def fusionar_hooks(rel, entradas, evento_clave="command"):
    """entradas: [(evento, matcher, comando, marca)]. Conserva todo lo que ya hubiera."""
    ruta = os.path.join(DEST, rel)
    datos = leer_json(ruta)
    hooks = datos.setdefault("hooks", {})
    nuevos = 0
    for evento, matcher, comando, marca in entradas:
        lista = hooks.setdefault(evento, [])
        if any(marca in (h.get(evento_clave) or "") for e in lista for h in (e.get("hooks") or [e])):
            continue
        lista.append({"matcher": matcher, "hooks": [{"type": "command", "command": comando}]} if matcher else {"command": comando})
        nuevos += 1
    if nuevos:
        linea("~", rel, "fusiona %d hook(s); se conserva todo lo tuyo" % nuevos)
        acciones.append(lambda: (os.makedirs(os.path.dirname(ruta), exist_ok=True),
                                 open(ruta, "w", encoding="utf-8").write(json.dumps(datos, indent=2, ensure_ascii=False) + "\n")))
    else:
        linea("=", rel, "los hooks ya estaban conectados")


print("%s en %s\n" % ("Instalando" if APLICAR else "Plan de instalación (NO se escribe nada: añade --aplicar)", DEST))

# 1 · código del harness (se sincroniza) y plantillas (solo si faltan)
for raiz, dirs, archivos in os.walk(os.path.join(ORIGEN, "harness")):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "contexto", "lecciones")]
    for a in sorted(archivos):
        if a in ("fricciones.log", "config.env") or a.endswith(".pyc"):
            continue
        copiar(os.path.relpath(os.path.join(raiz, a), ORIGEN))
copiar("harness/lecciones/_PLANTILLA.md")
# el contexto bajo demanda: la constitución lo cita por ruta, así que tiene que existir (solo si faltan; luego son tuyos)
for f in sorted(os.listdir(os.path.join(ORIGEN, "harness", "contexto"))) if os.path.isdir(os.path.join(ORIGEN, "harness", "contexto")) else []:
    if f.endswith(".md") and not os.path.isfile(os.path.join(DEST, "harness", "contexto", f)):
        copiar("harness/contexto/" + f)
pendientes.append("ADAPTA la constitución y harness/contexto/*.md a tu proyecto: hoy describen el proyecto de práctica, no el tuyo.")

# 2 · prompts: subagente y comando
for rel in (".claude/agents/revisor.md", ".claude/commands/fase.md"):
    if os.path.isfile(os.path.join(ORIGEN, rel)):
        copiar(rel)
    else:
        avisos.append("en el origen no existe %s (¿hiciste el bloque 5?)." % rel)

# 3 · constitución
def _leer_cfg(ruta):
    cfg = {}
    try:
        for l in open(ruta, encoding="utf-8"):
            if "=" in l and not l.lstrip().startswith("#"):
                k, v = l.split("=", 1)
                cfg[k.strip()] = v.split("#")[0].strip().strip('"')
    except OSError:
        pass
    return cfg


cfg_origen = _leer_cfg(os.path.join(H, "config.env"))
modo_previo = _leer_cfg(os.path.join(DEST, "harness", "config.env")).get("CONSTITUCION")  # cómo se instaló la vez anterior
tiene_instrucciones = any(os.path.isfile(os.path.join(DEST, f)) for f in ("AGENTS.md", "CLAUDE.md"))
if not os.path.isfile(os.path.join(ORIGEN, "AGENTS.md")):
    avisos.append("en el origen no existe AGENTS.md (¿hiciste el bloque 1?).")
    constitucion = "AGENTS.md"
elif modo_previo == "harness/CONSTITUCION.md" or (modo_previo is None and tiene_instrucciones):
    # el repo ya tenía sus propias instrucciones: la constitución va aparte, importada
    constitucion = "harness/CONSTITUCION.md"
    o, d = os.path.join(ORIGEN, "AGENTS.md"), os.path.join(DEST, constitucion)
    if not os.path.isfile(d):
        linea("+", constitucion, "tu repo ya tiene AGENTS.md/CLAUDE.md: no los toco")
        acciones.append(lambda: shutil.copy2(o, d))
    elif filecmp.cmp(o, d, shallow=False):
        linea("=", constitucion, "igual")
    elif FORZAR:
        linea("≈", constitucion, "difiere: se sobrescribe (--forzar)")
        acciones.append(lambda: shutil.copy2(o, d))
    else:
        linea("=", constitucion, "ya existe y la adaptaste: NO se toca (usa --forzar para sobrescribir)")
    importa = any("@harness/CONSTITUCION.md" in (open(os.path.join(DEST, f), encoding="utf-8").read() if os.path.isfile(os.path.join(DEST, f)) else "") for f in ("CLAUDE.md", "AGENTS.md"))
    if not importa:
        pendientes.append("añade esta línea a tu CLAUDE.md (o a tu AGENTS.md):   @harness/CONSTITUCION.md")
else:
    constitucion = "AGENTS.md"
    copiar("AGENTS.md")
    d = os.path.join(DEST, "CLAUDE.md")
    if not os.path.isfile(d):
        linea("+", "CLAUDE.md", "nuevo (@AGENTS.md: una constitución para Claude Code y Cursor)")
        acciones.append(lambda: open(d, "w", encoding="utf-8").write("@AGENTS.md\n"))
    else:
        linea("=", "CLAUDE.md", "ya existe")

# 4 · configuración (se genera una vez; si existe no se pisa)
d_cfg = os.path.join(DEST, "harness", "config.env")
if os.path.isfile(d_cfg):
    linea("=", "harness/config.env", "ya existe: no se pisa")
else:
    candidatos = ("back", "web", "src", "app", "lib", "backend", "frontend", "server", "client", "packages", "services", "api")
    prod = [c for c in candidatos if os.path.isdir(os.path.join(DEST, c))]
    if not prod:
        pendientes.append("PRODUCTO_DIRS: no encontré carpetas de código; edita harness/config.env o la guardia de alcance no protegerá nada.")
    texto = ('# Configuración del harness (generada por instalar.sh; edítala).\n'
             'PRODUCTO_DIRS="%s"          # carpetas de código de producto: ahí solo se edita lo que el expediente declara\n'
             'RAMAS_LARGAS="%s"\n'
             'PRESUPUESTO_BYTES=%s\n'
             'CONSTITUCION="%s"\n') % (" ".join(prod) or "back web", cfg_origen.get("RAMAS_LARGAS", "main master develop"),
                                      cfg_origen.get("PRESUPUESTO_BYTES", "3000"), constitucion)
    linea("+", "harness/config.env", "generado: PRODUCTO_DIRS=«%s»" % (" ".join(prod) or "back web (sin detectar)"))
    acciones.append(lambda t=texto: (os.makedirs(os.path.dirname(d_cfg), exist_ok=True), open(d_cfg, "w", encoding="utf-8").write(t)))

# 5 · cableado de Claude Code
fusionar_hooks(".claude/settings.json", [
    ("PostToolUse", "Edit|Write", 'bash "$CLAUDE_PROJECT_DIR/harness/hooks/puente.sh"', "harness/hooks/puente.sh"),
    ("PreToolUse", "Bash|Edit|Write", 'bash "$CLAUDE_PROJECT_DIR/harness/hooks/guardia.sh"', "harness/hooks/guardia.sh")])

# 6 · Cursor (experimental)
if CURSOR:
    ruta = os.path.join(DEST, ".cursor", "hooks.json")
    datos = leer_json(ruta)
    datos.setdefault("version", 1)
    hk, nuevos = datos.setdefault("hooks", {}), 0
    for ev, cmd in (("beforeShellExecution", "bash harness/hooks/cursor-guardia.sh"), ("afterFileEdit", "bash harness/hooks/puente.sh")):
        lista = hk.setdefault(ev, [])
        if not any(cmd == (e.get("command") or "") for e in lista):
            lista.append({"command": cmd}); nuevos += 1
    if nuevos:
        linea("~", ".cursor/hooks.json", "conecta %d hook(s) de Cursor (EXPERIMENTAL)" % nuevos)
        acciones.append(lambda: (os.makedirs(os.path.dirname(ruta), exist_ok=True),
                                 open(ruta, "w", encoding="utf-8").write(json.dumps(datos, indent=2) + "\n")))
    else:
        linea("=", ".cursor/hooks.json", "ya conectado")
    pendientes.append("Cursor: comprueba en tu versión qué hace cada valor de «permission» y si afterFileEdit le devuelve algo al agente.")

# 7 · git: compuerta en cada push + .gitignore
copiar(".githooks/pre-push")
hp = subprocess.run(["git", "config", "core.hooksPath"], cwd=DEST, capture_output=True, text=True).stdout.strip()
if hp == ".githooks":
    linea("=", "git config core.hooksPath", ".githooks")
elif not hp:
    linea("~", "git config core.hooksPath", "se fija en .githooks")
    acciones.append(lambda: subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=DEST))
else:
    linea("!", "git config core.hooksPath", "ya usas «%s»: NO lo cambio" % hp)
    pendientes.append("Tu repo usa core.hooksPath=%s. Enlaza la compuerta en tu pre-push:  bash harness/scripts/gate.sh origin/main" % hp)
gi = os.path.join(DEST, ".gitignore")
actual = open(gi, encoding="utf-8").read() if os.path.isfile(gi) else ""
faltan = [l for l in ("harness/fricciones.log", "work/RF-*/") if l not in actual.split("\n")]
if faltan:
    linea("~", ".gitignore", "añade: " + ", ".join(faltan))
    acciones.append(lambda: open(gi, "a", encoding="utf-8").write(("" if actual.endswith("\n") or not actual else "\n") + "\n".join(faltan) + "\n"))
else:
    linea("=", ".gitignore", "ya ignora el andamio local")

if not APLICAR:
    print("\nNo se escribió nada.%s" % (" Para instalar:  bash harness/instalar.sh %s --aplicar" % args[0]))
    for p in pendientes + avisos:
        print("  PENDIENTE: " + p)
    sys.exit(0)

for a in acciones:
    a()
for rel in ("harness/hooks/guardia.sh", "harness/hooks/puente.sh", "harness/hooks/after-edit.sh", "harness/hooks/cursor-guardia.sh",
            "harness/scripts/gate.sh", "harness/fase.sh", "harness/lecciones.sh", "harness/doctor.sh", "harness/instalar.sh", ".githooks/pre-push"):
    p = os.path.join(DEST, rel)
    if os.path.isfile(p):
        os.chmod(p, os.stat(p).st_mode | 0o111)
print("\nInstalado. No se hizo ningún commit: revisa con 'git status' en el destino.\n")
for p in pendientes + avisos:
    print("  PENDIENTE: " + p)
print("\n== doctor en el destino ==", flush=True)
sys.stdout.flush()
sys.exit(subprocess.run([sys.executable, os.path.join(DEST, "harness", "doctor.py"), DEST]).returncode)
