#!/usr/bin/env python3
"""doctor: ¿tu harness está vivo?  Prueba cada pieza con CANARIOS (casos que DEBEN pasar o DEBEN bloquearse).
Es portable: úsalo en cualquier repo donde hayas instalado el harness (y en CI). Sale con código 1 si algo falla.
Un objeto ausente es un fallo, no un caso omitido: un doctor que se calla ante lo que no encuentra miente."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or os.getcwd()
if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
    RAIZ = os.path.abspath(sys.argv[1])
H = os.path.join(RAIZ, "harness")
FALLOS = 0


def ok(m): print("  [OK] " + m)
def aviso(m): print("  [!]  " + m)
def info(m): print("  [i]  " + m)


def mal(m):
    global FALLOS
    FALLOS += 1
    print("  [X]  " + m)


def correr(args, entrada=None, env=None, cwd=None, timeout=30):
    return subprocess.run(args, input=entrada, capture_output=True, text=True, env=env, cwd=cwd, timeout=timeout)


def config():
    cfg = {"PRODUCTO_DIRS": "back web", "RAMAS_LARGAS": "main master develop", "PRESUPUESTO_BYTES": "3000", "CONSTITUCION": "AGENTS.md"}
    try:
        for l in open(os.path.join(H, "config.env"), encoding="utf-8"):
            m = re.match(r"""\s*([A-Z_]+)=(?:"([^"]*)"|'([^']*)'|(\S*))""", l)
            if m:
                cfg[m.group(1)] = m.group(2) or m.group(3) or m.group(4) or ""
    except OSError:
        pass
    return cfg


def coincide(matcher, nombre):
    if matcher in (None, "", "*"):
        return True
    if re.fullmatch(r"[A-Za-z0-9_\- ,|]+", matcher):
        return nombre in [x.strip() for x in re.split(r"[|,]", matcher)]
    return re.search(matcher, nombre) is not None


print("doctor · %s\n" % RAIZ)
cfg = config()

# 1 · constitución
print("Contexto")
cons = os.path.join(RAIZ, cfg["CONSTITUCION"])
if not os.path.isfile(cons):
    mal("falta la constitución (%s)" % cfg["CONSTITUCION"])
else:
    n = os.path.getsize(cons)
    pres = int(cfg["PRESUPUESTO_BYTES"] or 3000)
    (ok if 200 <= n <= pres else mal)("%s pesa %d B (≈ %d tokens) — presupuesto %d B" % (cfg["CONSTITUCION"], n, n // 4, pres))
    texto = open(cons, encoding="utf-8").read()
    ref = [r for r in dict.fromkeys(re.findall(r"`((?:harness|\.claude|\.githooks)/[\w./\-]+)`", texto)) if "XXX" not in r and "NNN" not in r]
    faltan = [r for r in ref if not os.path.exists(os.path.join(RAIZ, r))]
    (mal if faltan else ok)("rutas que cita la constitución: %d, inexistentes: %s" % (len(ref), ", ".join(faltan) or "ninguna"))
    if "mi-primer-harness" in texto or "RF-DEM" in texto:
        aviso("la constitución todavía habla del proyecto de práctica (mi-primer-harness / RF-DEM): adáptala a TU proyecto")

# 2 · cableado
print("\nCableado (.claude/settings.json)")
datos = None
try:
    datos = json.load(open(os.path.join(RAIZ, ".claude", "settings.json"), encoding="utf-8"))
    ok("settings.json es JSON válido")
except FileNotFoundError:
    mal("falta .claude/settings.json: los hooks no están conectados")
except ValueError as e:
    mal(".claude/settings.json no es JSON válido: %s" % e)
hooks = (datos or {}).get("hooks", {}) if isinstance(datos, dict) else {}


def cableado(evento, nombres, script):
    entradas = hooks.get(evento) or []
    cubren = [e for e in entradas if all(coincide(e.get("matcher"), n) for n in nombres)]
    if not cubren:
        return mal("%s: ninguna entrada cubre %s" % (evento, " y ".join(nombres)))
    cmds = [h.get("command", "") for e in cubren for h in (e.get("hooks") or [])]
    if not any(script in c for c in cmds):
        return mal("%s: ningún comando llama a %s" % (evento, script))
    if not any("$CLAUDE_PROJECT_DIR" in c for c in cmds if script in c):
        return mal("%s: usa una ruta que no parte de $CLAUDE_PROJECT_DIR (se rompe si el agente cambia de directorio)" % evento)
    if not os.path.isfile(os.path.join(H, "hooks", script)):
        return mal("%s: falta harness/hooks/%s" % (evento, script))
    ok("%s → %s" % (evento, script))


cableado("PostToolUse", ["Edit", "Write"], "puente.sh")
cableado("PreToolUse", ["Bash", "Edit", "Write"], "guardia.sh")

# 3 · canarios
print("\nCanarios (casos que deben pasar o deben bloquearse)")
tmp = tempfile.mkdtemp(prefix="doctor-")
try:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=RAIZ)
    malo = os.path.join(tmp, "Canario.java")
    open(malo, "w").write("class C {\n  private double montoBruto;\n}\n")
    puente = os.path.join(H, "hooks", "puente.sh")
    if os.path.isfile(puente):
        p = correr(["bash", puente], json.dumps({"tool_name": "Write", "tool_input": {"file_path": malo}}), env)
        (ok if p.returncode == 2 and "AVISO" in p.stderr else mal)("hook de edición: un double monetario avisa al agente (exit 2 con aviso; salió %d)" % p.returncode)
    else:
        mal("falta harness/hooks/puente.sh")
    guardia = os.path.join(H, "hooks", "guardia.sh")
    if os.path.isfile(guardia):
        def g(carga):
            return correr(["bash", guardia], carga if isinstance(carga, str) else json.dumps(carga), dict(os.environ, CLAUDE_PROJECT_DIR=tmp))
        os.makedirs(os.path.join(tmp, "harness"), exist_ok=True)
        (ok if g({"tool_name": "Bash", "tool_input": {"command": "git push"}}).returncode == 2 else mal)("guardia: «git push» se bloquea")
        (ok if g({"tool_name": "Bash", "tool_input": {"command": "git status"}}).returncode == 0 else mal)("guardia: «git status» pasa")
        (ok if g({"tool_name": "Bash", "tool_input": {"command": 'echo "git push"'}}).returncode == 0 else mal)("guardia: «echo \"git push\"» pasa (mira la posición, no el texto)")
        (ok if g("esto no es json").returncode == 2 else mal)("guardia: una entrada que no entiende se bloquea (falla cerrada)")
        # alcance, en un proyecto temporal construido con TUS archivos
        prod = (cfg["PRODUCTO_DIRS"].split() or ["back"])[0]
        shutil.copytree(H, os.path.join(tmp, "harness"), dirs_exist_ok=True, ignore=shutil.ignore_patterns("fricciones.log", "__pycache__"))
        os.makedirs(os.path.join(tmp, prod), exist_ok=True)
        os.makedirs(os.path.join(tmp, "work", "RF-DEM-001"), exist_ok=True)
        open(os.path.join(tmp, "work", "RF-DEM-001", "expediente.md"), "w").write("## Fase 3\n- %s/Permitido.java\n" % prod)
        for a in (["init", "-q"], ["config", "user.name", "d"], ["config", "user.email", "d@d"]):
            correr(["git"] + a, cwd=tmp)
        open(os.path.join(tmp, prod, "Permitido.java"), "w").write("x")
        correr(["git", "add", "-A"], cwd=tmp); correr(["git", "commit", "-qm", "b"], cwd=tmp)
        correr(["git", "checkout", "-q", "-b", "feat/RF-DEM-001-canario"], cwd=tmp)
        fuera = g({"tool_name": "Write", "tool_input": {"file_path": os.path.join(tmp, prod, "Otro.java")}})
        dentro = g({"tool_name": "Edit", "tool_input": {"file_path": os.path.join(tmp, prod, "Permitido.java")}})
        (ok if fuera.returncode == 2 else mal)("alcance: editar %s/Otro.java (fuera del expediente) se bloquea" % prod)
        (ok if dentro.returncode == 0 else mal)("alcance: editar %s/Permitido.java (declarado) pasa" % prod)
    else:
        mal("falta harness/hooks/guardia.sh")
    # compuerta, en un repo temporal
    gate = os.path.join(H, "scripts", "gate.sh")
    lint = os.path.join(H, "hooks", "after-edit.sh")
    if os.path.isfile(gate) and os.path.isfile(lint):
        repo = os.path.join(tmp, "gate"); remoto = os.path.join(tmp, "gate-remoto.git")
        correr(["git", "init", "-q", "--bare", remoto]); correr(["git", "init", "-q", repo])
        for a in (["symbolic-ref", "HEAD", "refs/heads/main"], ["config", "user.name", "d"], ["config", "user.email", "d@d"]):
            correr(["git"] + a, cwd=repo)
        os.makedirs(os.path.join(repo, "harness", "hooks")); os.makedirs(os.path.join(repo, "harness", "scripts"))
        os.makedirs(os.path.join(repo, prod))
        shutil.copy(gate, os.path.join(repo, "harness", "scripts")); shutil.copy(lint, os.path.join(repo, "harness", "hooks"))
        open(os.path.join(repo, prod, "Ok.java"), "w").write("class Ok { }\n")
        correr(["git", "add", "-A"], cwd=repo); correr(["git", "commit", "-qm", "b"], cwd=repo)
        correr(["git", "remote", "add", "origin", remoto], cwd=repo); correr(["git", "push", "-q", "origin", "main"], cwd=repo)
        rc1 = correr(["bash", "harness/scripts/gate.sh", "origin/main"], cwd=repo).returncode
        (ok if rc1 != 0 else mal)("compuerta: sin cambios NO sale en verde (salió %d)" % rc1)
        open(os.path.join(repo, prod, "Nueva.java"), "w").write("class N {\n  private double montoX;\n}\n")
        rc2 = correr(["bash", "harness/scripts/gate.sh", "origin/main"], cwd=repo).returncode
        (ok if rc2 != 0 else mal)("compuerta: un archivo NUEVO con double bloquea (salió %d)" % rc2)
    else:
        mal("falta harness/scripts/gate.sh o harness/hooks/after-edit.sh")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# 4 · git y configuración
print("\nGit y configuración")
hp = correr(["git", "config", "core.hooksPath"], cwd=RAIZ).stdout.strip()
pre = os.path.join(RAIZ, ".githooks", "pre-push")
if hp == ".githooks" and os.path.isfile(pre):
    ok("core.hooksPath = .githooks y existe el pre-push")
else:
    aviso("la compuerta no corre en cada push: core.hooksPath es «%s» (debería ser .githooks) %s" % (hp, "" if os.path.isfile(pre) else "y falta .githooks/pre-push"))
existen = [d for d in cfg["PRODUCTO_DIRS"].split() if os.path.isdir(os.path.join(RAIZ, d))]
if existen:
    ok("PRODUCTO_DIRS existentes: %s" % ", ".join(existen))
else:
    aviso("ninguna carpeta de PRODUCTO_DIRS («%s») existe en este repo: la guardia de alcance NO protege nada hasta que lo configures en harness/config.env" % cfg["PRODUCTO_DIRS"])
try:
    open(os.path.join(H, "fricciones.log"), "a").close()
    ok("el registro de fricciones es escribible (harness/fricciones.log)")
except OSError:
    aviso("no se puede escribir harness/fricciones.log")

print("\n" + ("El harness está vivo." if not FALLOS else "%d comprobación(es) en rojo: el harness NO está completo." % FALLOS))
sys.exit(1 if FALLOS else 0)
