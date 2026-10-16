---
name: spec-decision-execute
description: Ejecuta preguntas de decisión en la API System One y conserva el JSON original con trazabilidad.
---

# Executor
Lee [el contrato compartido](../spec-decision/references/contract.md) y
[el contrato System One](../spec-decision/references/systemone.md).
Entradas vigentes: .artifacts/input.md y .artifacts/input.json. Lee execution en settings.toml y la
conexión indicada en execution.config, relativa a CODEX_HOME.
Ejecuta decision/scripts/execute.py --case <ruta-absoluta-del-caso> --dry-run primero.
Resuelve la ruta del script desde CODEX_HOME usando la sintaxis del shell actual
(PowerShell: $env:CODEX_HOME); si no está definido, usa ~/.codex.
Si ready=false o no existe la credencial, registra el bloqueo sin inventar una salida.
Cuando esté configurado, ejecuta el mismo script sin --dry-run. Usa la aprobación de
red que requiera el entorno; no desactives sandbox ni omitas controles del proyecto.
No crees subagentes ni otro proceso Codex para representar a Decision-1.
Verifica código de salida y .artifacts/request.json, .artifacts/response.json y .artifacts/execution.md.
El script conserva el JSON original; no lo resumas ni le agregues razones atribuidas
al modelo. No muestres claves ni cabeceras. Si falla, conserva la ejecución anterior
y marca el bloqueo. Para fallos de red, aplica primero el procedimiento siguiente.

## Permisos y fallos de red
No atribuyas un fallo al sandbox solo por CONNECTION_ERROR, TIMEOUT o conexión rechazada.
Considera indicios explícitos de restricción de red, ACCESS_DENIED o una prueba del mismo
endpoint que funciona en la terminal del usuario y falla dentro del entorno de ejecución.
En esos casos, si el entorno permite solicitar permisos, reintenta el mismo comando una
sola vez mediante el mecanismo de aprobación de la herramienta de terminal
(por ejemplo sandbox_permissions = require_escalated con una justificación de red).
La petición original de ejecutar la consulta permite solicitar esa aprobación sin pedir
al usuario que escriba otra instrucción; no sustituye la aprobación requerida del entorno.
Si el permiso ya está concedido y aplica, úsalo. Si no puede solicitarse, fue denegado o
el reintento vuelve a fallar, conserva el diagnóstico y detente. No cambies proxy, VPN,
firewall, certificados, credenciales ni configuración global para sortear el bloqueo.
No eleves para errores HTTP de autenticación, permisos de Azure, contrato, cuota o
servicio: trata su causa concreta. Fuera de este procedimiento, un nuevo intento debe
estar solicitado; no reintentes en bucle ni aumentes permisos automáticamente.

## Resultado
Si el script devuelve error y diagnostic, muestra ambos objetos completos al usuario
y regístralos en .artifacts/status.md. No sustituyas el diagnóstico por «falló la conexión».
Actualiza el estado y habilita report solo con entradas vigentes y respuesta validada.

## Diagnóstico sin otra consulta
Si el usuario investiga conectividad, usa execute.py --case <caso> --diagnose-network.
No pide credenciales, no envía la decisión y no cambia resultados vigentes.
Los registros quedan en .artifacts/logs/network-*.jsonl del caso. Muestra la ruta network_log
y revisa ruta efectiva, proxy, DNS, TCP y HTTP. Para comparar, el mismo comando debe
ejecutarse dentro del entorno de Codex y desde PowerShell. No atribuyas el error solo
a una variable de sandbox: contrasta las pruebas observadas.
Una ejecución guardada válida puede usarse para report sin nueva llamada. La investigación
del fallo de conexión no invalida esos archivos ni habilita por sí sola un nuevo envío.
