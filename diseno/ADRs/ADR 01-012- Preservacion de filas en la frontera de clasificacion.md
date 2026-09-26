# ADR-01-012: Preservacion de filas en la frontera de clasificacion

- **Fecha:** 2026-09-06
- **Estado:** Aplicada

## Contexto

El contrato declara que `classify_daily_panel` devuelve las mismas filas del panel diario más `sku_class`. Un clasificador que omita, agregue, reordene o altere una fila puede producir un Parquet aparentemente válido pero semánticamente incorrecto.

## Decisión

La frontera 1.4 compara identidad y valores de las columnas del panel antes y después de clasificación. Rechaza cualquier diferencia y solo publica una copia tipada con las cinco columnas del handoff.

## Consecuencias

La salida conserva la continuidad, demanda, fechas y lead time validados en 1.2. Los errores de integración se detectan antes de la persistencia procesada y el clasificador queda obligado a respetar el contrato de intercambio.

## Evidencia de implementación

Decisión surgida de revisión de la implementación actual; PR pendiente de validación.

## Actualización — 2026-09-07

Aplicada en la frontera 1.4: se comparan identidad, orden y valores de las columnas transaccionales antes de publicar y solo se admite añadir `sku_class`. Evidencia: [https://github.com/pred-javeriana/pred-engine/pull/11](https://github.com/pred-javeriana/pred-engine/pull/11).
