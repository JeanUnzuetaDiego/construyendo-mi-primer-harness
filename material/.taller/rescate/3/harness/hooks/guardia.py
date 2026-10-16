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
#  Comandos: se mira la POSICIÓN del comando, no el texto  ->  `echo "git push"` NO se bloquea
# ----------------------------------------------------------------------------------------------
def _saltos_a_punto_y_coma(cmd):
    out, simple, doble, i = [], False, False, 0
    while i < len(cmd):
        c = cmd[i]
        if c == "\\" and not simple and i + 1 < len(cmd):
            out.append(cmd[i:i + 2]); i += 2; continue
        if c == "'" and not doble:
            simple = not simple
        elif c == '"' and not simple:
            doble = not doble
        out.append(" ; " if (c == "\n" and not simple and not doble) else c)
        i += 1
    return "".join(out)


def _sustituciones(cmd):
    """Cuerpos de $(...) y `...` fuera de comillas simples: la shell los ejecuta aunque estén entre comillas dobles."""
    out, i, n, simple, doble = [], 0, len(cmd), False, False
    while i < n:
        c = cmd[i]
        if c == "\\" and not simple:
            i += 2; continue
        if c == "'" and not doble:
            simple = not simple; i += 1; continue
        if c == '"' and not simple:
            doble = not doble; i += 1; continue
        if not simple:
            if cmd.startswith("$(", i) and not cmd.startswith("$((", i):
                prof, j = 1, i + 2
                while j < n and prof:
                    prof += (cmd[j] == "(") - (cmd[j] == ")")
                    j += 1
                out.append(cmd[i + 2:j - 1]); i = j; continue
            if c == "`":
                j = cmd.find("`", i + 1)
                if j != -1:
                    out.append(cmd[i + 1:j]); i = j + 1; continue
        i += 1
    return out


def _segmentos(cmd):
    lex = shlex.shlex(_saltos_a_punto_y_coma(cmd), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    segs, actual, previo = [], [], ""
    for t in lex:
        if t in SEPARADORES:
            if actual:
                segs.append((previo, actual))
            actual, previo = [], t
        else:
            actual.append(t)
    if actual:
        segs.append((previo, actual))
    return segs


def _desenvolver(t):
    """Quita asignaciones de entorno y envoltorios (sudo, env, timeout, xargs...) y deja el comando real."""
    t = list(t)
    for _ in range(12):
        while t and (t[0] in PREFIJOS or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t[0])):
            t.pop(0)
        if not t:
            return t
        prog = os.path.basename(t[0])
        if prog in ("sudo", "doas"):
            t.pop(0)
            while t and t[0].startswith("-"):
                if t.pop(0) in ("-u", "-g", "-h", "-p", "-r", "-t", "-U", "-C", "-D", "-R") and t:
                    t.pop(0)
        elif prog == "env":
            t.pop(0)
            while t and (t[0].startswith("-") or "=" in t[0]):
                if t.pop(0) in ("-u", "-C", "-S") and t:
                    t.pop(0)
        elif prog == "timeout":
            t.pop(0)
            while t and t[0].startswith("-"):
                if t.pop(0) in ("-k", "-s") and t:
                    t.pop(0)
            if t:
                t.pop(0)  # la duración
        elif prog in ("nice", "ionice", "stdbuf"):
            t.pop(0)
            while t and t[0].startswith("-"):
                if t.pop(0) in ("-n", "-c", "-p", "-i", "-o", "-e") and t and not t[0].startswith("-"):
                    t.pop(0)
        elif prog == "xargs":
            t.pop(0)
            while t and t[0].startswith("-"):
                if t.pop(0) in ("-n", "-I", "-P", "-L", "-d", "-E", "-s", "-a") and t:
                    t.pop(0)
        elif prog in ("command", "builtin", "exec", "nohup", "setsid", "caffeinate", "watch", "flock", "unbuffer"):
            t.pop(0)
            while t and t[0].startswith("-"):
                t.pop(0)
        else:
            return t
    return t


def _posicionales(args, n):
    return [a for a in args if not a.startswith("-")][:n]


def _subcomando_git(args):
    con_valor = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env", "--exec-path"}
    i = 0
    while i < len(args):
        a = args[i]
        if a in con_valor:
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            return a, args[i + 1:]
    return None, []


def _revisar_git(args):
    sub, resto = _subcomando_git(args)
    if sub is None:
        return
    if sub in GIT_SIN_PERMISO:
        bloquear("sin-permiso", "git %s necesita el permiso explícito de una persona." % sub,
                 "Deja los cambios sin commitear y propón el mensaje de commit; la persona decide.",
                 "Bash", "git " + sub)
    destructivo = (
        (sub == "reset" and "--hard" in resto)
        or (sub == "clean" and ("--force" in resto or any(a.startswith("-") and not a.startswith("--") and "f" in a for a in resto)))
        or (sub == "branch" and "-D" in resto)
        or (sub == "stash" and resto[:1] in (["drop"], ["clear"]))
    )
    if destructivo:
        bloquear("destructivo", "git %s %s destruye trabajo." % (sub, " ".join(resto[:2])),
                 "No lo ejecutes. Explica qué querías conseguir y la persona decide.", "Bash", "git " + sub)


def _revisar_rm(args):
    recursivo = any((a.startswith("-") and not a.startswith("--") and re.search("[rR]", a)) or a == "--recursive" for a in args)
    if not recursivo:
        return
    destinos, fin = [], False
    for a in args:
        if fin:
            destinos.append(a)
        elif a == "--":
            fin = True
        elif not a.startswith("-"):
            destinos.append(a)
    for d in destinos or ["(sin destino)"]:
        partes = os.path.normpath(d).split(os.sep)
        if os.path.isabs(os.path.normpath(d)) or ".." in partes or partes[0] not in RM_PERMITIDOS:
            bloquear("destructivo", "rm recursivo sobre «%s»." % d,
                     "Solo se pueden borrar artefactos de compilación (%s). Para lo demás, pídeselo a la persona."
                     % ", ".join(sorted(RM_PERMITIDOS)), "Bash", "rm -r " + d)


def _revisar_interprete(prog, args, prof):
    i = 0
    while i < len(args):
        a = args[i]
        if prog in SHELLS and a.startswith("-") and not a.startswith("--") and "c" in a[1:]:
            if i + 1 < len(args):
                _revisar_orden(args[i + 1], prof + 1)  # bash -c "..."
            return
        if a.startswith("-"):
            i += 2 if (a in ("-W", "-X", "-r", "-I") and prog not in SHELLS) else 1
            continue
        nombre = os.path.basename(a)  # el primer posicional es el script
        if NOMBRE_DESPLIEGUE.match(nombre):
            bloquear("despliegue", "%s es un script de despliegue." % nombre,
                     "Termina el cambio, corre la compuerta y avisa a la persona: ella despliega.", "Bash", prog + " " + a)
        if NOMBRE_DESTRUCTIVO.match(nombre):
            bloquear("destructivo", "%s es un script destructivo." % nombre,
                     "No lo ejecutes. Explica qué querías conseguir y la persona decide.", "Bash", prog + " " + a)
        return


def _revisar_segmento(previo, tokens, prof):
    t = _desenvolver(tokens)
    if not t:
        return
    prog, args = os.path.basename(t[0]), t[1:]
    if NOMBRE_DESPLIEGUE.match(prog):
        bloquear("despliegue", "%s despliega." % prog,
                 "Termina el cambio, corre la compuerta y avisa a la persona: ella despliega.", "Bash", " ".join(t))
    if NOMBRE_DESTRUCTIVO.match(prog):
        bloquear("destructivo", "%s es destructivo." % prog,
                 "No lo ejecutes. Explica qué querías conseguir y la persona decide.", "Bash", " ".join(t))
    if prog in SHELLS and previo in ("|", "|&") and not any(not a.startswith("-") or "c" in a[1:] for a in args):
        bloquear("evasion", "ejecutar como código un texto que llega por una tubería.",
                 "Escribe el comando completo y a la vista, para que se pueda revisar.", "Bash", " ".join(t))
    if prog in INTERPRETES:
        _revisar_interprete(prog, args, prof)
    elif prog == "eval":
        texto = " ".join(args)
        if "$" in texto or "`" in texto:
            bloquear("evasion", "eval con un texto construido en tiempo de ejecución.",
                     "Escribe el comando completo y a la vista, para que se pueda revisar.", "Bash", "eval " + texto)
        _revisar_orden(texto, prof + 1)
    elif prog == "git":
        _revisar_git(args)
    elif prog == "gh":
        if tuple(_posicionales(args, 2)) in GH_SIN_PERMISO:
            bloquear("sin-permiso", "esa acción de gh publica algo hacia fuera.",
                     "Prepara el texto y deja que la persona lo publique.", "Bash", "gh " + " ".join(args[:2]))
    elif prog == "rm":
        _revisar_rm(args)
    elif prog in ("psql", "mysql", "sqlite3", "mongosh"):
        if re.search(r"\b(drop|truncate)\b|delete\s+from", " ".join(args), re.I):
            bloquear("destructivo", "SQL destructivo desde la línea de comandos.",
                     "No lo ejecutes. Escribe una migración y que la revise una persona.", "Bash", prog)
    elif prog in ("dropdb", "dropuser"):
        bloquear("destructivo", "%s borra datos." % prog, "No lo ejecutes.", "Bash", prog)
    for tabla, regla, mensaje in ((DESTRUCTIVO, "destructivo", "es una acción destructiva."),
                                  (DESPLIEGUE, "despliegue", "es un despliegue.")):
        if prog in tabla:
            verbos, n = tabla[prog]
            hallado = [p for p in _posicionales(args, n) if p in verbos]
            if hallado:
                bloquear(regla, "%s %s %s" % (prog, hallado[0], mensaje),
                         "No lo ejecutes. Termina el cambio y avisa a la persona: ella decide.", "Bash", prog + " " + hallado[0])


def _revisar_orden(cmd, prof=0):
    if prof > 4:
        bloquear("evasion", "orden demasiado anidada para revisarla.", "Escribe el comando directamente.", "Bash", cmd)
    for cuerpo in _sustituciones(cmd):
        _revisar_orden(cuerpo, prof + 1)
    for previo, tokens in _segmentos(cmd):
        _revisar_segmento(previo, tokens, prof)


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
