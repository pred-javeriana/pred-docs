## Contexto & Problema

El Motor de Selección y Optimización de Predictores (Módulo 2) necesita tener una cantidad de datos suficiente para poder tomar desiciones confiables incluso para tipos de datos como intermittent o lumpy con una cantidad de datos reducidas por esto se debe decidir como aumentar los datos de entrenamiento disponibles por SKU antes de llegar al modulo 2, esta decisión debe tener en cuenta lo siguiente:

- Series por SKU frecuentemente cortas: los SKU clasificados como Intermittent o Lumpy pueden tener menos de 2 ciclos estacionales completos de historia.
- Un presupuesto de cómputo bajo ya que se utiliza la mayoria de los recursos en la fase de optimizacion del modulo 2.

Alternativas consideradas:

1. Sin Aumento de Datos
2. Generación Sintética vía GAN Condicional (T-CGAN / TTS-CGAN)
3. Moving Block Bootstrap (MBB)

## Opciones Consideradas

### Alternativa 1: Sin Aumento de Datos

**Descripción:** Opitimizar directamente sobre los datos reales disponibles por SKU, sin ningún paso de aumento previo.

**Pros:**

- Cero complejidad adicional: no hay técnica que calibrar, mantener ni versionar.
- Cero riesgo de introducir sesgo o ruido artificial que contamine la validación.
- Cero costo computacional adicional sobre el presupuesto ya comprometido para la fase de optimizacion.
- Es la línea base contra la que cualquier técnica de aumento debe demostrar que vale la pena, evitando adoptar complejidad no justificada.

**Contras:**

- En SKU Lumpy/Intermittent con series muy cortas, el volumen de datos reales puede ser insuficiente para que ML/DL generalicen, incluso con HPO bien calibrado.
- Ignora evidencia empírica directa de que, en el esquema de clasificación ADI-CV, la augmentación mejora el desempeño de forecasting frente al baseline sin aumento (Yun et al., 2025).
- Deja sobre la mesa una ganancia de desempeño documentada específicamente para el caso de datasets pequeños (Iwana & Uchida, 2021; Semenoglou et al., 2023).

### Alternativa 2: Generación Sintética vía GAN Condicional (T-CGAN / TTS-CGAN)

**Descripción:** Entrenar una GAN condicionada a `sku_class` sobre el conjunto de SKU de cada categoría, generando series sintéticas adicionales que se agrupan con los datos reales antes de optimizar.

**Pros:**

- Capacidad de aprender y reproducir la distribución completa de la demanda, no solo remuestrear observaciones existentes.
- Puede generar series en timestamps no observados si se condiciona explícitamente en el tiempo puntualmente opciones como T-CGAN.

**Contras:**

- Requiere un volumen de datos considerablemente mayor que MBB para no colapsar: existe evidencia consistente de que GAN entrenadas con muestras pequeñas producen colapso completo o memorización severa del generador (Kong et al., 2021), y que su calidad se degrada fuertemente a medida que el tamaño de entrenamiento disponible decrece (Desai et al., 2021).
- Costo computacional de generación significativamente mayor: en el benchmark comparable más riguroso disponible, generar series sintéticas con una técnica generativa tomó ~40 veces más tiempo que con MBB (Bandara et al., 2021).
- Compite directamente por el mismo presupuesto ya asignado a la optimizacion, sin garantía de que el retorno justifique el costo en todas las categorías `sku_class`.
- En el único estudio disponible con el esquema de clasificación ADI-CV, esta familia de técnicas (T-CGAN/TTS-CGAN) fue superada por MBB en las 4 categorías evaluadas (Yun et al., 2025).

### Alternativa 3: Moving Block Bootstrap — MBB (Escogida)

**Descripción:** Descomponer la serie de cada SKU vía STL en tendencia, estacionalidad y residuo; remuestrear el residuo en bloques consecutivos (preservando su estructura de autocorrelación); y recombinar con la tendencia y estacionalidad originales para producir series sintéticas adicionales, que se agrupan con los datos reales antes de optimizar.

**Pros :**

- No depende del tamaño del grupo `sku_class` al operar por SKU individual
- Costo de generación ~40x menor que una técnica generativa (Bandara et al., 2021)
- Al operar sobre el residuo evitamos inventar demandas o modificar el comportamiento base que al final es el que se intenta pronosticar
- Un solo parametro que calibrar, el largo del bloque.
- Mejor evidencia empírica en el estudio con el esquema ADI-CV
- Método validado específicamente para forecasting desde 2016

**Contras de MBB:**

- No aplica a SKU con menos de 2 ciclos estacionales de historia
- Menos consistente en datos de baja frecuencia (anual/trimestral)
- No puede condicionarse a variables exógenas o timestamps específicos como T-CGAN

## Decisión

## MBB como unico metodo de aumentacion

## Justificación

**Por qué MBB y no Sin Aumento:**
No aplicar ningún aumento en las categorías con menos datos (Intermittent, Lumpy) deja corta la posibilidad de un modelo que refleje el comportamiento importante y real de los datos, ademas la evidencia empírica (Yun et al., 2025; Semenoglou et al., 2023) muestra una ganancia consistente de desempeño frente al baseline sin aumento quando el set original es pequeño, que es el caso predominante en esas categorías.

**Por qué MBB y no GAN Condicional:**
El costo y el piso mínimo de datos de una estrategia GAN condicional son grandes contra los recursos disponibles y con el hecho de que, precisamente, las categorías que más se beneficiarían de un aumento (Intermittent, Lumpy) son las que tienen menos SKU y menos observaciones por SKU disponibles para entrenar una GAN garantizando resultados confiables. MBB no depende del tamaño del grupo, opera con un costo de generacion con orden de magnitud menor, y en el único estudio con el esquema de clasificación del sistema superó a T-CGAN/TTS-CGAN en las 4 categorías evaluadas.

## **Consecuencias**

### **Positivas**

1. **Costo de generación bajo:** MBB no compite de forma significativa con los recursos ya asignados a la fase de optimizacion, a diferencia de una GAN.
2. **No depende del tamaño del grupo `sku_class`:** funciona igual de bien sea cual sea la cantidad de SKU en esa categoría, siempre que tenga el minimo necesario de datos (Dos estaciones), a diferencia de las técnicas generativas.
3. **Un solo parametro que calibrar:**  En MBB solo se necesita asignar un largo de bloque lo cual es perfecto contra la necesidad calibración mucho mayor de una arquitectura GAN.
4. **Preserva la estructura de autocorrelación real de cada serie:** MBB mezcla el ruido evitando inventar demanda que no refleje realmente el comportamiento real.

### **Negativas**

1. **El desempeño de MBB en datos de baja frecuencia (anual/trimestral) es menos consistente que en datos de mayor frecuencia**, según el propio paper original de la técnica (Bergmeir et al., 2016).
    - *Riesgo:* Si en el futuro el sistema interactua con SKU con series agregadas a frecuencia mensual o menor, MBB podría no ofrecer la misma ganancia.
    - *Mitigación:* MBB es una solucion al dataset de prueba no un componente que se integre de manera obligatoria al sistema.

## Referencias

Yun, Park, Chung (2025). *Enhancing Demand Forecasting Performance Using Deep Learning and Time Series Data Augmentation Techniques.* IJISAE. https://ijisae.org/index.php/IJISAE/article/view/7895

Bandara, Hewamalage, Liu, Kang, Bergmeir (2021). *Improving the Accuracy of Global Forecasting Models using Time Series Data Augmentation.* Pattern Recognition. https://arxiv.org/abs/2008.02663

Bergmeir, Hyndman, Benítez (2016). *Bagging exponential smoothing methods using STL decomposition and Box-Cox transformation.* International Journal of Forecasting. https://www.sciencedirect.com/science/article/abs/pii/S0169207015001120

Semenoglou, Spiliotis, Assimakopoulos (2023). *Data augmentation for univariate time series forecasting with neural networks.* Pattern Recognition. https://www.sciencedirect.com/science/article/abs/pii/S0031320322006124

Iwana & Uchida (2021). *An empirical survey of data augmentation for time series classification with neural networks.* PLOS ONE. https://arxiv.org/abs/2007.15951

Desai et al. (2021). *TimeVAE: A Variational Auto-Encoder for Multivariate Time Series Generation.* arXiv:2111.08095. https://arxiv.org/abs/2111.08095

Kong, Kim, Han, Kwak (2021). *Few-shot Image Generation with Mixup-based Distance Learning.* arXiv:2111.11672. https://arxiv.org/abs/2111.11672
