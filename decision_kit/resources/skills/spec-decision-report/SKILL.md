---
name: spec-decision-report
description: Interpreta la ejecución de Decision-1 y entrega análisis detallado y resultado ejecutivo con decisiones, scoring, probabilidades e insights.
---

# Report: detalle y resultado
Lee [el contrato compartido](../spec-decision/references/contract.md) y
[las reglas de reportes](../spec-decision/references/reporting.md).
Entradas: context.md, .artifacts/input.md y .artifacts/input.json y los tres archivos de ejecución en .artifacts/ vigentes.
research.md solo es requerido si la entrada evaluada utilizó investigación adicional.
La omisión válida de research no bloquea el reporte; indica la evidencia realmente usada.
Ejecuta decision/scripts/verify_case.py --case <ruta-del-caso> antes de interpretar.
Este verificador no usa red ni necesita clave. Si falla, informa qué comprobar sin
volver a ejecutar Decision-1 ni presentar resultados como vigentes.

Produce TRES documentos: analysis.md con el detalle completo, report.md con
la recomendación y resultados, e insights.md con la lectura ejecutiva de negocio y técnica. En report.md y analysis.md identifica las decisiones evaluadas,
las alternativas, qué se preguntó, resultados cuantitativos y cómo fundamentan la
recomendación. El resultado ejecutivo no puede relegar todas las cifras al detalle.
Preserva IDs y valores originales; explica por separado la interpretación del LLM.
Decision-1 no devuelve razones escritas. No atribuyas argumentos al modelo, ni llames
scoring a una probabilidad. Si no se solicitaron score, dilo en ambos documentos.
Usa las plantillas de ../spec-decision/assets/ como guía, sin rellenar datos inexistentes.
Si la recomendación interpretada difiere de la selección del modelo, explica la
evidencia o restricción que lo justifica. Una recomendación queda propuesta hasta
aceptación expresa. No modifica fuentes, preguntas ni resultados originales.
Archiva solo los reportes reemplazados cuando haya cambios sustantivos; actualiza
.artifacts/status.md sin archivarlo ni acumular un diario de pasos y fallos ya resueltos.

En una iteración, analysis.md explica condición anterior, condición nueva, preguntas
afectadas y efecto sobre la recomendación. report.md resume qué cambió y por qué,
incluyendo si la recomendación se mantiene. Usa evidencia histórica disponible;
si no existe, no reconstruyas resultados anteriores por suposición.
Una ejecución antigua sin procedencia verificable es histórica: no la declares vigente
ni fabriques un manifiesto retroactivo. Explica la limitación y retoma analysis cuando
el usuario quiera reevaluar. No hagas una llamada adicional para un cambio editorial.

Genera también insights.md según la sección «Lectura ejecutiva» de reporting.md.
Se basa en la misma ejecución y recomendación; no requiere otra llamada ni otra skill.
Mantén los tres documentos coherentes y señala si son históricos o están desactualizados.
Al invalidar report, invalida también insights.md. Si solo se solicita la síntesis,
reutiliza report/analysis verificados y limita los cambios a insights.md y su enlace.
En cada iteración resume en insights.md si cambió la decisión y la razón práctica.
Actualiza README.md para que su primer enlace sea insights.md una vez generado.
