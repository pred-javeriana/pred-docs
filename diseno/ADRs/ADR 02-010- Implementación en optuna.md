# ADR-02-010: Implementación en optuna

- **Fecha:** 2026-09-08
- **Estado:** Aceptada

## Contexto & Problema

ADR-02-009 adoptó Hyperparameter Optimization sobre AICc/BIC/Box-Jenkins para la selección de configuración de modelos clásicos, y en su texto difiere explícitamente una decisión: *"la estrategia específica de búsqueda y asignación de recursos utilizada para implementar HPO se define en un ADR independiente"*. ADR-02-004 decidió que el motor temporal (`EjecutorGreedy`) debe ser agnóstico — *"no sabe qué es ASHA"* — y que la decisión de podar se delega *"exclusivamente al optimizador (Componente 5)"*. ADR-02-005 decidió que esa asignación de recursos es ASHA asíncrono: *"cada worker solicita métricas parciales al GreedyRunner y decide podar asincrónicamente comparando contra las métricas ya registradas, requiriendo un mínimo de 4 ventanas antes de descartar"*.
Ninguno de estos tres ADR resuelve **con qué biblioteca o implementación** se construyen el muestreador (componente 4) y el registro de trials (componente 9). Se implementó primero una versión propia en NumPy (`MuestreadorTPE`, `AsignadorRecursosASHA`, `RegistroEstudio` con volcado JSONL propio). Este ADR evalúa esa decisión contra las alternativas reales disponibles y documenta la decisión final.
Alternativas consideradas:
1. Mantener la implementación propia en NumPy
2. Adoptar Optuna solo como sampler (conservando el registro y el pruner propios)
3. Adopción completa de Optuna (`Study` + `TPESampler` + pruner propio sobre `BasePruner`)

## Opciones Consideradas

### Alternativa 1: Mantener la implementación propia en NumPy

**Descripción:** TPE univariado implementado a mano, `AsignadorRecursosASHA` y `RegistroEstudio` propios, con volcado/reanudación en un formato JSONL diseñado desde cero.
**Pros:**
- Cero dependencias nuevas obligatorias — Optuna requiere `sqlalchemy>=1.4.2` como dependencia dura de instalación (verificado), incluso sin usar su backend de persistencia en disco.
- Ya integrado sin capa adaptadora con `EjecutorGreedy`.
- Auditoría en un solo repositorio: el algoritmo completo vive en el git history del proyecto.
**Contras:**
- TPE univariado — asume independencia entre `p`/`P`, `d`/`D`, `q`/`Q` en SARIMA. Bergstra, Bardenet, Bengio y Kégl (2011) señalan que un espacio con estructura jerárquica o correlacionada se beneficia de capturar esas dependencias, algo que la versión multivariada del algoritmo hace y la implementación propia no.
- Exposición a casos borde muy inferior a la de una librería usada en producción a escala industrial desde 2019 (Akiba, Sano, Yanase, Ohta y Koyama, 2019).
- Cualquier mejora futura (TPE multivariado, nuevos samplers) exige trabajo de mantenimiento propio en vez de una actualización de versión.

### Alternativa 2: Optuna solo como sampler

**Descripción:** `TPESampler` de Optuna invocado vía `ask()`/`tell()` únicamente para proponer configuraciones; `AsignadorRecursosASHA` y `RegistroEstudio` propios sin cambios.
**Pros:**
- Aprovecha el sampler más maduro sin reescribir la lógica de poda/registro ya probada.
- Menor superficie de cambio inicial.
**Contras:**
- Mantiene dos representaciones paralelas de cada trial: el `FrozenTrial` interno que Optuna ya gestiona (con estados `RUNNING`/`COMPLETE`/`PRUNED`/`FAIL`/`WAITING`, verificado en `optuna.trial.TrialState`) y el `Trial` propio — duplicación sin necesidad, ya que Optuna **ya distingue nativamente** "podado" de "fallido" (`PRUNED` vs. `FAIL`), que es exactamente la regla de seguridad #4 que el proyecto necesita.
- La reanudación seguiría dependiendo de un formato JSONL propio, en vez de `optuna.trial.create_trial` + `study.add_trial`, que existen para esto exactamente y fueron verificados con una prueba de round-trip real.
- Se agrega la dependencia (`sqlalchemy` transitiva) sin capturar el beneficio que la justifica: un `Study` como fuente única de verdad.

### Alternativa 3: Adopción completa de Optuna (Escogida)

**Descripción:** `optuna.Study` como única fuente de verdad de los trials; `TPESampler(multivariate=True)` como muestreador; `PodadorASHA(optuna.pruners.BasePruner)` reimplementando las reglas de ASHA del dominio (piso de 4 ventanas, agregación recortada por escalón) sobre `trial.intermediate_values`/`study.get_trials()`. El contrato externo (`Trial`/`ResultadoEstudio` de `comun.dataclasses.hpo`, ya consumido por `classical_selection.py`) se preserva, traducido desde el `Study` al finalizar el estudio.
**Pros:**
- Fuente única de verdad: un solo objeto (`Study`) rastrea cada trial; no se mantiene una segunda estructura paralela.
- `multivariate=True` es la mejora algorítmica real sobre la versión anterior — TPE multivariado captura la correlación entre los órdenes no estacionales y estacionales de SARIMA que la versión univariada ignoraba por diseño.
- Reanudación nativa vía `optuna.trial.create_trial` + `study.add_trial`, verificado con una prueba de round-trip contra un `Study` real.
- Ya implementado y validado end-to-end: 340/340 pruebas de la suite completa, incluida la prueba de determinismo con ajuste SARIMA real y las pruebas de `classical_selection.py` (selección real por panel de SKUs).
**Contras:**
- Las reglas de ASHA del dominio no vienen gratis en Optuna — se reimplementaron dentro de `optuna.pruners.BasePruner` (`PodadorASHA`): el mismo trabajo de dominio que exigía la Alternativa 1, solo que alojado en la interfaz de Optuna en vez de en una clase propia.
- Cambio de comportamiento real: en el modelo de Optuna, un parámetro solo puede sugerirse una vez por trial (`trial.suggest_*` cachea el valor ya sampleado). Una configuración que viola las restricciones del espacio (`_no_degenerada`, `_orden_total_acotado`) ahora se marca como trial `fallido` y consume presupuesto de `n_trials`, en vez de reintentarse silenciosamente hasta 200 veces como hacía `EspacioBusqueda.muestrear()` en la implementación propia.
- Mayor superficie de cambio: se reescribien `asha.py`, `registro.py`, `estudio.py`, `muestreadores.py` y sus 3 suites de pruebas — no solo el sampler.

## Decisión

Se adopta la **Alternativa 3**. La adopción parcial (Alternativa 2) pagaría el costo completo de la nueva dependencia (`sqlalchemy` transitiva) sin capturar su beneficio principal: Optuna ya modela nativamente la distinción "podado vs. fallido" (regla de seguridad #4 de ADR-02-005) y ya provee un mecanismo de persistencia/reanudación (`create_trial`/`add_trial`) pensado para exactamente este caso de uso. Mantener un `RegistroEstudio` propio en paralelo a un `Study` de Optuna habría sido duplicar, sin necesidad, algo que Optuna ya resuelve.
La reimplementación de las reglas de ASHA como `PodadorASHA(BasePruner)` es un costo real, pero es el mismo costo que exige la Alternativa 1 — no es exclusivo de adoptar Optuna por completo. La ganancia algorítmica de `multivariate=True` (Bergstra et al., 2011) y la madurez operativa de una librería usada en producción industrial (Akiba et al., 2019) se obtienen sin costo adicional una vez que ya se paga el costo de integración de la Alternativa 2.

### Alternativas Descartadas

**Por qué se descartó mantener la implementación propia:** el TPE univariado no captura la correlación real entre órdenes estacionales y no estacionales de SARIMA, y una implementación de ~150 líneas no tiene el mismo nivel de exposición a casos borde que una librería con años de uso en producción (Akiba et al., 2019).

**Cuándo sería la mejor opción:** si la superficie de dependencias del proyecto fuera una restricción dura (por ejemplo, un entorno de despliegue que prohíbe dependencias con sub-dependencias de base de datos), el costo de `sqlalchemy` podría no justificarse frente a mantener una implementación 100% propia.
**Por qué se descartó Optuna solo como sampler:** habría agregado la misma dependencia nueva que la adopción completa, sin aprovechar que Optuna ya resuelve nativamente la distinción podado/fallido y la persistencia de trials — solo se habría evitado reescribir `asha.py`/`registro.py`, a costa de mantener dos modelos de trial en paralelo indefinidamente.

**Cuándo sería la mejor opción:** si el registro y la reanudación propios tuvieran requisitos que Optuna no cubre (por ejemplo, un formato de auditoría exigido por un tercero distinto al que ya provee `create_trial`/`add_trial`), aislar el cambio solo al sampler reduciría el riesgo de la migración.

## **Consecuencias **

### **Positivas**

- `Study` como fuente única de verdad para cada trial, eliminando la duplicación entre el registro propio y el modelo interno de Optuna.
- Ganancia algorítmica real (TPE multivariado) sobre la versión anterior, sin necesidad de mantenerla internamente.
- Persistencia y reanudación de estudios apoyadas en una API de Optuna ya pensada para ese propósito, en vez de un formato propio de punta a punta.

### **Negativas**

- **Comportamiento distinto ante configuraciones inválidas**
- Riesgo: una configuración que viola las restricciones del espacio consume un trial completo (marcado `fallido`) en vez de reintentarse de forma transparente.
- Mitigación: con las restricciones actuales de `EspacioClasico` (excluyen solo `(0,0,0)(0,0,0)` y órdenes por encima de `max_orden_total`), la fracción de configuraciones inválidas es baja; verificado en las 8 pruebas de `test_classical_selection.py`, incluida la de determinismo con ajuste SARIMA real.
- **Las reglas de dominio de ASHA siguen siendo responsabilidad propia**
- Riesgo: `PodadorASHA` debe mantenerse manualmente; Optuna no ofrece de fábrica el piso de 4 ventanas ni la agregación recortada por escalón.
- Mitigación: la lógica se portó 1:1 desde la implementación anterior y se revalidó con la suite de pruebas de `test_asha.py` reescrita contra un `Study` real (no mocks).
- **Mayor superficie de código migrado**
- Riesgo: se reescribieron 4 módulos y 3 suites de pruebas en una sola migración.
- Mitigación: el contrato externo (`Trial`/`ResultadoEstudio`, consumido por `classical_selection.py`) se preservó sin cambios, por lo que `test_estudio.py` y `test_classical_selection.py` no se modificaron y siguen pasando sin alteración.

## Referencias

- Akiba, T., Sano, S., Yanase, T., Ohta, T., & Koyama, M. (2019). Optuna: A next-generation hyperparameter optimization framework. In *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining* (KDD '19) (pp. 2623–2631). ACM. [https://doi.org/10.1145/3292500.3330701](https://doi.org/10.1145/3292500.3330701)
- Bergstra, J., Bardenet, R., Bengio, Y., & Kégl, B. (2011). Algorithms for hyper-parameter optimization. In *Advances in Neural Information Processing Systems 24* (NeurIPS 2011). [https://papers.neurips.cc/paper/4443-algorithms-for-hyper-parameter-optimization](https://papers.neurips.cc/paper/4443-algorithms-for-hyper-parameter-optimization)
- Bergstra, J., Yamins, D., & Cox, D. D. (2013). Making a science of model search: Hyperparameter optimization in hundreds of dimensions for vision architectures. In *Proceedings of the 30th International Conference on Machine Learning* (ICML 2013), PMLR 28, 115–123. [https://proceedings.mlr.press/v28/bergstra13.html](https://proceedings.mlr.press/v28/bergstra13.html)
- Li, L., Jamieson, K., Rostamizadeh, A., Gonina, E., Ben-tzur, J., Hardt, M., Recht, B., & Talwalkar, A. (2020). A system for massively parallel hyperparameter tuning. In *Proceedings of Machine Learning and Systems 2* (MLSys 2020). [https://arxiv.org/abs/1810.05934](https://arxiv.org/abs/1810.05934)
- Optuna Development Team. *optuna.samplers.TPESampler* (documentación oficial). [https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html](https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html)
- Optuna Development Team. *optuna.trial.TrialState* (documentación oficial). [https://optuna.readthedocs.io/en/stable/reference/generated/optuna.trial.TrialState.html](https://optuna.readthedocs.io/en/stable/reference/generated/optuna.trial.TrialState.html)
- Optuna Development Team. *Ask-and-Tell Interface* (tutorial oficial). [https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/009_ask_and_tell.html](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/009_ask_and_tell.html)
- Optuna Development Team. *User-Defined Pruner* (tutorial oficial). [https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/006_user_defined_pruner.html](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/006_user_defined_pruner.html)
- Optuna Development Team. *FAQ — How can I obtain reproducible optimization results?* [https://optuna.readthedocs.io/en/stable/faq.html](https://optuna.readthedocs.io/en/stable/faq.html)
- Pineau, J., Vincent-Lamarre, P., Sinha, K., Larivière, V., Beygelzimer, A., d'Alché-Buc, F., Fox, E., & Larochelle, H. (2021). Improving reproducibility in machine learning research (a report from the NeurIPS 2019 reproducibility program). *Journal of Machine Learning Research*, 22(164), 1–20. [https://jmlr.org/papers/v22/20-303.html](https://jmlr.org/papers/v22/20-303.html)
- Semmelrock, H., Kopeinik, S., Theiler, D., Ross-Hellauer, T., & Kowald, D. (2025). Reproducibility in machine-learning-based research: Overview, barriers, and drivers. *AI Magazine*. [https://doi.org/10.1002/aaai.70002](https://doi.org/10.1002/aaai.70002)
