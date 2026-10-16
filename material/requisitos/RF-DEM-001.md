# RF-DEM-001 — Emitir la boleta de un trabajador

**Historia:** Como analista de planilla, quiero emitir la boleta de un trabajador para
entregársela al cierre del período.

## Criterios de aceptación

**Escenario 1 — Emisión correcta**
Dado un trabajador con neto calculado
Cuando emito su boleta
Entonces la boleta muestra el neto con dos decimales

**Escenario 2 — Neto negativo**
Dado un trabajador cuyo cálculo da neto negativo
Cuando emito su boleta
Entonces el sistema rechaza la emisión y muestra el motivo

**Escenario 3 — Boleta ya emitida**
Dado un trabajador con boleta emitida en el período
Cuando intento emitirla otra vez
Entonces el sistema no genera una segunda boleta

## Fuera de alcance

- Envío de la boleta por correo.
- Firma digital de la boleta.
