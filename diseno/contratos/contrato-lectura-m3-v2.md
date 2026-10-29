# Contrato de lectura de evidencia M3 para M4 (2.2.0)

M3 decide y publica. M4 muestra esa decisión y su evidencia sin recalcular métricas, contrastes ni campeones. Este contrato sustituye `validation_verdicts`, los tres veredictos de v1 y su `Champion` para el consumo de M3. No hay traducción a esos modelos ni lectura alternativa de `resultados_comparativos` o `reportes_validacion`.

## 1. Responsabilidades y fuentes

```text
pred-engine: publica M3
           |
pred-platform: DAL de solo lectura
           |
modelos v2 -> DataRepository
           |
vistas M4 y exportación CSV
```

El código de lectura M4 pertenece a `pred-platform`. Este documento publica el contrato, no implementa esa lectura ni migra todavía sus consumidores. El [inventario previo](inventario-consumidores-m4.md) identifica los usos existentes y sus incompatibilidades.

Fuentes contrastadas: `pred-platform` en `6ef53bc` y `pred-engine` en `f8678bf`; `m3_exclusiones`, en `pred-engine` `811ca0d`.

| Fuente publicada | Proyección v2 |
|---|---|
| `m3_corridas` | `M3Run`: identidad, ingesta, origen, estado y causa de rechazo |
| `m3_protocolos.protocolo.politica` | `SelectionPolicy`: versión, `n_min`, `n_min_dm`, `alfa_dm` |
| `evidencia_publicada` | `M3Verdict`: los cinco veredictos, campeón, números decisivos y prueba `dm_*` |
| `m3_metricas` | `M3Metric`: métricas por candidato y ventana, incluida `agregada` |
| `m3_categorias` | `M3Category`: selección por clase y resumen publicado de veredictos |
| `m3_cartera` | `M3PortfolioRow`: distribuciones ya calculadas, por clase, familia y métrica |
| `m3_pronosticos` | `M3Forecast`: candidato, origen, horizonte, fecha y valor |
| `m3_fallos` | `M3Failure`: fallos de adaptación, con campo, código y mensaje |
| `m3_unidades` | `M3Unit`: unidad SKU × candidato × origen, confirmada o fallida con causa |
| `m3_cortes` + `m3_lanzamientos_tardios` | `LateLaunches`: corte, cantidad y lista de productos lanzados después del corte |
| `m3_exclusiones` | `EligibilityExclusions`: cantidad y lista de productos que M2 excluyó de la competencia, con clase, código y causa |
| `m3_observaciones` | `M3Observation`: demanda observada de un día de la reserva |
| `m3_campeones` (vista) | `M3ChampionCount`: conteos de SKU por familia campeona publicada |

El esquema SQL inicial es `pred-engine/src/pred_engine/forecasting/persistencia_evidencia/esquema_m3.sql`, con sus migraciones posteriores. La plataforma aplica ese esquema en `dal/migrations/0005_evidencia_m3.sql` a `0009_origen_publicado.sql`. Su módulo `dal/evidencia.py` es la frontera de lectura que debe alimentar el contrato. La vista pública incluye `datos_sinteticos`, `origen_declarado` e `identidad`; el adaptador debe añadir `ingesta_sha256` desde la misma corrida, también en consultas por SKU.

## 2. Identidad, publicación y selección de corrida

- `run_id` siempre es el identificador **exacto de M3**, no el de M2. `run_id_m2` conserva el vínculo con M2.
- Una referencia de M2 o una `identidad` sirve para buscar corridas, nunca para mezclar sus filas. Cada documento de evidencia contiene una sola corrida M3.
- Sin elección explícita, se selecciona la PUBLICADA más nueva por `creado_en DESC, run_id DESC`. El desempate es estable. Una corrida RECHAZADA más nueva no desplaza a una PUBLICADA.
- Una selección explícita conserva ese `run_id`, aunque aparezca otra publicación. Los enlaces de detalle, filtros, paginación y CSV conservan el identificador resuelto, no `latest`.
- Cada `M3Run` incluye la lista **completa** `publicadas_misma_identidad`, ordenada por esa misma regla, sin limitarla a la página actual. Se compara el texto canónico de `identidad`, no solo `run_id_m2`.
- Cuando esa lista tiene más de un elemento, `aviso = "varias_publicadas_misma_identidad"`. La vista muestra un aviso visible: «Hay varias corridas PUBLICADA con esta identidad. Se muestra {run_id}.» No basta con registrarlo en un log.
- `identidad` conserva el JSON canónico guardado por M3 como texto, sin reserializarlo para agrupar. `creado_en` se presenta como fecha-hora con zona; el adaptador interpreta el `datetime('now')` de SQLite como UTC.

Los estados son `EN_CURSO`, `EVALUADA`, `SELECCIONADA`, `PUBLICADA` y `RECHAZADA`. `M3RunStatus` muestra solo metadatos, causa y avance durable. No admite métricas ni veredictos parciales. RECHAZADA exige `causa_rechazo` y los demás estados no la admiten.

Todos los documentos de evidencia exigen PUBLICADA para `availability.status = "available"`. El DAL lee estado y evidencia en una misma instantánea de solo lectura. Nunca comprueba el estado en una conexión y lee las filas en otra. El filtro PUBLICADA se aplica también a las tablas auxiliares, no solo a los veredictos.

## 3. Trazabilidad y tipos

Cada fila conserva `run_id`, `sku` e `ingesta_sha256`. El SHA tiene 64 caracteres hexadecimales en minúscula y corresponde a `m3_corridas.ingesta_sha256`; no se sustituye por una ruta, el nombre de archivo ni `run_id_m2`.

Las filas agregadas por corrida, clase o cartera llevan **`sku: null` explícito**. No representan un SKU y no usan valores ficticios como `TODOS`. Las filas por producto, incluidos los modelos evaluados y las exclusiones, llevan el SKU real. `policy`, `availability`, `page`, conteos y mapas internos son objetos de valores, no filas independientes.

El adaptador conserva los nombres SQL. Decodifica los campos JSON de categorías y `modelos_evaluados` en sus tipos declarados. Convierte los bits SQLite a booleanos JSON; `false` no se reemplaza por `null`. Los campos anulables son obligatorios incluso cuando valen `null`, para distinguir la ausencia explicada de un campo omitido.

Los documentos llevan `schema_version: "2.x.y"`, `generated_at`, `source` y `availability`. Los consumidores rechazan otra versión mayor. `source: "fixture"` significa ejemplo de interfaz, **no** origen sintético de los datos científicos. Los campos adicionales y los números no finitos se rechazan.

## 4. Veredicto y significancia son columnas distintas

La vista conserva estas cinco etiquetas exactas, sin traducirlas a `mantiene`, `parcial`, `falla` ni a un estado de tarea:

| Grupo de presentación | Veredictos |
|---|---|
| Evaluados | `VALIDADO`, `EXPLORATORIO` |
| No evaluados | `FALLO_TECNICO`, `NO_EVALUABLE`, `EVIDENCIA_INSUFICIENTE` |

La lista por SKU muestra `justificacion` tal como la publicó M3 y los números que permiten entenderla:

- `n_ventanas` frente a `n_min`, leído de la política congelada. El valor inicial publicado es **30**; no es un ajuste de la interfaz.
- `razon_sn`, el cociente **r = RMSE del candidato / RMSE de Seasonal Naive**, sobre las ventanas comunes que M3 utilizó. Se muestran también `cobertura`, `comparacion_incompleta` y `pierde_frente_a_linea_base`.
- `datos_sinteticos` y `origen_declarado`, también en cada fila de veredicto. `(false, true)` declara datos reales; `(true, true)`, sintéticos o aumentados; `(false, false)`, origen desconocido. `(true, false)` no es válido.
- `familia_campeona` y `candidato_campeon` vienen de `m3_veredictos`. `seasonal_naive` es una familia válida cuando gana la línea base. El candidato puede ser nulo en un fallo técnico. La familia de un SKU puede diferir de la campeona de su clase por el fallback documentado en `justificacion`.

La columna **Significancia** muestra HLN-DM, `dm_p_valor`, el p ajustado BH (`dm_p_ajustado`), `dm_alfa`, `dm_significativa`, `dm_n_ventanas` y `dm_horizonte`. `dm_estadistico < 0` favorece al campeón. El ajuste BH pertenece a la corrida completa, no a los SKU de una página o filtro.

Si no hay prueba, todos sus resultados inferenciales son nulos y la columna muestra `dm_causa` literalmente. Los números de ventanas y horizonte permanecen como M3 los publicó. Entre las causas están `datos_sinteticos`, `origen_desconocido`, `campeon_es_linea_base`, `pocas_ventanas`, `varianza_no_positiva` y `veredicto:FALLO_TECNICO`. No se inventa un p-valor de cero ni se interpreta la ausencia como «no significativa».

`VALIDADO` es una conclusión **descriptiva**, no una afirmación de significancia. Puede tener p ajustado no significativo o no tener prueba con una causa. Los datos sintéticos o de origen desconocido no admiten inferencia ni `VALIDADO`. El contrato valida integridad, pero no vuelve a ejecutar las reglas de selección o de veredicto.

## 5. Embudo completo y exclusiones

`M3Evidence` contiene `funnel`, `late_launches` y `eligibility_exclusions` para **toda la corrida**, antes de los filtros o la paginación. El embudo cuenta productos únicos, no candidatos ni unidades:

```text
Todos los productos
  - lanzados despues del corte
  - excluidos por elegibilidad en M2
= tras_exclusiones
  - FALLO_TECNICO
  - NO_EVALUABLE
  - EVIDENCIA_INSUFICIENTE
= evaluados
  + EXPLORATORIO
  + VALIDADO
```

`total_productos = excluded_count + eligibility_excluded_count + tras_exclusiones`, donde `excluded_count` cuenta los lanzamientos tardíos. Los cinco conteos suman `tras_exclusiones`; los tres primeros suman `no_evaluados` y los otros dos suman `evaluados`. Los conteos incluyen ceros explícitos. Cada producto no excluido debe tener exactamente un veredicto. Los conteos no se deducen de la página visible.

`late_launches` conserva `t_star`, `excluded_count` y la lista completa `items`. Cada elemento conserva la corrida, ingesta, SKU y la causa exacta **`lanzado despues del corte`**. Es una exclusión anterior a M3, no un sexto veredicto, una exclusión de familia ni un fallo técnico. Ningún SKU de esa lista puede aparecer entre los veredictos de la misma corrida.

`eligibility_exclusions` conserva `excluded_count` y la lista completa `items` de `m3_exclusiones`: los productos que M2 excluyó de la competencia antes de L3. Cada elemento conserva la corrida, ingesta, SKU, su clase `sku_class`, el código `codigo` (`eligibility.*`) y la causa `causa` tal como M3 los publicó. La regla de dos familias publica `eligibility.fewer_than_two_families`, y su causa nombra la familia evaluable que conservó el producto y las familias fallidas con su código. M3 no publica esas familias en columnas propias, así que el contrato no las separa del texto de la causa. `funnel.eligibility_excluded_count` es igual a `eligibility_exclusions.excluded_count`. Un SKU de esa lista no puede tener veredicto ni ser también un lanzamiento tardío. La vista cuenta y lista estos productos por clase y causa; no son un sexto veredicto ni un `FALLO_TECNICO`.

`eligibility_exclusions` y `funnel.eligibility_excluded_count` son los únicos campos que un documento puede omitir: omitirlos equivale a `null`, y ambos son nulos o ambos tienen valor. El valor nulo significa que el documento no informa las exclusiones de M2, no que haya cero. Así un documento 2.1 sigue siendo válido. La evidencia no disponible no las expone.

El adaptador lee el corte de `m3_cortes` y los excluidos de `m3_lanzamientos_tardios`, que M3 publica con la corrida. Una corrida PUBLICADA sin fila en `m3_cortes` responde `metadata_missing`. La falta de metadatos no significa cero exclusiones. No infiere exclusiones comparando los SKU de la ingesta con las filas M3 ni vuelve a calcular la fecha de lanzamiento.

Si una publicación histórica no conserva esos metadatos, `M3Evidence` responde `metadata_missing`, con detalle visible, sin embudo ni filas. **La falta de metadatos no significa cero exclusiones.** Las operaciones auxiliares todavía pueden mostrar evidencia PUBLICADA que sí esté completa, sin inventar un embudo.

## 6. Métricas, categorías y evidencia auxiliar

El contrato lleva **MAE, RMSE, MASE, ME y r** con los nombres persistidos `mae`, `rmse`, `mase`, `me`, `razon_sn`. No contiene sMAPE. `m3_metrics` conserva también los conteos publicados `n_pares`, `n_ventanas_totales`, `n_ventanas_validas` y `n_pronosticos_validos`. `ventana` es una fecha ISO o el literal `agregada`. Un `valor: null` exige `causa`; un valor calculado no lleva causa. ME puede ser negativo.

Las métricas del campeón se consultan con `candidato_campeon`; la línea base usa el candidato publicado de familia `seasonal_naive`. El patrón actual de M3 es `{sku}/seasonal_naive/seasonal_naive`. El repositorio devuelve esas filas, no calcula cocientes ni agrega ventanas. `razon_sn` se muestra como **r**; no se renombra en el JSON.

El segmento es `sku_class`, la clase **Syntetos-Boylan**: `smooth`, `intermittent`, `erratic`, `lumpy`. No se añade ABC-XYZ ni se infiere desde `profile`. La topología ADI/CV² de M1/M2 sigue siendo contexto de entrada, no evidencia retrospectiva M3.

Las categorías conservan `medianas_r`, SKU comparables y excluidos con causa, familias excluidas, motivo de selección, conteos y porcentajes. Las distribuciones de cartera conservan los denominadores `n_skus`, `n_instancias`, `n_calculables` y `n_no_calculables`. No se mezclan con los conteos de productos del embudo.

`m3_forecasts` preserva `valor: null` cuando el pronóstico no fue finito. La causa técnica se consulta en unidades o fallos, sin añadir una métrica ficticia. `m3_failures` recoge fallos de adaptación y `m3_units` expone los fallos por ventana. Una exclusión de una familia de M2 no se convierte por sí sola en `FALLO_TECNICO` del SKU.

`m3_observations` contiene la demanda observada de cada día de la reserva, para el gráfico de pronóstico frente a realidad; `valor: null` significa que no hubo observación ese día.

`m3_champions` cuenta SKU por `familia_campeona` publicada, divididos en los dos grupos de §4; las filas con `sku_class: null` representan la cartera completa. La plataforma no los suma ni los recalcula.

## 7. Operaciones de DataRepository a implementar

Estos nombres definen el punto de entrada de lectura en ambos modos, `dal` y `fixture`. No constituyen rutas HTTP nuevas ni una implementación incluida en este cambio.

| Operación | Documento |
|---|---|
| `list_m3_runs(...)` | `m3_runs` / `M3Runs` |
| `get_m3_run_status(run_id)` | `m3_run_status` / `M3RunStatus` |
| `get_m3_evidence(run_id, ...)` | `m3_evidence` / `M3Evidence` |
| `get_m3_metrics(run_id, ...)` | `m3_metrics` / `M3Metrics` |
| `get_m3_categories(run_id, ...)` | `m3_categories` / `M3Categories` |
| `get_m3_portfolio(run_id, ...)` | `m3_portfolio` / `M3Portfolio` |
| `get_m3_forecasts(run_id, ...)` | `m3_forecasts` / `M3Forecasts` |
| `get_m3_failures(run_id, ...)` | `m3_failures` / `M3Failures` |
| `get_m3_units(run_id, ...)` | `m3_units` / `M3Units` |
| `get_m3_observations(run_id, ...)` | `m3_observations` / `M3Observations` |
| `get_m3_champions(run_id, ...)` | `m3_champions` / `M3Champions` |

`list_m3_runs` admite filtros por identidad, referencia M2 o ingesta y estado. `selected_run_id` se resuelve sobre todas las coincidencias PUBLICADA, antes de paginar. Las otras operaciones exigen el `run_id` exacto resuelto. El estado por M2 se obtiene listando sus corridas, no fusionando su avance.

Las listas se filtran, ordenan y paginan en el servidor. `page = {number, size, total}`: número desde 1, tamaño de 1 a 500 (por defecto 50), total de la consulta filtrada. El tamaño de `items` debe corresponder a la página solicitada. Una página fuera de rango llega vacía, conservando el total. Cada orden termina con las claves naturales para deshacer empates.

- Evidencia: SKU exacto o búsqueda de SKU, `sku_class`, `veredicto`, grupo evaluado/no evaluado y `familia_campeona`. El estado de familia de M2 no es un filtro de veredicto.
- Métricas: SKU, candidato, ventana y métrica.
- Categorías/cartera: clase, familia y, en cartera, métrica.
- Pronósticos/unidades: SKU, candidato y origen; los pronósticos también por `h` y las unidades por `estado`.
- Fallos: SKU o candidato.
- Observaciones: SKU y `fecha`.
- Campeones: `sku_class` y `familia`.

Los filtros desconocidos se rechazan, no se ignoran. Las claves naturales son `(run_id, sku)` para veredictos; más candidato, ventana y métrica para métricas; más candidato, origen y `h` para pronósticos; candidato y origen para unidades; candidato para fallos; clase para categorías; clase, familia y métrica para cartera; `(run_id, sku, fecha)` para observaciones; `(run_id, sku_class, familia)`, clase nula al final, para campeones.

CSV usa la misma corrida y consulta que la vista, sin el límite de la página. Conserva identificadores, nulos y causas, las cinco etiquetas y las columnas `dm_*` separadas. El CSV de exclusiones conserva `t_star`, la clase, el código y la causa. La exportación recorre páginas bajo una misma instantánea; no vuelve a evaluar modelos. No se afirma aquí una medición de rendimiento ni una integración plataforma-motor.

## 8. Disponibilidad, ejemplos y comprobación

| Estado | `reason_code` | Contenido |
|---|---|---|
| Disponible | `null` | Corrida PUBLICADA, filas de la consulta y metadatos completos requeridos |
| No hay coincidencia | `no_data` | `run: null`, sin evidencia |
| Corrida no publicada | `not_published` | Metadatos de la corrida, pero sin filas, conteos ni exclusiones de evidencia |
| Faltan metadatos publicados | `metadata_missing` | Corrida PUBLICADA, sin un embudo inventado |

Un filtro sin coincidencias sobre una corrida PUBLICADA es **available**, con `items: []` y `page.total: 0`; el embudo completo permanece. En todos los casos no disponibles se exige un detalle visible. `M3RunStatus` puede estar disponible para una corrida no PUBLICADA porque solo muestra estado y avance. El estado `metadata_missing` aplica también a `m3_observations` cuando `m3_cortes` no contiene fila para la corrida.

Los [ejemplos v2](ejemplos/v2/) son datos ilustrativos independientes, no resultados de un experimento. Cubren PUBLICADA, RECHAZADA, EN_CURSO, varias publicaciones de la misma identidad, los cinco veredictos, origen sintético/desconocido, campeón Seasonal Naive, fallo por candidato y ventana, métricas nulas con causa, p-valor ausente con `dm_causa`, exclusiones tardías y de elegibilidad y embudo completo. El ejemplo `publicada` contiene ocho productos: dos lanzados después del corte, uno excluido por la regla de dos familias, tres no evaluados y dos evaluados. `filtrada` conserva esos mismos totales y muestra solo un SKU.

Los [modelos](referencia/modelos_v2.py) son la fuente de los [esquemas](schemas/v2/). CI valida los ejemplos contra ambos, comprueba que los esquemas exportados coinciden con los publicados y ejecuta regresiones de integridad. Las reglas entre campos se aplican en Pydantic; JSON Schema por sí solo no prueba publicación, conservación del embudo ni coherencia de trazas.
