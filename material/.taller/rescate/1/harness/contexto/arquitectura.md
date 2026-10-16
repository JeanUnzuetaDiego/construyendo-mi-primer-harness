# Arquitectura (se abre solo cuando tocas código)

- `back/` — Java 21. Una clase por concepto de negocio (`Liquidacion`, `Boleta`). Sin lógica en los constructores.
- `web/` — TypeScript estricto: `any` está prohibido; si no sabes el tipo, defínelo o pregunta.
- `requisitos/` — qué hay que construir. Cada cambio nace de un `RF-XXX-NNN` y va en una rama `feat/RF-XXX-NNN-…`.
- `work/RF-XXX-NNN/expediente.md` — el alcance declarado (`## Fase 3`) y los criterios de aceptación (`## Fase 2`).
- `bin/` — herramientas de operación. **Las usa una persona**, no el agente.
