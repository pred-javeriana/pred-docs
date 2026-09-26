# ADR-02-015: Definición de la Política Inicial de Routing por Topología de Demanda

- **Fecha:** 2026-09-20
- **Estado:** Propuesto

## Contexto & Problema

El Módulo 1 clasifica cada SKU mediante `sku_class` en una de cuatro topologías de demanda: `Smooth`, `Erratic`, `Intermittent` y `Lumpy`.
La clasificación se construye a partir del Average Inter-Demand Interval (ADI) y del coeficiente de variación cuadrático de las demandas no nulas (CV²). Esta clasificación distingue dos dimensiones relevantes para el pronóstico:
- frecuencia con la que ocurre la demanda;
- variabilidad de la magnitud cuando la demanda ocurre.
De acuerdo con esta estructura:
- `Smooth` representa demanda frecuente y relativamente estable;
- `Erratic` representa demanda frecuente pero con alta variabilidad en la magnitud;
- `Intermittent` representa demanda con numerosos periodos de cero, pero magnitudes positivas relativamente estables;
- `Lumpy` combina alta intermitencia con alta variabilidad de las magnitudes positivas.
La Sección 2.2 establece que `sku_class` debe utilizarse para reducir el espacio de candidatos del Módulo 2. ADR-02-012 establece adicionalmente que esta lógica debe representarse mediante una `RoutingPolicy` declarativa e inyectable, separada de la implementación del `SelectionRouter`.
Queda pendiente decidir qué familias de predictores deben evaluarse inicialmente para cada topología.
Si todas las clases son enviadas a todas las familias, la clasificación deja de tener un efecto material sobre el espacio de selección y el `SelectionRouter` se reduce a un mecanismo de delegación sin capacidad real de reducir costo computacional.
En el extremo contrario, asignar una única familia o modelo a cada `sku_class` convertiría la clasificación topológica en una decisión determinista de pronóstico, eliminando la comparación experimental posterior y creando un sesgo arquitectónico.
Se requiere, por tanto, una política intermedia: reducir de manera explícita el espacio de familias según la estructura de la demanda, manteniendo más de una alternativa cuando sea metodológicamente razonable.

## Opciones Consideradas

- **Option A: Sin segregación por topología.**
Todas las clases se enrutan hacia las cuatro familias:
`CLASSICAL`, `ML`, `DL` y `FOUNDATION`.
- *Pros:*
- Máxima cobertura experimental.
- No se excluye anticipadamente ninguna familia.
- Simplifica la política de routing.
- *Cons:*
- `sku_class` no reduce materialmente el espacio experimental.
- El `SelectionRouter` aporta poco valor más allá de la delegación.
- Se ejecuta HPO costoso incluso sobre topologías con pocos eventos positivos.
- No se aprovecha la caracterización matemática producida por el Módulo 1.
- **Option B: Routing determinista hacia una única familia o modelo.**
Cada `sku_class` se asigna directamente a una familia o predictor específico.
Ejemplo conceptual:
`Smooth → SARIMA`
`Lumpy → Foundation Model`
- *Pros:*
- Máxima reducción del costo computacional.
- Flujo de ejecución muy simple.
- *Cons:*
- Convierte la clasificación en una decisión final de modelado.
- Impide comparar alternativas dentro de una misma topología.
- Introduce un fuerte sesgo previo al benchmark.
- Acopla la taxonomía de demanda con modelos concretos.
- Reduce la capacidad experimental del framework.
- **Option C: Routing segregado por familias y perfiles de selección.**
`sku_class` determina un subconjunto de familias candidatas y un perfil de selección apropiado para la topología.
La política inicial propuesta es:
<table header-row="true">
<tr>
<td>`sku_class`</td>
<td>Clásicos</td>
<td>ML</td>
<td>DL</td>
<td>Fundacionales</td>
</tr>
<tr>
<td>`Smooth`</td>
<td>Sí</td>
<td>Sí</td>
<td>Sí</td>
<td>Sí</td>
</tr>
<tr>
<td>`Erratic`</td>
<td>Sí</td>
<td>Sí</td>
<td>Sí</td>
<td>Sí</td>
</tr>
<tr>
<td>`Intermittent`</td>
<td>Sí</td>
<td>Sí</td>
<td>No</td>
<td>Sí</td>
</tr>
<tr>
<td>`Lumpy`</td>
<td>Sí</td>
<td>No</td>
<td>No</td>
<td>Sí</td>
</tr>
</table>
El Router no decide modelos concretos. Además de la familia, entrega un perfil que permite a cada estrategia adaptar su espacio de candidatos.
Ejemplos conceptuales:
`Smooth → CLASSICAL(profile="dense_stable")`
`Erratic → ML(profile="dense_variable")`
`Intermittent → CLASSICAL(profile="sparse_stable")`
`Lumpy → CLASSICAL(profile="sparse_variable")`
- *Pros:*
- `sku_class` produce una reducción real del espacio experimental.
- Evita convertir la clasificación en selección determinista del ganador.
- Reduce HPO costoso sobre las topologías más dispersas.
- Permite que cada estrategia especialice sus candidatos sin introducir modelos concretos dentro del Router.
- Conserva al menos dos paradigmas de predicción para las topologías más restrictivas.
- Permite modificar posteriormente la política sin modificar el `SelectionRouter`.
- *Cons:*
- Algunas familias potencialmente válidas quedan fuera de determinadas topologías en la política inicial.
- La política constituye una hipótesis de asignación de presupuesto que deberá validarse empíricamente.
- Las estrategias deben soportar perfiles diferenciados para aprovechar completamente la clasificación.

## Decisión

Se adopta la **Option C: Routing segregado por familias y perfiles de selección**.
La política inicial queda definida de la siguiente manera:
- `Smooth` → `{CLASSICAL, ML, DL, FOUNDATION}`
- `Erratic` → `{CLASSICAL, ML, DL, FOUNDATION}`
- `Intermittent` → `{CLASSICAL, ML, FOUNDATION}`
- `Lumpy` → `{CLASSICAL, FOUNDATION}`
La diferencia entre las clases no se limita a las familias habilitadas. Cada decisión de routing incluirá también un perfil de topología:
- `Smooth` → `dense_stable`
- `Erratic` → `dense_variable`
- `Intermittent` → `sparse_stable`
- `Lumpy` → `sparse_variable`
El `SelectionRouter` será responsable exclusivamente de transformar:
`sku_class → RoutingDecision(familia, perfil)`
y delegar posteriormente a las estrategias correspondientes.
El Router no conocerá modelos concretos ni hiperparámetros.
Por ejemplo, el Router no contendrá reglas como:
`Intermittent → Croston`
sino:
`Intermittent → CLASSICAL(profile="sparse_stable")`
La `ClassicalSelectionStrategy` será responsable de interpretar dicho perfil y determinar qué modelos y espacios de configuración son apropiados. Métodos especializados para demanda intermitente, como Croston y sus variantes, podrán pertenecer a estos perfiles cuando formen parte de la estrategia clásica implementada.
De la misma forma, el perfil podrá reducir o adaptar el espacio HPO de una estrategia sin que el `SelectionRouter` conozca la implementación interna del optimizador.

### Justificación por topología

**Smooth**
La demanda ocurre de forma frecuente y presenta baja variabilidad relativa. Existe suficiente densidad temporal para permitir inicialmente la comparación de modelos clásicos, ML, DL y modelos fundacionales.
Por este motivo no se realiza una reducción de familias en la política inicial.
**Erratic**
La demanda continúa ocurriendo con frecuencia, pero su magnitud presenta alta variabilidad. Aunque constituye un problema predictivo más complejo que `Smooth`, la disponibilidad frecuente de observaciones positivas mantiene información suficiente para evaluar inicialmente las cuatro familias.
La diferenciación frente a `Smooth` se realiza mediante el perfil `dense_variable`, que puede permitir a las estrategias adaptar sus espacios de búsqueda.
**Intermittent**
La serie contiene numerosos periodos sin demanda, por lo que la cantidad de eventos positivos disponibles para entrenamiento se reduce.
Se conservan:
- modelos clásicos, permitiendo estrategias especializadas en intermitencia;
- Machine Learning, dado que existen enfoques capaces de explotar características derivadas y relaciones no lineales;
- modelos fundacionales, debido a que no requieren HPO arquitectónico dentro de este módulo.
Deep Learning se excluye de la política inicial para evitar dedicar un proceso de HPO arquitectónico de alto costo a series cuya densidad de eventos positivos es reducida.
Esta exclusión representa una decisión de asignación inicial de presupuesto experimental y no una afirmación de incapacidad de los modelos de Deep Learning para pronosticar demanda intermitente.
**Lumpy**
Esta topología combina dos dificultades: largos intervalos sin demanda y alta variabilidad en la magnitud de los eventos positivos.
Por esta razón se adopta la política más restrictiva.
Se conservan:
- la familia clásica bajo un perfil especializado en series dispersas;
- los modelos fundacionales como paradigma alternativo preentrenado.
Machine Learning y Deep Learning se excluyen de la política inicial debido al mayor costo de optimización frente a la baja densidad y alta variabilidad de la señal disponible.
La comparación entre un paradigma estadístico especializado y un paradigma preentrenado mantiene diversidad metodológica sin ejecutar el espacio completo de HPO sobre la topología de mayor dificultad.

## Consecuencias

### Positivas

- `sku_class` tiene un efecto real y verificable sobre el comportamiento del Módulo 2.
- Se reduce el costo computacional de HPO para las topologías más dispersas.
- Se mantiene más de una alternativa de modelado para evitar una selección completamente determinista.
- El Router permanece independiente de modelos concretos.
- Las estrategias pueden adaptar espacios de búsqueda mediante perfiles sin modificar la infraestructura de routing.
- La política puede evolucionar independientemente del código del `SelectionRouter`.
- Los resultados experimentales pueden analizarse posteriormente por `sku_class` para determinar si las exclusiones iniciales deben mantenerse o revisarse.

### Negativas

- ML y DL no serán evaluados inicialmente sobre `Lumpy`, por lo que el benchmark no producirá métricas para esas combinaciones.
- DL no será evaluado inicialmente sobre `Intermittent`.
- La reducción de familias constituye una hipótesis de asignación de presupuesto y deberá quedar registrada con la versión de la política utilizada.
- El perfil clásico para demanda intermitente requiere que la `ClassicalSelectionStrategy` disponga de candidatos apropiados para ese tipo de series; el `SelectionRouter` por sí mismo no resuelve esta necesidad.
- Una modificación futura de la matriz puede afectar la comparabilidad entre corridas realizadas con versiones distintas de la política.

## Referencias

- Syntetos, A. A., Boylan, J. E., & Croston, J. D. (2005). On the categorization of demand patterns. Journal of the Operational Research Society, 56(5), 495–503.
- Syntetos, A. A., & Boylan, J. E. (2005). The accuracy of intermittent demand estimates. International Journal of Forecasting, 21(2), 303–314. DOI: 10.1016/j.ijforecast.2004.10.001.
- Kourentzes, N. (2013). Intermittent demand forecasts with neural networks. International Journal of Production Economics, 143(1), 198–206. DOI: 10.1016/j.ijpe.2013.01.009.
- Giannopoulos, P. G., Dasaklis, T. K., Tsantilis, I., & Patsakis, C. (2025). Machine learning algorithms in intermittent demand forecasting: a review. International Journal of Production Research.
