# ADR-01-003: Trazabilidad Activa mediante Logs Estructurados (JSON)

- **Fecha:** 2026-08-16
- **Estado:** Aplicada

## Contexto & Problema

Para garantizar la reproducibilidad y facilitar la auditoría, cada paso del ETL debe registrarse. Utilizar simples `print()` o la configuración básica de la librería `logging` de Python produce texto plano que es difícil de analizar algorítmicamente y resulta ineficiente si el *framework* escala.

## Opciones Consideradas

- **A: Librería `logging` estándar de Python (Texto plano).**
- *Pros:* Viene preinstalada, fácil de usar.
- *Cons:* Difícil de parsear programáticamente; no separa adecuadamente los metadatos de la cadena de texto.
- **B: Trazabilidad vía Logs Estructurados (Formato JSON).  **
- *Pros:* Cada ejecución genera un *payload* JSON registrando el *hash* del archivo de origen, filas leídas y la marca de tiempo (Timestamp). Es el estándar de oro en la industria de software escalable.
- *Cons:* Obliga a estandarizar el formato de log en todo el equipo desde el día 1.

## Decisión

Opción B. Se configurará el sistema de trazabilidad (*Audit Trail*) para escupir logs estrictamente estructurados (JSON), implementado mediante librerías especializadas (como `structlog`) o formateadores JSON nativos.

## **Consecuencias **

- **Positivas:** Un diseño de software que cumple estándares empresariales de telemetría y observabilidad. Permite en el futuro buscar fallos en la ingesta mediante *queries* precisos a los logs.
- **Negativas:** Requiere definir un esquema base para el JSON del log.
