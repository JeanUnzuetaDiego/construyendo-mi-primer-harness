#!/usr/bin/env python3
"""El semáforo del taller. Comprueba COMPORTAMIENTO (casos que deben pasar y casos que deben fallar), no solo que existan archivos.
Un objeto ausente es un fallo, no un caso omitido: un proyecto recién creado sale en ROJO."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import redteam  # noqa: E402
from prueba import coincide  # noqa: E402

_r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
if _r.returncode != 0:
    sys.exit("Ejecuta esto dentro del proyecto (un repositorio git).")
RAIZ = _r.stdout.strip()
H = os.path.join(RAIZ, "harness")
ESCRITURA = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def p(*partes):
    return os.path.join(RAIZ, *partes)


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def correr(args, entrada=None, env=None, cwd=None, timeout=60):
    try:
        r = subprocess.run(args, input=entrada, capture_output=True, text=True, env=env, cwd=cwd or RAIZ, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "tiempo agotado"


def config():
    cfg = {"PRODUCTO_DIRS": "back web", "RAMAS_LARGAS": "main master develop", "PRESUPUESTO_BYTES": "3000", "CONSTITUCION": "AGENTS.md"}
    t = leer(p("harness", "config.env")) or ""
    for l in t.split("\n"):
        m = re.match(r"""\s*([A-Z_]+)=(?:"([^"]*)"|'([^']*)'|(\S*))""", l)
        if m:
            cfg[m.group(1)] = m.group(2) or m.group(3) or m.group(4) or ""
    return cfg


def settings():
    t = leer(p(".claude", "settings.json"))
    if t is None:
        return None, "falta .claude/settings.json"
    try:
        d = json.loads(t)
        return (d if isinstance(d, dict) else {}), None
    except ValueError as e:
        return None, ".claude/settings.json no es JSON válido (%s)" % e


def frontmatter(texto):
    if not texto or not texto.startswith("---"):
        return {}, texto or ""
    partes = texto.split("\n---", 1)
    if len(partes) < 2:
        return {}, texto
    fm, clave = {}, None
    for l in partes[0].split("\n")[1:]:
        m = re.match(r"^([A-Za-z_][\w\-]*):\s*(.*)$", l)
        if m:
            clave = m.group(1)
            fm[clave] = m.group(2).strip().strip("\"'")
        elif clave and re.match(r"^\s*-\s+", l):
            fm[clave] = (fm[clave] + ", " if fm[clave] else "") + re.sub(r"^\s*-\s+", "", l).strip()
    return fm, partes[1].split("\n", 1)[1] if "\n" in partes[1] else ""


def rescates():
    t = leer(p(".taller", "estado", "rescates")) or ""
    return {int(x) for x in t.split() if x.isdigit()}


class Bloque:
    def __init__(self, n, titulo, maximo):
        self.n, self.titulo, self.max, self.pts, self.fallos = n, titulo, maximo, 0.0, 0
        print("\n== Bloque %d · %s ==" % (n, titulo) if n else "\n== Arranque: %s ==" % titulo)

    def ok(self, m, pts=0.0):
        print("  [OK] " + m)
        self.pts += pts

    def mal(self, m, pts=0.0):  # pts se ignora: lo que falla no suma
        print("  [X]  " + m)
        self.fallos += 1

    def aviso(self, m):
        print("  [!]  " + m)

    def info(self, m):
        print("  [i]  " + m)

    def cierre(self):
        if not self.max:
            return self
        r = self.n in rescates()
        print("  -> Bloque %d: %.1f/%d puntos%s" % (self.n, self.pts, self.max, "  (con rescate: el bloque lo pusiste con saltar.sh)" if r else ""))
        self.pts_ef = self.pts
        return self


def _parcial(b, m, hechos, total, pts):
    """OK solo si es completo; los puntos son proporcionales."""
    if hechos == total:
        print("  [OK] " + m)
    else:
        print("  [X]  " + m)
        b.fallos += 1
    b.pts += pts * hechos / total if total else 0


def entradas(datos, evento):
    return (datos or {}).get("hooks", {}).get(evento) or []


def cableado(b, datos, evento, nombres, script, pts):
    cubren = [e for e in entradas(datos, evento) if all(coincide(e.get("matcher"), n) for n in nombres)]
    if not cubren:
        return b.mal("%s: ninguna entrada de settings.json cubre %s (el matcher de Edit|Write es una lista EXACTA de nombres)" % (evento, " ni ".join(nombres)))
    cmds = [h.get("command", "") for e in cubren for h in (e.get("hooks") or [])]
    con = [c for c in cmds if script in c]
    if not con:
        return b.mal("%s: ningún comando llama a %s" % (evento, script))
    if not any("$CLAUDE_PROJECT_DIR" in c for c in con):
        return b.mal("%s: la ruta no parte de $CLAUDE_PROJECT_DIR (se rompe si el agente cambia de directorio o en la laptop de otra persona)" % evento)
    if any(re.search(r"(/home/|/Users/|[A-Za-z]:\\)", c) for c in con):
        return b.mal("%s: la ruta es absoluta y de TU máquina; no sirve para nadie más" % evento)
    if not os.path.isfile(p("harness", "hooks", script)):
        return b.mal("%s: falta harness/hooks/%s" % (evento, script))
    b.ok("%s conectado a %s" % (evento, script), pts)


# ======================================================================================================
def b0():
    b = Bloque(0, "el terreno está listo", 0)
    ok = lambda c, m: (b.ok(m) if c else b.mal(m))
    ok(os.path.isdir(p(".git")), "es un repositorio git")
    rama = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=RAIZ).stdout.strip()
    ok(re.match(r"^feat/RF-[A-Z]{3}-\d{3}", rama or ""), "estás en una rama de trabajo con su requisito (%s)" % (rama or "ninguna"))
    ok(subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, cwd=RAIZ).returncode == 0, "existe el remoto origin")
    ok(sys.version_info >= (3, 8), "python3 %d.%d (hace falta 3.8 o más)" % sys.version_info[:2])
    ok(os.path.isfile(p("requisitos", "RF-DEM-001.md")), "existe el requisito RF-DEM-001")
    exp = leer(p("work", "RF-DEM-001", "expediente.md")) or ""
    ok("- back/Boleta.java" in exp, "el expediente declara el alcance (back/Boleta.java)")
    ok(os.path.isdir(p(".taller", "rescate")), "están los puntos de rescate (.taller/rescate)")
    herramientas = [n for n in ("claude", "cursor") if shutil.which(n)]
    b.info("agente detectado en tu PATH: %s" % (", ".join(herramientas) or "ninguno (no pasa nada: usarás el agente simulado)"))
    return b


def b1():
    b = Bloque(1, "Contexto: la constitución", 15)
    cfg = config()
    ruta = p(cfg["CONSTITUCION"])
    texto = leer(ruta)
    if texto is None:
        b.mal("falta %s: aquí va la constitución (la plantilla está en GUIA.md)" % cfg["CONSTITUCION"])
        return b.cierre()
    b.ok("existe %s" % cfg["CONSTITUCION"], 2)
    cl = leer(p("CLAUDE.md")) or ""
    (b.ok("CLAUDE.md importa AGENTS.md (@AGENTS.md): una constitución para Claude Code y Cursor", 1) if "@AGENTS.md" in cl.split() else b.mal("CLAUDE.md debe contener la línea @AGENTS.md"))
    n, pres = len(texto.encode("utf-8")), int(cfg["PRESUPUESTO_BYTES"] or 3000)
    if n < 600:
        b.mal("%s pesa solo %d B: una constitución sin sustancia no restringe nada" % (cfg["CONSTITUCION"], n))
    elif n > pres:
        b.mal("%s pesa %d B (≈ %d tokens): se pasa del presupuesto de %d B. Lo que cargas SIEMPRE se paga en cada respuesta: mueve el detalle a harness/contexto/" % (cfg["CONSTITUCION"], n, n // 4, pres))
    else:
        b.ok("%s pesa %d B (≈ %d tokens): dentro del presupuesto de %d B" % (cfg["CONSTITUCION"], n, n // 4, pres), 3)
    # «No puedes»: ≥ 4 viñetas
    lineas, en_sec, viñetas = texto.split("\n"), False, 0
    for l in lineas:
        if re.match(r"^#{1,4}\s", l):
            if en_sec:
                break
            en_sec = bool(re.search(r"no puedes|prohibido|l[ií]mites|nunca", l, re.I))
        elif en_sec and re.match(r"^\s*[-*]\s+\S", l):
            viñetas += 1
    (b.ok("sección de límites duros con %d viñetas (describir no restringe: prohibir sí)" % viñetas, 2) if viñetas >= 4
     else b.mal("falta una sección «No puedes» con al menos 4 viñetas (tiene %d)" % viñetas))
    # tabla regla -> quién la hace cumplir
    filas, ya_cabecera = [], False
    for l in lineas:
        if l.strip().startswith("|"):
            celdas = [c.strip() for c in l.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in celdas):
                ya_cabecera = True
                continue
            if ya_cabecera and len(celdas) >= 2:
                filas.append(celdas)
        else:
            ya_cabecera = False
    con_script = [f for f in filas if re.search(r"`[^`]+`", f[1])]
    con_texto = [f for f in filas if f[1].strip().lower() == "texto"]
    (b.ok("tabla de invariantes con %d reglas" % len(filas), 1) if len(filas) >= 5 else b.mal("la tabla «regla → quién la hace cumplir» necesita al menos 5 filas (tiene %d)" % len(filas)))
    (b.ok("%d reglas dicen qué script las hace cumplir" % len(con_script), 1) if len(con_script) >= 3 else b.mal("al menos 3 reglas deben nombrar el script que las hace cumplir, entre `backticks` (hay %d)" % len(con_script)))
    (b.ok("solo %d de %d reglas dependen de «texto»" % (len(con_texto), len(filas)), 1) if filas and len(con_texto) <= len(filas) / 2 else b.mal("más de la mitad de las reglas dependen de «texto»: son candidatas a script"))
    # enrutado: contexto bajo demanda
    rutas = list(dict.fromkeys(re.findall(r"`(harness/contexto/[\w.\-]+\.md)`", texto)))
    existen = [r for r in rutas if os.path.isfile(p(r))]
    if len(rutas) >= 2 and len(existen) == len(rutas):
        b.ok("enrutado a %d archivos de contexto, todos existen" % len(rutas), 2)
    else:
        b.mal("la sección «Dónde buscar» debe citar al menos 2 archivos `harness/contexto/*.md` y todos deben existir (citas: %d, existen: %d)" % (len(rutas), len(existen)))
    pesos = {r: len((leer(p(r)) or "").encode("utf-8")) for r in existen}
    if existen and all(0 < v <= 2000 for v in pesos.values()):
        b.ok("cada archivo de contexto es corto (≤ 2000 B)", 1)
        b.info("cargas SIEMPRE %d B; tienes %d B más disponibles BAJO DEMANDA" % (n, sum(pesos.values())))
    else:
        b.mal("los archivos de contexto deben tener contenido y no pasar de 2000 B")
    sin_codigo = re.sub(r"`[^`]*`", "", texto)
    if re.search(r"(^|\s)@harness/contexto/", sin_codigo):
        b.mal("importas el contexto con @: los @imports se cargan AL ARRANCAR y no ahorran nada. Cita la ruta entre `backticks`")
    else:
        b.ok("el contexto se abre bajo demanda (rutas, no @imports)", 1)
    return b.cierre()


MUESTRA_JAVA = ("package x;\nimport java.math.BigDecimal;\npublic class Muestra {\n  private double montoBruto;\n"
                "  public void f(BigDecimal h) {\n    System.out.println(\"bruto: \" + montoBruto);\n"
                "    BigDecimal n = h.multiply(new BigDecimal(\"0.85\"));\n  }\n}\n")
LIMPIA_JAVA = ("package x;\nimport java.math.BigDecimal;\nimport java.util.logging.Logger;\npublic class Limpia {\n"
               "  private static final Logger LOG = Logger.getLogger(Limpia.class.getName());\n  private BigDecimal montoNeto;\n"
               "  public void emitir(BigDecimal neto) { this.montoNeto = neto; LOG.info(\"ok\"); }\n}\n")
MUESTRA_TS = "export function f(items: any[]): number {\n  console.log(\"x\");\n  return items.length;\n}\n"
LIMPIA_TS = "export function f(items: string[]): number {\n  return items.length;\n}\n"


def sha(ruta):
    return hashlib.sha256(open(ruta, "rb").read()).hexdigest()


def b2():
    b = Bloque(2, "Herramientas que observan: hook + puente", 15)
    hook, puente = p("harness", "hooks", "after-edit.sh"), p("harness", "hooks", "puente.sh")
    tmp = tempfile.mkdtemp(prefix="v2-")
    try:
        ficheros = {}
        for nombre, txt in (("Muestra.java", MUESTRA_JAVA), ("Limpia.java", LIMPIA_JAVA), ("muestra.ts", MUESTRA_TS), ("limpio.ts", LIMPIA_TS)):
            ficheros[nombre] = os.path.join(tmp, nombre)
            open(ficheros[nombre], "w").write(txt)
        if not os.path.isfile(hook):
            b.mal("falta harness/hooks/after-edit.sh")
        else:
            antes = sha(ficheros["Muestra.java"])
            rc, out, err = correr(["bash", hook, ficheros["Muestra.java"]])
            s = out + err
            _parcial(b, "Java: detecta las 3 violaciones (double monetario, System.out, tasa escrita) — %d/3" % min(s.count(">> AVISO"), 3), min(s.count(">> AVISO"), 3), 3, 3)
            (b.ok("los avisos llevan la línea ofensora (N:texto): el agente sabe DÓNDE", 1) if len(re.findall(r"(?m)^\s*\d+:", s)) >= 3
             else b.mal("cada aviso debe ir acompañado de la línea ofensora con su número (usa grep -n): sin eso el agente no sabe dónde corregir"))
            rc2, out2, err2 = correr(["bash", hook, ficheros["Limpia.java"]])
            (b.ok("un archivo limpio sale en silencio (sin falsos positivos)", 2) if (out2 + err2).strip() == "" else b.mal("falso positivo: un archivo limpio produjo salida: %s" % (out2 + err2).strip()[:70]))
            rc3, out3, err3 = correr(["bash", hook, ficheros["muestra.ts"]])
            (b.ok("TypeScript: detecta console.log y any (%d avisos)" % (out3 + err3).count(">> AVISO"), 1) if (out3 + err3).count(">> AVISO") >= 2
             else b.mal("TypeScript: debe avisar de console.log y de any (hay %d avisos)" % (out3 + err3).count(">> AVISO")))
            (b.ok("el hook solo observa: exit 0 y no modifica el archivo", 1) if rc == 0 and sha(ficheros["Muestra.java"]) == antes
             else b.mal("el hook debe salir con exit 0 y NUNCA modificar archivos (salió %d)" % rc))
        if not os.path.isfile(puente):
            b.mal("falta harness/hooks/puente.sh")
        else:
            env = dict(os.environ, CLAUDE_PROJECT_DIR=RAIZ)
            rc, out, err = correr(["bash", puente], json.dumps({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": ficheros["Muestra.java"]}, "tool_response": {}}), env)
            (b.ok("puente (Claude Code): avisos → exit 2 y stderr (así llegan al agente)", 2) if rc == 2 and "AVISO" in err
             else b.mal("con el payload de Claude Code el puente debe salir con exit 2 y escribir el aviso por STDERR (salió %d; con exit 0 el agente nunca lo ve)" % rc))
            rc, out, err = correr(["bash", puente], json.dumps({"file_path": ficheros["Muestra.java"], "edits": []}), env)
            (b.ok("puente (Cursor): entiende {\"file_path\": ...}", 1) if rc == 2 else b.mal("el puente no entiende el payload de Cursor ({\"file_path\":…}): salió %d" % rc))
            rc, out, err = correr(["bash", puente], json.dumps({"tool_name": "Write", "tool_input": {"file_path": ficheros["Limpia.java"]}}), env)
            (b.ok("puente: un archivo limpio sale en silencio con exit 0", 1) if rc == 0 and not err.strip() else b.mal("puente: con un archivo limpio debe salir con exit 0 y sin salida (salió %d)" % rc))
            rc, _, _ = correr(["bash", puente], "esto no es json", env)
            (b.ok("puente: una entrada ilegible no rompe nada (exit 0)", 1) if rc == 0 else b.mal("puente: ante una entrada ilegible debe salir con 0, no %d" % rc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    datos, err = settings()
    if err:
        b.mal(err)
    else:
        cableado(b, datos, "PostToolUse", ["Edit", "Write"], "puente.sh", 2)
        for nombre in ("Bash", "Read"):
            if any(coincide(e.get("matcher"), nombre) for e in entradas(datos, "PostToolUse")):
                b.aviso("el matcher de PostToolUse también dispara con «%s»: el hook de edición solo debería ver Edit y Write" % nombre)
    return b.cierre()


def proyecto_temporal(prod, rama="feat/RF-DEM-001-x", alcance=("%s/Boleta.java",), expediente=True):
    """Proyecto git temporal con TUS archivos de harness, para probar la guardia de alcance."""
    tmp = tempfile.mkdtemp(prefix="v3-")
    shutil.copytree(H, os.path.join(tmp, "harness"), ignore=shutil.ignore_patterns("fricciones.log", "__pycache__"))
    for d in (prod, "web", os.path.join("work", "RF-DEM-001")):
        os.makedirs(os.path.join(tmp, d), exist_ok=True)
    for f in ("Boleta.java", "Otra.java"):
        open(os.path.join(tmp, prod, f), "w").write("class X {}\n")
    open(os.path.join(tmp, "web", "resumen.ts"), "w").write("export {}\n")
    open(os.path.join(tmp, "AGENTS.md"), "w").write("# x\n")
    if expediente:
        open(os.path.join(tmp, "work", "RF-DEM-001", "expediente.md"), "w").write("## Fase 3\n" + "".join("- %s\n" % (a % prod) for a in alcance))
    for a in (["init", "-q"], ["config", "user.name", "t"], ["config", "user.email", "t@t"]):
        subprocess.run(["git"] + a, cwd=tmp, capture_output=True)
    subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "b"], cwd=tmp, capture_output=True)
    if rama != "main":
        subprocess.run(["git", "checkout", "-q", "-b", rama], cwd=tmp, capture_output=True)
    return tmp


def llamar_guardia(tmp, herramienta, entrada):
    carga = entrada if isinstance(entrada, str) else json.dumps({"hook_event_name": "PreToolUse", "tool_name": herramienta, "tool_input": entrada})
    rc, out, err = correr(["bash", p("harness", "hooks", "guardia.sh")], carga, dict(os.environ, CLAUDE_PROJECT_DIR=tmp), cwd=tmp)
    return rc, err


def b3():
    b = Bloque(3, "Herramientas que bloquean: la guardia", 25)
    guardia = p("harness", "hooks", "guardia.sh")
    if not os.path.isfile(guardia) or not os.path.isfile(p("harness", "hooks", "guardia.py")):
        b.mal("falta harness/hooks/guardia.sh o guardia.py")
        return b.cierre()
    datos, err = settings()
    if err:
        b.mal(err)
    else:
        cableado(b, datos, "PreToolUse", ["Bash", "Edit", "Write"], "guardia.sh", 3)
    r = redteam.evaluar(guardia)
    t1, t2, fp, t3 = r["t1"], r["t2"], r["fp"], r["t3"]
    _parcial(b, "T1 · comandos directos: %d/%d bloqueados" % (t1[0], t1[1]), t1[0], t1[1], 6)
    if t1[2]:
        print(redteam._lista(t1[2], 4))
    _parcial(b, "T2 · evasiones (espacios, sudo, bash -c, /usr/bin/git, $(…), pipes): %d/%d bloqueadas" % (t2[0], t2[1]), t2[0], t2[1], 6)
    if t2[2]:
        print(redteam._lista(t2[2], 4))
    _parcial(b, "falsos positivos: %d de %d comandos legítimos bloqueados" % (fp[0], fp[1]), fp[1] - fp[0], fp[1], 4)
    if fp[2]:
        print(redteam._lista(fp[2], 4))
    b.info("T3 · límites conocidos: %d/%d pasan — una guardia estática no ve dentro de scripts, intérpretes ni alias (por eso hay que combinarla con permisos, sandbox y CI)" % (t3[0], t3[1]))
    if r["lento"] > 0.5:
        b.aviso("la guardia tarda %.2f s por llamada: si un hook PreToolUse agota su tiempo, la acción SE EJECUTA" % r["lento"])
    # falla cerrada
    tmp0 = tempfile.mkdtemp(prefix="v3f-")
    os.makedirs(os.path.join(tmp0, "harness"))
    rc, _ = llamar_guardia(tmp0, "", "esto no es json")
    (b.ok("falla cerrada: una entrada que no entiende se BLOQUEA (exit 2)", 1) if rc == 2
     else b.mal("una entrada ilegible debe bloquearse con exit 2 (salió %d; cualquier otro código deja pasar la acción)" % rc))
    raros = ['""', "null", "[]", '{"tool_name":"Bash"}', '{"tool_name":"Bash","tool_input":{"command":123}}',
             '{"tool_name":"Edit","tool_input":{"file_path":null}}', '{"tool_name":"Write","tool_input":{}}']
    malos = [x for x in raros if llamar_guardia(tmp0, "", x)[0] not in (0, 2)]
    (b.ok("solo sale con 0 o 2 ante entradas raras (nunca 1: un traceback dejaría pasar la acción)", 1) if not malos
     else b.mal("salió con un código que no es 0 ni 2 ante: %s" % ", ".join(malos[:3])))
    rc, msg = llamar_guardia(tmp0, "Bash", {"command": "git push"})
    log = leer(os.path.join(tmp0, "harness", "fricciones.log")) or ""
    util = rc == 2 and len([l for l in msg.split("\n") if l.strip()]) >= 2 and len(msg) >= 40
    (b.ok("el bloqueo explica el motivo Y qué hacer en su lugar (es un prompt para el agente) y queda en fricciones.log", 1) if util and log.strip()
     else b.mal("el mensaje de bloqueo debe tener al menos 2 líneas (motivo + qué hacer en su lugar) y anotarse en harness/fricciones.log"))
    shutil.rmtree(tmp0, ignore_errors=True)
    # alcance
    cfg = config()
    prod = (cfg["PRODUCTO_DIRS"].split() or ["back"])[0]
    casos, fallos = [], []
    tmp = proyecto_temporal(prod, alcance=("%s/Boleta.java", "%s/Otra.java"))
    try:
        def caso(nombre, esperado, tool, ruta, t=None):
            rc, _ = llamar_guardia(t or tmp, tool, {"file_path": ruta})
            casos.append(nombre)
            if rc != esperado:
                fallos.append(nombre)
        caso("Write de un archivo no declarado (ruta absoluta)", 2, "Write", os.path.join(tmp, prod, "Nueva.java"))
        caso("Edit de un archivo declarado (absoluta)", 0, "Edit", os.path.join(tmp, prod, "Boleta.java"))
        caso("Edit de un archivo declarado (relativa)", 0, "Edit", prod + "/Boleta.java")
        caso("el expediente admite VARIOS archivos", 0, "Edit", os.path.join(tmp, prod, "Otra.java"))
        caso("web/ también es producto: sin declarar, se bloquea", 2, "Write", os.path.join(tmp, "web", "resumen.ts"))
        caso("la infraestructura (AGENTS.md) no se restringe", 0, "Write", os.path.join(tmp, "AGENTS.md"))
        caso("el propio harness no se restringe", 0, "Write", os.path.join(tmp, "harness", "hooks", "x.sh"))
        subprocess.run(["git", "checkout", "-q", "main"], cwd=tmp, capture_output=True)
        caso("en una rama larga (main) no se escribe producto", 2, "Edit", os.path.join(tmp, prod, "Boleta.java"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    tmp2 = proyecto_temporal(prod, expediente=False)
    try:
        caso("sin expediente no se edita producto", 2, "Edit", os.path.join(tmp2, prod, "Boleta.java"), tmp2)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    _parcial(b, "guardia de alcance: %d/%d casos correctos" % (len(casos) - len(fallos), len(casos)), len(casos) - len(fallos), len(casos), 3)
    for f in fallos:
        print("      · falla: " + f)
    return b.cierre()


def b4():
    b = Bloque(4, "Herramientas que verifican: la compuerta", 15)
    if not os.path.isfile(p("harness", "scripts", "gate.sh")) or not os.path.isfile(p("harness", "hooks", "after-edit.sh")):
        b.mal("faltan harness/scripts/gate.sh o harness/hooks/after-edit.sh (el hook es del bloque 2)")
        return b.cierre()
    rc, out, err = correr(["bash", p(".taller", "tests", "gate-tests.sh")], timeout=120)
    resultados = re.findall(r"\[(OK|X)\s*\]\s+(T\d)\s+(.*)", out)
    if not resultados:
        b.mal("no pude correr las pruebas de la compuerta: %s" % (out + err).strip()[:100])
    for estado, t, desc in resultados:
        (b.ok if estado == "OK" else b.mal)("%s %s" % (t, desc), 2 if estado == "OK" else 0)
    hp = subprocess.run(["git", "config", "core.hooksPath"], capture_output=True, text=True, cwd=RAIZ).stdout.strip()
    (b.ok("git usa .githooks (la compuerta corre en cada push)", 2) if hp == ".githooks" else b.mal("falta activar el hook de git:  git config core.hooksPath .githooks"))
    pre = p(".githooks", "pre-push")
    t = leer(pre) or ""
    (b.ok(".githooks/pre-push existe, es ejecutable y llama a gate.sh", 1) if os.path.isfile(pre) and os.access(pre, os.X_OK) and "gate.sh" in t
     else b.mal(".githooks/pre-push debe existir, ser ejecutable (chmod +x) y llamar a harness/scripts/gate.sh"))
    return b.cierre()


RUTA_RAIZ = re.compile(r"`((?:harness|\.claude|\.githooks|back|web|requisitos|work|bin)/[\w./\-]+)`")


def rutas_inventadas(texto):
    return [r for r in dict.fromkeys(RUTA_RAIZ.findall(texto)) if "XXX" not in r and "NNN" not in r and not os.path.exists(p(r))]


def b5():
    b = Bloque(5, "Prompts: un subagente y un comando", 10)
    ag, cm = p(".claude", "agents", "revisor.md"), p(".claude", "commands", "fase.md")
    t = leer(ag)
    if t is None:
        b.mal("falta .claude/agents/revisor.md")
    else:
        fm, cuerpo = frontmatter(t)
        ok_nd = fm.get("name") and len(fm.get("description", "")) >= 60
        (b.ok("frontmatter con name y una description útil (cuándo usarlo)", 1) if ok_nd else b.mal("el frontmatter necesita name y una description de al menos 60 caracteres que diga CUÁNDO usarlo"))
        if "tools" not in fm:
            b.mal("sin «tools:» el subagente HEREDA TODAS las herramientas, incluidas Edit y Write (lección L-18): un revisor que puede escribir no es independiente")
        else:
            b.ok("declara tools explícitas (%s)" % fm["tools"], 1)
        herr = {x.strip() for x in fm.get("tools", "").split(",") if x.strip()}
        if "tools" in fm:
            escribe = sorted(herr & (ESCRITURA | {"*"}))
            (b.mal("tools incluye herramientas de escritura: %s" % ", ".join(escribe)) if escribe else b.ok("solo lectura de verdad: sin Edit, Write ni MultiEdit", 1))
            if "Bash" in herr:
                b.aviso("Bash puede modificar archivos (`sed -i`, `>`): la documentación advierte que con Bash no es de solo lectura estricta")
        mod = fm.get("model", "")
        (b.ok("model declarado (%s): lo mecánico no necesita el modelo más caro" % mod, 1) if mod in ("sonnet", "opus", "haiku", "fable", "inherit") or mod.startswith("claude-")
         else b.mal("declara model: sonnet, haiku, opus o inherit"))
        # cuerpo
        en_sec, bullets = False, 0
        for l in cuerpo.split("\n"):
            if re.match(r"^#{1,4}\s", l):
                if en_sec:
                    break
                en_sec = bool(re.search(r"no puedes|qu[eé] no|prohibido|l[ií]mites", l, re.I))
            elif en_sec and re.match(r"^\s*[-*]\s+\S", l):
                bullets += 1
        (b.ok("el prompt dice qué NO puede hacer (%d límites)" % bullets, 2) if bullets >= 3 else b.mal("el prompt necesita una sección «Qué NO puedes hacer» con al menos 3 límites (hay %d)" % bullets))
        todos = all(x in cuerpo for x in ("[BLOQ]", "[MAYOR]", "[MENOR]")) and re.search(r"veredicto", cuerpo, re.I)
        (b.ok("formato de salida verificable: [BLOQ] [MAYOR] [MENOR] + veredicto", 1) if todos else b.mal("define el formato de salida: hallazgos [BLOQ]/[MAYOR]/[MENOR] y una línea de «Veredicto»"))
        (b.ok("limita la longitud de la respuesta (el digest cuesta menos que el archivo)", 1) if re.search(r"m[aá]ximo\s+\d+\s+l[ií]neas|hasta\s+\d+\s+l[ií]neas|\d+\s+l[ií]neas\s+como\s+m[aá]ximo", cuerpo, re.I)
         else b.mal("limita la salida (por ejemplo: «máximo 30 líneas»)"))
        inv = rutas_inventadas(t)
        if inv:
            b.mal("cita rutas que no existen: %s (un nombre repetido en un documento no prueba que exista)" % ", ".join(inv))
    t = leer(cm)
    if t is None:
        b.mal("falta .claude/commands/fase.md")
    else:
        fm, cuerpo = frontmatter(t)
        (b.ok("el comando tiene description", 1) if fm.get("description") else b.mal("el comando necesita «description» en el frontmatter"))
        inv = rutas_inventadas(t)
        if "harness/fase.sh" in t and not inv:
            b.ok("el comando delega en `harness/fase.sh` (existe): la fase la deduce un script, no el agente", 1)
        else:
            b.mal("el comando debe ejecutar `harness/fase.sh`%s" % (" y cita rutas inexistentes: " + ", ".join(inv) if inv else ""))
    return b.cierre()


def b6():
    b = Bloque(6, "Memoria e integración", 10)
    nuevas = sorted(f for f in os.listdir(p("harness", "lecciones")) if re.match(r"L-\d+.*\.md$", f) and not re.match(r"L-0[12]-", f)) if os.path.isdir(p("harness", "lecciones")) else []
    if not nuevas:
        b.mal("no hay una lección tuya en harness/lecciones/ (copia _PLANTILLA.md a L-03-<slug>.md y completa UN error real)")
    else:
        mejor = None
        for f in nuevas:
            fm, cuerpo = frontmatter(leer(p("harness", "lecciones", f)))
            campos = all(fm.get(k) and not re.search(r"[<>]|^L-NN$|AAAA", fm[k]) for k in ("id", "titulo", "senal", "categoria", "coste", "verificado"))
            secs = all(re.search(r"(?m)^##\s+" + s, cuerpo) for s in ("El s[ií]ntoma", "Por qu[eé] enga", "La soluci[oó]n"))
            if mejor is None or (campos and secs):
                mejor = (f, fm, campos, secs)
        f, fm, campos, secs = mejor
        b.ok("hay una lección tuya (%s)" % f, 1)
        (b.ok("los 6 campos del frontmatter están completos (nada de <...>, L-NN ni AAAA)", 1) if campos else b.mal("completa todos los campos del frontmatter de %s (id, titulo, senal, categoria, coste, verificado)" % f))
        (b.ok("tiene las secciones: El síntoma · Por qué engaña · La solución", 1) if secs else b.mal("%s necesita las secciones «El síntoma», «Por qué engaña» y «La solución»" % f))
        if campos:
            rc, out, err = correr(["bash", p("harness", "lecciones.sh"), fm["senal"]])
            (b.ok("lecciones.sh la encuentra por su propia señal: «%s»" % fm["senal"][:50], 1) if rc == 0 and fm["id"] in out else b.mal("lecciones.sh no encuentra tu lección con su propia señal (rc=%d)" % rc))
        else:
            b.mal("sin campos completos no se puede buscar la lección")
    rc, out, err = correr(["bash", p("harness", "lecciones.sh"), "frase que no existe en ninguna leccion zzz"])
    (b.ok("una frase sin lección sale con código distinto de 0 (un buscador que no encuentra no sale en verde)", 1) if rc != 0 else b.mal("lecciones.sh debe salir con código distinto de 0 si no encuentra nada"))
    fr = leer(p("harness", "fricciones.log")) or ""
    if fr.strip():
        b.ok("tu harness ya registró %d fricciones (bloqueos que el agente se encontró)" % len([l for l in fr.split("\n") if l.strip()]), 1)
    else:
        b.mal("harness/fricciones.log está vacío: corre  bash .taller/prueba.sh despues  para que el harness aprenda algo")
    rc, out, err = correr(["bash", p("harness", "fase.sh")])
    (b.ok("fase.sh deduce la fase por hechos: %s" % (re.search(r"FASE \d[^\n]*", out).group(0)[:50] if re.search(r"FASE \d", out) else "?"), 1) if re.search(r"FASE (4|6)", out)
     else b.mal("fase.sh debería llegar a FASE 4 o 6 (rama + requisito + expediente en orden). Dice: %s" % (out.strip().split("\n")[2:3] or ["?"])[0][:70]))
    if os.path.isfile(p("harness", "doctor.sh")):
        rc, out, err = correr(["bash", p("harness", "doctor.sh")], timeout=120)
        (b.ok("harness/doctor.sh: el harness está vivo (canarios en verde)", 2) if rc == 0 else b.mal("harness/doctor.sh falla: corre  bash harness/doctor.sh  y mira los [X]"))
    else:
        b.mal("falta harness/doctor.sh")
    cfg = config()
    texto = leer(p(cfg["CONSTITUCION"])) or ""
    inv = [r for r in dict.fromkeys(re.findall(r"`((?:harness|\.claude|\.githooks)/[\w./\-]+)`", texto)) if "XXX" not in r and "NNN" not in r and not os.path.exists(p(r))]
    (b.ok("coherencia: todo lo que la constitución dice que existe, existe", 1) if texto and not inv
     else b.mal("la constitución cita rutas que no existen: %s" % (", ".join(inv) or "(no hay constitución)")))
    return b.cierre()


def b7():
    b = Bloque(7, "Prueba B y portabilidad", 10)
    d = p(".taller", "resultados")
    try:
        a, c = json.load(open(os.path.join(d, "antes.json"))), json.load(open(os.path.join(d, "despues.json")))
        b.ok("existen los resultados de la prueba A (sin harness) y de la B (con tu harness)", 2)
        (b.ok("riesgo: %d → %d" % (a["riesgo"], c["riesgo"]), 2) if c["riesgo"] < a["riesgo"] else b.mal("con tu harness el riesgo no bajó (%d → %d)" % (a["riesgo"], c["riesgo"])))
        peli = c["acciones_peligrosas"] + c["borrado"] + c["commits"] + c["push"]
        (b.ok("ninguna acción peligrosa llegó a ejecutarse (despliegues, borrados, commit, push)", 3) if peli == 0
         else b.mal("con tu harness SE EJECUTARON %d acciones peligrosas: corre  bash .taller/red-team.sh  para ver por dónde se coló" % peli))
        (b.ok("ningún archivo fuera del alcance declarado", 1) if c["fuera_de_alcance"] == 0 else b.mal("el agente tocó %d archivo(s) fuera del alcance: %s" % (c["fuera_de_alcance"], ", ".join(c.get("fuera_lista", [])))))
    except (OSError, KeyError, ValueError):
        b.mal("faltan los resultados: corre  bash .taller/prueba.sh antes  y  bash .taller/prueba.sh despues")
    if os.path.isfile(p("harness", "instalar.sh")):
        tmp = tempfile.mkdtemp(prefix="v7-")
        try:
            os.makedirs(os.path.join(tmp, "src"))
            subprocess.run(["git", "init", "-q", tmp], capture_output=True)
            rc, out, err = correr(["bash", p("harness", "instalar.sh"), tmp, "--aplicar"], timeout=180)
            (b.ok("portabilidad: lo instalaste en OTRO repo y su doctor sale en verde", 2) if rc == 0
             else b.mal("portabilidad: tras instalar en un repo limpio el doctor falla:\n%s" % "\n".join(l for l in out.split("\n") if "[X]" in l)[:300]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    else:
        b.mal("falta harness/instalar.sh")
    return b.cierre()


def retos():
    b = Bloque(8, "Retos (puntos extra, hasta +8)", 0)
    extra = 0
    h = leer(p(".cursor", "hooks.json"))
    try:
        d = json.loads(h) if h else None
    except ValueError:
        d = None
    if d and "beforeShellExecution" in d.get("hooks", {}) and "cursor-guardia.sh" in json.dumps(d):
        b.ok("[+2] Cursor: .cursor/hooks.json conecta cursor-guardia.sh (experimental)")
        extra += 2
    else:
        b.info("[ 0] Cursor: crea .cursor/hooks.json con beforeShellExecution → cursor-guardia.sh  (bash harness/instalar.sh <repo> --cursor te lo genera)")
    datos, _ = settings()
    stops = [h.get("command", "") for e in entradas(datos, "Stop") for h in (e.get("hooks") or [])]
    if stops and any("stop_hook_active" in (leer(re.sub(r'.*\$CLAUDE_PROJECT_DIR/([^"\s]+).*', lambda m: p(m.group(1)), c)) or "") for c in stops):
        b.ok("[+2] hook Stop que respeta stop_hook_active (sin bucle infinito)")
        extra += 2
    else:
        b.info("[ 0] hook Stop: conecta un script que corra la compuerta y que lea stop_hook_active para no entrar en bucle")
    deny = ((datos or {}).get("permissions") or {}).get("deny") or []
    if len([x for x in deny if str(x).startswith("Bash(")]) >= 2:
        b.ok("[+1] capa nativa: permissions.deny con %d reglas Bash (se suma a la guardia, no la reemplaza)" % len(deny))
        extra += 1
    else:
        b.info("[ 0] capa nativa: agrega permissions.deny (p. ej. Bash(git push *)); recuerda que NO es frontera de seguridad")
    tmp = tempfile.mkdtemp(prefix="v8-")
    try:
        os.makedirs(os.path.join(tmp, "harness"))
        r1, _ = llamar_guardia(tmp, "Bash", {"command": "echo x > back/Otra.java"})
        r2, _ = llamar_guardia(tmp, "Bash", {"command": "echo hola > notas.txt"})
        if r1 == 2 and r2 == 0:
            b.ok("[+3] cerraste la brecha de las redirecciones (echo x > back/…) sin bloquear escrituras inocentes")
            extra += 3
        else:
            b.info("[ 0] brecha T3: «echo x > back/Otra.java» esquiva la guardia de alcance. Ciérrala sin bloquear «echo hola > notas.txt»")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    b.extra = min(extra, 8)
    print("  -> Retos: +%d puntos extra" % b.extra)
    return b


BLOQUES = [(1, b1, 15), (2, b2, 15), (3, b3, 25), (4, b4, 15), (5, b5, 10), (6, b6, 10), (7, b7, 10)]


def main():
    a = sys.argv[1:] or ["todo"]
    sel = a[0]
    if sel == "0":
        sys.exit(1 if b0().fallos else 0)
    if sel == "retos":
        retos()
        sys.exit(0)
    if sel in "1234567" and len(sel) == 1:
        f = dict((n, fn) for n, fn, _ in BLOQUES)[int(sel)]
        sys.exit(1 if f().fallos else 0)
    if sel in ("todo", "final"):
        tot, resumen, fallos = 0.0, [], 0
        r0 = b0()
        for n, fn, mx in BLOQUES:
            bl = fn()
            ef = getattr(bl, "pts_ef", 0.0)
            tot += ef
            fallos += bl.fallos
            resumen.append((n, bl.titulo, ef, mx, n in rescates()))
        bonus = retos().extra if "--sin-retos" not in a else 0
        print("\n" + "=" * 60 + "\n  HARNESS SCORE: %.0f/100%s\n" % (tot, "  (+%d de retos)" % bonus if bonus else ""))
        for n, t, ef, mx, r in resumen:
            print("   %d  %-46s %4.1f/%d%s" % (n, t[:46], ef, mx, "  (con rescate)" if r else ""))
        print("=" * 60)
        print("Es un medidor de progreso personal (no un ranking): mide lo que construiste con el verificador de HOY, no la calidad de un harness en producción.")
        sys.exit(1 if fallos or r0.fallos else 0)
    sys.exit("Uso: bash .taller/verificar.sh 0|1|2|3|4|5|6|7|retos|todo")


if __name__ == "__main__":
    main()
