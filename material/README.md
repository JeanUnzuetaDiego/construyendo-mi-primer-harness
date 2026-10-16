# mi-primer-harness

Proyecto de práctica del taller **«Construyendo mi primer Harness»**. No es código real: es un sistema de
planillas en miniatura sobre el que vas a construir, paso a paso, un harness funcional.

- `back/`, `web/` — el producto. `requisitos/` — qué hay que construir (RF-DEM-001).
- `bin/deploy.sh <ambiente>` despliega; `bin/kubectl`, `bin/db-reset.sh`. **Son simulados**: solo dejan
  constancia en `.simulado/acciones.log`, pero para un agente se ven como lo que parecen.
- `harness/` — **lo que vas a construir** (y llevarte). `.taller/` — andamio del taller (no se lleva).

Empieza por `GUIA.md`. Comprueba tu avance con `bash .taller/verificar.sh <bloque>`.
