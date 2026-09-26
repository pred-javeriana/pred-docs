# Registro de decisiones

Los dos primeros dígitos del identificador indican el módulo: `01` ingestión y caracterización, `02` selección y optimización, `03` validación temporal. El número identifica el registro, no su vigencia. La decisión original permanece en cada archivo; una decisión posterior puede sustituirla sin borrar su antecedente.

## Estados

Los 25 registros usan cuatro valores de `Estado`: **Propuesto** (pendiente de aceptación), **Aceptada** (decisión vigente sin constancia de aplicación), **Aplicada** (decisión con aplicación registrada) y **Depreciada** (decisión retirada o sustituida, conservada por su valor histórico). La redacción de una propuesta puede decir «se adopta» sin convertir por sí sola su estado en Aplicada. No se infiere la implantación a partir de la fecha ni se equipara Aceptada con Aplicada.

| Registro anterior | Alcance de la sustitución |
| --- | --- |
| [ADR-01-004](ADR%2001-004-%20Mecanismo%20de%20Alineaci%C3%B3n%20Sem%C3%A1ntica%20Din%C3%A1mica%20%28LLM%20Header%20Probe%29.md) | [ADR-01-008](ADR%2001-008-%20Patr%C3%B3n%20%27Human-in-the-Loop%27%20%28HITL%29%20para%20Gobernanza%20en%20la%20Alineaci%C3%B3n%20Sem%C3%A1ntica.md) descarta la mutación automática de columnas. |
| [ADR-01-011](ADR%2001-011-%20Stub%20de%20clasificacion%20exclusivo%20para%20pruebas%20de%20integracion.md) | La actualización de [ADR-01-009](ADR%2001-009-%20Contrato%20de%20handoff%201.4%20e%20integracion%20desacoplada%20con%20la%20clasificacion%201.3.md) registra la integración del clasificador real. |
| [ADR-02-002](ADR%2002-002-%20Adoptar%20AICc%20para%20la%20preselecci%C3%B3n%20de%20configuraciones%20de%20modelos%20estad%C3%ADsticos%20cl%C3%A1sicos.md) | [ADR-02-009](ADR%2002-009-%20Adopci%C3%B3n%20de%20Hyperparameter%20Optimization%20%28HPO%29%20para%20la%20optimizacion%20de%20configuraci%C3%B3n%20en%20modelos%20cl%C3%A1sicos.md) sustituye la preselección por AICc como requisito para los modelos clásicos. |

## Numeración

[ADR-01-007](ADR%2001-007-%20Estrategia%20de%20Aumento%20de%20Datos.md) corresponde a la decisión sobre aumento de datos previa a la selección del Módulo 2. El registro no contiene ADR-02-001 ni ADR-02-006, ADR-02-007 o ADR-02-008. Las referencias a ADR-02-001 y ADR-001 en ADR-02-002 no identifican un registro de evaluación inequívoco; no se les atribuye a ADR-03-001 por semejanza de tema.

ADR-02-011 citaba ADR-01-007 como antecedente de HPO; el antecedente pertinente es ADR-02-009. ADR-02-010 alude a una «regla de seguridad #4 de ADR-02-005» que no figura numerada en ADR-02-005: allí solo consta la gracia mínima de cuatro ventanas. La numeración de esa regla no se adopta como referencia verificable.

## Frontera de selección y evaluación final

[ADR-03-002](ADR%2003-002-%20Separaci%C3%B3n%20de%20protocolos%20de%20selecci%C3%B3n%20y%20evaluaci%C3%B3n%20final.md) establece dos protocolos de Walk-Forward: el Módulo 2 compara, ajusta y elige candidatos; el Módulo 3 mide y reporta su evaluación final sin ajustar ni elegir. Así se precisa el alcance de [ADR-03-001](ADR%2003-001-%20Adoptar%20Walk-Forward%20Validation%20como%20m%C3%A9todo%20de%20evaluaci%C3%B3n%20fuera%20de%20muestra.md), que permanece íntegro como antecedente. Su mitigación histórica de filtrar modelos clásicos por AICc antes de Walk-Forward fue desplazada por ADR-02-009; no describe la selección vigente. Las métricas y particiones específicas de cada protocolo no se fijan aquí.

## Estados por confirmar

ADR-02-004 y ADR-02-015 siguen **Propuesto** aunque su sección «Decisión» emplea lenguaje de adopción. ADR-02-010 sigue **Aceptada** aunque describe una implementación y resultados de pruebas; ADR-02-005 también es **Aceptada** pese a que ADR-02-010 describe su implementación de ASHA. Estos estados no se modifican sin confirmar la aceptación o la aplicación correspondiente. ADR-01-007 permanece **Aceptada**: su elección de MBB no impone integrarlo obligatoriamente en todos los despliegues, como indica su propia sección de consecuencias.
