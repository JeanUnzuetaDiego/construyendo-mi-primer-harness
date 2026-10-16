# Dinero y tasas (se abre solo cuando el cambio toca importes)

- Todo importe es `BigDecimal`. Se redondea una sola vez, al final, con `setScale(2, RoundingMode.HALF_UP)`.
- Una tasa (AFP, impuesto, bono) **nunca** se escribe en el código: sale de configuración y por la fecha del período.
- Si el requisito no dice cuál es la tasa, no la inventes: pregunta a la persona y deja la pregunta escrita.
- Un neto negativo no se emite: el sistema rechaza la boleta y muestra el motivo.
