# ADR-01-011: Stub de clasificacion exclusivo para pruebas de integracion

- **Fecha:** 2026-09-06
- **Estado:** Depreciada
- **Sustituida por:** la integración con `classify_daily_panel` real descrita en la actualización de ADR-01-009.

## Contexto

La exportación de `classify_daily_panel` de 1.3 se desarrolla en paralelo. La ruta de ingesta debe validarse de extremo a extremo sin duplicar la lógica SBC ni bloquear el desarrollo de 1.4.

## Decisión

Usar un stub únicamente en las pruebas de integración para representar el contrato de Tomas. El stub devuelve el panel recibido con una etiqueta permitida y no se instala como clasificador de producción ni calcula ADI o CV². La prueba atraviesa la ingesta canónica, el contrato de cinco columnas y la escritura en `data/processed/`.

## Consecuencias

Se prueba el flujo completo y la frontera de datos ahora, mientras la implementación real de 1.3 permanece propiedad de Tomas. La prueba debe eliminarse o sustituirse por el export real cuando el contrato de Tomas esté integrado; no se publica un artefacto real basado en el stub.

## Evidencia de implementación

Implementación en `pred-engine`; PR pendiente de validación.

## Actualización — 2026-09-07

Esta decisión queda depreciada: la integración final usa `classify_daily_panel` real de 1.3 y las pruebas de handoff ya no dependen de un stub. Se conserva como registro histórico del desarrollo paralelo.
