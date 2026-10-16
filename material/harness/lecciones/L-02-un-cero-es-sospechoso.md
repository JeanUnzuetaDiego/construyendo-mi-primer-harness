---
id: L-02
titulo: Un cero es la respuesta que más hay que dudar
senal: "la consulta devolvió cero, entonces no hay datos"
categoria: medicion
coste: alto
verificado: 2026-10-16
---

## El síntoma

Una consulta dice «cero» y se afirma en un informe que no existe nada. Después aparecen 42.

## Por qué engaña

Casi siempre un cero significa que la consulta no está mirando donde crees: un filtro mal puesto, un
join que esconde justo lo que buscas.

## La solución

Antes de creerle a un cero, medir lo mismo por otro camino (un conteo directo).

## Cómo compruebo que quedó bien

Dos formas distintas de medir dan la misma cifra.
