# Contrato de consumo frontend ↔ motor (v1.0.0)

- **Fecha:** 2026-10-02
- **Estado:** Propuesto (pendiente de validación del equipo)
- **Tarea:** TASK-UI-1.0-A3
- **Decisión de base:** [ADR-05-001](../ADRs/ADR%2005-001-%20Stack%20y%20repositorio%20del%20frontend%20de%20la%20plataforma.md)

## 1. Propósito y alcance

Las vistas de `pred-platform` no leen al motor: leen la **base de datos de la plataforma** (SRS §3.6). El motor es una biblioteca que el worker de la plataforma llama en proceso; el worker guarda lo que el motor devuelve en el DAL y las vistas lo consultan por repositorios. Este documento fija las dos fronteras que hay que respetar:

1. **DAL → vistas:** los *modelos de lectura* que consumen C1 a C4 y el monitoreo (secciones 6 y 7). Con ellos se construyen la capa de acceso a datos con fixtures (TASK-UI-1.1-B4) y las vistas sin depender del resto.
2. **Motor → DAL:** qué devuelve el motor, dónde se persiste y qué falta en cada lado para que el modelo de lectura se pueda llenar con datos reales (secciones 8 y 12).

Fuera de alcance: implementar el worker, el DAL o cambios en el motor (los huecos están en la sección 12) y los textos finales de usuario.

## 2. Arquitectura de consumo

```
pred-engine (biblioteca Python, en proceso)
      │  objetos tipados en memoria (TopologyArtifact, SelectionResult, ResultadoWalkForward…)
      ▼
pred-platform · worker (consume tareas pendientes, una transacción por tarea)
      │  escribe
      ▼
DAL · SQLite (SRS §3.6)  ──repositorios──►  modelos de lectura (este contrato)  ──►  vistas
```

| Capa | Responsabilidad |
|---|---|
| **Motor** | Calcula y devuelve objetos tipados. No persiste estado de plataforma ni conoce las vistas. |
| **Worker** | Orquesta la corrida: crea las tareas (SKU × modelo × corte), llama al motor, registra estado, tiempos y errores, y confirma cada tarea. |
| **DAL** | Único punto de acceso a SQLite. Expone los repositorios que alimentan los modelos de lectura. |
| **Vistas** | Presentan los modelos de lectura. No recalculan nada ni tocan el motor. |

Estado de `pred-platform` (commit `140db0b`): el DAL define 11 tablas (`dal/schema.py`) y `worker/` y `auth/` son solo un docstring; la dependencia de `pred-engine` está comentada en `pyproject.toml` (`DEPENDENCIES.md`). El motor (commit `ab94847`) ya ejecuta una corrida completa de M0 a M2 (`pred-engine run` o `Pipeline.run`) y la deja en `data/runs/{run_id}/` con su estado por unidad, tiempos, errores y resultados; la plataforma todavía no la lee.

## 3. Principios

1. **Las vistas leen solo del DAL.** El modo real de B4 consulta repositorios; el modo fixture lee [`ejemplos/v1/`](ejemplos/v1/).
2. **El vocabulario es el del DAL cuando existe y el del motor cuando no.** Estados de tarea y de ejecución, veredictos y severidades son los de `dal/schema.py`; la evidencia técnica (familias, ensayos, hiperparámetros) conserva los nombres del motor. La sección 9 reúne las equivalencias con la SRS, el motor y la interfaz.
3. **Cada documento declara su disponibilidad.** Un dato que todavía no se produce llega con `availability.status = "unavailable"` y un `reason_code`, no como error. Así las acciones se deshabilitan explicando el motivo y los estados vacíos guían al siguiente paso.
4. **Los errores se identifican por `code`**, el mismo que se guarda en `bitacora_calidad.codigo`. La plataforma traduce el código a español.
5. **Versionado semántico por carpeta mayor** (`schemas/v1/`). Un cambio aditivo sube la versión menor; uno incompatible crea `v2/`.

## 4. Qué existe hoy

**DAL (`pred-platform/src/pred_platform/dal/schema.py`):**

| Tabla | Columnas relevantes | Lo usan |
|---|---|---|
| `ingestas` | `sha256` (único), `nombre_archivo`, `filas`, `skus`, `fecha_inicio`, `fecha_fin` | C1 |
| `bitacora_calidad` | `ingesta_id`, `severidad` (`info`/`advertencia`/`error`), `codigo`, `mensaje`, `fila`, `columna` | C1, errores |
| `series` | `ingesta_id`, `sku`, `familia`, `perfil_demanda` (texto libre), `n_obs` | C3 |
| `configuraciones` | `version`, `descripcion`, `parametros` | monitoreo |
| `ejecuciones` | `ingesta_id`, `configuracion_id`, `seed`, `estado`, `iniciada_en`, `finalizada_en` | monitoreo |
| `tareas` | `ejecucion_id`, `sku`, `modelo`, `corte`, `estado`, `seed`, `tiempo_pared_s`, `detalle_error`, `iniciada_en`, `finalizada_en` | monitoreo, C2 |
| `metricas` | `tarea_id`, `sku`, `modelo`, `metrica`, `valor` | C2 |
| `pronosticos` | `tarea_id`, `sku`, `modelo`, `fecha`, `valor` | fuera de v1 |
| `resultados_comparativos` | `ejecucion_id`, `sku`, `modelo_campeon`, `metrica_seleccion`, `valor_seleccion` | C2 (campeón) |
| `reportes_validacion` | `ejecucion_id`, `sku`, `modelo_campeon`, `veredicto`, `detalle` | validación retrospectiva |

**Motor (en proceso o en disco):**

| Origen | Contenido | Estado |
|---|---|---|
| `pred-engine run` o `Pipeline.run(workers=N)` | Corrida de L1 a L3: una unidad por SKU × familia en L2 y en L3, en paralelo, con fallos aislados y SKU excluidos con su causa | Se ejecuta como CLI o en proceso |
| `{data_root}/runs/{run_id}/corrida.json` | Esquema `pred-engine.corrida/1`: entradas, etapas con sus tiempos, corte t\* y reserva, exclusiones, fallas, procedencia de cada candidato y resumen de telemetría | En disco, **al terminar** la corrida |
| `{data_root}/runs/{run_id}/unidades.jsonl` | Una línea por unidad: etapa, SKU, familia, modelo, estado (`completada` o `fallida`), proceso, inicio, fin, segundos, CPU y error | En disco, al terminar |
| `candidatos.json`, `evaluacion.parquet`, `walk_forward.parquet`, `pronosticos.parquet` (misma carpeta) | Configuración completa de cada candidato (manifiesto para M3), métrica agregada, valor real y pronóstico por ventana, y pronóstico de los días reservados | En disco, al terminar |
| `recursos.jsonl`, `telemetria.svg` (misma carpeta) | CPU y memoria por proceso cada segundo | En disco; `recursos.jsonl` se escribe en vivo |
| `{data_root}/runs/{run_id}/hpo/` | Manifiesto y ensayos de cada estudio HPO (reanudación), en formato de Optuna | En disco |
| `run_classify_csv`, `run_ingest` | `TopologyArtifact.metrics` (ADI, CV², conteos por SKU) e `IngestResult` | En memoria; `Pipeline.ingest` los descarta |
| `{data_root}/processed/*.parquet` | Panel clasificado de 5 columnas | En disco |
| `{data_root}/logs/fase0_*.json`, `leer_bitacoras()` y `raw/panel_sintetico_fase0.csv` | Bitácora y artefacto de la Fase 0 | En disco |

## 5. Sobre común y disponibilidad

Todo modelo de lectura (excepto `error`) hereda estos campos:

| Campo | Tipo | Significado |
|---|---|---|
| `schema_version` | `1.x.y` | Versión del contrato con el que se emitió |
| `generated_at` | fecha-hora UTC | Momento de generación |
| `source` | `dal` \| `fixture` | Lectura real del DAL o dato de prueba |
| `availability` | objeto | Si el dato existe hoy |

`availability`: `status` (`available` \| `unavailable`) y, cuando no está disponible, `reason_code`, `blocked_by` (ids de hueco `G1`–`G8`) y `detail`.

| `reason_code` | Cuándo | Qué muestra la vista |
|---|---|---|
| `no_data` | Aún no hay datos (sin ingesta, sin ejecuciones) | Estado vacío con la acción siguiente |
| `not_implemented` | El dato lo producirá un hueco abierto; exige `blocked_by` | Estado vacío o acción deshabilitada con el motivo |
| `stage_not_implemented` | La etapa L4 o la selección final de M3 no existen | Sección marcada como no disponible |
| `prerequisite_missing` | Falta un prerrequisito del flujo | Acción deshabilitada con el motivo |

Las listas paginadas añaden `page = {number, size, total}` (`number ≥ 1`, `size ≤ 500`, por defecto 50). **El filtro, el orden y la paginación se resuelven en el servidor** (RNF-DES-04).

## 6. Vistas, operaciones y modelos de lectura

| Vista (tarea) | Operaciones | Modelos de lectura |
|---|---|---|
| Carga y validación (C1) | `submit_ingest`, `get_ingest_report`, `list_ingests` | `ingest_report`, `ingest_list` |
| Selección de modelos por SKU (C2) | `list_sku_selections`, `get_sku_selection`, `get_capabilities` | `sku_selection_list`, `sku_selection`, `capabilities` |
| Topología de demanda (C3) | `get_topology_report` | `topology_report` |
| Datos sintéticos (C4) | `list_synthetic_runs`, `get_synthetic_run`, `download_synthetic_artifact` | `synthetic_list`, `synthetic_run` |
| Monitoreo de ejecución (sin tarea UI aún) | `get_run_status` | `run_status` |
| Validación retrospectiva (sin tarea UI aún; reservado) | `get_validation_verdicts` | `validation_verdicts` |
| Transversal | — | `error`, `capabilities` |

## 7. Modelos de lectura

Cada uno tiene su [esquema JSON](schemas/v1/) y sus [ejemplos](ejemplos/v1/). La columna **Hoy** indica si el dato existe en el DAL o en el motor; `Gn` es el hueco que lo bloquea (sección 12).

### 7.1 `ingest_report` (C1)

| Campo | Fuente | Hoy |
|---|---|---|
| `ingest_id` | `ingestas.sha256` | Existe |
| `source_file` | `ingestas.nombre_archivo`, `filas` | Existe |
| `status` | `accepted` / `rejected` / `failed` / `needs_confirmation` | Falta columna de estado en `ingestas` ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778)) |
| `header_diagnostic` | `HeaderDiagnostic` del motor (`status` y entradas `field`/`severity`/`message`/`action`) | El motor lo devuelve en memoria; el DAL no lo guarda (G1) |
| `validation`, `published` | `IngestResult`, `publish_classified_panel` | Falta ruta del Parquet y conteos (G1) |
| `quality_log[]` | `bitacora_calidad` (`severidad`, `codigo`, `mensaje`, `fila`, `columna`) | Existe |
| `deposit` | Comparación del hash con `raw/<nombre>` | En curso ([G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f)): el motor compara hashes, rechaza un conflicto y, con confirmación, conserva ambos archivos. Ver «Semántica del depósito» abajo |
| `error` | Excepción normalizada (sección 11) | Con [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) |

Reglas que el esquema JSON no expresa: `needs_confirmation` exige `deposit.would_overwrite = true`; `failed` exige `error`; `rejected` exige `header_diagnostic.status = rejected`. Los códigos de `quality_log` y de `error` son los mismos (sección 11).

**Semántica del depósito (G5, decisión del 2026-10-14).** El motor nunca modifica ni borra un archivo ya depositado en `raw/` (ADR-01-002). Si llega un archivo con el mismo nombre y el mismo hash, `deposit.status = already_present_identical` y se reutiliza. Si el nombre coincide pero el contenido es distinto, la ingesta queda en `needs_confirmation` con `deposit.status = already_present_different` y `deposit.would_overwrite = true` (la bandera indica una **colisión de nombre**; nada se escribe). Con `confirm_overwrite = true` el motor **conserva ambos**: deposita el archivo nuevo como `<nombre>-<8 primeros caracteres del SHA-256><extensión>`, `deposit.status = deposited` y `deposit.raw_path` es esa ruta. El nombre del parámetro se mantiene por compatibilidad; significa «confirmar el depósito con otro nombre».

### 7.2 `ingest_list` (C1)

Una fila por ingesta: `ingest_id`, `name`, `status`, `parquet_path`, `rows`, `n_skus`, `published_at`. Hoy solo existen `sha256`, `nombre_archivo`, `filas` y `skus`; el resto requiere G1 y llega nulo.

### 7.3 `topology_report` (C3)

| Campo | Fuente | Hoy |
|---|---|---|
| `thresholds` | `ADI_THRESHOLD = 1.32`, `CV2_THRESHOLD = 0.49` (`comun/modelos/contrato.py` del motor) | Constantes del motor |
| `summary.by_class` | Conteo de `sku_class` | Derivable |
| `t_star` | Corte de la reserva (`ReserveCut`): el motor clasifica cada SKU solo con la historia hasta t\* (ADR-019 del motor) | Se calcula del calendario del panel; no se guarda |
| `items[]` | `TopologyMetrics`: `sku_id`, `n_periods`, `n_positive`, `adi`, `cv2`, `sku_class` | `run_classify_csv` y `run_ingest` los devuelven en memoria, pero `Pipeline.ingest` los descarta y `pred-engine run` no los guarda; `series` solo guarda `sku`, `familia`, `perfil_demanda` y `n_obs`. Faltan `adi`, `cv2`, `n_positive` y una clase tipada ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778)) |

### 7.4 `run_status` (monitoreo)

Una ejecución y sus tareas, con el vocabulario de `ejecuciones` y `tareas`.

| Campo | Fuente | Hoy |
|---|---|---|
| `ejecucion` | `ejecuciones`: `estado` (`pendiente`, `ejecutando`, `completada`, `completada_con_fallos`, `detenida`), `seed`, `iniciada_en`, `finalizada_en` | La escribe el worker de la plataforma al lanzar y seguir la corrida ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)); el id del motor queda en `ejecuciones.run_id` |
| `settings` | `configuraciones.parametros` (ventanas, métrica, familias, versión de política) | El worker escribe `parametros` con el formato acordado (7.4) al crear la ejecución (G3) |
| `reserve` | `summarize_run().reserve` y `corrida.json`: `fraction`, `t_star`, `first_reserved`, `last_observed`, `reserved_days` | El motor lo calcula y lo guarda en `corrida.json`; el worker lo guarda en `ejecuciones.reserva_json` (G3) |
| `tasks[]` | `tareas`: una por unidad del motor (SKU × modelo), con `estado` (`pendiente`, `ejecutando`, `exitosa`, `fallida`, `no_ejecutable`), `tiempo_pared_s`, `detalle_error`, `corte` | El worker las crea con el plan de la corrida (`planned`) y las actualiza con `progreso.jsonl`; al terminar `unidades.jsonl` y `corrida.json` son la verdad final (G3) |
| `progress` | Derivado del conteo de tareas por estado | Derivable |

Cada **unidad del motor** (SKU × modelo) es una tarea (decisión D6). Las ventanas de Walk-Forward no son tareas: son evidencia dentro de `sku_selection` (`walk_forward.windows`). La clave de `tareas` sigue siendo (ejecución, SKU, modelo, corte); como el corte es el mismo para toda la ejecución, no se repite ninguna fila.

**Estado de una tarea a partir de lo que deja el motor:**

| En el motor | Estado de la tarea |
|---|---|
| Unidad `completada` en L2 y en L3 | `exitosa` |
| Unidad `fallida` en L2 o en L3 | `fallida`, con su `error` |
| SKU en `exclusions` (por ejemplo, historia insuficiente) | `no_ejecutable` para todos sus modelos, con la causa |
| Unidad en el plan (`planned`) que aún no empezó | `pendiente` |
| Unidad con `unit_started` y sin `unit_finished` | `ejecutando`, con `iniciada_en` |

**Estado de la ejecución** a partir de las tareas y del proceso del motor (G3):

| Situación | `ejecuciones.estado` |
|---|---|
| Creada y aún no reclamada por el worker | `pendiente` |
| El motor corre (proceso vivo) | `ejecutando` |
| Terminó y todas las tareas son `exitosa` | `completada` |
| Terminó y alguna tarea es `fallida` o `no_ejecutable` | `completada_con_fallos` |
| El proceso del motor murió, se cerró la plataforma o una etapa no dejó resultados | `detenida`, con `error_json` (`platform.engine_unavailable` si no se pudo lanzar) |
| El operador la detiene desde la interfaz (§19) | `detenida`, con `error_json` = `platform.run_stopped`; el worker termina el proceso del motor y cierra sus tareas abiertas con ese error |

Reanudar es relanzar con el mismo `run_id` (se deriva de la entrada y los ajustes): el motor reutiliza sus estudios de HPO guardados y la plataforma actualiza las mismas filas de `tareas` (clave `(ejecución, SKU, modelo, corte)`), sin duplicarlas. Al reanudar, las tareas que habían terminado mal (`fallida` o `no_ejecutable`, también las que cerró una detención) vuelven a `pendiente` hasta que el motor las empieza de nuevo; las `exitosa` conservan su resultado. El motor **no omite** las unidades que ya habían terminado.

**Formatos acordados (decisión D5):**

| Campo | Formato | Ejemplo |
|---|---|---|
| `tareas.corte` | Texto ISO 8601 `AAAA-MM-DD`, sin hora: la fecha de corte t\* de la reserva (decisión D6), la misma para todas las tareas de una ejecución. Los cortes de cada ventana de Walk-Forward están en `walk_forward.windows[].corte`. Como texto ordena bien | `2026-06-29` |
| `tareas.modelo` | `familia:algoritmo` en minúsculas. La familia se deduce del prefijo, así que no hace falta un catálogo de modelos | `classical:sarima`, `ml:lightgbm`, `dl:mlp`, `foundation:chronos2` (los nombres de modelo son los del motor) |
| `configuraciones.parametros` | JSON con `schema_version` (entero) y los ajustes de la corrida (`RunSettings`). No se añaden umbrales de perfil de la SRS: la decisión D4 mantiene Syntetos-Boylan | `{"schema_version": 1, "min_train": 60, …}` |
| `tareas.detalle_error` | JSON de un `ErrorInfo` (hoy es texto libre, [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056)) | `{"code": "model.fit_failed", …}` |

El identificador `modelo` se usa también en `families[].modelo`, `champion.modelo` y `modelo_campeon`, y `family` solo puede coincidir con su prefijo. El nombre que ve el usuario (por ejemplo «SARIMA») lo define la plataforma a partir del identificador.

**Quién cambia el esquema y cómo se versiona (decisión D5).** Los cambios a `dal/schema.py` para G1, G3 y G4 los hace quien tenga esas tareas, con revisión del autor del esquema. Hoy el esquema usa `CREATE TABLE IF NOT EXISTS`, que no modifica las tablas ya creadas: una columna nueva no llegaría a las bases que ya existen. Lo acordado es guardar un número de versión dentro de SQLite (`PRAGMA user_version`) y aplicar al arrancar scripts de migración numerados, en orden y dentro de una transacción, con el esquema actual como versión 1. El ADR-05-002 (Propuesto) lo formaliza: ver `diseno/ADRs/`.

### 7.5 `sku_selection` y `sku_selection_list` (C2)

`sku_selection` es el detalle de un SKU y `sku_selection_list` son las filas de la tabla.

| Campo | Fuente | Hoy |
|---|---|---|
| `sku_class`, `profile`, `policy_version` | `SelectionResult` del motor | El motor los entrega en `seleccion.jsonl` (sección 20) y el DAL los guarda en `selecciones` ([G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f)) |
| `families[].estado` | El motor decide las cuatro familias de cada SKU (sección 20): `excluida` si la política o la configuración no la incluye, `no_ejecutable` si excluyó el SKU, `fallida` si su unidad falló en L2 o L3 y `exitosa` solo si terminó L2 y L3 | En `seleccion_familias`; la plataforma no replica la política |
| `families[].evidence` | `SelectionResult.payload`, unión discriminada por `family` | El payload serializable, con `family` y `estudio_hpo` (la referencia al estudio persistido), viaja en `seleccion.jsonl` y se guarda en `seleccion_familias` |
| `families[].trials[]` | `Trial`: `id`, `configuracion`, `estado`, `valor`, `n_ventanas`, `motivo`, `timestamp` | El motor los lee de `hpo/<estudio_hpo>/` sin Optuna (`pred_engine.comun.ensayos_hpo`, [G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5)) y los entrega en `seleccion.jsonl`; el DAL los guarda en `ensayos`. Son `null` en la familia fundacional, que no tiene estudio |
| `families[].walk_forward` | Resumen y ventanas con sus métricas (`seleccion.jsonl`) | El DAL guarda el resumen en `seleccion_familias`, las ventanas en `ventanas_wf` y sus métricas en `metricas`, ligadas a la tarea de la familia |
| `champion` | `resultados_comparativos` | Tabla existe; nadie la escribe (M3 no existe) |

**Evidencia por familia** (`evidence`, discriminada por `family`):

| `family` | Campos propios | Campos comunes |
|---|---|---|
| `classical` | `order` (3 enteros), `seasonal_order` (4 enteros) | `metrica_objetivo`, `valor`, `n_ventanas`, `n_trials`, `n_completados`, `n_podados`, `n_fallidos`, `seed` |
| `ml` | `hiperparametros` | los mismos |
| `dl` | `hiperparametros` | los mismos |
| `foundation` | `configuracion` (modelo, revisión, dispositivo…), `optimizado: false` | ninguno: no hay HPO |

**7.5.1 Exclusiones.** Las familias aplicables por clase salen de la política `2.2.0-initial` del motor y son estáticas:

| `sku_class` | Perfil | Familias permitidas |
|---|---|---|
| `smooth` | `dense_stable` | classical, ml, dl, foundation |
| `erratic` | `dense_variable` | classical, ml, dl, foundation |
| `intermittent` | `sparse_stable` | classical, ml, foundation |
| `lumpy` | `sparse_variable` | classical, foundation |

`exclusion.reason_code`: `not_in_policy_matrix` (la matriz no asigna esa familia a la clase), `not_configured` (la corrida usó un subconjunto de familias, RF-MOD-12), `series_too_short` y `execution_failed` (el motor las registra como exclusión de SKU y falla de unidad, con la causa en texto libre; los códigos están en [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438)). Ejemplo: [`sku_selection.lumpy_solo_clasica.json`](ejemplos/v1/sku_selection.lumpy_solo_clasica.json).

Reglas que el esquema JSON no expresa: `excluida` y `no_ejecutable` exigen `exclusion`; `fallida` exige `error`; `evidence.family` debe coincidir con `family`. Están en los [modelos de referencia](referencia/modelos_v1.py).

### 7.6 `validation_verdicts` (reservado)

Una fila de `reportes_validacion` por SKU: `modelo_campeon`, `veredicto` (`mantiene`, `parcial`, `falla`) y `detalle`. La etapa L4 no existe y la selección final es de M3: en v1 llega con `availability.reason_code = stage_not_implemented`. El esquema queda fijado para construir la pantalla de validación retrospectiva contra fixtures.

### 7.7 `synthetic_run` y `synthetic_list` (C4)

`log` es espejo de `BitacoraCorrida` (`aumentacion/bitacora.py` del motor) y `artifact` describe el CSV de `raw/` con su SHA-256. El DAL no tiene tablas para esto: se lee de los archivos de la Fase 0, y `leer_bitacoras()` del motor ya las lista. El motor añadió campos (método de aumento, tamaño de bloque, mapeo de columnas, huella de la corrida y configuración); las bitácoras anteriores no los traen, así que son opcionales y los dos formatos son válidos. El nombre del archivo ahora lleva microsegundos (`fase0_AAAAMMDDTHHMMSSffffff_seed42.json`). La bitácora no declara versión de esquema ([G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28)). El CSV de la Fase 0 tiene `demand_qty` entero (`int64`), distinto del Parquet de M1 (`float64`).

### 7.8 `capabilities`

Qué puede hacer el sistema hoy. La interfaz la usa para habilitar o deshabilitar acciones y explicar el motivo (criterio de C2).

| Capacidad | Hoy | Bloqueo |
|---|---|---|
| `parquet_read` | Sí | — (la plataforma lo da por disponible desde G3: el worker lanza el motor sobre el Parquet de la ingesta) |
| `synthetic_log_read` | Sí | — |
| `ingest_report_persisted`, `topology_persisted` | Sí | — (G1) |
| `run_orchestration` | Sí | — (G3) |
| `family_comparison` | Sí | — (G2, G3) |
| `selection_results_persisted` | Sí | — (G4) |
| `trial_detail_persisted` | Sí | — (G2, G4) |
| `walkforward_evidence_persisted` | Sí | — (G3, G4) |
| `champion_selection`, `retrospective_validation` | No | `stage_not_implemented` (M3 y L4) |

La acción «ejecutar selección» de C2 se habilita solo si `parquet_read`, `family_comparison` y `selection_results_persisted` están disponibles.

## 8. Frontera motor → DAL

Qué hace el worker con lo que el motor devuelve. Es la guía para G1 a G4.

| Llamada al motor | Devuelve | Se persiste en | Faltante |
|---|---|---|---|
| `run_ingest` / `run_classify_csv` | `IngestResult` (`source.sha256`, `diagnostic`, conteos) y `TopologyArtifact.metrics` | `ingestas`, `bitacora_calidad`, `series` | Columnas nuevas en el DAL y que el motor deje disponibles las métricas: `Pipeline.ingest` las descarta y `pred-engine run` no las guarda ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778)). `run_classify_csv` no devuelve el hash ni deposita en `raw/` ([G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f)) |
| `pred-engine run` o `Pipeline.run(workers=N)` | Corrida de L1 a L3 con unidades SKU × familia, fallos aislados y SKU excluidos con causa | `ejecuciones` y `tareas` (una por SKU × modelo) | El worker que la lanza y lee su resultado; el motor escribe `corrida.json` y `unidades.jsonl` solo al terminar, sin progreso en vivo ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)) |
| `unidades.jsonl` y `corrida.json` | Por unidad: etapa, SKU, familia, modelo, estado (`completada`/`fallida`), segundos, CPU y error. Por corrida: etapas con tiempos, t\*, exclusiones y fallas | `tareas` (estado, tiempo, error) y `ejecuciones` (inicio y fin) | Mapeo de estados de 7.4 |
| `candidatos.json`, `evaluacion.parquet`, `walk_forward.parquet` y los `candidates` de `corrida.json` | Configuración completa del candidato, métrica agregada, valores por ventana y procedencia (estudio HPO y contadores) | Resultado por SKU y familia, y `metricas` | Tablas de evidencia ([G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f)). Los ensayos solo están en `hpo/` ([G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5)) |
| `seleccion.jsonl` | Por SKU y familia: estado, exclusión, evidencia, ensayos del HPO y ventanas del Walk-Forward (sección 20) | `selecciones`, `seleccion_familias`, `ensayos`, `ventanas_wf` y `metricas` por ventana | El campeón sigue vacío hasta que M3 escriba `resultados_comparativos` |
| SKU excluidos y unidades fallidas | `exclusions` (causa en texto libre) y `failures` (`NombreDeClase: mensaje`) | `tareas.estado` = `no_ejecutable` o `fallida`, `bitacora_calidad.codigo` y `tareas.detalle_error` | Un código estable por causa ([G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056), [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438)) |

## 9. Vocabularios y equivalencias

Cuatro vocabularios conviven; el modelo de lectura usa el del DAL donde existe.

| Concepto | SRS / errata | DAL | Motor | Interfaz (`lenguaje-visual.md`) |
|---|---|---|---|---|
| Estado de tarea | `estadoFinal` de ED-07: `exitoso`, `fallido`, `interrumpido` | `pendiente`, `ejecutando`, `exitosa`, `fallida`, `no_ejecutable` | Unidad de la corrida: `completada`, `fallida`; manifiesto de estudio HPO: `nueva`, `en_progreso`, `interrumpida`, `completada`, `fallida` | Los mismos cinco del DAL |
| Estado de ejecución | — | `pendiente`, `ejecutando`, `completada`, `completada_con_fallos`, `detenida` | Etapas L1–L4: `pending`, `completed`, `blocked`, `failed` | Barra de progreso global |
| Veredicto | «veredicto categórico» (RF) | `mantiene`, `parcial`, `falla` | `hold`, `partial`, `fail` | se sostiene, se sostiene parcialmente, no se sostiene |
| Severidad | — | `info`, `advertencia`, `error` | `DiagnosticEntry`: `info`, `error` | Alertas: información, éxito, aviso, error |
| Perfil de demanda | ED-04: `tipoPerfil` (`regular`, `intermitente/lumpy`), `categoriaCombinada` (ABC-XYZ), CV, ZVI | `series.perfil_demanda` (texto libre) | `smooth`, `intermittent`, `erratic`, `lumpy` con ADI y CV² | Insignias de perfil, ABC y XYZ |
| Familia de modelos | ED-05 (errata v1.1): `estadisticos_clasicos`, `aprendizaje_automatico`, `aprendizaje_profundo_global`, `fundacionales` | `series.familia` (texto libre) | `classical`, `ml`, `dl`, `foundation` | — |
| Ensayo (trial) | — | `ensayos` | `pendiente`, `corriendo`, `completado`, `podado`, `fallido` | pendiente, ejecutando, completada, **podada**, fallida (D1) |

Observaciones:

- El estado de estudio del motor (`interrumpida`, etc.) es interno: la plataforma ve tareas y ejecuciones, y no lo necesita en las vistas.
- **ABC/XYZ no existe en el motor ni en el DAL** (se buscó `XYZ` y `categoria_combinada` en `pred-engine` y `pred-platform`), pero `contexto-diseno-ui.md` §3 espera insignias ABC/XYZ junto a cada SKU. La decisión D4 se resolvió el 2026-10-14: se mantiene Syntetos-Boylan y no se implementa ABC-XYZ (la SRS se ajusta a eso). El contrato no define campos de la SRS para el perfil (CV, ZVI, ABC-XYZ, `regular`/`intermitente/lumpy`) y las insignias ABC/XYZ de `contexto-diseno-ui.md` §3 quedan fuera.
- Un ensayo `podado` **no es un fallo**: la configuración sí corrió y la regla de poda la detuvo porque ya no era competitiva; su `motivo` lo explica (por ejemplo `poda_semantica:prediccion_nula`). La interfaz lo muestra con un estado propio, «podada», distinto de «fallida» (decisión D1). Equivalencias de los ensayos: `corriendo` → ejecutando, `completado` → completada, `podado` → podada, `fallido` → fallida. `motivo` es texto libre del motor y no se interpreta en v1.

## 10. Operaciones

Parámetros comunes de lista: `filters`, `sort`, `page`, `size`. Son consultas a los repositorios del DAL; cada una devuelve el modelo indicado o un [`error`](#11-errores).

| Operación | Parámetros | Devuelve |
|---|---|---|
| `get_capabilities()` | — | `capabilities` |
| `list_ingests(page, size)` | — | `ingest_list` |
| `get_ingest_report(ingest_id)` | `ingest_id` | `ingest_report` |
| `submit_ingest(file, confirm_overwrite=false)` | CSV con las cabeceras canónicas (`sku_id`, `timestamp`, `demand_qty`, `lead_time_days`): la plataforma ejecuta `pred-engine classify`, sin LLM (la alineación de cabeceras libres con un proveedor queda fuera); con `confirm_overwrite=false` y conflicto devuelve `needs_confirmation` sin tocar `raw/`; con `true` conserva ambos archivos (el nuevo con nombre versionado) | `ingest_report` |
| `get_topology_report(ingest_id, filters, sort, page, size)` | filtros `sku_class`, `q` (texto en `sku_id`); orden por `sku_id`, `adi`, `cv2`, `n_positive` | `topology_report` |
| `get_run_status(run_id, filters, page, size)` | filtros de `tasks`: `estado`, `sku`, `family` | `run_status` |
| `list_sku_selections(run_id, filters, sort, page, size)` | filtros `sku_class`, `family`, `estado`, `q`; orden por `sku_id`, `valor` | `sku_selection_list` |
| `get_sku_selection(run_id, sku_id, include_windows=false)` | `include_windows` incluye `walk_forward.windows` | `sku_selection` |
| `get_validation_verdicts(run_id)` | — | `validation_verdicts` |
| `list_synthetic_runs(page, size)` | — | `synthetic_list` |
| `get_synthetic_run(run_ref)` | `run_ref` = nombre de la bitácora sin extensión | `synthetic_run` |
| `download_synthetic_artifact(run_ref)` | verifica el SHA-256 antes de entregar | archivo `text/csv` |

**Referencia a una ejecución.** Donde una operación recibe `run_id` acepta el id de `ejecuciones`, el `run_id` del motor o el alias `latest`, que es la ejecución de mayor id (la última lanzada). Una vista que no sabe cuál mostrar usa `latest` y puede aceptar `?ejecucion=` para ver otra. Sin ejecuciones, `latest` responde con el estado vacío (`no_data`), no con un error. El alias no cambia ningún modelo, así que el contrato sigue en 1.0.0.

Lanzar, detener y reanudar corridas no entra en v1: no hay tarea de interfaz para esas pantallas.

## 11. Errores

`error` es `{code, stage, severity, detail, field, row_index, column, source_exception, retryable}`. `code` es el que se guarda en `bitacora_calidad.codigo`; **la plataforma lo traduce a un mensaje en español y a la acción sugerida** (RNF-USA-02). `detail` es el texto técnico del motor y no se muestra tal cual. `severity` usa el vocabulario del DAL. `stage`: `L0` (Fase 0), `L1` a `L4`, o `platform`.

| `code` | Etapa | Origen en el motor | Mensaje sugerido |
|---|---|---|---|
| `ingest.file_not_found` | L1 | `FileNotFoundError` | No se encontró el archivo. Verifique la ruta o cárguelo de nuevo. |
| `ingest.not_csv` | L1 | `ValueError` en `extract_csv` (sin tipo propio) | El archivo debe ser CSV y estar en la carpeta de datos crudos. |
| `ingest.header_rejected` | L1 | `HeaderDiagnostic.status = rejected`, `SemanticAlignmentError` | Las cabeceras no coinciden con el formato esperado. Revise cada observación. |
| `ingest.llm_provider` | L1 | `LlmError`, `LlmTimeoutError`, `LlmProviderError` | No se pudo consultar al proveedor de alineación semántica. |
| `ingest.schema_barrier` | L1 | `SchemaBarrierError` (`row_index`, `column`) | La fila {row_index} tiene un valor inválido en {column}. Corríjalo en el archivo. |
| `ingest.temporal_continuity` | L1 | `TemporalContinuityError` | Las fechas no forman una serie diaria válida. |
| `ingest.raw_write_blocked` | L1 | `RawWritePermissionError` | La carpeta de datos crudos es de solo lectura. |
| `ingest.raw_conflict` | L1 | `RawConflictError` (G5) | Ya existe un archivo con ese nombre y contenido distinto. Confirme para conservar ambos. |
| `topology.math` / `topology.routing` / `topology.contract` | L1 | `TopologyMathError` / `TopologyRoutingError` / `TopologyContractError` | No se pudo clasificar la demanda de uno o más SKU. |
| `handoff.contract` | L1 | `OutputContractError` | El resultado no cumple el formato de salida. |
| `handoff.preservation` | L1 | `PanelPreservationError` | La clasificación alteró filas del panel. |
| `handoff.precondition` | L1 | `HandoffPreconditionError` | Hay SKU sin demanda positiva; no se pueden clasificar. |
| `selection.contract` | L2 | `SelectionContractError` | No se pudo seleccionar un modelo para el SKU. |
| `selection.no_viable_trial` | L2 | `SelectionContractError` con mensaje «ningun trial de HPO completo» | Ninguna configuración terminó la búsqueda para este SKU. |
| `selection.unregistered_family` | L2 | `UnregisteredFamilyError` | La familia solicitada no está registrada. |
| `selection.unknown_class` | L2 | `UnknownSkuClassError` | La clase de demanda del SKU no es válida. |
| `selection.router_config` | L2 | `RouterConfigurationError`, `DuplicateStrategyError` | La configuración del enrutador no es válida. |
| `model.series_too_short` | L2/L3 | `SerieCortaError`, `VentanaInsuficienteError` | La serie es demasiado corta para esta familia. |
| `model.fit_failed` | L2/L3 | `AjusteModeloError` | El modelo no pudo ajustarse. |
| `model.foundation_unavailable` | L2/L3 | `ModeloFundacionalNoDisponibleError` | El modelo fundacional no está disponible en este equipo. |
| `hpo.invalid_space` / `hpo.study_failed` | L2 | `EspacioInvalidoError` / `EstudioError` | La búsqueda de configuraciones no pudo completarse. |
| `run.incompatible_config` | L2 | `IncompatibilidadCorridaError` | La configuración no coincide con la corrida guardada. |
| `run.failed_terminal` | L2 | `CorridaFallidaError` | La corrida anterior falló y no puede reanudarse. |
| `run.invalid_transition` | L2 | `TransicionEstadoError` | La corrida no admite esa operación en su estado actual. |
| `run.manifest_missing` / `run.manifest_corrupt` / `run.manifest_version` | L2 | `ManifiestoAusenteError` / `ManifiestoCorruptoError` / `VersionManifiestoError` | No se pudo leer el manifiesto de la corrida. |
| `evaluation.failed` | L3 | `EvaluacionError` | La evaluación Walk-Forward no pudo completarse. |
| `pipeline.stage_failed` | L1–L4 | `PipelineExecutionError` (`stage`) | La etapa {stage} falló. |
| `pipeline.stage_unavailable` | L4 | `StageUnavailableError` | Esta etapa aún no está disponible. |
| `synthetic.worm_overwrite` | L0 | `WormOverwriteError` | El archivo sintético ya existe y no puede reemplazarse. |
| `synthetic.conformance` | L0 | `SchemaConformanceError` | El archivo sintético no cumple el contrato. |
| `synthetic.divergence_exhausted` | L0 | `DivergenceRejectionExhausted` | No se logró una serie sintética aceptable. |
| `synthetic.physical_constraint` | L0 | `PhysicalConstraintError` | Se violó una restricción física de los datos. |
| `platform.contract_invalid` | platform | La respuesta no valida contra el esquema | Los datos recibidos no tienen el formato esperado. |
| `platform.schema_version_unsupported` | platform | `schema_version` con otra versión mayor | La versión del documento no es compatible. |
| `platform.artifact_missing` | platform | Archivo ausente o ilegible | No se encontró el resultado esperado. |
| `platform.engine_unavailable` | platform | El motor no responde | El motor no está disponible. |
| `platform.run_stopped` | platform | El operador detuvo la ejecución desde la interfaz | La ejecución se detuvo a petición del operador. Reanúdela cuando quiera. |

Los textos son sugerencias; la plataforma define la copia final. El código se deduce del **tipo** de la excepción; `ingest.not_csv` y `selection.no_viable_trial` solo se distinguen por el mensaje ([G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056)).

## 12. Huecos

Cada hueco tiene su tarea en el backlog. Ninguno se resuelve en A3. La columna **Dueño** indica de qué repositorio es el trabajo. Revisada el 2026-10-04 contra el motor tras el cierre de M0 a M2.

| Id | Hueco | Dueño | Evidencia | Bloquea | Tarea |
|---|---|---|---|---|---|
| G1 | El DAL no guarda el informe de ingesta ni las métricas topológicas, y el motor tampoco las deja disponibles en la corrida | Plataforma y motor | `ingestas` sin estado ni ruta del Parquet; `series` sin `adi`, `cv2`, `n_positive` y con `perfil_demanda` libre. `Pipeline.ingest` descarta `TopologyArtifact` y `pred-engine run` no lo guarda | C1, C3 | [G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778) (P1) |
| G2 | ~~Los ensayos de cada familia no salen del motor~~ **Resuelto** (2026-10-16) | Motor | `pred_engine.comun.ensayos_hpo` los lee de `hpo/` sin Optuna y `seleccion.jsonl` (sección 20) los entrega por SKU y familia | C2 | [G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5) (P1) |
| G3 | Falta el worker que lance y lea corridas y escriba `ejecuciones` y `tareas`; el motor no informa progreso en vivo | Plataforma y motor | `worker/__init__.py` solo tiene docstring. El motor guarda `corrida.json` y `unidades.jsonl` solo al terminar la corrida | Monitoreo, C2 | [G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6) (P1) |
| G4 | ~~El DAL no guarda la selección por SKU: ensayos, evidencia ni configuración elegida~~ **Resuelto** (2026-10-16) | Plataforma | Migración 0004: `selecciones`, `seleccion_familias`, `ensayos`, `ventanas_wf` y `metricas` por ventana | C2 | [G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f) (P1) |
| G5 | `deposit_raw_csv` sobrescribe sin avisar; la ruta canónica no deposita ni devuelve el hash | Motor | `ingesta/pipeline.py` (`copy2`) | C1 | [G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f) (P1) |
| G6 | No hay catálogo de códigos de error ni mapeo desde las excepciones | Plataforma y motor | Las unidades fallidas guardan `NombreDeClase: mensaje`, lo que permite mapear por clase; dos casos siguen sin tipo propio | Todas | [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) (P1) |
| G7 | Las exclusiones y las fallas del motor son texto libre | Motor y plataforma | El motor ya excluye los SKU con causa y aísla los fallos por unidad (RF-MOD-13); falta un código por causa | Monitoreo, C2 | [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438) (P2) |
| G8 | La bitácora de la Fase 0 no declara versión de esquema y ganó campos | Motor | `aumentacion/bitacora.py` ahora incluye método, mapeo de columnas, huella de la corrida y configuración | C4 | [G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28) (P2) |

Estado a 2026-10-16: **G2** y **G4** están resueltas con el archivo de la sección 20 y la migración 0004 de la plataforma. Estado a 2026-10-14: **G5** y la parte de ingesta de **G1** están resueltas (sección 17); **G3** se resuelve con el flujo de progreso de la sección 18 y el worker de la plataforma, que lanza el motor como subproceso del CLI (`pred-engine run`) y lee su carpeta de corrida, sin añadir `pred-engine` como dependencia.

Ya cubierto por el backlog existente: la selección final y los veredictos (M3, ADR-03-003) y la validación retrospectiva (L4).

## 13. Fixtures

Los [ejemplos](ejemplos/v1/) son la base de los fixtures de B4 y de las pruebas de D1. Cubren, por modelo, el caso normal, el vacío o no disponible y el de error.

| Escenario | Archivos |
|---|---|
| Capacidades hoy y con todo disponible | `capabilities.actual`, `.todo_disponible` |
| Carga aceptada, rechazada por cabeceras, fallida por fila y conflicto de sobrescritura | `ingest_report.accepted`, `.rejected`, `.failed`, `.needs_confirmation` |
| Lista de ingestas con datos y vacía | `ingest_list.normal`, `.vacio` |
| Topología con las cuatro clases y no disponible | `topology_report.normal`, `.vacio` |
| Ejecución en curso, con los cinco estados de tarea, y sin ejecuciones | `run_status.normal`, `.cinco_estados`, `.vacio` |
| SKU `lumpy` con solo la familia clásica, ensayos podados y exclusiones | `sku_selection.lumpy_solo_clasica` |
| SKU `smooth` con las cuatro familias, un ensayo fallido y campeón | `sku_selection.smooth_cuatro_familias` |
| Familia fallida y familia no ejecutable | `sku_selection.familia_fallida` |
| Lista de selecciones con datos y no disponible | `sku_selection_list.normal`, `.vacio` |
| Veredictos no disponibles y con veredictos | `validation_verdicts.no_disponible`, `.con_veredictos` |
| Bitácora nueva y bitácora anterior, lista y vacía | `synthetic_run.normal`, `synthetic_run.bitacora_anterior`, `synthetic_list.normal`, `.vacio` |
| Errores | `error.schema_barrier`, `.corrida_incompatible`, `.etapa_fallida`, `.contrato_invalido` |

**Procedencia.** La topología, la selección clásica, los ensayos y el Walk-Forward salen de una ejecución real del motor sobre un CSV mínimo de cuatro SKU (una por clase), hecha antes de que el motor incorporara la reserva de M3. Los ejemplos suponen un panel de 225 días con t\* = 2026-06-29, de modo que la historia hasta t\* (180 días) coincide con la de esa ejecución. Los ejemplos de ML, DL y foundation se construyeron a partir del código de sus estrategias y **no se ejecutaron**. La carga aceptada, las tareas, las ejecuciones, la reserva y el campeón son construidos con la forma del DAL: hoy nadie escribe esas tablas. Los errores, los veredictos, las capacidades y las bitácoras también son construidos (la bitácora anterior se instanció con el dataclass `BitacoraCorrida` original). Todos llevan `source: "fixture"`.

## 14. Decisiones

| Id | Pregunta | Quién | Estado |
|---|---|---|---|
| D1 | `podado` no está en los estados de la interfaz: ¿se añade una etiqueta propia para ensayos, con ícono y texto distintos de `fallido`? | Diseño (B2) | **Resuelta** (2026-10-04): los ensayos usan pendiente, ejecutando, completada, podada y fallida; «podada» es un estado aparte. B2 debe reflejarlo en `lenguaje-visual.md` y en `docs/DESIGN.md` de `pred-platform` |
| D2 | ¿Se acepta el catálogo de códigos de la sección 11 como el de la plataforma (`bitacora_calidad.codigo`)? | Equipo | **Aceptada** (2026-10-04) |
| D3 | Validar el contrato con el equipo y, si aplica, con los directores. | Equipo | **Validado por el equipo** (2026-10-04) |
| D4 | La SRS (RF-ING-10 a 13) exige calcular CV, ZVI y ABC-XYZ y etiquetar el perfil como `regular` o `intermitente/lumpy`. El motor clasifica con Syntetos-Boylan (ADI y CV², cuatro clases) y no calcula nada de lo anterior; además, ABC necesita costo unitario, que no entra en el contrato de datos del motor. | Equipo y directores | **Resuelta** (2026-10-14): se mantiene Syntetos-Boylan y no se implementa ABC-XYZ; la SRS se ajusta. El contrato conserva las cuatro clases del motor y no añade campos de perfil |
| D5 | Quién modifica `dal/schema.py`, cómo se versionan los cambios y qué formato tienen `tareas.corte`, `tareas.modelo`, `configuraciones.parametros` y `tareas.detalle_error`. | Dueño de la plataforma | **Resuelta** (2026-10-04): ver 7.4. El significado de `corte` se ajustó con D6. El ADR-05-002 de migraciones está redactado (Propuesto) |
| D6 | ¿Qué granularidad tienen las tareas de una ejecución? El DAL y el diseño original suponían una por ventana de Walk-Forward; el motor trabaja por SKU × familia. | Dueño de la plataforma | **Resuelta** (2026-10-04): una tarea por unidad del motor (SKU × modelo), con `corte` igual a t\*. Las ventanas quedan como evidencia |

## 15. Cómo se verificó

- Los 11 esquemas de [`schemas/v1/`](schemas/v1/) se exportaron de los [modelos de referencia](referencia/modelos_v1.py) (Pydantic v2) y coinciden exactamente con ellos.
- Los 28 ejemplos validan contra los modelos y, de forma independiente, contra los `.schema.json` (Draft 2020-12).
- Los modelos rechazan 36 casos inválidos probados: `unavailable` sin motivo, `not_implemented` sin `blocked_by`, `source` inexistente, clase inexistente, ADI no positivo, estado de tarea o veredicto o severidad del motor en lugar del DAL, `fallida` sin error (tarea o familia), `excluida` sin exclusión, tarea en curso con fecha de fin, `evidence.family` distinta de `family`, versión mayor 2.x, campos extra, hash mal formado y, por D5, un `modelo` sin familia o con mayúsculas, una `family` que no coincide con el prefijo de `modelo` (en tarea, familia y campeón), un `corte` que no es fecha ISO (formato distinto, con hora o inexistente) y parámetros sin `schema_version`; por D6, una reserva con fechas incoherentes, un `t_star` mal formado y campos de bitácora inválidos o desconocidos. Una bitácora anterior, sin los campos nuevos, sigue siendo válida, y las tareas son únicas por (SKU, modelo, corte).
- Las reglas entre campos (sección 7) **no** se expresan en JSON Schema; viven en los modelos de referencia y B4 debe conservarlas.
- El DAL se leyó en el commit `50803e9` de `pred-platform` (sin cambios en `140db0b`) y el motor en `ab94847`; si cambian, hay que revisar las secciones 4, 7, 8 y 12.

## 16. Para B4

1. Copiar los [modelos de referencia](referencia/modelos_v1.py) a `pred-platform` y completarlos; son la fuente de los esquemas (ADR-05-001).
2. Comparar el esquema exportado de esos modelos contra [`schemas/v1/`](schemas/v1/) en una prueba, de modo que un cambio accidental falle el CI.
3. Implementar los repositorios del modo `dal` sobre `pred_platform.dal` y un modo `fixture` que lea [`ejemplos/v1/`](ejemplos/v1/); el cambio entre ambos es una configuración. Mientras G1 a G4 estén abiertos, el modo `dal` devuelve `unavailable` con el hueco que bloquea. Los identificadores `modelo` y las fechas `corte` siguen los formatos de 7.4.
4. Rechazar con `platform.contract_invalid` cualquier respuesta que no valide, y con `platform.schema_version_unsupported` toda `schema_version` de otra versión mayor.
5. Tratar `availability.status = "unavailable"` como un estado de primera clase, no como un error.
6. Resolver las rutas relativas del contrato (`data/…`) contra la raíz de datos (`PRED_DATA_ROOT`, ADR-001 del motor).
7. Para `download_synthetic_artifact` en modo fixture, generar un CSV pequeño de cuatro columnas y calcular su SHA-256: los hashes y los 52 000 registros de [`synthetic_run.normal.json`](ejemplos/v1/synthetic_run.normal.json) son ilustrativos.
8. Antes de ejecutar el motor en macOS, instalar `libomp` (LightGBM); documentarlo en la tarea de documentación (TASK-UI-1.3-D3) y en el README de `pred-platform`.
9. El motor deja cada corrida en `data/runs/{run_id}/`. Mientras el worker (G3) no exista, el modo `dal` no tiene ejecuciones que mostrar, y el estado `ejecutando` no puede leerse del motor porque este escribe sus archivos al terminar.

## 17. Informe de ingesta del motor (`pred-engine.ingesta/1`)

Es el archivo con el que el motor entrega a la plataforma el resultado de **una ingesta** (G1). El motor lo escribe de forma atómica en `data/ingestas/<sha256>.json`, donde `<sha256>` es el hash del CSV de origen (el `ingest_id` del contrato), también cuando la ingesta termina `rejected`, `failed` o `needs_confirmation`. La plataforma lo importa al DAL (`ingestas`, `bitacora_calidad`, `series`); las vistas nunca lo leen directamente. Repetir la misma ingesta sobrescribe el mismo archivo con el mismo contenido (salvo `written_at`).

| Campo | Tipo | Notas |
|---|---|---|
| `schema` | texto | `pred-engine.ingesta/1`. La plataforma rechaza otra versión mayor con `platform.schema_version_unsupported` |
| `written_at` | fecha-hora ISO 8601 con zona | |
| `ingest_id` | SHA-256 | Hash del CSV de origen |
| `status` | `accepted`, `rejected`, `failed`, `needs_confirmation` | Vocabulario de 7.1 |
| `source_file` | `{name, sha256, row_count}` | `row_count` son las filas crudas |
| `deposit` | `{raw_path, status, would_overwrite}` o `null` | Rutas relativas a la raíz de datos (`raw/…`). Semántica en 7.1 |
| `header_diagnostic` | `{status, entries[]}` o `null` | `null` en la ruta canónica (sin sonda LLM) |
| `validation` | `{rows_validated, rows_daily_panel, n_skus}` o `null` | |
| `published` | `{parquet_path, rows, n_skus, columns[]}` o `null` | `parquet_path` relativo a la raíz (`processed/…`) |
| `quality_log` | lista de `{severity, code, message, row_index, column}` | `severity` usa el vocabulario del motor (`info`, `warning`, `error`); la plataforma lo traduce al del DAL (`warning` → `advertencia`). Los `code` son los de la sección 11 |
| `error` | `{code, stage, detail, field, row_index, column, source_exception, retryable}` o `null` | Obligatorio si `status = failed` |
| `reserve` | `{t_star, first_reserved, last_observed, reserved_days, fraction}` o `null` | Fechas ISO `AAAA-MM-DD`. Solo si hubo clasificación |
| `topology` | `{thresholds: {adi, cv2}, metrics[]}` o `null` | `metrics[]`: `{sku_id, n_periods, n_positive, adi, cv2, sku_class}`; `sku_class` es una de las cuatro clases del contrato 1.4 |

Reglas: `accepted` exige `published` y `topology`; `needs_confirmation` exige `deposit.would_overwrite = true`; `failed` exige `error`; los SKU de `topology.metrics` son únicos. `pred-engine run` además guarda las mismas métricas en `topologia.json` dentro de la carpeta de la corrida.

## 18. Flujo de progreso de la corrida (`pred-engine.progreso/1`)

Mientras `pred-engine run` ejecuta, el motor agrega una línea JSON por evento a `data/runs/{run_id}/progreso.jsonl` (una sola escritura `O_APPEND` por línea). La plataforma lo lee por desplazamiento y aplica cada evento a `tareas` y `ejecuciones` de forma idempotente. Una reanudación (mismo `run_id`) agrega un nuevo `run_started` y conserva los intentos anteriores.

Todos los eventos llevan `event` y `t` (ISO 8601 con zona). Campos propios:

| `event` | Campos | Significado |
|---|---|---|
| `run_started` | `schema` (`pred-engine.progreso/1`), `run_id`, `attempt`, `workers` | Empieza un intento de la corrida |
| `stage_started` / `stage_finished` | `stage` (`L1`, `L2`, `L3`), `state` (`completed`, `failed`) y `message` al fallar | Etapas del pipeline |
| `planned` | `stage` (`L2`, `L3`), `units[]` = `{sku_id, family, model}` | Unidades de la etapa, todas **pendientes** |
| `excluded` | `sku_id`, `cause` | SKU que no entra en L2 (texto libre hasta G7) |
| `unit_started` | `stage`, `sku_id`, `family`, `model`, `pid`, `started_at` | La unidad empieza; la escribe el proceso que la corre |
| `unit_finished` | `stage`, `sku_id`, `family`, `model`, `state` (`completada`, `fallida`), `pid`, `started_at`, `finished_at`, `seconds`, `cpu_s`, `error` (`NombreDeClase: mensaje`) | La unidad termina; si el proceso hijo muere, la escribe el padre como `fallida` |
| `run_finished` | `state` (`completed`, `failed`), `exit_code`, `failed_stage`, `blocked_stage` | Se escribe **después** de `corrida.json`: al verlo, los archivos finales ya existen |

Reglas: `model` es el nombre del motor (`sarima`, `lightgbm`, `mlp`, `chronos2`); la plataforma lo expresa como `familia:algoritmo` (7.4). Una tarea es `exitosa` solo si su unidad terminó `completada` en L2 y en L3. El archivo es evidencia de observabilidad: ninguna decisión del motor depende de él, y un fallo al escribirlo no interrumpe la corrida.

## 19. Lanzar, detener y reanudar una corrida (API de la plataforma)

Lanzar, detener y reanudar no son operaciones de lectura y no forman parte de los modelos de este contrato ni de `DataRepository`. La plataforma las ofrece como servicio de comandos (`pred_platform.worker.control.RunControl`, que la interfaz usa en `/ejecucion`), y el lanzamiento también como comando (`python -m pred_platform.worker --launch --ingest <sha256>`):

1. **Lanzar** (`launch`): valida que la ingesta exista y esté `accepted` (sección 17), crea una fila de `configuraciones` con `parametros` (7.4: `schema_version`, `min_train`, `horizon`, `step`, `metric`, `seasonality`, `aggregation`, `trim`, `families`, `trials`, `seed`, `workers`) y una de `ejecuciones` en `pendiente`. Pedir otra vez la misma ingesta con los mismos ajustes devuelve la ejecución existente.
2. El worker la reclama de forma atómica, lanza `pred-engine run --parquet <processed/…> --data-root <raíz> …` como subproceso (comando configurable con `PRED_ENGINE_CMD`) y la sigue mediante el flujo de la sección 18. Procesa una corrida a la vez; las demás esperan `pendiente`.
3. **Detener** (`stop`): pasa una ejecución `pendiente` o `ejecutando` a `detenida` con el error `platform.run_stopped` (sección 11), solo si todavía estaba en curso. El worker, que consulta el estado mientras sigue al motor, termina el proceso, cierra las tareas abiertas con ese error y no la da por terminada.
4. **Reanudar** (`resume`): una ejecución `detenida` o `completada_con_fallos` vuelve a `pendiente` con sus mismos ajustes y `run_id` (7.4: el motor reutiliza sus estudios de HPO y las tareas con mal resultado vuelven a `pendiente`).

El error propio de la ejecución se guarda en `ejecuciones.error_json`, pero `run_status` 1.0.0 no tiene un campo para él (la interfaz muestra los errores de las tareas); añadir un `ejecucion.error` opcional sería un cambio aditivo del contrato.

## 20. Selección por SKU de la corrida (`pred-engine.seleccion/1`)

Es el archivo con el que el motor entrega a la plataforma **la selección de cada SKU** (G2): para cada una de las cuatro familias, su estado, la evidencia de la configuración elegida, los ensayos del HPO y el Walk-Forward por ventana. Lo escribe `pred-engine run` en `data/runs/{run_id}/seleccion.jsonl`, de forma atómica, en cuanto termina L2 (también si L3 falla; sin L2 no hay archivo), y `corrida.json` lo lista en `files`. La plataforma lo importa al DAL al cerrar la ejecución (G4); las vistas nunca lo leen directamente. Repetir la corrida con el mismo `run_id` lo reescribe con el mismo contenido.

Una línea por SKU del panel, con el vocabulario del motor para lo que el contrato normaliza después (el código de un error, la razón de una exclusión por falla) y la forma de `FamilyEntry` (7.5) para el resto:

| Campo | Tipo | Notas |
|---|---|---|
| `schema` | texto | `pred-engine.seleccion/1`. La plataforma rechaza otra versión mayor |
| `run_id` | texto | `run_id` de la corrida del motor |
| `sku_id`, `sku_class`, `profile` | texto | `profile` sale de la matriz de la política |
| `policy_version` | texto | Por ejemplo `2.2.0-initial:configured:classical,ml` |
| `families` | lista de 4 | Siempre `classical`, `ml`, `dl`, `foundation`, en ese orden |

Cada elemento de `families` lleva `family` y `estado`, y según el estado:

| `estado` | Cuándo | Campos |
|---|---|---|
| `excluida` | La política no la asigna a la clase del SKU (`not_in_policy_matrix`) o la corrida se configuró con otro subconjunto de familias (`not_configured`) | `exclusion` = `{reason_code, detail}` |
| `no_ejecutable` | El motor excluyó el SKU antes de L2 | `cause`: texto libre, el mismo del evento `excluded` (sección 18). La plataforma deriva el `reason_code` (7.5.1) hasta G7 |
| `fallida` | La unidad falló en L2 o L3 | `modelo`, `error` = `{stage, text}` con `text` = `NombreDeClase: mensaje` (la plataforma lo normaliza como en la sección 11), `trials` del estudio si llegó a existir y, si falló en L3, también `evidence`, `produced_by`, `forecast_config` y `forecast_seed` |
| `exitosa` | Terminó L2 **y** L3 | `modelo`, `produced_by`, `evidence`, `forecast_config`, `forecast_seed`, `trials`, `walk_forward` |

- `modelo` es `familia:algoritmo` (D5), por ejemplo `classical:sarima`.
- `evidence` es el payload de la estrategia con `family` (7.5). La familia fundacional lleva `configuracion` y `optimizado: false`: **no optimiza, así que no tiene estudio, ni ensayos, ni contadores** (`trials` es `null`).
- `trials` es una lista de `{id, configuracion, estado, valor, n_ventanas, motivo, timestamp}` en el orden en que se cerraron los ensayos, con `estado` en `pendiente`, `corriendo`, `completado`, `podado` o `fallido` (9). Un ensayo `podado` y uno `fallido` llevan siempre su `motivo`. `null` significa que no hay estudio persistido (familia fundacional o corrida sin carpeta `hpo/`); una lista vacía, que el estudio no cerró ningún ensayo.
- `walk_forward` = `{metrica_objetivo, valor_agregado, completo, n_ventanas_evaluadas, n_ventanas_totales, selection_scope, statistical_comparison_available, windows[]}`, con `windows[]` = `{indice, corte, inicio_train, fin_train, inicio_val, fin_val, metricas, duracion_s, fallo}`. `corte` es el primer día de validación de la ventana (`AAAA-MM-DD`); los índices cuentan días desde el inicio de la historia del SKU; `metricas` trae `mae`, `rmse`, `smape` y `mase`. Un valor no finito se escribe `null`.

Los ensayos se leen de `hpo/<estudio_hpo>/backend.jsonl`, que usa el formato de Optuna; **quien consume `seleccion.jsonl` no necesita Optuna** y quien quiera leer un estudio suelto dispone de `pred_engine.comun.ensayos_hpo.leer_ensayos`, que traduce `COMPLETE`, `PRUNED`, `FAIL`, `RUNNING` y `WAITING` a `completado`, `podado`, `fallido`, `corriendo` y `pendiente` sin importarlo.

Reglas: el campeón no forma parte del archivo (lo escribirá M3 en `resultados_comparativos`); una línea ilegible o con una familia que no coincide con su `modelo` invalida solo a ese SKU en la importación.
