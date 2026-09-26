# ADR-01-006: Imputación Estructural y Continuidad Temporal (Zero-Filling)

- **Fecha:** 2026-08-16
- **Estado:** Aplicada

## Contexto & Problema

Los datos transaccionales de inventarios suelen ser esporádicos (no hay registros de los días sin ventas). Si se inyecta este archivo crudo directamente a un algoritmo, el modelo interpretará que el tiempo "saltó" de un lunes a un jueves, destruyendo la estacionalidad, la autocorrelación temporal y la frecuencia real de la serie.

## Opciones Consideradas

- **A: Ignorar los días sin transacciones (Sparse Time-Series).**
- *Pros:* Mantiene el tamaño del DataFrame pequeño (menor consumo de RAM).
- *Cons:* Destruye la validez matemática de ARIMA, Prophet y algoritmos de Deep Learning que asumen intervalos de tiempo equidistantes.
- **B: Generación de Grid Temporal y *Zero-Filling* (Remuestreo).  **
- *Pros:* Crea un índice de fechas continuas con resolución diaria para cada `sku_id` y realiza un *Left Join* de las transacciones. Los valores nulos de demanda resultantes se imputan explícitamente con un Cero matemático.
- *Cons:* Aumenta significativamente la cantidad de filas en memoria, especialmente para históricos largos con muchos SKUs.

## Decisión

Opción B. Se utilizará la funcionalidad de remuestreo (Resampling) de Pandas para forzar la continuidad temporal. Se imputarán los ceros explícitamente para garantizar la equidistancia de los intervalos de tiempo.

## **Consecuencias **

- **Positivas:** Permite capturar con precisión la esparsidad de la serie (fundamental para calcular correctamente el Índice de Velocidad Cero - ZVI en la caracterización). Los modelos matemáticos funcionarán sin errores de dimensión temporal. Funciones puramente sin estado (stateless).
- **Negativas:** Obliga a apoyarnos fuertemente en el formato columnar (Parquet) definido en el [ADR 1](/p/3befbd1bee4680a19651ec1a35659f0d?pvs=25) para compensar el aumento de tamaño del set de datos en disco.
