# ADR-03-001: Adoptar Walk-Forward Validation como método de evaluación fuera de muestra

- **Fecha:** 2026-08-29
- **Estado:** Aceptada

## Contexto & Problema

Necesitamos decidir el método de evaluación fuera de muestra para comparar configuraciones y familias de modelos de forecasting sobre series temporales de SKUs. El contexto y las restricciones del problema son:
- Las observaciones de una serie temporal tienen dependencia temporal: el futuro no puede estar disponible en el momento de entrenar, lo que invalida cualquier partición aleatoria convencional entre entrenamiento y prueba.
- El resultado de esta evaluación debe ser un valor único, final y comparable entre familias de modelos heterogéneas, es decir debe ser agnostico a la familia del modelo.
- Un número relevante de SKUs del sistema (`Intermittent`/`Lumpy`) tiene historiales cortos y un comportamiento que puede variar sustancialmente entre distintos tramos de la serie.
Alternativas consideradas:
1. Holdout simple
2. K-fold cross-validation estándar
3. Walk-Forward Validation

## Opciones Consideradas

### Alternativa 1: Holdout simple

**Descripción:** Reservar el tramo final de la serie como conjunto de prueba y entrenar con el resto, mediante una única partición cronológica.
**Pros:**
- Computacionalmente barato: un único ajuste por configuración.
- Simple de implementar y de explicar.
- Respeta el orden temporal básico (no mezcla pasado y futuro).
**Contras:**
- Produce una única medición de error, sensible al período específico que quedó como test.
- No aporta ninguna estimación de la variabilidad del error entre distintos períodos.
- Es la práctica tradicional en pronóstico, pero no aprovecha completamente los datos disponibles ni refleja el reentrenamiento periódico que ocurre en producción (Bergmeir & Benítez, 2012).

### Alternativa 2: K-fold cross-validation estándar

**Descripción:** Particionar aleatoriamente las observaciones en *k* pliegues, sin respetar el orden cronológico entre entrenamiento y prueba.
**Pros:**
- Uso completo del conjunto de datos disponible.
- Permite estimar la varianza del error entre pliegues.
**Contras:**
- Al mezclar aleatoriamente las observaciones, se rompe el orden cronológico y se introduce fuga de información futura hacia el entrenamiento, lo que genera estimaciones de desempeño poco realistas para datos de series temporales.
- No es apropiado para datos con dependencia temporal, precisamente la característica que define a este componente.

### Alternativa 3: Walk-Forward Validation (Escogida)

**Descripción:** Partición secuencial en la que el origen de pronóstico avanza en el tiempo. En cada iteración, el modelo se entrena únicamente con datos anteriores al origen y se evalúa sobre el punto inmediatamente siguiente, replicando el esquema `t1→t5` valida `t6`, `t1→t6` valida `t7`, y así sucesivamente, bajo un esquema de ventana expansiva (el conjunto de entrenamiento crece en cada iteración en lugar de mantenerse de tamaño fijo).
**Pros:**
- Es reconocido en la literatura de evaluación de pronósticos como el enfoque más apropiado para estimar el error fuera de muestra en datos secuenciales.
- Genera múltiples mediciones de error a lo largo del tiempo en lugar de una sola, lo que permite evaluar también la consistencia del modelo.
- Replica de forma cercana cómo se usaría el modelo en producción, donde se reentrena a medida que llegan nuevas observaciones.
- El esquema de ventana expansiva (en lugar de ventana deslizante de tamaño fijo) es particularmente adecuado para conjuntos de datos o series cortas.
**Contras:**
- Computacionalmente más costoso que un holdout simple, porque requiere reajustar el modelo en cada ventana.

## Decisión

La evaluación fuera de muestra es esencial para estimar la capacidad de generalización de un modelo, especialmente considerando la posibilidad de cambios estructurales o desplazamientos no anticipados en los valores futuros (Tashman, 2000). Dentro de las estrategias de evaluación disponibles, la evaluación con origen rodante ("rolling origin") es ampliamente reconocida como el enfoque más apropiado (Bergmeir & Benítez, 2012), frente a alternativas como el holdout simple o el k-fold aleatorio.
En la práctica tradicional de pronóstico es común reservar solo el tramo final de la serie para prueba, lo que deja sin aprovechar buena parte de los datos disponibles (Bergmeir & Benítez, 2012). El walk-forward corrige esta limitación al generar múltiples splits de entrenamiento/validación a lo largo de toda la serie, respetando siempre el orden cronológico y evitando que datos futuros informen al entrenamiento.
Respecto al esquema de ventana expansiva elegido para la generación de `t1...t9`, la literatura documenta que el conjunto de entrenamiento crece a medida que el origen de pronóstico avanza, y que este esquema resulta particularmente adecuado para conjuntos de datos o series cortas, en contraste con el esquema de ventana deslizante de tamaño fijo (Bell & Smyl, 2018, citado en Cerqueira et al., 2020). Esto es directamente relevante para el caso de SKUs `Intermittent`/`Lumpy`, que suelen tener historiales cortos o dispersos.
Finalmente, el uso de la métrica final agregada sobre todas las ventanas —y no de una sola medición— es coherente con la recomendación de que la evaluación de pronósticos produzca múltiples mediciones de error a través de distintos puntos en el tiempo para obtener una mejor noción de la consistencia del modelo, en lugar de depender de una única partición de prueba.

## Alternativas Descartadas

**Por qué se descartó el Holdout simple:** produce una única medición de error dependiente del período específico reservado como prueba, sin ninguna noción de variabilidad, y no aprovecha completamente los datos disponibles, a diferencia de la evaluación con origen rodante (Bergmeir & Benítez, 2012).
**Cuándo sería la mejor opción:** prototipos rápidos o validaciones preliminares donde el costo computacional del walk-forward no se justifica, o series extremadamente largas donde una sola partición ya es representativa.
**Por qué se descartó el K-fold estándar:** al no respetar el orden cronológico, permite que observaciones futuras informen el entrenamiento de un modelo que luego se evalúa sobre observaciones pasadas, lo cual es incompatible con la dependencia temporal inherente a los datos de series temporales.
**Cuándo sería la mejor opción:** nunca para este dominio; el k-fold aleatorio es apropiado para datos independientes e idénticamente distribuidos, no para series temporales.

## **Consecuencias **

### **Positivas**

- La estimación de error refleja de forma más realista el desempeño esperado en producción, donde los modelos se reentrenan periódicamente.
- Permite comparar de forma homogénea familias de modelos heterogéneas, ya que todas se someten al mismo procedimiento de evaluación completo.
- Reduce el riesgo de seleccionar una configuración que solo luce bien en un período particular de la serie, al promediar el desempeño sobre múltiples ventanas.
- El esquema de ventana expansiva favorece a las series cortas de SKUs `Intermittent`/`Lumpy`, que son un caso especial del sistema.

### **Negativas**

- **Mayor costo computacional que un holdout simple**
- Riesgo: reentrenar el modelo en cada ventana incrementa el tiempo total de evaluación, especialmente si se aplica a un espacio de búsqueda amplio.
- Mitigación: para la familia de modelos clásicos, Walk-Forward no se aplica a todo el espacio de configuraciones candidatas, sino únicamente al top-X preseleccionado mediante AICc, reduciendo el número de ejecuciones de Walk-Forward requeridas.
- **Series muy cortas pueden generar pocas ventanas válidas**
- Riesgo: en SKUs con historiales muy reducidos, el número de splits `t_i→t_{i+1}` disponibles puede ser insuficiente para una estimación robusta.
- Mitigación: se documenta explícitamente la longitud mínima de serie requerida para generar al menos una ventana válida, y se registra cuando una configuración no puede evaluarse por esta razón.

## Referencias

- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: an analysis and review. *International Journal of Forecasting*, 16(4), 437–450.
- Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. *Information Sciences*, 191, 192–213. [https://doi.org/10.1016/j.ins.2011.12.028](https://doi.org/10.1016/j.ins.2011.12.028)
- Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series forecasting models: an empirical study on performance estimation methods. *Machine Learning*, 109(11), 1997–2028. [https://doi.org/10.1007/s10994-020-05910-7](https://doi.org/10.1007/s10994-020-05910-7)
- Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts.
