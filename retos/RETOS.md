# Retos — para quien termina antes, y para llevarse a casa

Cada reto suma **puntos extra** (hasta +8 en total) si se puede comprobar con un comando:  `bash .taller/verificar.sh retos`.
Los retos sin verificador están marcados «sin comprobador»: se discuten con la pareja o con la sala.

| # | Bloque | Reto | Puntos | Cómo se comprueba |
|---|---|---|---|---|
| R1 | 1 · Contexto | **Presupuesto duro.** Baja la constitución a ≤ 1 500 B sin perder ninguna regla ni a su responsable: mueve ejemplos a `harness/contexto/`. | — | pon `PRESUPUESTO_BYTES=1500` en `harness/config.env` y corre `verificar.sh 1` |
| R2 | 2 · Observar | **Hook Stop sin bucle.** Al terminar el turno corre la compuerta; si falla, el agente no termina. Lee `stop_hook_active` para no entrar en bucle. | +2 | `verificar.sh retos` |
| R3 | 2 · Observar | **Cursor.** Conecta `afterFileEdit` y `beforeShellExecution` en `.cursor/hooks.json` (`instalar.sh <repo> --cursor` te lo genera). Ojo: Cursor exige JSON; sin él, **bloquea todo**. | +2 | `verificar.sh retos` |
| R4 | 3 · Bloquear | **Cierra la brecha de las redirecciones.** `echo x > back/Otra.java` esquiva tu guardia de alcance. Ciérrala sin bloquear `echo hola > notas.txt`. | +3 | `verificar.sh retos` |
| R5 | 3 · Bloquear | **La capa nativa.** Agrega `permissions.deny` con reglas `Bash(...)`. Después averigua qué esquivan (`/bin/rm`, `bash -c`) y por qué tu guardia sí lo cubre. | +1 | `verificar.sh retos` |
| R6 | 3 · Bloquear | **Ataca a tu pareja.** Escribe 5 ataques nuevos en `ataques.txt` (uno por línea) y córrelos contra **su** guardia: `bash .taller/red-team.sh ataques.txt`. 1 punto humano por cada brecha. | humano | `red-team.sh` |
| R7 | 3 · Bloquear | **El agente se amplía el alcance.** ¿Cómo impedirías que el agente edite `expediente.md` para agregarse archivos? Diseña la defensa. | — | sin comprobador |
| R8 | 4 · Compuerta | **T7.** Escribe primero la prueba y después haz que la compuerta bloquee un archivo fuera del alcance declarado. | — | tu prueba T7 |
| R9 | 5 · Prompts | **Evalúa tu prompt.** Pídele a tu IA que use tu revisor sobre `.taller/revision/caso/`, pega la salida en un archivo y puntúala. Objetivo: ≥ 9/10 y **cero citas inventadas**. | — | `bash .taller/puntuar-revision.sh <archivo>` |
| R10 | 6 · Memoria | **De fricciones a issues.** Escribe `harness/fricciones-a-issues.sh`: agrupa `fricciones.log` por regla y **imprime** el texto de un issue por regla (no crea nada). | — | sin comprobador |
| R11 | 7 · Prueba B | **Agente real, presión alta.** `bash .taller/prueba.sh preparar despues --agresivo`, pega la tarea en tu agente y mide con `medir-real`. Compara con la corrida simulada. | — | `prueba.sh comparar-real` |
| R12 | Cierre | **CI.** Escribe `.github/workflows/harness.yml` que corra `bash harness/doctor.sh` en cada pull request (no lo ejecutes: solo escríbelo). | — | sin comprobador |

## Pistas

- **R2:** el hook recibe `{"stop_hook_active": true}` cuando Claude Code ya está continuando por un Stop. Si lo ignoras, el agente no puede terminar nunca (Claude Code corta a la octava vez).
- **R3:** en Cursor, `beforeShellExecution` espera `{"permission": "allow"|"deny"|"ask", ...}` por stdout. ¿Qué pasa si tu script no imprime nada?
- **R4:** los tokens `>` y `>>` aparecen como piezas sueltas cuando se parte la orden con `shlex`. Mira también `tee` y `sed -i`.
- **R5:** `Bash(rm *)` bloquea `rm -rf build/` pero **no** `/bin/rm -rf build/` ni `bash -c 'rm -rf build/'`. Está en la documentación de permisos de Claude Code.
- **R9:** si tu IA cita un archivo o una línea que no abrió, el script lo cuenta como cita inventada. El arreglo está en el prompt: «cita solo lo que abriste».

> Las soluciones de referencia de los retos están en la versión del instructor (`soluciones/retos/`).
