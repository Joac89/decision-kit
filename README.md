# Decision Kit

Workflows de decisiones asistidas por IA con Microsoft Decision-1. Convierte el
contexto de un proyecto en recomendaciones trazables e insights accionables.

Versión inicial: Python 3.11 o posterior; integración con Codex. El núcleo llama
directamente a la API con configuración explícita. OpenCode y otras herramientas
todavía no están integrados ni verificados.

## Instalación

Desde este repositorio:

```powershell
python -m pip install .
decision-kit install --target "$HOME/.codex"
```

Instala recursos en `decision/` y los seis skills en `skills/`. No modifica el
perfil, la configuración base ni los permisos de red. Los skills instalados en
un home compartido pueden estar disponibles en otros perfiles; usa un home
aislado si deseas limitar su descubrimiento.

Para crear además un perfil Codex mínimo y opcional:

```powershell
decision-kit install --target "$HOME/.codex-decision" --profile
$env:CODEX_HOME = "$HOME/.codex-decision"
codex -p decision
```

El perfil no configura proveedor ni claves del modelo principal; esa configuración
es del usuario. Nunca sobrescribe un perfil existente. Si tu Codex restringe la red,
habilítala mediante sus permisos admitidos o solicita aprobación. Una política
administrada requiere intervención del administrador; el kit no la elude.

## Conexión a Decision-1

```powershell
decision-kit configure --home "$HOME/.codex-decision" --endpoint "https://YOUR-RESOURCE.services.ai.azure.com/providers/microsoft/v1/systemone" --deployment "YOUR-DEPLOYMENT" --credential-env DECISION_API_KEY
```

Define `DECISION_API_KEY` en el entorno que ejecuta el kit. No pases la clave como
argumento ni la guardes en el repositorio. Se admite una credencial persistente
de usuario en Windows. TLS se verifica por defecto.

La configuración explícita permite usar el núcleo sin perfil ni variables de Codex:

```powershell
decision-kit diagnose --case ./decision/my-case --config "$HOME/.codex-decision/decision/executor.toml"
```

La carpeta del caso debe existir. El diagnóstico no envía claves ni decisiones.
Un HTTP 401 indica conectividad, no autenticación válida. Ejecútalo también dentro
de Codex para comprobar sus permisos efectivos: que funcione en PowerShell no
garantiza acceso desde el sandbox.

## Uso con Codex

En la carpeta del proyecto, solicita `spec-decision` y describe qué necesitas decidir.
También puedes invocar una etapa:

`spec-decision-context` → `spec-decision-research` (opcional) →
`spec-decision-analysis` → `spec-decision-execute` → `spec-decision-report`.

El skill analysis prepara la entrada y registra procedencia. El ejecutor verifica
fuentes y contrato antes de consultar al proveedor. Report genera:

- `insights.md`: decisiones, porcentajes interpretables e implicaciones de negocio/técnicas.
- `report.md`: recomendación y resultados cuantitativos.
- `analysis.md`: detalle y fundamento.

El caso incluye además `context.md`, investigación opcional y README. Estado,
petición, respuesta original, procedencia y logs quedan en `.artifacts/`.

Cambiar una condición requiere revisar las etapas afectadas. Mejorar el texto de
los reportes no requiere otra llamada. Los porcentajes no garantizan éxito real.
Las ejecuciones antiguas sin procedencia no se declaran vigentes retroactivamente.

## CLI sin agente

El CLI ejecuta o verifica una entrada ya preparada; no genera documentos con un LLM:

```powershell
decision-kit prepare --case ./decision/my-case --research omitted
decision-kit execute --case ./decision/my-case --config ./executor.toml --dry-run
decision-kit execute --case ./decision/my-case --config ./executor.toml
decision-kit verify --case ./decision/my-case
```

`prepare` registra huellas: debes comprobar antes que el input refleja contexto y
evidencia. No certifica coherencia semántica por sí solo. `--config` explícito es una
elección directa de conexión; no usa el interruptor `execution.ready` del adaptador.
Los scripts instalados sin `--config` conservan ese interruptor en settings.toml.

## Actualización

```powershell
decision-kit update --target "$HOME/.codex-decision"
```

Preserva executor.toml, settings.toml y perfiles; respalda los recursos reemplazados.
Si un recurso gestionado fue modificado, se detiene para evitar perder cambios.
No adopta automáticamente instalaciones anteriores que no tengan su manifiesto.
Las migraciones de esas instalaciones se revisan por separado.

## Desarrollo y comprobación

```powershell
python -m unittest discover -s tests -v
python -m pip wheel --no-deps --no-build-isolation . --wheel-dir dist
```

Las pruebas usan transporte simulado, no claves ni llamadas facturables. El
repositorio contiene solo recursos genéricos; no incluye casos privados.
