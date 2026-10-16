---
name: spec-decision
description: Coordina cinco etapas de decisión sobre documentos del proyecto y entrega detalle e insights con resultados trazables.
---

# Método de decisiones
Lee [el contrato compartido](references/contract.md) y
$CODEX_HOME/decision/settings.toml. Retoma el caso existente antes de crear uno nuevo.

| Etapa | Skill hermana | Salida |
|---|---|---|
| Interpretar | ../spec-decision-context/SKILL.md | context.md |
| Investigar (opcional) | ../spec-decision-research/SKILL.md | research.md |
| Analizar y preparar | ../spec-decision-analysis/SKILL.md | .artifacts/input.md y .artifacts/input.json |
| Ejecutar | ../spec-decision-execute/SKILL.md | .artifacts/execution.md y JSON originales |
| Exportar | ../spec-decision-report/SKILL.md | insights.md, report.md y analysis.md |

Lee cada skill al llegar a su etapa. Una petición general sigue el flujo; una invocación
individual respeta su alcance y verifica dependencias. No interpretes report como nueva
llamada a Decision-1. Si ya hay ejecución válida y se pide mejorar los reportes, ve a report.
Si cambian contexto o investigación, invalida las etapas posteriores. Si cambia la entrada,
no reutilices una respuesta anterior. En modo step_by_step entrega una etapa y espera.
En modo continuous continúa mientras haya datos suficientes y no exista un bloqueo.
Ruta rápida: context -> analysis -> execute -> report cuando la investigación adicional
no es necesaria o el usuario la omite. No conviertas la ausencia de research.md en
un bloqueo automático. Aplica los criterios y límites de research.mode del contrato.
Al crear un caso copia assets/README.md y sigue la organización del contrato compartido.
