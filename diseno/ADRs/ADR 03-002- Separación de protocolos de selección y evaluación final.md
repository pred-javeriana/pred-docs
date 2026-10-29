# ADR-03-002: Separación de protocolos de selección y evaluación final

- **Fecha:** 2026-09-26
- **Estado:** Aceptada

## Contexto & Problema

ADR-03-001 adopta Walk-Forward Validation para obtener una evaluación fuera de muestra comparable entre familias. A la vez, ADR-02-003, ADR-02-004 y ADR-02-009 emplean Walk-Forward durante la selección y optimización del Módulo 2. Sin una frontera explícita, una misma evaluación podría usarse indistintamente para elegir candidatos y para informar su desempeño final.

ADR-03-001 también conserva una mitigación basada en preselección por AICc para modelos clásicos. ADR-02-009 sustituyó esa preselección obligatoria por HPO sobre Walk-Forward; el registro anterior se mantiene como antecedente de la decisión metodológica, no como política vigente de selección clásica.

## Opciones Consideradas

1. **Protocolo compartido a cargo del Módulo 2:** el Módulo 3 consumiría los resultados de la evaluación utilizada para seleccionar.
2. **Protocolo compartido a cargo del Módulo 3:** el Módulo 2 consumiría una evaluación definida para el informe final.
3. **Protocolos separados para selección y evaluación final:** cada módulo tendría una finalidad distinta, aunque ambos utilicen Walk-Forward.

## Decisión

Se adopta la **opción 3**. El Módulo 2 ejecuta el protocolo de Walk-Forward de selección: puede comparar candidatos, ajustar configuraciones y elegirlos. El Módulo 3 ejecuta un protocolo distinto de evaluación final: mide y reporta resultados, pero no ajusta configuraciones ni elige candidatos o ganadores. Un resultado obtenido para seleccionar en el Módulo 2 no se presenta como resultado de evaluación final del Módulo 3.

Esta separación precisa el alcance de ADR-03-001 sin renumerarlo ni sustituir su elección de Walk-Forward como método de evaluación fuera de muestra. Las métricas, ventanas y particiones concretas de cada protocolo no quedan fijadas por este registro.

## Consecuencias

### Positivas

- La elección de configuraciones y el informe final tienen responsables y resultados distinguibles.
- Se mantiene la comparación experimental del Módulo 2 sin atribuirle la evaluación final del Módulo 3.
- La evaluación final conserva el método fuera de muestra establecido en ADR-03-001, sin reutilizar como resultado final el resultado de selección.

### Negativas

- Ejecutar dos protocolos requiere identificar por separado sus resultados y puede aumentar el costo de evaluación.
- Las reglas concretas de cada protocolo deben definirse antes de interpretar conjuntamente sus resultados.
