# Contrato del executor System One

Fuente: https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision

## Petición y autenticación
POST al endpoint completo definido en decision/executor.toml, sin añadir /responses.
Content-Type: application/json. API key: cabecera api-key, desde una variable de entorno.
Alternativa: Authorization: Bearer para un token Entra obtenido por el usuario.
No se inicia sesión ni se adquieren tokens automáticamente.

El cuerpo contiene model (nombre del despliegue configurado), state (texto u objeto JSON)
y questions (objeto no vacío con identificadores de preguntas). Analysis produce
.artifacts/input.json con state y questions, sin model ni secretos; .artifacts/input.md explica contexto,
evidencias y correspondencia con las preguntas.

Cada pregunta contiene instructions no vacío y type:
- choice: criteria es un objeto de al menos dos alternativas descritas con texto.
- score: criteria es una lista ordenada de al menos dos niveles descritos con texto.
- noul: criteria es opcional; si se usa, define las claves true y false con texto.

La validación local rechaza claves desconocidas de entrada, tipos incorrectos y JSON
con claves duplicadas o números no finitos. No inventar evidencia ni opciones para forzar
una pregunta abierta al formato acotado del modelo.

## Respuesta
JSON con answers indexado por las preguntas enviadas. Cada respuesta es un objeto con
type coincidente; en choice, choice debe pertenecer a las alternativas enviadas.
Los demás campos del proveedor se conservan sin renombrarlos. No exigir nombres de
campos de probabilidades que la documentación no haya establecido.
model en la respuesta puede diferir del despliegue solicitado. Las respuestas no incluyen
justificación escrita. Las probabilidades no son garantías de viabilidad o éxito.

## Persistencia y errores
.artifacts/request.json conserva la petición transmitida sin cabeceras; .artifacts/response.json conserva
los bytes originales de la respuesta validada; .artifacts/execution.md incluye hashes y JSON legible.
Si las entradas cambian durante la llamada, no reemplazar la ejecución anterior.
400/422: preguntas/despliegue. 401/403: credenciales/permisos. 404: endpoint/despliegue.
429: cuota/límite. 5xx: servicio. Red, timeout o protocolo inválido: bloqueo sin reintento
automático. Conservar la ejecución anterior y no mostrar cuerpos de error privados.
Rechazar redirecciones HTTP para no reenviar credenciales a otro endpoint.


Validación numérica: noul debe estar entre 0 y 1. Choice requiere distribución completa
de sus alternativas. Score usa índices 0..N-1 y promedio ponderado por la distribución.
Se rechazan booleanos, valores no finitos, probabilidades fuera de 0..1, distribuciones
incompletas o que no sumen 1 y score inconsistente (tolerancia absoluta 1e-5).
confidence se valida si existe, sin exigirlo ni derivarlo de otros campos.
