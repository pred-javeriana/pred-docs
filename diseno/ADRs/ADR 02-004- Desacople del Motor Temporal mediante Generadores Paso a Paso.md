# ADR-02-004: Desacople del Motor Temporal mediante Generadores Paso a Paso

- **Fecha:** 2026-08-31
- **Estado:** Propuesto

## Contexto & Problema

Durante Hyperparameter Optimization se evalúan múltiples configuraciones mediante Walk-Forward Validation. Ejecutar todas las ventanas de cada configuración antes de permitir una decisión de poda aumenta considerablemente el costo computacional.
El mecanismo ASHA necesita recibir métricas parciales después de determinadas ventanas para decidir si una configuración debe continuar o ser descartada.
Sin embargo, permitir que ASHA implemente su propio recorrido temporal duplicaría la lógica de Walk-Forward Validation y podría producir diferencias entre la evaluación completa y la evaluación utilizada durante HPO.

## Opciones Consideradas

- **Option A: Implementar el recorrido temporal dentro del optimizador.**
ASHA controla directamente la generación y ejecución de las ventanas de Walk-Forward.
- *Pros:*
- Flujo de control concentrado en un solo componente.
- *Cons:*
- Duplica la lógica temporal.
- Acopla ASHA a la implementación de Walk-Forward.
- Puede producir diferencias entre validación íntegra y validación utilizada por HPO.
- **Option B: Exponer el motor temporal mediante ejecución incremental paso a paso.**
La misma definición de ventanas causales y la misma función de ejecución por ventana son reutilizadas tanto por el modo completo como por el modo greedy.
El componente incremental entrega un `EstadoParcial` después de cada ventana, pero no decide si la configuración debe ser podada.
- *Pros:*
- Una única definición de causalidad temporal.
- Métricas comparables entre modo completo y modo greedy.
- ASHA permanece separado de la mecánica temporal.
- El motor temporal puede utilizarse independientemente del optimizador.
- *Cons:*
- Requiere mantener explícitamente el ciclo de vida de un ejecutor incremental.
- El llamador debe decidir cuándo continuar o cerrar la ejecución.

## Decisión

Se adopta la **Option B**.
La implementación utilizará un generador incremental (`iterar_walk_forward`) encapsulado por `EjecutorGreedy`.
Tanto el modo completo como el modo incremental reutilizarán la misma generación de ventanas causales y la misma ejecución individual de ventana.
`EjecutorGreedy` tendrá exclusivamente la responsabilidad de:
- ejecutar la siguiente ventana;
- mantener el historial evaluado;
- calcular y devolver el agregado parcial;
- cerrar la ejecución cuando el llamador lo solicite.
La decisión de poda permanecerá fuera del motor temporal y será responsabilidad exclusiva del componente de asignación de recursos/ASHA.

## Consecuencias

### Positivas

- No existe una segunda implementación del esquema temporal.
- Walk-Forward completo y greedy permanecen matemáticamente comparables.
- ASHA puede sustituirse sin modificar el motor temporal.
- La lógica de validación puede probarse independientemente de HPO.

### Negativas

- El ciclo de vida del ejecutor requiere manejo explícito de estados como avanzar, cerrar y obtener resultado.
- La reanudación de una corrida interrumpida no queda resuelta por este ADR y requiere un componente separado.
