# Reportes de decisiones

## Información común obligatoria
Ambos documentos deben permitir entender qué se decidió o qué quedó sin resolver.
Abre con la recomendación y el estado (propuesta/aceptada/descartada/condicionada).
Identifica cada decisión D... con pregunta, alternativas y restricciones esenciales.
Conserva el mapeo a los IDs Q originales. En casos antiguos sin IDs D, asígnalos solo
en los reportes y aclara que son organización editorial, no otra consulta al modelo.

Explica el proceso observable: fuentes revisadas, criterios/hipótesis enviados, preguntas,
resultados de Decision-1, contraste del LLM con evidencia y validación humana pendiente.
No lo presentes como una explicación interna del razonamiento de Decision-1.

## Resultados cuantitativos
Para cada pregunta muestra tipo y resultado original, con interpretación delimitada.
- choice: elección, probabilidades de todas las alternativas y confidence si fue devuelta,
  identificada como campo distinto de la probabilidad de la alternativa elegida.
- noul: valor y enunciado exacto de la hipótesis true; no confundir falta de demostración
  con demostración de imposibilidad. No inventar umbral ni calcular un confidence ausente.
- score: puntuación, escala ordinal, etiquetas, sentido favorable y distribución si existe.
  Indica que es una evaluación modelada, no una medición independiente del proyecto.
Si no hubo preguntas score, declara «No se solicitó scoring por criterio» en ambos reportes.
No sustituyas un score ausente por probabilities * 100 ni por confidence * 100.
Si conviertes probabilidades a porcentaje, etiqueta la conversión y redondea de forma
consistente; conserva valores originales de precisión completa en el detalle o en tabla
enlazada al JSON. No confundas probabilidad de una respuesta con probabilidad de éxito.

Agregación: solo con fórmula, pesos acordados, escalas compatibles y tratamiento explícito
de incertidumbres. Distingue cálculos derivados de resultados originales. Si no existe
un método acordado, no produzcas un ranking o nota global inventados.

## analysis.md: detalle completo
Incluye inventario de decisiones y alternativas, metodología y cobertura de preguntas;
todas las respuestas y distribuciones con cifras originales; verificación de hashes;
evidencias por criterio, límites, contradicciones, abstenciones, sensibilidad y escenarios;
interpretación propia del LLM, recomendación por decisión y los datos que la cambiarían.
Si el modelo recibe evidencia incompleta y se le pregunta si algo está demostrado,
explica ese alcance: su respuesta no es corroboración independiente del servicio o precio.

## report.md: resultado ejecutivo autocontenido
Abre con qué se recomienda decidir. Resume cada decisión y todas las preguntas evaluadas
en una tabla con el resultado cuantitativo relevante. Muestra las probabilidades de
alternativas choice de forma compacta, las condiciones noul y los score cuando existan.
Explica en lenguaje claro cómo se llegó a la recomendación, evidencia que la sostiene,
insights, trade-offs, riesgos, vacíos determinantes y siguientes pasos con responsables
propuestos. Debe ser útil sin abrir el detalle; el enlace amplía, no sustituye lo esencial.
Identifica «Resultado de Decision-1» e «Interpretación del LLM» sin duplicar toda la prosa.
No inventes «todo el cuento» atribuido al servicio: escribe tu explicación verificable.


## Lectura ejecutiva de report.md
Empieza con una recomendación clara y una tabla con decisión, alternativas evaluadas,
recomendación y resultado cuantitativo etiquetado. No antepongas metadatos ni metodología.
Una abstención es un resultado: indica qué no se puede decidir todavía.
Después explica brevemente fundamento, insights de Codex, límites y qué cambiaría
la recomendación. Enlaza analysis.md para profundizar sin sustituir lo esencial.

Muestra probabilities y confidence como porcentajes con dos decimales, identificados
por separado. Para noul respeta su contrato: si solo define un valor entre 0 y 1,
etiqueta «valor modelado: X % de la escala 0–1»; no inventes probabilidad de verdad,
confianza ni éxito. Un score solo se normaliza con extremos documentados:
100 * (score - mínimo) / (máximo - mínimo). Identifica fórmula, escala y sentido;
una escala ordinal normalizada no representa porcentaje de cumplimiento ni confianza.
Sin extremos conocidos conserva el score original. No agregues notas globales sin
método y pesos acordados. Guarda precisión completa en analysis.md y response.json.


## Lectura ejecutiva: insights.md
Es el punto de entrada para quien necesita decidir, desde negocio y técnica. Conserva
report.md y analysis.md: este documento los sintetiza, no sustituye sus resultados.
Apunta a una lectura de un minuto (aproximadamente 200–350 palabras, menos si basta).
Abre con qué se recomienda decidir. Si hay varias decisiones, usa una lista breve o
tabla con cada decisión y su recomendación; no ocultes abstenciones ni condiciones.
Explica impacto de negocio, implicaciones técnicas relevantes, qué falta confirmar
y próximo paso. Usa lenguaje comprensible sin exigir conocimiento del método.
Muestra al inicio una tabla breve: decisión, recomendación y respaldo cuantitativo.
Para cada choice incluye el porcentaje de probabilidad asignado a la opción elegida,
con dos decimales y etiqueta comprensible. No lo llames probabilidad de éxito.
Si una recomendación depende de score o noul, usa el resultado pertinente con su
significado y escala en lenguaje simple, conforme al contrato. Nunca inventes un
porcentaje si no existe una conversión válida; indica que no hay porcentaje aplicable.
No confundas confidence, probabilidad de elección ni score; no mezcles ni agregues
esas cifras. Omite resultados contradictorios como respaldo y conserva la limitación.
Añade una sola nota: «Porcentajes asignados por Decision-1 bajo las premisas del caso;
no representan probabilidades de éxito en producción», adaptada si presentas otra escala.
No incluyas IDs D/Q, fórmulas, niveles de scoring, metodología ni distribuciones completas.
El nombre Decision-1 puede aparecer en esa nota de atribución; no exige explicar el método.
No crees nueva evidencia ni cambies la recomendación al resumir. Distingue beneficio
esperado de resultado demostrado y conserva las condiciones que pueden cambiar la decisión.
Termina con enlaces relativos a report.md y analysis.md. Indica el estado humano y
la vigencia en lenguaje simple; una decisión pendiente no se presenta como aprobada.
En iteraciones añade una frase sobre qué cambió y si afecta la recomendación.
Las reglas de tablas cuantitativas completas y precisión de las secciones anteriores
aplican a report.md y analysis.md; no obligan a repetir esas tablas en insights.md.
