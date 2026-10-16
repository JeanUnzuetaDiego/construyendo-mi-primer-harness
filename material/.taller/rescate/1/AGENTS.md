# mi-primer-harness — constitución del agente

Sistema de planillas en miniatura (Java 21 + React). Un error de cálculo es una contingencia, no un bug.
Trabajas con una persona que decide: tú propones, el harness verifica, la persona aprueba.

## No puedes
- Hacer commit ni push sin el permiso explícito de una persona. Entregas el mensaje de commit, no el commit.
- Desplegar ni ejecutar nada destructivo (`bin/deploy.sh`, `bin/kubectl`, `bin/db-reset.sh`, `rm -rf`).
- Editar código de producto (`back/`, `web/`) fuera del alcance declarado en `work/RF-XXX-NNN/expediente.md`.
- Inventar un requisito, una ruta, una regla de negocio o una tasa: si no lo encuentras, pregunta.
- Dar algo por terminado sin haber corrido la compuerta (`bash harness/scripts/gate.sh`).

## Invariantes — quién las hace cumplir
| Regla | La hace cumplir |
|---|---|
| El dinero va en `BigDecimal`, nunca en `double` ni `float` | `harness/hooks/after-edit.sh` |
| Nada de `System.out` ni `console.log` | `harness/hooks/after-edit.sh` |
| Ninguna tasa escrita en el código | `harness/hooks/after-edit.sh` |
| Sin commit, push, despliegue ni borrado sin permiso | `harness/hooks/guardia.sh` |
| Solo se edita lo que el expediente declara | `harness/hooks/guardia.sh` |
| Nada sale con la compuerta en rojo | `harness/scripts/gate.sh` |
| Los nombres son claros | texto |

## Dónde buscar (se abre solo cuando hace falta)
- Cómo está organizado el código: `harness/contexto/arquitectura.md`
- Reglas de dinero y de tasas: `harness/contexto/dinero.md`
- En qué fase estás: `bash harness/fase.sh` · Errores ya cometidos: `bash harness/lecciones.sh "<tu frase>"`
