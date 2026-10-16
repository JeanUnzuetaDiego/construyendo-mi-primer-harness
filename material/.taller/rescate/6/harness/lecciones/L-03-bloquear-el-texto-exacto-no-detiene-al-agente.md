---
id: L-03
titulo: Bloquear el texto exacto no detiene a un agente que reintenta: la misma intención vuelve con otra forma
senal: "ya bloqueé git push, el agente ya no puede subir nada"
categoria: herramientas
coste: alto
verificado: 2026-10-16
---

## El síntoma

Escribes una guardia para «git push» y la pruebas con «git push»: bloquea. Pero en el registro de fricciones cada
acción peligrosa aparece 3 o 4 veces seguidas: el agente prueba «git  push», «bash -c "git push"», «sudo git push»…
La intención es la misma; la forma cambia.

## Por qué engaña

Una guardia que busca texto cubre la forma que tú imaginaste. Un agente que quiere completar la tarea es
persistente: si lo frenan, prueba otra forma de decir lo mismo. Y un grep ingenuo, además, bloquea lo legítimo
(`echo "git push"` no ejecuta nada). El fallo es doble: deja pasar lo malo y bloquea lo bueno.

## La solución

Mirar la POSICIÓN del comando (qué se ejecuta), no el texto; desenvolver `sudo`, `env`, `bash -c` y `$(…)`; y probar
la guardia con un corpus de ataques (`bash .taller/red-team.sh`) antes de confiar en ella. Y no depender de una sola
capa: permisos, sandbox y protección de ramas la complementan.

## Cómo compruebo que quedó bien

`bash .taller/red-team.sh` → T1 y T2 completos y 0 falsos positivos.
