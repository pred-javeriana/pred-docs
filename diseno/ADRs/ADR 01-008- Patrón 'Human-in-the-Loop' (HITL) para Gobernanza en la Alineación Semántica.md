# ADR-01-008: Patrón "Human-in-the-Loop" (HITL) para Gobernanza en la Alineación Semántica

- **Fecha:** 2026-08-25
- **Estado:** Aplicada

### **Contexto & Problema**

El framework requiere ingerir archivos caóticos de sistemas externos. Delegar la modificación estructural (renombrar y eliminar columnas) a un LLM introduce un riesgo inaceptable de corrupción silenciosa de datos (Data Leakage/Loss) en caso de alucinaciones. Los directores del proyecto exigen que el sistema no tome decisiones unilaterales sobre la viabilidad de los datos de una empresa.

#### **Opciones Consideradas**

- **Option A: Auto-mapeo y limpieza forzada por LLM (Zero-Shot Mapping).**
- *Pros:* Menor fricción para el usuario; proceso 100% automatizado.
- *Cons:* Viola los principios de Data Governance. Si el LLM se equivoca, el Módulo 2 entrenará con datos erróneos y será imposible rastrear la falla.
- **Option B: Asistente Diagnóstico (Human-in-the-Loop).**
- *Pros:* El LLM actúa como un validador experto sin estado (Stateless). Analiza y devuelve un reporte estructurado instruyendo a la empresa sobre cómo adecuar sus datos. Garantiza que el usuario final mantenga el control y la responsabilidad sobre la estructura de su información.
- *Cons:* Requiere que el usuario intervenga manualmente en su archivo CSV original antes de poder continuar.

### **Decisión**

Opción B. Se implementará un Asistente Diagnóstico impulsado por LLM. El sistema tendrá estrictamente prohibido ejecutar funciones de mutación (`df.rename()`, `df.drop()`) basadas en la inferencia del LLM.

### **Consecuencias**

- **Positivas:** Máxima trazabilidad, transparencia y cumplimiento de buenas prácticas de ingeniería de software. Crea un componente altamente reutilizable para validación de datos (Data Quality Gate).
- **Negativas:** Introduce un paso manual en la experiencia del usuario (operador de la empresa) si su archivo no cumple con el esquema base.
