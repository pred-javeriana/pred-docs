# ADR-03-012: Bloques de selección y de prueba en la reserva con campeón congelado

- **Fecha:** 2026-10-29
- **Estado:** Aceptada

## Contexto & Problema

ADR-03-003 reserva el 20 % final y cronológico del panel para M3. M3 compara los candidatos sobre todas las ventanas de la reserva y emite la selección definitiva. ADR-03-007 elige la familia campeona de cada clase de demanda con la mediana de la razón $r = RMSE_{\text{candidato}} / RMSE_{\text{Seasonal Naive}}$, y toma como representante de cada familia la configuración de menor RMSE en la reserva. ADR-03-011 publica la prueba HLN-DM con corrección Benjamini-Hochberg (BH) entre SKU, sin fijar el alcance de esa familia de pruebas. La implementación descrita por ADR-021 de pred-engine agrupa todos los SKU probados de la corrida. Con estas tres reglas, la misma reserva elige el campeón y mide su desempeño. Por eso el puntaje del campeón es optimista (Cawley y Talbot, 2010), como reconoce ADR-03-007.

El protocolo tiene además cuatro vacíos:

- La regla de ADR-03-007 elige el campeón por la mediana de r, sin una prueba pareada entre familias.
- La corrección BH sobre toda la corrida deja que la clase más grande fije el umbral de las clases pequeñas (Efron, 2008). Las afirmaciones de la tesis, en cambio, se hacen por clase.
- La política de routing envía los SKU `lumpy` solo a las familias clásica y fundacional. Si la unidad clásica falla en L2, el SKU queda con una sola familia evaluable, y la competencia tiene un ganador obvio.
- ADR-03-003 dejó pendiente la reconciliación con ADR-03-002, que dice que M3 no elige candidatos ni ganadores.

El equipo observó el periodo reservado durante el desarrollo. Por eso todos los parámetros del protocolo deben quedar fijos antes de las corridas cuyos resultados cita la tesis.

## Opciones Consideradas

1. **Bloques de selección y de prueba dentro de la reserva.** El primer tramo de la reserva elige y congela el campeón de cada clase. El tramo final, que ninguna decisión lee, produce todos los resultados. Los modelos se ajustan una sola vez en t\*. Su desventaja es que el bloque de prueba no contiene la temporada de fin de año.
2. **Selección antes de t\* con los pliegues de L3 y prueba sobre toda la reserva.** La prueba conserva todos los orígenes de la reserva. Su desventaja es que las familias optimizadas se califican en los mismos pliegues que optimizó su HPO, mientras que Chronos-2 opera sin ajuste. Así, el error de L3 de las familias optimizadas es optimista.
3. **Partición en tres tramos, con un HPO que termina antes de un periodo de validación.** Separa el ajuste, la selección y la prueba. Su desventaja es que exige nuevos ajustes de L2 con una historia más corta y una nueva ejecución del motor.

## Decisión

Se adopta la **opción 1**. La opción 2 se reporta como verificación de robustez, calculada con los datos de L3 de las corridas finales.

### 1. Bloques de la reserva

Sea R el número de días reservados y H = 7 el horizonte y la longitud de cada ventana. El origen k (k = 0, …, R − H) pronostica los días k + 1 a k + H de la reserva. La fracción de selección es f = 0,4, y el límite entre los bloques es S = ⌊f · R⌋.

| Bloque | Orígenes | Días pronosticados | Uso |
| --- | --- | --- | --- |
| Selección | k = 0, …, S − H | 1 a S | Elige y congela el campeón de cada clase |
| Embargo | k = S − H + 1, …, S − 1 | cruzan el límite | Ninguno |
| Prueba | k = S, …, R − H | S + 1 a R | Produce todos los resultados reportados |

En el panel de datos reales, t\* es el 11 de septiembre de 2016 y R = 338 días. Entonces S = 135, con 129 orígenes de selección, 6 de embargo y 197 de prueba. Los días pronosticados del bloque de prueba van del 25 de enero al 15 de agosto de 2017.

La selección agrupa cientos de SKU por clase y necesita menos días que las pruebas por SKU. Un bloque de selección corto deja una serie de prueba larga, que da más potencia a esas pruebas (Hansen y Timmermann, 2012). La política de selección de M3 declara la fracción y cambia de versión con ella. La fracción queda fija antes de las corridas finales y no se ajusta con sus resultados.

Cada candidato se ajusta una vez con la historia hasta t\* y no se reajusta. Un origen del bloque de prueba usa todas las observaciones disponibles hasta ese origen, incluidas las del bloque de selección, porque esa información existe en el momento del pronóstico.

### 2. Qué lee cada bloque

| Solo el bloque de selección | Solo el bloque de prueba |
| --- | --- |
| Conjunto común de SKU comparables de cada clase | Los cinco veredictos por SKU |
| Representante de cada familia por SKU | r de cada modelo frente a Seasonal Naive |
| Regla de la mediana de r, compuerta frente a Seasonal Naive y desempate | HLN-DM frente a Seasonal Naive y corrección BH |
| Orden de respaldo para un SKU sin instancia de la familia campeona | Prueba confirmatoria del campeón y tamaños de efecto |
| | Chronos-2 frente a la mejor familia no Chronos |

El código lo garantiza así: la función de selección recibe solo ventanas del bloque de selección. La prueba de aceptación altera todas las observaciones del bloque de prueba y comprueba que el registro del campeón queda idéntico byte a byte.

### 3. Campeón congelado

En el bloque de selección, M3 aplica la regla de ADR-03-007 sin cambiar su cálculo: representante por familia, mediana de r sobre el conjunto común, compuerta frente a Seasonal Naive y desempate por simplicidad con la tolerancia predeclarada. Un SKU entra en el conjunto común de su clase solo si tiene al menos 30 ventanas válidas de selección en cada familia que compite. Un SKU fuera del conjunto común recibe igualmente su veredicto en el bloque de prueba.

El campeón de cada clase queda congelado al terminar la selección. Ningún resultado del bloque de prueba lo cambia.

### 4. Prueba confirmatoria del campeón de cada clase

En el bloque de prueba, M3 compara el campeón congelado f\* de cada clase con cada familia competidora g:

1. Entran los SKU de la clase con instancias válidas de f\* y de g y al menos 30 ventanas comunes de prueba.
2. Para cada SKU i, $x_i = \log(RMSE_{f^*,i} / RMSE_{g,i})$.
3. $p_g$ es el valor p bilateral de la prueba de rangos con signo de Wilcoxon sobre los $x_i$, exacto con 50 SKU o menos. $p_g$ cuenta solo si la mediana de los $x_i$ es negativa. Si no, $p_g = 1$.
4. El valor p de la clase es el máximo de los $p_g$ (prueba de intersección-unión; Berger, 1982).
5. Los valores p de las cuatro clases se corrigen con Holm.
6. El campeón queda **confirmado** si su valor p corregido es a lo sumo 0,05 y si, para cada competidor, el intervalo de 95 % de la mediana de la razón de RMSE queda por debajo de 1. Ese intervalo sale de un bootstrap circular por bloques de 14 días (Politis y Romano, 1992), con 2000 réplicas, que remuestrea los mismos días para todos los SKU. La semilla del bootstrap es una constante de la política.

El estado del campeón de cada clase toma uno de cuatro valores: `confirmado`, `no_confirmado`, `sin_comparables` (menos de 10 SKU frente a algún competidor) o `no_aplica` (la compuerta eligió a Seasonal Naive). Una confirmación fallida se reporta y nunca cambia el campeón, porque elegirlo de nuevo con el bloque de prueba devolvería el sesgo que esta decisión elimina.

La interpretación de Wilcoxon como una comparación de localización supone independencia entre SKU y simetría de los logaritmos de las razones bajo la hipótesis nula. El bootstrap conserva los choques comunes al remuestrear los mismos días para todos los SKU. Sus intervalos suponen que el bloque de 14 días representa la dependencia temporal relevante.

### 5. Prueba frente a Seasonal Naive y multiplicidad

La prueba HLN-DM de ADR-03-011 no cambia: diferencial de la pérdida cuadrática media de cada ventana, varianza de largo plazo con autocovarianzas hasta el rezago H − 1, factor de Harvey, Leybourne y Newbold, distribución t con T − 1 grados de libertad y un mínimo de 30 ventanas comunes. La prueba se calcula solo con el bloque de prueba.

La corrección BH se aplica dentro de cada clase de demanda, con el nivel nominal q = 0,05, el mismo nivel `alfa_dm` de la política. Su control de la tasa de descubrimientos falsos requiere independencia o la condición de dependencia positiva de Benjamini y Yekutieli (2001). Los choques compartidos entre SKU no bastan para establecer esa condición. Cada tipo de comparación forma su propia familia de pruebas y nunca se mezcla con otro: campeón frente a Seasonal Naive, campeón frente a cada competidor por SKU, y Chronos-2 frente a la mejor familia no Chronos. Los conteos con la corrección de Benjamini-Yekutieli, válida bajo cualquier dependencia, se reportan como análisis de sensibilidad.

### 6. Tamaños de efecto

- **Por SKU:** r con un intervalo obtenido al invertir la prueba HLN-DM. Para los SKU que BH selecciona, el intervalo usa el nivel $1 - R_c q / m_c$, donde $R_c$ es el número de rechazos y $m_c$ el número de pruebas de la clase (Benjamini y Yekutieli, 2005).
- **Por clase, para cada competidor:** la razón de Hodges-Lehmann con su intervalo, la mediana de la razón con el intervalo del bootstrap por bloques, y la proporción de SKU en que gana el campeón, con intervalo de Wilson.
- **Por clase, frente a Seasonal Naive:** la mediana de r del campeón con el intervalo del bootstrap por bloques.

### 7. Veredictos y significancia

Los cinco veredictos de ADR-03-008 conservan sus nombres y su orden de reglas. Cada condición se evalúa en el bloque de prueba. La significancia se publica en su propia columna y nunca se mezcla con el veredicto. La columna muestra el estadístico, el valor p, el valor p ajustado por BH dentro de la clase, o la causa cuando no se ejecuta la prueba. `VALIDADO` no significa significancia estadística. Una diferencia no significativa no significa equivalencia.

### 8. SKU con menos de dos familias evaluables

Una familia es evaluable para un SKU si está enrutada para su clase y su unidad de L2 terminó con un candidato. Seasonal Naive es la línea base, no una familia. Cuando terminan todas las unidades de L2 de un SKU:

| Familias evaluables | Resultado |
| --- | --- |
| 0 | M3 asigna `FALLO_TECNICO`, y el SKU se cuenta en su clase |
| 1 | El SKU sale de la competencia con la causa `eligibility.fewer_than_two_families` antes de L3 |
| 2 o más | El SKU sigue a L3 y M3 |

La regla depende solo de resultados de L2, que son anteriores a la reserva. El embudo de exclusiones muestra esta etapa por separado, con su conteo por clase. Si un SKU con dos o más familias no tiene instancia de la familia campeona, recibe su veredicto con la siguiente familia del orden de respaldo del bloque de selección y queda fuera de la prueba confirmatoria de su clase.

### 9. Chronos-2 frente a la mejor familia no Chronos

M3 aplica la regla de selección del punto 3 en el bloque de selección sin la familia fundacional. La familia que gana es la contendiente. En el bloque de prueba, M3 compara Chronos-2 con esa familia mediante la prueba del punto 4 y los tamaños de efecto del punto 6.

### 10. Grupo final de corridas

La tesis y los documentos de resultados citan solo un grupo final de tres corridas. Las corridas de desarrollo son evidencia de diseño y no se citan como resultados.

- **Semillas:** 0, 1 y 2. La semilla del motor es lo único que cambia entre las corridas. Ninguna semilla se reemplaza: una corrida con fallo técnico se repite con la misma semilla, y todas las corridas se reportan.
- **Productos:** el catálogo completo del panel, si el control de memoria de la etapa de ajuste lo permite. Si no lo permite, la muestra fija más grande que ese control admite, la misma en las tres corridas y fijada antes de la primera. Los productos que no se usaron en ninguna corrida de desarrollo se reportan también como subgrupo.
- **Lo que queda fijo:** commit del motor y archivo de bloqueo de dependencias, huella del archivo de datos, lista de productos, t\*, fracción de reserva, fracción de selección, H, versión y parámetros de la política, presupuestos de HPO, hilos de trabajo y de BLAS, revisión de Chronos-2 y semilla del bootstrap.

Los resultados se combinan así:

1. Cada corrida reporta sus campeones, el estado de cada campeón, la tabla de la prueba confirmatoria, los veredictos y la significancia por SKU, y r de cada familia.
2. Una tabla muestra el campeón de cada clase en cada corrida.
3. Por SKU se reporta si el veredicto y la significancia coinciden en las tres corridas. Se listan los SKU que difieren y los que compiten solo en algunas corridas.
4. Por SKU y familia se reporta la media de r y su rango entre corridas. Por clase se reporta el rango de las medianas entre corridas, para el campeón frente a Seasonal Naive y frente a la segunda familia.
5. La significancia del grupo se calcula para los SKU que compiten en las tres corridas y tienen un valor p HLN-DM válido en cada una. Para cada SKU se toma el mayor de esos tres valores p bilaterales y se aplica BH una sola vez dentro de su clase. Los SKU sin alguna prueba válida se reportan por separado con su causa y no reciben un valor p del grupo. El máximo contrasta la presencia de una diferencia en las tres corridas bajo cualquier dependencia entre ellas (Berger, 1982; Vovk y Wang, 2020). Una mejora significativa del grupo exige además que el diferencial de pérdida del campeón frente a Seasonal Naive sea negativo en las tres corridas. Se publican las tres direcciones. No se suman descubrimientos entre corridas, no se mezclan sus ventanas y no se combinan los valores p con Fisher o Stouffer. Para la prueba confirmatoria se reporta el valor p de Holm de cada corrida y su máximo cuando los tres están disponibles. Si falta alguno, se publica su estado y no se calcula ese máximo.

Un resultado es estable bajo estas reglas:

- **Campeón estable:** la misma familia gana la clase en las tres corridas, y su confirmación pasa en las tres.
- **Resultado estable de un SKU:** el SKU compite en las tres corridas con el mismo veredicto y el mismo resultado de significancia.
- **Efecto estable:** el rango entre corridas de la mediana de la razón de la clase, frente a Seasonal Naive y frente a la segunda familia, es menor que 0,01, la tolerancia de desempate de la política.

Una clase que no cumple una regla se reporta como no estable, con sus valores por corrida. Para esa clase no se afirma un campeón.

## Registros que sustituye en parte

| Registro | Texto sustituido | Regla vigente |
| --- | --- | --- |
| ADR-03-003 | M3 «las evalúa sobre todas las ventanas disponibles del periodo final reservado y emite la selección definitiva» | M3 elige en el bloque de selección y evalúa en el bloque de prueba. La reserva del 20 %, la política por categoría, la visibilidad por SKU y el veredicto de evidencia insuficiente no cambian. |
| ADR-03-003 | Reconciliación pendiente con ADR-03-002 | Queda cerrada por la fila de ADR-03-002 de esta tabla. |
| ADR-03-007 | Paso 2: representante «de menor RMSE en la reserva»; paso 3: conjunto común de SKU con r calculable en todas las familias; cláusula de sesgo por elegir y puntuar sobre la misma reserva | El representante y la regla de selección se calculan solo en el bloque de selección. El conjunto común exige r calculable y al menos 30 ventanas válidas de selección en cada familia que compite. El bloque de prueba produce la evaluación final. La prueba confirmatoria del punto 4 complementa la regla. |
| ADR-03-011 | Aplicación de BH entre SKU, cuyo alcance no fija ese registro | Se precisa una familia de pruebas por clase de demanda y tipo de comparación, calculada solo con el bloque de prueba. Se conservan el carácter complementario de la prueba, la exclusión de datos sintéticos y el mínimo de orígenes. El alcance sobre toda la corrida descrito por ADR-021 de pred-engine queda sustituido por este alcance por clase. |
| ADR-03-002 | M3 «no ajusta configuraciones ni elige candidatos o ganadores» | M3 no ajusta configuraciones. M3 elige la familia campeona solo con el bloque de selección, y su evaluación final usa solo el bloque de prueba. Así se mantiene dentro de M3 el principio de ADR-03-002: un resultado usado para elegir no se presenta como evaluación final. |
| ADR-021 de pred-engine | Decisión 3 y sección «Límites»: el campeón se elige sobre la misma reserva que produce su puntaje, y BH se aplica entre todos los SKU probados | Las reglas de los puntos 1 a 5 de esta decisión. |

ADR-03-008 no cambia: sus reglas de veredicto se evalúan en el bloque de prueba.

## Consecuencias

### Positivas

- Ninguna decisión lee el bloque de prueba, y el código lo verifica.
- La superioridad de la familia campeona de cada clase tiene una prueba pareada con tamaño de efecto, además de la mediana de r.
- La corrección por multiplicidad coincide con la unidad de las afirmaciones de la tesis: la clase de demanda.
- Ningún SKU entra en la competencia con un único competidor.
- La tesis cita un grupo de corridas con parámetros fijados de antemano, y ese grupo mide la estabilidad del resultado frente a la aleatoriedad del ajuste.

### Negativas

- **Sin fin de año en la prueba.** El bloque de prueba no contiene diciembre. El desempeño de diciembre se reporta de forma descriptiva con el bloque de selección.
- **Series de prueba más cortas.** Algunos SKU no alcanzan las 30 ventanas de prueba y reciben `EVIDENCIA_INSUFICIENTE`.
- **Exposición durante el desarrollo.** El equipo observó la reserva durante el desarrollo. La tesis declara este límite y reporta por separado los productos que no se usaron en el desarrollo.
- **Población seleccionada.** La regla de dos familias conserva los SKU en que al menos dos familias producen un modelo válido, que no son una muestra aleatoria. La tesis reporta el conteo por clase con sus causas y compara el perfil previo a la reserva de los SKU excluidos y conservados.
- **Costo.** El grupo final cuesta tres corridas completas. La semilla puede cambiar qué SKU `lumpy` compiten, por eso el resumen del grupo prueba solo los SKU que compiten en las tres.

## Referencias

- Benjamini, Y., y Hochberg, Y. (1995). Controlling the false discovery rate: A practical and powerful approach to multiple testing. *Journal of the Royal Statistical Society: Series B*, 57(1), 289-300.
- Benjamini, Y., y Yekutieli, D. (2001). The control of the false discovery rate in multiple testing under dependency. *Annals of Statistics*, 29(4), 1165-1188.
- Benjamini, Y., y Yekutieli, D. (2005). False discovery rate-adjusted multiple confidence intervals for selected parameters. *Journal of the American Statistical Association*, 100(469), 71-81.
- Berger, R. L. (1982). Multiparameter hypothesis testing and acceptance sampling. *Technometrics*, 24(4), 295-300.
- Cawley, G. C., y Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent selection bias in performance evaluation. *Journal of Machine Learning Research*, 11, 2079-2107.
- Efron, B. (2008). Simultaneous inference: When should hypothesis testing problems be combined? *Annals of Applied Statistics*, 2(1), 197-223.
- Hansen, P. R., y Timmermann, A. (2012). Choice of sample split in out-of-sample forecast evaluation. *EUI Working Paper ECO 2012/10*.
- Harvey, D., Leybourne, S., y Newbold, P. (1997). Testing the equality of prediction mean squared errors. *International Journal of Forecasting*, 13(2), 281-291.
- Hodges, J. L., y Lehmann, E. L. (1963). Estimates of location based on rank tests. *Annals of Mathematical Statistics*, 34(2), 598-611.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.
- Politis, D. N., y Romano, J. P. (1992). A circular block-resampling procedure for stationary data. En R. LePage y L. Billard (eds.), *Exploring the Limits of Bootstrap*, 263-270. Wiley.
- Vovk, V., y Wang, R. (2020). Combining p-values via averaging. *Biometrika*, 107(4), 791-808.
- Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin*, 1(6), 80-83.
- Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association*, 22(158), 209-212.
