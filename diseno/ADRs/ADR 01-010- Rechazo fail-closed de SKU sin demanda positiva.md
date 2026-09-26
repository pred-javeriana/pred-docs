# ADR-01-010: Rechazo fail-closed de SKU sin demanda positiva

- **Fecha:** 2026-09-06
- **Estado:** Aplicada

## Contexto

Un SKU sin ningún período de demanda positiva no permite calcular ADI ni CV² de forma válida. Publicarlo haría que el Módulo 2 consuma una clasificación sin fundamento.

## Decisión

La ingesta rechaza el conjunto completo cuando algún SKU no tiene demanda positiva en el panel diario. La validación ocurre antes de invocar el clasificador 1.3 y antes de escribir el artefacto procesado. El error identifica el SKU afectado y explica que las métricas de topología son indefinidas.

## Consecuencias

Los datos inválidos no llegan a clasificación ni a modelado. El operador debe corregir la fuente y volver a ingerirla. Se evita una etiqueta arbitraria y se conserva el comportamiento fail-closed.

## Evidencia de implementación

Implementación en `pred-engine`; PR pendiente de validación.

## Actualización — 2026-09-07

Aplicada en el pipeline: cada SKU debe tener demanda estrictamente positiva antes de invocar el clasificador y antes de escribir el artefacto procesado. Evidencia: [https://github.com/pred-javeriana/pred-engine/pull/11](https://github.com/pred-javeriana/pred-engine/pull/11).
