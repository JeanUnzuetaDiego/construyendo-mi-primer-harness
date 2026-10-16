#!/usr/bin/env python3
"""Guardia del harness · hook PreToolUse (Claude Code) y beforeShellExecution (Cursor).

Lee por stdin la llamada a una herramienta (JSON) y decide:
  exit 0  -> sin objeción. NO es un permiso: las reglas nativas de la herramienta se siguen aplicando.
  exit 2  -> BLOQUEADO. Lo que escribas por stderr es lo que lee el agente: dile qué hacer EN SU LUGAR.

Solo el exit 2 bloquea; cualquier otro código (1, 127, un traceback...) deja pasar la acción.
Por eso esta guardia FALLA CERRADA: ante cualquier error propio, bloquea.
"""
import datetime
import json
import os
import re
import shlex
import subprocess
import sys


def _ejecutar(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def _raiz():
    r = os.environ.get("CLAUDE_PROJECT_DIR")
    if not r:
        r = _ejecutar(["git", "rev-parse", "--show-toplevel"]).stdout.strip() or os.getcwd()
    return os.path.realpath(r)


RAIZ = _raiz()


def config():
    cfg = {"PRODUCTO_DIRS": "back web", "RAMAS_LARGAS": "main master develop"}
    try:
        with open(os.path.join(RAIZ, "harness", "config.env"), encoding="utf-8") as f:
            for linea in f:
                m = re.match(r"""\s*([A-Z_]+)=(?:"([^"]*)"|'([^']*)'|(\S*))""", linea)
                if m:
                    cfg[m.group(1)] = m.group(2) or m.group(3) or m.group(4) or ""
    except OSError:
        pass
    return cfg


# ----------------------------------------------------------------------------------------------
#  REGLAS DE PIEDRA — son datos, no código: amplíalas aquí
# ----------------------------------------------------------------------------------------------
GIT_SIN_PERMISO = {"commit", "push", "cherry-pick", "revert", "merge", "rebase", "am"}
GH_SIN_PERMISO = {("pr", "create"), ("pr", "merge"), ("pr", "close"), ("release", "create"),
                  ("release", "delete"), ("repo", "delete")}
# herramienta -> (verbos, cuántos argumentos posicionales mirar)
DESTRUCTIVO = {
    "kubectl": ({"delete", "drain", "replace", "scale", "patch", "edit"}, 3),
    "oc": ({"delete", "drain", "replace", "scale", "patch", "edit"}, 3),
    "docker": ({"rm", "rmi", "prune", "kill", "down"}, 2),
    "podman": ({"rm", "rmi", "prune", "kill"}, 2),
    "docker-compose": ({"down"}, 1),
    "terraform": ({"destroy"}, 2), "tofu": ({"destroy"}, 2), "pulumi": ({"destroy"}, 2),
    "helm": ({"uninstall", "delete"}, 2),
}
DESPLIEGUE = {
    "kubectl": ({"apply", "rollout", "set", "create"}, 3), "oc": ({"apply", "rollout", "set", "create"}, 3),
    "helm": ({"install", "upgrade", "rollback"}, 2),
    "terraform": ({"apply"}, 2), "tofu": ({"apply"}, 2), "pulumi": ({"up"}, 2),
    "docker": ({"push"}, 2), "podman": ({"push"}, 2),
    "serverless": ({"deploy"}, 2), "sls": ({"deploy"}, 2), "vercel": ({"deploy"}, 2),
    "netlify": ({"deploy"}, 2), "fly": ({"deploy"}, 2), "flyctl": ({"deploy"}, 2),
}
NOMBRE_DESPLIEGUE = re.compile(r"^(deploy|despliega|release|publish|rollout)[\w.\-]*$", re.I)
NOMBRE_DESTRUCTIVO = re.compile(r"^(db-)?(reset|wipe|destroy|drop|purge)[\w.\-]*$", re.I)
RM_PERMITIDOS = {"target", "build", "dist", "node_modules", ".gradle", "__pycache__", ".pytest_cache"}

SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
INTERPRETES = SHELLS | {"python", "python3", "node", "ruby", "perl", "php", "deno", "bun"}
SEPARADORES = {"&&", "||", ";", ";;", "|", "|&", "&", "(", ")"}
PREFIJOS = {"{", "}", "!", "then", "do", "else", "elif", "if", "while", "until", "time"}


def bloquear(regla, motivo, que_hacer, herramienta="", detalle=""):
    try:
        with open(os.path.join(RAIZ, "harness", "fricciones.log"), "a", encoding="utf-8") as f:
            ahora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write("\t".join([ahora, herramienta, regla, detalle.replace("\n", " ")[:200]]) + "\n")
    except OSError:
        pass  # el registro nunca debe impedir el bloqueo
    sys.stderr.write("BLOQUEADO por el harness [%s]: %s\n  -> %s\n" % (regla, motivo, que_hacer))
    sys.exit(2)


# ----------------------------------------------------------------------------------------------
#  Comandos  >>>  AQUÍ ESTÁ TU TRABAJO (bloque 3)
# ----------------------------------------------------------------------------------------------
def _revisar_orden(cmd, prof=0):
    """TODO: decide si la orden `cmd` (el texto que el agente quiere ejecutar) debe bloquearse.

    Si debe bloquearse, llama a:  bloquear(regla, motivo, que_hacer, "Bash", detalle)   (eso hace exit 2).
    Si no, simplemente retorna.  Las reglas de piedra (GIT_SIN_PERMISO, DESTRUCTIVO, DESPLIEGUE...) están arriba.

    Cómo saber si vas bien:      bash .taller/red-team.sh
    Pista para cuando falle:     ¿importa el TEXTO del comando o la POSICIÓN en la que aparece?
                                 echo "git push"  no ejecuta nada;  /usr/bin/git push  sí.
    """
    return


# ----------------------------------------------------------------------------------------------
#  Alcance: el agente solo edita lo que el expediente declara (la frontera que el requisito no ponía)
# ----------------------------------------------------------------------------------------------
def _alcance_declarado(expediente):
    en_fase3, permitidos = False, []
    with open(expediente, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("## "):
                en_fase3 = linea.startswith("## Fase 3")
                continue
            m = re.match(r"^\s*-\s+`?([^`\s]+)`?\s*$", linea)
            if en_fase3 and m:
                permitidos.append(m.group(1).lstrip("./"))
    return permitidos


def _revisar_alcance(ruta, herramienta):
    cfg = config()
    absoluta = ruta if os.path.isabs(ruta) else os.path.join(RAIZ, ruta)
    rel = os.path.relpath(os.path.realpath(absoluta), RAIZ).replace(os.sep, "/")
    if rel.startswith("..") or rel.split("/")[0] not in cfg["PRODUCTO_DIRS"].split():
        return  # el harness, la documentación y lo demás no se restringen aquí
    p = _ejecutar(["git", "branch", "--show-current"], cwd=RAIZ)
    rama = p.stdout.strip()
    if p.returncode != 0 or not rama:
        bloquear("alcance", "no pude determinar la rama de trabajo.", "Trabaja en una rama feat/RF-XXX-NNN-descripcion.", herramienta, rel)
    if rama in cfg["RAMAS_LARGAS"].split():
        bloquear("alcance", "estás en «%s», una rama larga: ahí no se escribe código de producto." % rama,
                 "Crea una rama feat/RF-XXX-NNN-descripcion y declara el alcance en su expediente.", herramienta, rel)
    m = re.search(r"RF-[A-Z]{3}-\d{3}", rama)
    if not m:
        bloquear("alcance", "la rama «%s» no declara un requisito (RF-XXX-NNN)." % rama,
                 "Renombra la rama o vuelve a localizar el requisito. No inventes el código.", herramienta, rel)
    rf = m.group(0)
    exp = os.path.join(RAIZ, "work", rf, "expediente.md")
    if not os.path.isfile(exp):
        bloquear("alcance", "no hay expediente para %s." % rf,
                 "Crea work/%s/expediente.md y declara los archivos a tocar bajo «## Fase 3». Sin alcance declarado no se edita código." % rf,
                 herramienta, rel)
    permitidos = _alcance_declarado(exp)
    if not permitidos:
        bloquear("alcance", "el expediente de %s no declara archivos bajo «## Fase 3»." % rf,
                 "Declara los archivos a tocar (uno por línea, con «- »). Sin alcance declarado no se edita código.", herramienta, rel)
    if rel not in permitidos:
        bloquear("alcance", "%s no está en el alcance declarado para %s." % (rel, rf),
                 "Alcance declarado: %s. Si hace falta otro archivo, pídele a la persona que amplíe el alcance; no lo edites por otro camino."
                 % ", ".join(permitidos), herramienta, rel)


def main():
    try:
        datos = json.load(sys.stdin)
        assert isinstance(datos, dict)
    except Exception:
        bloquear("guardia", "no pude leer la llamada a la herramienta (JSON inválido).",
                 "Se bloquea por seguridad: una guardia que no entiende no deja pasar.")
    herramienta = datos.get("tool_name") or ""
    entrada = datos.get("tool_input") if isinstance(datos.get("tool_input"), dict) else {}
    cmd = entrada.get("command", datos.get("command"))      # Claude Code · Cursor preToolUse · Cursor beforeShellExecution
    ruta = entrada.get("file_path", datos.get("file_path"))
    if isinstance(cmd, str) and herramienta in ("Bash", "Shell", ""):
        _revisar_orden(cmd)
    elif isinstance(ruta, str) and herramienta in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        _revisar_alcance(ruta, herramienta)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # FALLA CERRADA
        sys.stderr.write("BLOQUEADO por el harness [guardia]: error interno (%s: %s). Se bloquea por seguridad.\n"
                         % (type(e).__name__, e))
        sys.exit(2)
