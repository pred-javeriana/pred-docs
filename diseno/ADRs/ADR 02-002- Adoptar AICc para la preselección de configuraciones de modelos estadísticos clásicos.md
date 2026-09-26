# ADR-02-002: Adoptar AICc para la preselección de configuraciones de modelos estadísticos clásicos

- **Fecha:** 2026-08-29
- **Estado:** Depreciada

## Contexto & Problema

Antes de someter una configuración candidata de ARIMA/SARIMA (`p,d,q` / `P,D,Q,m`) al proceso completo de Walk-Forward (ADR-02-001), necesitamos un mecanismo que permita rankear y filtrar el espacio de configuraciones candidatas de forma económica, sin incurrir en el costo de evaluarlas todas mediante Walk-Forward. El contexto y las restricciones del problema son:
- Elegir la configuración por menor error de entrenamiento favorece el sobreajuste: se necesita alguna forma de penalizar la complejidad del modelo, no solo su ajuste a los datos observados.
- Un número relevante de SKUs del sistema (`Intermittent`/`Lumpy`) tiene pocas observaciones (`n`) en relación con el número de parámetros estimados (`k`) de las configuraciones candidatas.
- El mecanismo de preselección no debería tratar de forma distinta a los SKUs únicamente por el tamaño de su historial: su comportamiento debe ser razonable tanto en series muy cortas como en series con mucho historial.
- El mecanismo debe permitir identificar y descartar de forma explícita las configuraciones cuyo resultado no sea válido o comparable (por ejemplo, cuando no exista suficiente información para calcularlo).
Alternativas consideradas:
1. AIC estándar
2. BIC
3. AICc

## Opciones Consideradas

### Alternativa 1: AIC estándar

**Descripción:** Usar el criterio de información de Akaike sin corrección, `AIC = 2k − 2·log-verosimilitud`.
**Pros:**
- Ampliamente conocido y utilizado.
- Asintóticamente eficiente para fines predictivos.
**Contras:**
- Presenta un sesgo hacia el sobreajuste conocido cuando el tamaño de muestra no es sustancialmente mayor que el número de parámetros, situación habitual en SKUs `Intermittent`/`Lumpy` con pocas observaciones (Hurvich & Tsai, 1989).
- Diversos autores señalan que, siempre que el tamaño de muestra sea pequeño, es necesaria algún tipo de corrección sobre el AIC estándar (Burnham & Anderson, 2002, citados en la documentación de la función AICc).

### Alternativa 2: BIC

**Descripción:** Usar el Criterio de Información Bayesiano, que penaliza la complejidad del modelo de forma más fuerte que el AIC (`BIC = k·log(n) − 2·log-verosimilitud`).
**Pros:**
- Es consistente: bajo ciertas condiciones, selecciona el modelo generador verdadero cuando este se encuentra entre los candidatos y `n` tiende a infinito.
- Penaliza más fuertemente la complejidad, lo que puede reducir el sobreajuste en algunos contextos.
**Contras:**
- El objetivo del BIC es identificar el modelo generador "verdadero", mientras que el AIC (y su versión corregida) están orientados a la capacidad predictiva; la elección entre uno y otro depende de qué se asume sobre la realidad y del propósito de la inferencia, no de una preferencia bayesiana o frecuentista (Aho, Derryberry & Peterson, 2014).
- Dado que el objetivo del sistema es la capacidad predictiva de las configuraciones (y no identificar el proceso generador verdadero de cada SKU), un criterio orientado a consistencia como el BIC no está alineado con el objetivo de negocio.

### Alternativa 3: AICc (Escogida)

**Descripción:** Usar `AICc = AIC + [2k(k+1)]/(n−k−1)`, la corrección de Hurvich & Tsai (1989) al AIC estándar para regresión y modelos de series temporales.
**Pros:**
- Corrige el sesgo de sobreajuste del AIC estándar específicamente en muestras pequeñas o cuando el número de parámetros es una fracción moderada a grande del tamaño de muestra (Hurvich & Tsai, 1989).
- Converge al AIC estándar cuando `n` es grande, por lo que no penaliza innecesariamente a los SKUs con historiales largos.
- Es el criterio por defecto para la selección automática de orden en modelos ARIMA/SARIMA en herramientas de referencia de la industria: el algoritmo de Hyndman & Khandakar (2008), implementado en la función `auto.arima`, combina pruebas de raíz unitaria, minimización de AICc y estimación por máxima verosimilitud.
- Un estudio de simulación mostró que, incluso en tamaños de muestra moderados, AICc produce selecciones de modelo sustancialmente mejores que el AIC estándar cuando el proceso generador es una autorregresión de orden infinito (Hurvich & Tsai, 1989).
**Contras:**
- Al igual que el AIC, sigue siendo un criterio calculado en muestra (in-sample); no reemplaza una validación fuera de muestra.
- Requiere un denominador `n−k−1` positivo; para configuraciones con muchos parámetros sobre series muy cortas, el valor puede volverse no finito o indeterminado.

## Decisión

El objetivo de este componente no es identificar el proceso generador "verdadero" de cada SKU, sino obtener una preselección económica de configuraciones con buena capacidad predictiva antes de invertir en la evaluación completa por Walk-Forward. Esto orienta la elección hacia la familia AIC (orientada a predicción) y no hacia BIC (orientada a consistencia/identificación del modelo verdadero) (Aho, Derryberry & Peterson, 2014).
Dentro de la familia AIC, se elige la versión corregida AICc porque el AIC estándar presenta un sesgo de sobreajuste documentado cuando el tamaño de muestra no es sustancialmente mayor que el número de parámetros estimados (Hurvich & Tsai, 1989), que es precisamente el escenario típico de los SKUs `Intermittent`/`Lumpy` con pocas observaciones. Además, distintos autores recomiendan usar AICc de forma prácticamente universal en lugar del AIC estándar, dado que converge a este último cuando `n` es grande y por tanto no introduce ninguna penalización adicional en series largas.
La adopción de AICc es también consistente con la práctica establecida en herramientas de referencia para pronóstico automático de ARIMA/SARIMA, donde el algoritmo de selección de orden usa por defecto la minimización de AICc (Hyndman & Khandakar, 2008), lo que refuerza que se trata de un criterio validado y ampliamente adoptado para este tipo exacto de problema (selección de orden `p,d,q`/`P,D,Q,m`).

## Alternativas Descartadas

**Por qué se descartó el AIC estándar:** presenta un sesgo de sobreajuste documentado cuando el tamaño de muestra no es sustancialmente mayor que el número de parámetros, exactamente la situación habitual en SKUs `Intermittent`/`Lumpy` (Hurvich & Tsai, 1989).
**Cuándo sería la mejor opción:** si el sistema únicamente tratara SKUs con historiales largos donde `n` es sustancialmente mayor que `k` para todas las configuraciones candidatas, el AIC estándar y el AICc producirían resultados prácticamente idénticos.
**Por qué se descartó el BIC:** su objetivo es identificar el modelo generador verdadero, no maximizar la capacidad predictiva fuera de muestra, que es el objetivo de este componente (Aho, Derryberry & Peterson, 2014).
**Cuándo sería la mejor opción:** en contextos donde el objetivo explícito es la identificación o interpretación del proceso generador de los datos (inferencia causal/estructural) y no únicamente la precisión del pronóstico.

## **Consecuencias **

### **Positivas**

- Reduce el riesgo de seleccionar configuraciones sobreajustadas en SKUs con pocas observaciones, sin necesidad de ejecutar Walk-Forward sobre todo el espacio de búsqueda.
- Al converger al AIC estándar para `n` grande, no penaliza artificialmente a los SKUs con historiales largos.
- Se alinea con una práctica de la industria ya validada (selección automática de orden ARIMA basada en AICc).
- Reduce el costo computacional total del pipeline, ya que solo el top-X según AICc se somete a Walk-Forward.

### **Negativas**

- **AICc sigue siendo un criterio en muestra**
- Riesgo: una configuración con buen AICc podría no generalizar bien fuera de muestra.
- Mitigación: AICc se usa exclusivamente como filtro/ranking previo; la decisión final se basa en el resultado de Walk-Forward sobre el top-X (ADR-001), no directamente en el valor de AICc.
- **Riesgo de AICc no finito o indeterminado en series muy cortas con configuraciones complejas**
- Riesgo: cuando `n−k−1` se acerca a cero, el término de corrección se dispara o se vuelve indeterminado.
- Mitigación: estas configuraciones se descartan explícitamente y su motivo de descarte queda registrado.
