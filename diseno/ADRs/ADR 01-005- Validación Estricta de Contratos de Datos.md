# ADR-01-005: Validación Estricta de Contratos de Datos

- **Fecha:** 2026-08-16
- **Estado:** Aplicada

## Contexto & Problema

Los modelos de series de tiempo de aprendizaje profundo (LSTM, N-HiTS) y estadísticos (Módulo 2) son extremadamente frágiles ante datos mal tipados o imposibles. Si el pipeline de ingesta permite el paso de demandas negativas o fechas corruptas, el error matemático ocurrirá dentro del motor de Machine Learning, haciendo imposible rastrear el origen del fallo (efecto cascada).

## Opciones Consideradas

- **A: Limpieza manual y coerción de tipos nativa en Pandas.**
- *Pros:* No requiere librerías adicionales.
- *Cons:* Lógica imperativa propensa a errores humanos. Difícil de leer, mantener y auditar. No actúa como un "contrato" formal.
- **B: Validación por contrato de esquemas usando Pydantic.  **
- *Pros:* Define las leyes del inventario de forma declarativa: `timestamp` debe ser `datetime64`, `demand_qty` $`\ge 0`$, y `lead_time_days` $`\ge 1`$. Actúa como un *Quality Gate*: si el DataFrame viola las reglas, levanta una excepción crítica y detiene la ejecución inmediatamente (Fail-fast).
- *Cons:* Curva de aprendizaje inicial para definir los validadores.

## Decisión

Opción B. Se implementará validación estricta de esquemas (Pydantic) inmediatamente después del *Header Probe*. Cualquier violación de los tipos de datos o rangos lógicos generará una excepción que será registrada en los logs estructurados, deteniendo el procesamiento de ese archivo.

## **Consecuencias **

- **Positivas:** Sanidad matemática garantizada. El Módulo 2 y 3 asumen con 100% de confianza que los datos que reciben son correctos, eliminando la necesidad de programar validaciones redundantes en los algoritmos de ML. El código es auto-documentado.
- **Negativas:** Los archivos de prueba (*mock data*) para los tests unitarios deberán ser creados con mucho rigor para no fallar esta validación.
