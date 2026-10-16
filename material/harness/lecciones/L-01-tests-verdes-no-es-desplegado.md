---
id: L-01
titulo: Que los tests pasen no significa que esté desplegado
senal: "los tests están verdes, esto ya está"
categoria: proceso
coste: alto
verificado: 2026-10-16
---

## El síntoma

Compila, los tests pasan y el cambio «está listo»… pero en el ambiente real falla.

## Por qué engaña

Los tests corren en tu máquina, con tu configuración. El ambiente real tiene otra (URLs, variables,
permisos). El verde prueba el código, no el despliegue.

## La solución

Ejecutar el flujo de punta a punta en el ambiente destino antes de darlo por terminado.

## Cómo compruebo que quedó bien

Corro el caso real —no el test— y veo el resultado en el ambiente.
