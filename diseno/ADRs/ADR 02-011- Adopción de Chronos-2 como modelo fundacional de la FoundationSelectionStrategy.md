# ADR-02-011: Adopción de Chronos-2 como modelo fundacional de la FoundationSelectionStrategy

- **Fecha:** 2026-09-18
- **Estado:** Aceptada

## Contexto & Problema

La arquitectura Router + Strategy (ADR-02-003) define una familia de modelos fundacionales. La documentación 2.7 establece que esa familia no se optimiza con AICc ni HPO: se usa como predictor preentrenado y compite contra Clásicos, ML y DL bajo el mismo Walk-Forward (ADR-03-001). Falta decidir **qué modelo fundacional concreto** se integra.

Restricciones del problema:
- **Datos:** series diarias por SKU, con zero-filling (ADR-01-006) y clasificadas por Syntetos-Boylan. Una parte relevante es `Intermittent`/`Lumpy`, con historiales cortos y mayoría de ceros.
- **Presupuesto de cómputo bajo:** la mayor parte del cómputo ya la consume HPO + ASHA (ADR-02-009, ADR-02-005). El modelo debe poder correr en CPU o en una GPU modesta.
- **Evaluación:** Walk-Forward con ventana expansiva exige una inferencia por cada origen de pronóstico y por cada SKU. El modelo tiene que ser rápido en inferencia por lotes.
- **Licencia:** PRED se presenta como sistema de código abierto, auditable y de costo cero de licencia para empresas y PyMEs (ver Estado del Arte). Los pesos del modelo deben permitir uso comercial y en producción.
- **Reproducibilidad:** el protocolo exige resultados deterministas y trazables (ADR-01-003).
- **Volatilidad del campo:** el ranking de TSFM cambia cada pocos meses. La decisión debe poder revisarse sin tocar el Router.
Alternativas consideradas:
1. Chronos-2 (Amazon)
2. TimesFM 2.5 (Google)
3. TimesFM-3 (Google)
4. Moirai (1.x / 2.0) (Salesforce)
5. TiRex (NX-AI)
6. TimeGPT (Nixtla, vía API)

## Opciones Consideradas

#### Alternativa 1: Chronos-2 (Escogida)

**Descripción:** Modelo encoder-only de 120M de parámetros para pronóstico zero-shot, que soporta tareas univariadas, multivariadas y con covariables en una sola arquitectura y produce pronósticos multi-paso por cuantiles.
**Pros:**
- **Estado del arte en benchmarks independientes.** Reporta desempeño de estado del arte en tres benchmarks amplios: fev-bench, GIFT-Eval y Chronos Benchmark II. En fev-bench alcanza una tasa de victoria promedio de 90.7% y un skill score de 47.3%, por encima del siguiente mejor modelo, TiRex (80.8% y 42.6%).
- **Aprendizaje cruzado entre SKUs.** En tareas univariadas, el in-context learning permite compartir información entre ítems de un mismo lote y produce pronósticos más precisos que la inferencia univariada aislada. Esto es relevante para SKUs con poco historial.
- **Eficiencia y hardware.** Genera más de 300 pronósticos por segundo en una sola GPU A10G y soporta inferencia en GPU y CPU. Hay benchmarks que ejecutan Chronos-2 en hardware de consumo (AMD Ryzen 7, 16 GB de RAM, sin GPU).
- **Capacidad de contexto y horizonte.** Acepta hasta 8192 pasos de contexto y 1024 de predicción, frente a 2048/64 de Chronos-Bolt. En datos diarios esto cubre más de 20 años de historia.
- **Licencia.** Se distribuye bajo Apache-2.0.
- **Preparado para covariables.** Soporta de forma nativa covariables pasadas y futuras conocidas, mientras que Chronos y Chronos-Bolt necesitan regresores externos. Deja abierta una evolución futura (promociones, festivos) sin cambiar de modelo.
- **Salida probabilística determinista.** Emite cuantiles directamente, sin muestreo estocástico. Con versión fija, el resultado es reproducible.
**Contras:**
- **Sesgo negativo en demanda intermitente.** En el benchmark más cercano al dominio de PRED, los TSFM líderes en precisión sub-pronosticaron de forma acumulada y entregaron menor nivel de servicio bajo la misma política de inventario. Los autores atribuyen parte del sesgo a la normalización: Chronos-2 centra la serie en una media dominada por ceros, lo que puede contribuir al sesgo negativo observado.
- **El fine-tuning no ayudó en series intermitentes.** En un barrido de 31 configuraciones de fine-tuning con LoRA, ninguna superó a Chronos-2 zero-shot. Esto refuerza el uso zero-shot, pero elimina una palanca de mejora.
- **Benchmarks generales no representativos del dominio.** Los benchmarks que hoy se usan para rankear TSFM (Monash, GIFT-Eval) están dominados por series suaves y regulares, con poca demanda cero-inflada. El liderazgo en GIFT-Eval no garantiza liderazgo sobre los SKUs de PRED.

#### Alternativa 2: TimesFM 2.5

**Descripción:** Modelo decoder-only de Google basado en parches. Está disponible como TimesFM 2.0 (500M de parámetros) y TimesFM 2.5 (200M de parámetros, contexto de 16K).
**Pros:**
- **Licencia permisiva.** Los checkpoints de TimesFM 1.0 a 2.5 permanecen bajo Apache-2.0.
- **Buen desempeño en demanda intermitente.** En el panel público RAF de repuestos, los Chronos-Bolt, TimesFM y un modelo de gradient boosting por cuantiles lideraron, mientras que Moirai tuvo un error mucho mayor.
- **Madurez y ecosistema.** Tiene integración con BigQuery y es el modelo que ya se mencionaba en la documentación del proyecto.
**Contras:**
- **Solo univariado.** Hasta TimesFM 2.5 los modelos estaban limitados a pronóstico univariado, es decir, solo con la historia de la propia serie. No permite aprendizaje cruzado entre SKUs ni covariables nativas.
- **Superado en los benchmarks generales.** En GIFT-Eval, Chronos-2 obtiene 81.9% de tasa de victoria y 51.4% de skill score, por encima de TimesFM-2.5 y TiRex.
- **Más costoso en cómputo.** Tiene más parámetros que Chronos-2. Algunos benchmarks en hardware sin GPU excluyeron TimesFM por requerir aceleración GPU para inferencia.
- **El mismo sesgo en intermitentes.** TimesFM también mostró deriva acumulada negativa (−8.3), con solo 51% de materiales sobre-pronosticados.

#### Alternativa 3: TimesFM-3

**Descripción:** Modelo de 330M de parámetros, preentrenado de forma nativa para pronóstico multivariado con más de un billón de puntos temporales. Obtiene el mejor rango promedio entre los modelos fundacionales en GIFT-Eval, fev-bench y el leaderboard TIME.
**Pros:**
- Probablemente el mejor modelo general disponible a la fecha de este ADR.
- Es multivariado y acepta covariables pasadas y futuras.
**Contras:**
- **Licencia incompatible con el objetivo de PRED.** El código del repositorio es Apache-2.0, pero los pesos de TimesFM 3.0 usan la timesfm-non-commercial-license-v1.0, restringida a uso no comercial y no productivo.
- **Evidencia limitada.** Fue publicado el 31 de agosto de 2026. Todavía no hay evaluaciones independientes sobre demanda intermitente, y los resultados disponibles son autorreportados.

#### Alternativa 4: Moirai (1.x / 2.0)

**Descripción:** Familia de Salesforce con atención any-variate. Moirai 2.0 es un modelo decoder-only basado en parches que usa predicción multi-token y emite nueve niveles de cuantiles por paso.
**Pros:**
- Arquitectura flexible para cualquier frecuencia y número de variables.
- Moirai-2.0-R-small se distribuye bajo Apache-2.0.
**Contras:**
- **Licencia restrictiva en 1.x.** Moirai-1.1-R-large está bajo CC-BY-NC-4.0.
- **Mal desempeño en datos intermitentes y dispersos.** Moirai quedó en el puesto 34 de 38 métodos en el panel industrial y 32 en RAF, con un MASE por material de 14.2 en RAF. En pronóstico anual con datos escasos, las variantes de Moirai quedaron detrás de Chronos-Bolt, Chronos-2 y TimesFM.

#### Alternativa 5: TiRex

**Descripción:** Modelo de NX-AI basado en xLSTM (NeurIPS 2025). Es competitivo en GIFT-Eval y fev-bench.
**Pros:**
- Fuerte desempeño en horizontes cortos y largos.
- Arquitectura eficiente.
**Contras:**
- **Licencia.** TiRex 1.0 usa la NXAI Community License, con límites comerciales para empresas grandes. Aunque la misma fuente indica que TiRex 2.0 pasó a Apache-2.0, la versión 2.0 es reciente y tiene poca evidencia en demanda intermitente.
- En fev-bench quedó por debajo de Chronos-2 (ver Alternativa 1).

#### Alternativa 6: TimeGPT (Nixtla, API)

**Descripción:** Modelo propietario al que se accede mediante API.
**Pros:**
- Cero infraestructura local.
**Contras:**
- Se usa como servicio alojado con API key; en producción queda sujeto a los términos y precios de Nixtla, sin pesos abiertos.
- Rompe tres principios del proyecto: código abierto y costo cero, reproducibilidad offline, y confidencialidad de los datos (la demanda de la empresa saldría a un tercero).

## Decisión

Se adopta **Chronos-2** (`amazon/chronos-2`, Apache-2.0) como modelo fundacional principal de la `FoundationSelectionStrategy`, en **modo zero-shot y sin fine-tuning**.

#### Justificación

**Por qué un modelo fundacional zero-shot.** Es coherente con 2.7: el modelo ya viene preentrenado y no se optimiza. La evidencia en demanda intermitente muestra que adaptarlo tampoco rinde: ninguna de 31 configuraciones LoRA superó a Chronos-2 zero-shot (Chin et al., 2026).
**Por qué Chronos-2 y no TimesFM-3.** TimesFM-3 es posiblemente superior en benchmarks generales, pero su licencia prohíbe el uso en producción. Eso contradice el diferenciador de PRED como sistema abierto de costo cero de licencia.
**Por qué Chronos-2 y no TimesFM 2.5 como principal.** Chronos-2 supera a TimesFM 2.5 en GIFT-Eval y fev-bench, tiene menos parámetros y permite aprendizaje cruzado entre SKUs. Ninguno de los dos está libre del sesgo negativo en intermitentes.
**Por qué no Moirai, TiRex ni TimeGPT.** Moirai tiene licencias restrictivas y es el fundacional con peor desempeño documentado en datos intermitentes. TiRex tiene restricciones de licencia en 1.x y poca evidencia en 2.0. TimeGPT es incompatible con la apertura, la reproducibilidad y la confidencialidad del sistema.

### Alternativas Descartadas

**TimesFM-3**
- *Por qué se descartó:* los pesos no permiten uso comercial ni en producción.
- *Cuándo sería la mejor opción:* si Google libera los pesos bajo Apache-2.0, o como referencia puramente académica en el benchmark del Módulo 4, siempre que el documento de tesis lo declare explícitamente.
**TimesFM 2.5 como modelo principal**
- *Por qué se descartó:* es solo univariado, rinde menos que Chronos-2 en los benchmarks generales y tiene mayor costo por inferencia.
- *Cuándo sería la mejor opción:* si en el piloto supera de forma significativa a Chronos-2 sobre los SKUs reales.
**Moirai**
- *Por qué se descartó:* licencia no comercial en 1.x y peor desempeño documentado en demanda intermitente.
- *Cuándo sería la mejor opción:* en series multivariadas suaves de alta frecuencia (energía, operaciones de nube).
**TiRex**
- *Por qué se descartó:* licencia con restricciones en 1.x y evidencia limitada en 2.0.
- *Cuándo sería la mejor opción:* si una evaluación independiente sobre demanda intermitente lo favorece y se confirma la licencia Apache-2.0 de la versión 2.0.
**TimeGPT**
- *Por qué se descartó:* es propietario, tiene costo, saca los datos del sistema y no garantiza reproducibilidad.
- *Cuándo sería la mejor opción:* en prototipos sin restricciones de confidencialidad ni de presupuesto.

## **Consecuencias **

### **Positivas**

- La familia fundacional queda definida con un modelo de estado del arte, con licencia permisiva y que corre en el hardware disponible.
- El costo en Walk-Forward es bajo: cada ventana es solo una inferencia, sin reentrenamiento. Además se puede procesar por lotes de SKUs en cada origen.
- La salida probabilística queda disponible para una futura evaluación por cuantiles (pinball loss o CRPS) y para decisiones de inventario.
- La interfaz Strategy permite reemplazar o añadir modelos fundacionales sin tocar el Router, lo que absorbe la volatilidad del campo.

### **Negativas**

**Sub-pronóstico sistemático en SKUs `Intermittent`/**`Lumpy`**
- *Riesgo:* el modelo puede ganar en precisión y perder en nivel de servicio (Chin et al., 2026).
- *Mitigación:* reportar el sesgo con signo en el Módulo 3. Como trabajo futuro documentado queda la corrección por re-centrado en la media no nula, que los autores aplicaron sin reentrenar.
**Contaminación por datos de preentrenamiento**
- *Riesgo:* los corpus de preentrenamiento pueden incluir datasets públicos. Si el Módulo 0 simula datos a partir de datasets como M5, el modelo pudo haberlos visto. El preentrenamiento sobre grandes volúmenes de series extraídas de repositorios públicos introduce riesgos de evaluación similares a los observados en LLMs. [arXiv](https://arxiv.org/html/2510.13654v1)
- *Mitigación:* documentar el origen de los datos del Módulo 0. Preferir datos propios o simulados que no deriven de datasets públicos conocidos.
**Obsolescencia rápida de la elección**
- *Riesgo:* el modelo puede ser superado en meses.
- *Mitigación:* versionado fijo, revisión semestral de este ADR, y estrategia intercambiable.
**Dependencia de una librería externa (`chronos-forecasting`)**
- *Riesgo:* cambios de API entre versiones.
- *Mitigación:* fijar la versión en el entorno y envolver el modelo en un adaptador propio dentro de la estrategia.

## Referencias

- Ansari, A. F., et al. (2024). Chronos: Learning the language of time series. *Transactions on Machine Learning Research*.
- Ansari, A. F., et al. (2025). Chronos-2: From univariate to universal forecasting. arXiv:2510.15821.
- Das, A., Kong, W., Sen, R., & Zhou, Y. (2024). A decoder-only foundation model for time-series forecasting. *Proceedings of ICML 2024* (PMLR 235).
- Woo, G., et al. (2024). Unified training of universal time series forecasting transformers. *Proceedings of ICML 2024*.
- Liu, C., et al. (2025). Moirai 2.0: When less is more for time series forecasting. arXiv:2511.11698.
- Auer, A., et al. (2025). TiRex: Zero-shot forecasting across long and short horizons with enhanced in-context learning. *NeurIPS 2025*. arXiv:2505.23719.
- Aksu, T., et al. (2024). GIFT-Eval: A benchmark for general time series forecasting model evaluation. *NeurIPS Workshop on Time Series in the Age of Large Models*. arXiv:2410.10393.
- Shchur, O., et al. (2025). fev-bench: A realistic benchmark for time series forecasting. arXiv:2509.26468.
- Chin, J. E., Cheng, S.-F., & Gunawan, A. (2026). Accuracy is not service: A decision-aware benchmark for intermittent-demand forecasting. arXiv:2609.13840.
- Time series foundation models: Benchmarking challenges and requirements (2025). arXiv:2510.13654.
- Time series foundation models for energy load forecasting on consumer hardware (2026). arXiv:2602.10848.
- Bergmeir, C. (2024). LLMs and foundational models: Not (yet) as good as hoped. *Foresight: The International Journal of Applied Forecasting*, 73, 33–38.
- Syntetos, A. A., Boylan, J. E., & Croston, J. D. (2005). On the categorization of demand patterns. *Journal of the Operational Research Society*, 56(5), 495–503.
- Google Research (2026). TimesFM-3: A zero-shot foundation model for multivariate forecasting (blog y model card).
