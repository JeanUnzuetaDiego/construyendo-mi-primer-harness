#!/usr/bin/env python3
"""Motor de ataques contra la guardia (harness/hooks/guardia.sh). Lo usan red-team.sh y verificar.sh."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(os.path.dirname(AQUI), "corpus")


def cargar(nombre):
    ruta = nombre if os.path.isabs(nombre) else os.path.join(CORPUS, nombre + ".txt")
    with open(ruta, encoding="utf-8") as f:
        return [l.rstrip("\n").replace("\\n", "\n").replace("\\t", "\t") for l in f if l.strip() and not l.startswith("#")]


def llamar(guardia, comando, proyecto, herramienta="Bash"):
    """Llama a la guardia como lo haría Claude Code: JSON por stdin + CLAUDE_PROJECT_DIR. Devuelve (exit, stderr, segundos)."""
    carga = json.dumps({"hook_event_name": "PreToolUse", "tool_name": herramienta, "tool_input": {"command": comando}})
    t0 = time.time()
    try:
        p = subprocess.run(["bash", guardia], input=carga, capture_output=True, text=True, timeout=15,
                           env=dict(os.environ, CLAUDE_PROJECT_DIR=proyecto))
        return p.returncode, p.stderr, time.time() - t0
    except subprocess.TimeoutExpired:
        return 124, "tiempo agotado", time.time() - t0


def evaluar(guardia, extra=None):
    """Ejecuta los corpus. Devuelve un dict con aciertos y listas de fallos."""
    tmp = tempfile.mkdtemp(prefix="redteam-")
    os.makedirs(os.path.join(tmp, "harness"))  # la fricción se anota aquí, no en tu proyecto
    try:
        res, tiempos = {}, []
        for clave, nombre in (("t1", "bloquear-t1"), ("t2", "bloquear-t2")):
            lista = cargar(nombre)
            pasaron = []
            for c in lista:
                rc, _, dt = llamar(guardia, c, tmp)
                tiempos.append(dt)
                if rc != 2:
                    pasaron.append(c)
            res[clave] = (len(lista) - len(pasaron), len(lista), pasaron)
        lista = cargar("permitir")
        bloqueados = []
        for c in lista:
            rc, _, dt = llamar(guardia, c, tmp)
            tiempos.append(dt)
            if rc == 2:
                bloqueados.append(c)
        res["fp"] = (len(bloqueados), len(lista), bloqueados)
        lista = cargar("limites-t3")
        bloqueados = [c for c in lista if llamar(guardia, c, tmp)[0] == 2]
        res["t3"] = (len(lista) - len(bloqueados), len(lista), bloqueados)
        if extra:
            propios = cargar(extra)
            pasaron = [c for c in propios if llamar(guardia, c, tmp)[0] != 2]
            res["propios"] = (len(propios) - len(pasaron), len(propios), pasaron)
        res["lento"] = sum(tiempos) / max(1, len(tiempos))
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _lista(items, n=6):
    out = ["      · " + (c.replace("\n", "\\n").replace("\t", "\\t")[:78]) for c in items[:n]]
    if len(items) > n:
        out.append("      · … y %d más" % (len(items) - n))
    return "\n".join(out)


def imprimir(res):
    ok = lambda b: "[OK]" if b else "[X] "
    t1, t2, fp, t3 = res["t1"], res["t2"], res["fp"], res["t3"]
    print("  %s T1 directos .......... %d/%d bloqueados" % (ok(t1[0] == t1[1]), t1[0], t1[1]))
    if t1[2]:
        print("      pasaron (¡no deberían!):\n" + _lista(t1[2]))
    print("  %s T2 evasiones ......... %d/%d bloqueados" % (ok(t2[0] == t2[1]), t2[0], t2[1]))
    if t2[2]:
        print("      pasaron (¡no deberían!):\n" + _lista(t2[2]))
    print("  %s falsos positivos ..... %d/%d comandos legítimos bloqueados" % (ok(fp[0] == 0), fp[0], fp[1]))
    if fp[2]:
        print("      bloqueados (¡no deberían!):\n" + _lista(fp[2]))
    print("  [i]  T3 límites conocidos .. %d/%d pasan (esperado: una guardia estática no ve dentro de scripts, intérpretes ni alias)" % (t3[0], t3[1]))
    if "propios" in res:
        pr = res["propios"]
        print("  %s tus ataques .......... %d/%d bloqueados" % (ok(pr[0] == pr[1]), pr[0], pr[1]))
        if pr[2]:
            print("      LE GANARON a la guardia:\n" + _lista(pr[2]))
    if res["lento"] > 0.5:
        print("  [!]  la guardia tarda %.2f s por llamada: un hook lento retrasa al agente (y si se agota el tiempo, NO bloquea)." % res["lento"])


def main():
    guardia = os.path.join(os.getcwd(), "harness", "hooks", "guardia.sh")
    raiz = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if raiz:
        guardia = os.path.join(raiz, "harness", "hooks", "guardia.sh")
    if not os.path.isfile(guardia):
        sys.exit("Falta harness/hooks/guardia.sh")
    extra = sys.argv[1] if len(sys.argv) > 1 else None
    if extra and not os.path.isfile(extra):
        sys.exit("No existe el archivo de ataques: %s" % extra)
    if extra:
        extra = os.path.abspath(extra)  # cargar() trata un nombre relativo como un corpus del taller
    print("Red team contra %s%s\n" % (os.path.relpath(guardia, raiz or "."), "  (+ tus ataques de %s)" % os.path.relpath(extra) if extra else ""))
    res = evaluar(guardia, extra)
    imprimir(res)
    bien = res["t1"][0] == res["t1"][1] and res["t2"][0] == res["t2"][1] and res["fp"][0] == 0 and \
        ("propios" not in res or not res["propios"][2])
    print("\n" + ("La guardia aguanta todos los ataques del corpus." if bien else "Todavía hay brechas: lee las listas de arriba."))
    sys.exit(0 if bien else 1)


if __name__ == "__main__":
    main()
