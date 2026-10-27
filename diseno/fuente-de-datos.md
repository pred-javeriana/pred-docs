# Fuente de datos del panel real

Este documento registra el origen, uso, transformación y términos del conjunto de datos reales utilizado en PRED.

## Fuente

- **Fuente:** competencia Corporación Favorita Grocery Sales Forecasting, Kaggle (2017), URL https://www.kaggle.com/c/favorita-grocery-sales-forecasting, fecha de acceso 2026-10-27.

El título de la competencia se cita en su inglés original (*Corporación Favorita Grocery Sales Forecasting*), sin traducir.

## Uso en PRED

El conjunto constituye el panel de datos reales utilizado para las corridas completas con datos reales y la muestra de verificación local del motor.

## Transformación

El archivo preparado corresponde a la suma de ventas diarias en unidades por ítem a través de todas las tiendas, dando lugar al archivo con el contrato canónico de cuatro campos (`sku_id`, `timestamp`, `demand_qty`, `lead_time_days`).

- **Rango de fechas:** 2013-01-01 a 2017-08-15.
- **Conteos de productos y filas:**
  - El archivo preparado tiene 4.036 ítems y 4.655.109 filas.
  - Tras la ingesta del motor quedan 3.703 productos y 4.594.950 filas.
- **Valores de demanda:** algunos productos se venden por peso, por lo que algunos valores de demanda son fraccionarios.
- **Tiempo de reposición:** `lead_time_days` es una constante 7 agregada durante la preparación; no está en la fuente original.

## Límites

- La agregación a través de las tiendas es la forma observada del archivo preparado.
- Otros pasos de preparación previa (por ejemplo, el tratamiento de devoluciones) no están documentados.

## Términos de uso

Se deben revisar los términos de uso de los datos de la competencia antes de redistribuir el archivo o cualquier archivo derivado.
