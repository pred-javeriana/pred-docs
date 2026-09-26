# ADR-01-002: Política Estricta de Solo Lectura (Read-Only Policy) en Capa de Extracción

- **Fecha:** 2026-08-16
- **Estado:** Aplicada

## Contexto & Problema

Existe el riesgo de que un error en el script de Python en la capa de extracción (o un desarrollador inexperto en el futuro) sobrescriba accidentalmente las exportaciones transaccionales. En entornos académicos experimentales y en arquitecturas de sistemas empresariales, contaminar la fuente original invalida cualquier evaluación posterior.

## Opciones Consideradas

- **A: Permisos unificados de Lectura/Escritura en el directorio `/data`.**
- *Pros:* Menos fricción a nivel de sistema de archivos al desarrollar.
- *Cons:* Alto riesgo de modificación accidental del origen; rompe el aislamiento del sistema.
- **B: Imposición de *Read-Only Policy* en los scripts de ingesta.  **
- *Pros:* Los scripts de extracción (`ingest_pipeline.py`) actúan de forma pasiva, garantizando la inmutabilidad de la fuente.
- *Cons:* Requiere manejo explícito de excepciones y control de I/O en la codificación del script.

## Decisión

Opción B. Los scripts de extracción en Python tendrán estrictamente permisos de lectura sobre `/data/raw/`. Toda operación de escritura en este directorio generará una excepción forzada desde el código.

## **Consecuencias **

- **Positivas:** Trazabilidad perfecta. Actúa como un muro de contención seguro entre el sistema de origen de datos y el motor PRED.
- **Negativas:** Los *tests unitarios* requerirán crear dinámicamente archivos ficticios de solo lectura (mocking) para no fallar por permisos.
