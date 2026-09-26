# ADR-01-009: Contrato de handoff 1.4 e integracion desacoplada con la clasificacion 1.3

- **Fecha:** 2026-09-06
- **Estado:** Aplicada

## Contexto

El Módulo 2 necesita un artefacto procesado estable para evaluar modelos sin conocer la extracción o limpieza. La clasificación de topología pertenece al submódulo 1.3 y se desarrolla en paralelo por Tomas Pinilla.

## Decisión

El contrato de handoff de 1.4 publica exactamente `sku_id`, `timestamp`, `demand_qty`, `lead_time_days` y `sku_class` en Parquet bajo `data/processed/`. El clasificador 1.3 expone `classify_daily_panel(panel)` y devuelve las mismas filas con una etiqueta por SKU. 1.4 valida columnas, tipos, etiquetas permitidas, constancia por SKU y preservación de filas antes de publicar. La integración acepta el clasificador por inyección y no duplica ADI ni CV².

## Consecuencias

El motor de topología y el contrato de salida evolucionan de forma independiente. El artefacto es consumible por el Módulo 2. La ruta canónica queda lista para conectarse al export público de 1.3 cuando Tomas lo integre.

## Evidencia de implementación

Implementación en `pred-engine`; PR pendiente de validación.

## Actualización — 2026-09-07

Aplicada con la integración que publica el artefacto de cinco columnas en Parquet y lo deja disponible para el Módulo 2. La composición vigente usa el clasificador real de 1.3 directamente en el pipeline; no depende de un stub ni duplica ADI/CV². Evidencia: [https://github.com/pred-javeriana/pred-engine/pull/11](https://github.com/pred-javeriana/pred-engine/pull/11).
