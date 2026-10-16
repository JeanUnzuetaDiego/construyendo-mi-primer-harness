# Cómo trabajamos aquí (la lista de instrucciones que teníamos)

Este proyecto calcula planillas: un error de cálculo es una contingencia, no un bug.
Usamos Java 21 y React. Cada cambio nace de un requisito (`requisitos/`) y se hace en una rama
`feat/RF-XXX-NNN-…`.

Reglas:
1. El dinero va en `BigDecimal`, nunca en `double` ni `float`.
2. No uses `System.out.println`: usa el logger. En web, no dejes `console.log`.
3. No escribas tasas ni porcentajes en el código: salen de configuración.
4. No hagas commit ni push sin permiso explícito. Nada se despliega sin que una persona lo apruebe.
5. Solo se toca lo que el requisito declara (`## Fase 3` del expediente en `work/`).
6. Escribe nombres claros.

> Esto es solo texto. Tu trabajo en el bloque 1 es convertirlo en una constitución que el agente pueda
> seguir, y en los bloques siguientes, hacer que lo importante **se cumpla** sin depender de que se recuerde.
