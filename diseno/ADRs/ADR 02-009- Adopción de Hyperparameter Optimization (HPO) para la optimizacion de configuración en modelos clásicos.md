# ADR-02-009: Adopción de Hyperparameter Optimization (HPO) para la optimizacion de configuración en modelos clásicos

- **Fecha:** 2026-09-01
- **Estado:** Aplicada

## Contexto & Problema

Necesitamos decidir el mecanismo general para seleccionar la configuración interna óptima de los modelos clásicos ARIMA/SARIMA del módulo PRED. El contexto y las restricciones del problema son:
- La familia de modelos de Machine Learning del módulo utiliza un proceso automatizado de optimización de hiperparámetros para seleccionar configuraciones.
- El módulo procesa un volumen alto de SKUs, por lo que la selección debe realizarse automáticamente y sin intervención manual por serie.
- Algunos SKUs presentan historiales cortos o comportamientos `Intermittent`/`Lumpy`, lo que limita la cantidad de información disponible para estimar configuraciones complejas.
Alternativas consideradas:
1. AICc + Walk-Forward Validation
2. BIC + Walk-Forward Validation
3. Selección manual/heurística mediante Box-Jenkins
4. Hyperparameter Optimization sobre Walk-Forward Validation

## Opciones Consideradas

### Alternativa 1: AICc + Walk-Forward Validation

**Descripción:** Ajustar las configuraciones candidatas, ordenarlas mediante AICc y evaluar posteriormente mediante Walk-Forward Validation únicamente un subconjunto de las configuraciones mejor clasificadas.
**Pros:**
- El AICc fue desarrollado como una corrección del AIC para muestras pequeñas y para situaciones donde el número de parámetros representa una fracción importante del tamaño de muestra (Hurvich & Tsai, 1989).
- Permite comparar configuraciones a partir del ajuste estadístico realizado sin requerir inicialmente una evaluación completa fuera de muestra para todas ellas.
- Es utilizado en procedimientos de selección automática de modelos ARIMA, como `auto.arima()` del paquete `forecast` (Hyndman & Khandakar, 2008).
**Contras:**
- Optimiza un criterio de información y no directamente la métrica de error calculada posteriormente mediante Walk-Forward Validation.
- Mantiene dos etapas de selección: una basada en un criterio de información y otra basada en desempeño fuera de muestra.
- La comparación depende del ajuste estadístico y de la estimación de la verosimilitud de cada configuración.

### Alternativa 2: BIC + Walk-Forward Validation

**Descripción:** Ajustar las configuraciones candidatas, ordenarlas mediante BIC y aplicar posteriormente Walk-Forward Validation al subconjunto mejor clasificado.
**Pros:**
- Permite comparar configuraciones penalizando la complejidad del modelo.
- Puede calcularse a partir del ajuste estadístico sin realizar inicialmente una evaluación fuera de muestra para todas las configuraciones.
**Contras:**
- Optimiza un criterio distinto de la métrica de error fuera de muestra utilizada finalmente por el PRED.
- Mantiene una separación entre el criterio utilizado para seleccionar inicialmente configuraciones y la evaluación final.
- Penaliza la complejidad mediante una función dependiente del tamaño de muestra (Schwarz, 1978).

### Alternativa 3: Selección manual/heurística mediante Box-Jenkins

**Descripción:** Determinar la configuración mediante análisis de la serie y de sus estructuras de autocorrelación, siguiendo el procedimiento tradicional de identificación, estimación y diagnóstico de Box-Jenkins.
**Pros:**
- Permite incorporar juicio experto durante la selección del modelo.
- Facilita la interpretación individual de la configuración elegida.
**Contras:**
- Requiere análisis específico por serie.
- No es adecuado como mecanismo principal para procesar automáticamente un volumen alto de SKUs.
- Introduce dependencia de la intervención y del criterio de los analistas.

### Alternativa 4: Hyperparameter Optimization sobre Walk-Forward Validation (Escogida)

**Descripción:** Tratar los órdenes y componentes del modelo como un espacio de configuraciones y seleccionar automáticamente la configuración que minimiza una función objetivo calculada mediante Walk-Forward Validation.
**Pros:**
- La selección puede optimizar directamente la métrica de error fuera de muestra definida para evaluar el módulo.
- Permite automatizar la exploración de configuraciones sin intervención manual por SKU.
- Evita separar conceptualmente el criterio inicial de selección de la evaluación final del desempeño.
- Puede utilizarse un mecanismo común de selección para diferentes familias de modelos.
**Contras:**
- Requiere evaluar múltiples configuraciones mediante Walk-Forward Validation.
- Su costo computacional depende del tamaño del espacio de búsqueda y del presupuesto de optimización.
- Requiere definir explícitamente el espacio de configuraciones y la función objetivo.

## Decisión

La selección de una configuración debe estar alineada con la forma en que el PRED evalúa finalmente su desempeño. Los criterios de información y la evaluación fuera de muestra constituyen procedimientos diferentes: AICc y BIC permiten comparar configuraciones a partir de su ajuste estadístico, mientras que Walk-Forward Validation evalúa el desempeño predictivo sobre observaciones que no estuvieron disponibles durante el entrenamiento correspondiente.
El AICc constituye una corrección del AIC particularmente relevante para muestras pequeñas o cuando el número de parámetros representa una fracción importante del tamaño de muestra (Hurvich & Tsai, 1989). Sin embargo, utilizar AICc como filtro inicial mantiene una diferencia entre el criterio utilizado para seleccionar configuraciones y la métrica de error utilizada posteriormente para compararlas. El mismo problema de alineación existe con BIC, aunque su formulación y penalización de complejidad son diferentes (Schwarz, 1978).
La selección manual mediante la metodología Box-Jenkins constituye un procedimiento fundamental para el análisis individual de modelos de series temporales. Sin embargo, requiere intervención experta y análisis específico por serie, lo que no resulta compatible con el procesamiento automático de un volumen alto de SKUs.
Se opta, en consecuencia, por utilizar Hyperparameter Optimization como mecanismo general para seleccionar la configuración interna de los modelos clásicos del módulo PRED. Las configuraciones de ARIMA/SARIMA se representan como un espacio de búsqueda y cada evaluación se realiza mediante la métrica obtenida sobre Walk-Forward Validation.
Esta decisión permite que el mecanismo de selección optimice directamente el desempeño fuera de muestra definido por el módulo y establece un paradigma común de selección automatizada para las diferentes familias de modelos. La estrategia específica de búsqueda y asignación de recursos utilizada para implementar HPO se define en un ADR independiente.

## Alternativas Descartadas

**Por qué se descartó AICc + Walk-Forward Validation:** aunque AICc está específicamente diseñado para corregir el sesgo del AIC en muestras pequeñas o con una proporción importante de parámetros respecto al tamaño de muestra (Hurvich & Tsai, 1989), utilizarlo como filtro inicial mantiene una diferencia entre el criterio utilizado para seleccionar configuraciones y la métrica de error utilizada posteriormente para compararlas.
**Cuándo sería la mejor opción:** cuando evaluar un espacio amplio de configuraciones mediante Walk-Forward sea computacionalmente prohibitivo y se requiera reducir previamente el número de candidatos.
**Por qué se descartó BIC + Walk-Forward Validation:** el BIC constituye una alternativa establecida para seleccionar modelos, pero sigue siendo un criterio diferente de la métrica de error fuera de muestra utilizada por el módulo (Schwarz, 1978). Utilizarlo como ranking previo mantiene el esquema de selección en dos etapas.
**Cuándo sería la mejor opción:** cuando el objetivo del sistema requiera explícitamente utilizar un criterio de selección basado en la penalización de complejidad del BIC.
**Por qué se descartó la selección manual/heurística mediante Box-Jenkins:** requiere intervención experta y análisis individual de las series, lo que no resulta compatible con el procesamiento automático de un volumen alto de SKUs.
**Cuándo sería la mejor opción:** cuando exista un número reducido de series críticas y se justifique la revisión individual por especialistas.

## **Consecuencias **

### **Positivas**

- La selección de configuraciones puede optimizar directamente la métrica de error fuera de muestra utilizada por el módulo.
- Se elimina la necesidad de utilizar AICc o BIC como etapa obligatoria previa de selección.
- El proceso puede ejecutarse automáticamente para un volumen alto de SKUs.
- Se establece un mecanismo común de selección para diferentes familias de modelos.
- La estrategia concreta de búsqueda puede modificarse sin cambiar el principio general de selección basado en HPO

### **Negativas**

- **Mayor costo computacional que un criterio de información**
- Riesgo: múltiples configuraciones deben ser evaluadas mediante Walk-Forward Validation.
- Mitigación: utilizar un mecanismo de optimización que permita limitar el número de configuraciones evaluadas y asignar recursos progresivamente.
- **Dependencia de la definición del espacio de búsqueda**
- Riesgo: un espacio `(p, d, q, P, D, Q, m)` excesivamente amplio incrementa el costo de evaluación.
- Mitigación: definir explícitamente límites y condiciones válidas para las configuraciones antes de iniciar la optimización.
- **Mayor complejidad operativa**
- Riesgo: el mecanismo requiere gestionar evaluaciones, presupuestos y reproducibilidad.
- Mitigación: separar la decisión del uso de HPO de la decisión sobre su implementación concreta.

- Hurvich, C. M., & Tsai, C.-L. (1989). Regression and time series model selection in small samples. *Biometrika*, 76(2), 297–307. [https://doi.org/10.1093/biomet/76.2.297](https://doi.org/10.1093/biomet/76.2.297)
- Schwarz, G. (1978). Estimating the dimension of a model. *The Annals of Statistics*, 6(2), 461–464. [https://doi.org/10.1214/aos/1176344136](https://doi.org/10.1214/aos/1176344136)
- Box, G. E. P., & Jenkins, G. M. (1970). *Time Series Analysis: Forecasting and Control*. San Francisco: Holden-Day.
- Hyndman, R. J., & Khandakar, Y. (2008). Automatic time series forecasting: The forecast package for R. *Journal of Statistical Software*, 27(3), 1–22. [https://doi.org/10.18637/jss.v027.i03](https://doi.org/10.18637/jss.v027.i03)
- Bergmeir, C., Hyndman, R. J., & Koo, B. (2018). A note on the validity of cross-validation for evaluating autoregressive time series prediction. *Computational Statistics & Data Analysis*, 120, 70–83. [https://doi.org/10.1016/j.csda.2017.11.003](https://doi.org/10.1016/j.csda.2017.11.003)
