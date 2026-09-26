# Errata v1.1 - Especificación de Requerimientos de Software (SRS)

**Documentos base:** SRS v1.0 (25 de mayo de 2026) y VFP (propuesta aprobada)  
**Fecha:** 26 de septiembre de 2026  
**Destinatarios:** Directores del proyecto

Esta errata registra dos correcciones sobre la línea base. La primera ajusta el conjunto de familias de modelos que compara el benchmark y modifica el objetivo general, por lo que requiere aprobación de los directores. La segunda revierte una decisión anterior sobre el tratamiento de registros duplicados y adopta el contrato vigente de la ingesta. Los textos de la línea base se citan de forma literal.

## 1. Conjunto de familias de modelos del benchmark

| Campo | Detalle |
| :--- | :--- |
| Referencias | RF-MOD-02, RF-MOD-03, ED-05 y objetivo general (VFP §1.2.1). |
| Texto vigente | RF-MOD-02: «El sistema debe ejecutar modelos de la familia de modelos híbridos (p. ej., Prophet) sobre cada serie de tiempo del portafolio.» RF-MOD-03: «El sistema debe ejecutar modelos de aprendizaje profundo global (p. ej., LSTM, N-BEATS, N-HITS) sobre cada serie de tiempo bajo entrenamiento local.» ED-05 enumera `estadisticos_clasicos`, `hibridos`, `aprendizaje_profundo_global` y `fundacionales`. El objetivo general promete el benchmarking de «familias de modelos estadísticos, híbridos, de aprendizaje profundo y fundacionales». |
| Estado actual | El benchmark compara tres familias: estadística clásica (SARIMA con optimización de hiperparámetros), aprendizaje automático (LightGBM con optimización de hiperparámetros) y fundacional (Chronos-2 en inferencia zero-shot). Seasonal Naive se conserva como línea base (RF-MOD-05). La familia de aprendizaje profundo está pendiente de incorporación y no hay modelos híbridos. |
| Cambio en v1.1 | Se retira del alcance únicamente RF-MOD-02: la familia híbrida no se construye ni se evalúa. RF-MOD-03 se conserva y se incorpora al benchmark un modelo de la familia de aprendizaje profundo global. También se incorpora al conjunto la familia de aprendizaje automático (LightGBM con optimización de hiperparámetros), que la línea base no nombra. El objetivo general pasa a enumerar «familias de modelos estadísticos, de aprendizaje automático, de aprendizaje profundo y fundacionales», y la enumeración de ED-05 se ajusta al mismo conjunto: se retira `hibridos` y se agrega `aprendizaje_automatico`. Por modificar el objetivo general, el cambio queda sujeto a la aprobación de los directores. |
| Fecha y motivo | 26 de septiembre de 2026. El tiempo restante del proyecto está comprometido con M2 (corona y congelamiento del campeón), M3, M4 y la plataforma; construir y validar la familia híbrida adicional no es viable. La familia de aprendizaje profundo permanece en el alcance y su modelo se incorpora al benchmark para cumplir RF-MOD-03. |

## 2. Tratamiento de registros duplicados en la ingesta

| Campo | Detalle |
| :--- | :--- |
| Referencia | RF-ING-04. |
| Texto vigente | Descripción: «El sistema debe detectar y reportar registros duplicados dentro del archivo cargado.» Criterio de Medición: «El sistema debe identificar como duplicados aquellos registros con el mismo SKU, marca temporal y tipo de movimiento, permitiendo al usuario decidir si los consolida o los descarta.» |
| Estado actual | El contrato del archivo preparado no incluye `Movement_Type` y la ingesta rechaza de forma fail-closed los duplicados de `(sku_id, timestamp)`, sin publicar el artefacto procesado. Una decisión del 5 de julio de 2026 (errata #2) había confirmado agregar `Movement_Type` y conservar la elección del usuario entre consolidar y descartar; esa decisión no se implementó. |
| Cambio en v1.1 | RF-ING-04 pasa a exigir: «El sistema debe rechazar los duplicados de `(sku_id, timestamp)` nombrando ambas filas, sin publicar el artefacto procesado.» No se incorpora `Movement_Type` ni la opción de consolidar o descartar. |
| Fecha y motivo | 26 de septiembre de 2026. El archivo preparado traslada la preparación de los datos al proveedor del histórico y el contrato vigente rechaza el archivo completo cuando detecta duplicados; se registra la reversión de la errata #2 en lugar de construir la decisión interactiva. |

**Solicitud:** aprobar la corrección de alcance del numeral 1 y dejar constancia de la reversión del numeral 2.
