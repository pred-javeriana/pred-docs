# ADR-01-004: Mecanismo de Alineación Semántica Dinámica (LLM Header Probe)

- **Fecha:** 2026-08-16
- **Estado:** Depreciada

## Contexto & Problema

El *framework* debe ingerir archivos transaccionales exportados de sistemas ERP externos que no poseen cabeceras estandarizadas. En la práctica, un sistema puede exportar `"Fecha_Venta"`, otro `"Transaction_Date"`, y otro simplemente `"Date"`. Si hardcodeamos diccionarios de mapeo (con sentencias `if/else`), el código se acoplará a la fuente de datos específica, generando código desechable que requerirá mantenimiento manual cada vez que se evalúe un nuevo caso de estudio.

## Opciones Consideradas

- **A: Mapeo manual mediante diccionarios estáticos.**
- *Pros:* Implementación trivial; no requiere dependencias de red.
- *Cons:* Cero escalabilidad. El código se rompe inmediatamente si el origen cambia una letra en la exportación. Acopla el *framework* al set de datos.
- **B: Sonda de Cabeceras (Header Probe) mediante LLM (Zero-Shot).  **
- *Pros:* El motor extrae una muestra de 5 filas y usa un LLM con temperatura 0.0 (determinista) para mapear semánticamente las columnas del cliente hacia nuestro contrato estándar (`sku_id`, `timestamp`, `demand_qty`, `lead_time_days`). Posteriormente, se aplica el mapeo vía Pandas (`df.rename()`) y se descartan las columnas no mapeadas. Garantiza un desacople total de la fuente.
- *Cons:* Introduce latencia en el primer paso de ingesta y requiere manejo de excepciones de red/API.

## Decisión

Opción B. Se implementará un *Header Probe* impulsado por un LLM con temperatura cero para inferir el esquema. Este componente actuará como un adaptador que transforma entradas caóticas en un formato predecible sin tocar la lógica central del ETL.

## **Consecuencias **

- **Positivas:** El *framework* se vuelve verdaderamente agnóstico y plug-and-play. El código resultante es modular y altamente reutilizable para cualquier pipeline de ingesta de datos transaccionales en el futuro. Optimización de memoria al descartar de inmediato variables ruidosas.
- **Negativas:** Exige utilizar tokens para las llamadas al LLM, definir prompts muy estrictos y parsear la salida del LLM a un formato JSON válido para evitar fallos de ejecución.
