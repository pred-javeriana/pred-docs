# ADR-01-001: Patrón de Almacenamiento Inmutable y Formato Columnar (Parquet)

- **Fecha:** 2026-08-16
- **Estado:** Aplicada

## Contexto & Problema

La ingesta de datos transaccionales masivos (archivos .csv de 50.000+ registros) puede generar cuellos de botella en I/O y problemas graves de reproducibilidad si los datos se procesan "en el lugar". El motor matemático de PRED necesita operar con extrema rapidez sobre la memoria y los directores/jurados exigirán evidencia inmutable de la fuente original para validar el *benchmarking*.

## Opciones Consideradas

- **A: Sobreescritura en directorio único (Archivos CSV).**
- *Pros:* Implementación rápida en Pandas (`df.to_csv()`).
- *Cons:* Destruye el dato crudo original, es inauditable, genera cuellos de botella en memoria, y acopla el sistema al formato de texto.
- **B: Jerarquía estricta (`/raw`, `/staging`, `/processed`) con exportación en formato Parquet.  **
- *Pros:* El archivo crudo actúa como frontera estricta y artefacto de auditoría. El almacenamiento final en `/processed` utilizando Parquet garantiza tipado estricto a nivel de columna, compresión masiva y lectura ultra-rápida, logrando un desacople total entre el ETL y el Módulo de Machine Learning.
- *Cons:* Requiere incluir dependencias adicionales (`pyarrow` o `fastparquet`).

## Decisión

Opción B. Se implementará una jerarquía de almacenamiento estricta. Los archivos .csv originales residirán en `/data/raw`, los artefactos temporales en `/data/staging`, y el resultado final a consumir por los modelos (Módulo 2 y 3) se guardará en formato Parquet en `/data/processed`.

## **Consecuencias **

- **Positivas:** Máxima reproducibilidad ante el jurado. Al utilizar Parquet, el Módulo 2 y 3 pueden leer el panel de datos sin preocuparse por parseo de fechas o inferencia de tipos. El código resultante es modular y altamente reutilizable.
- **Negativas:** Ligera curva de aprendizaje en el manejo de metadatos de Parquet.
