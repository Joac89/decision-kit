---
name: spec-decision-analysis
description: Analiza coherencia y prepara state y preguntas de decisión, con validación semántica y técnica antes de ejecutar Decision-1.
---

# Analysis: preparación antes de ejecutar
Lee [el contrato compartido](../spec-decision/references/contract.md) y
[System One](../spec-decision/references/systemone.md).
Entrada obligatoria: context.md vigente. research.md se usa si se hizo research y sigue vigente.
Aplica research.mode y el criterio de suficiencia del contrato compartido. Esta etapa prepara la consulta;
no interpreta una respuesta ya recibida: para eso usa spec-decision-report.

## Coherencia y cobertura
Identifica cada decisión D01... y las alternativas relevantes. Mapea cada pregunta Q...
a una decisión, criterio, evidencias E... y finalidad. Comprueba que no haya requisitos
contradictorios, alternativas incomparables, escalas ambiguas ni evidencia inventada.
Distingue verificar si hay evidencia de viabilidad de evaluar la viabilidad misma.
Evita preguntas cuya conclusión esté sugerida por opciones desbalanceadas. Una abstención
debe significar evidencia insuficiente, no inviabilidad de todas las alternativas.

## Preparación de entrada
Genera .artifacts/input.md y .artifacts/input.json. state incluye contexto, alternativas, restricciones,
evidencias suficientes, supuestos y vacíos; el modelo no verá los archivos del proyecto.
questions contiene preguntas acotadas choice, noul o score. El JSON tiene solo state y
questions; execute añade model. No pidas prosa ni razones al modelo.
Para comparar alternativas por criterios, prepara scoring donde exista evidencia suficiente;
define preguntas score con niveles
ordenados y significados operativos antes de ejecutar. Declara escala, sentido favorable
y qué se puntúa; si hace falta, formula una pregunta por combinación alternativa/criterio.
Identifica las rúbricas propuestas por el LLM y su fundamento; no inventes mediciones
para completarlas. Si faltan datos determinantes, pregunta o declara el criterio no evaluable.
No inventes pesos ni una fórmula global. Documenta agregación solo si está acordada;
no promedies escalas heterogéneas ni conviertas probabilities/confidence en notas.
Si solo se plantean choice/noul, declara expresamente que no habrá scoring por criterio.

## Entregable y validación
.artifacts/input.md incluye inventario de decisiones, tabla Q -> D/criterio/tipo/fuentes, hipótesis
true/false o alternativas, escalas, pesos/fórmula si existen y revisión de coherencia.
Antes de validar, registra las fuentes realmente usadas con
decision/scripts/provenance.py --case <caso> --research used|omitted.
Hazlo solo después de revisar que state y preguntas reflejan esas fuentes: no actualices
el manifiesto para hacer pasar una ejecución anterior. Incluye las fuentes originales
en el inventario de evidencia; las huellas verifican context/research y la entrada preparada.
Ejecuta decision/scripts/execute.py --case <caso> --dry-run, resolviendo el script desde
CODEX_HOME y usando el shell actual. Esa validación no envía nada ni prueba conectividad.
No marques preparada una entrada con errores determinantes. No ejecutes la consulta.
Actualiza el estado actual sin crear historia de .artifacts/status.md. Si se alteró cualquiera
de los dos archivos de entrada, invalida execute y report.

## Paso directo desde context
En auto, si el contexto ya contiene la evidencia necesaria, prepara y valida la entrada
sin exigir research. Registra «research omitida: <motivo>» y las fuentes utilizadas.
En required no omitas investigación. En skip o ante una instrucción de omitirla, no la
ejecutes por tu cuenta: explicita límites y pregunta solo por vacíos determinantes.
No crees un research.md vacío ni reutilices uno desactualizado para simular la etapa.
