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

Estado del repositorio `pred-platform` al escribir este documento (commit `50803e9`): el DAL define 11 tablas (`dal/schema.py`) y `worker/` y `auth/` son solo un docstring; la dependencia de `pred-engine` está comentada en `pyproject.toml` (`DEPENDENCIES.md`). El motor solo escribe en disco el Parquet clasificado y el CSV depositado en `raw/`, el CSV y la bitácora de la Fase 0 y, si se le pide, un manifiesto de reanudación por estudio HPO (estado interno del motor, no de la plataforma).

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
| `run_classify_csv`, `run_ingest` | `TopologyArtifact.metrics` (ADI, CV², conteos por SKU), `IngestResult` | En memoria |
| `{data_root}/processed/*.parquet` | Panel clasificado de 5 columnas | En disco |
| `SelectionRouter.route` y las estrategias | `SelectionResult` con `payload` por familia | En memoria |
| `iterar_walk_forward`, `EjecutorGreedy` | Recorrido de Walk-Forward ventana por ventana | En memoria |
| `{raiz_corrida}/{run_id}/manifiesto.json` y `backend.jsonl` | Reanudación de un estudio HPO | En disco, si se pasa `raiz_corrida` y `sesion` |
| `{data_root}/logs/fase0_*.json` y `raw/panel_sintetico_fase0.csv` | Bitácora y artefacto de la Fase 0 | En disco |

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
| `deposit` | Comparación del hash con `raw/<nombre>` | `deposit_raw_csv` sobrescribe sin avisar ([G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f)) |
| `error` | Excepción normalizada (sección 11) | Con [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) |

Reglas que el esquema JSON no expresa: `needs_confirmation` exige `deposit.would_overwrite = true`; `failed` exige `error`; `rejected` exige `header_diagnostic.status = rejected`. Los códigos de `quality_log` y de `error` son los mismos (sección 11).

### 7.2 `ingest_list` (C1)

Una fila por ingesta: `ingest_id`, `name`, `status`, `parquet_path`, `rows`, `n_skus`, `published_at`. Hoy solo existen `sha256`, `nombre_archivo`, `filas` y `skus`; el resto requiere G1 y llega nulo.

### 7.3 `topology_report` (C3)

| Campo | Fuente | Hoy |
|---|---|---|
| `thresholds` | `ADI_THRESHOLD = 1.32`, `CV2_THRESHOLD = 0.49` (`comun/modelos/contrato.py` del motor) | Constantes del motor |
| `summary.by_class` | Conteo de `sku_class` | Derivable |
| `items[]` | `TopologyMetrics`: `sku_id`, `n_periods`, `n_positive`, `adi`, `cv2`, `sku_class` | El motor los devuelve en memoria; `series` solo guarda `sku`, `familia`, `perfil_demanda` y `n_obs`. Faltan `adi`, `cv2`, `n_positive` y una clase tipada ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778)) |

### 7.4 `run_status` (monitoreo)

Una ejecución y sus tareas, con el vocabulario de `ejecuciones` y `tareas`.

| Campo | Fuente | Hoy |
|---|---|---|
| `ejecucion` | `ejecuciones`: `estado` (`pendiente`, `ejecutando`, `completada`, `completada_con_fallos`, `detenida`), `seed`, `iniciada_en`, `finalizada_en` | Tabla existe; nadie la escribe ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)) |
| `settings` | `configuraciones.parametros` (ventanas, métrica, familias, versión de política) | Tabla existe; el formato de `parametros` no está definido (G3) |
| `tasks[]` | `tareas`: `estado` (`pendiente`, `ejecutando`, `exitosa`, `fallida`, `no_ejecutable`), `tiempo_pared_s`, `detalle_error`, `corte` | Tabla existe; nadie la escribe (G3) |
| `progress` | Derivado del conteo de tareas por estado | Derivable |

Cada **ventana de Walk-Forward** es una tarea (`corte` = fecha de corte). `family` es derivado: no hay catálogo de modelos en el DAL ([G4](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f)). `detalle_error` se guarda como JSON de un `ErrorInfo`; hoy es texto libre (G6).

### 7.5 `sku_selection` y `sku_selection_list` (C2)

`sku_selection` es el detalle de un SKU y `sku_selection_list` son las filas de la tabla.

| Campo | Fuente | Hoy |
|---|---|---|
| `sku_class`, `profile`, `policy_version` | `SelectionResult` del motor | En memoria; el DAL no los guarda (G4) |
| `families[].estado` | Tareas del SKU agrupadas por modelo; `excluida` si la política o la configuración no la incluye | Derivable cuando exista G3; la exclusión por política ya es derivable (tabla 7.5.1) |
| `families[].evidence` | `SelectionResult.payload`, unión discriminada por `family` | En memoria; el payload de DL incluye un objeto no serializable ([G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5)) |
| `families[].trials[]` | `Trial`: `id`, `configuracion`, `estado`, `valor`, `n_ventanas`, `motivo`, `timestamp` | El motor no los expone en el resultado (G2) y el DAL no tiene tabla (G4) |
| `families[].walk_forward` | `metricas` y `tareas` por corte | Tablas existen; falta G3 |
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

`exclusion.reason_code`: `not_in_policy_matrix` (la matriz no asigna esa familia a la clase), `not_configured` (la corrida usó un subconjunto de familias, RF-MOD-12), `series_too_short` y `execution_failed` ([G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438)). Ejemplo: [`sku_selection.lumpy_solo_clasica.json`](ejemplos/v1/sku_selection.lumpy_solo_clasica.json).

Reglas que el esquema JSON no expresa: `excluida` y `no_ejecutable` exigen `exclusion`; `fallida` exige `error`; `evidence.family` debe coincidir con `family`. Están en los [modelos de referencia](referencia/modelos_v1.py).

### 7.6 `validation_verdicts` (reservado)

Una fila de `reportes_validacion` por SKU: `modelo_campeon`, `veredicto` (`mantiene`, `parcial`, `falla`) y `detalle`. La etapa L4 no existe y la selección final es de M3: en v1 llega con `availability.reason_code = stage_not_implemented`. El esquema queda fijado para construir la pantalla de validación retrospectiva contra fixtures.

### 7.7 `synthetic_run` y `synthetic_list` (C4)

`log` es espejo de `BitacoraCorrida` (`aumentacion/bitacora.py` del motor) y `artifact` describe el CSV de `raw/` con su SHA-256. El DAL no tiene tablas para esto: se lee de los archivos de la Fase 0. La bitácora no declara versión de esquema ([G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28)). El CSV de la Fase 0 tiene `demand_qty` entero (`int64`), distinto del Parquet de M1 (`float64`).

### 7.8 `capabilities`

Qué puede hacer el sistema hoy. La interfaz la usa para habilitar o deshabilitar acciones y explicar el motivo (criterio de C2).

| Capacidad | Hoy | Bloqueo |
|---|---|---|
| `parquet_read` | Sí | — |
| `synthetic_log_read` | Sí | — |
| `ingest_report_persisted`, `topology_persisted` | No | G1 |
| `run_orchestration` | No | G3 |
| `family_comparison` | No | G2, G3 |
| `selection_results_persisted` | No | G4 |
| `trial_detail_persisted` | No | G2, G4 |
| `walkforward_evidence_persisted` | No | G3, G4 |
| `champion_selection`, `retrospective_validation` | No | `stage_not_implemented` (M3 y L4) |

La acción «ejecutar selección» de C2 se habilita solo si `parquet_read`, `family_comparison` y `selection_results_persisted` están disponibles.

## 8. Frontera motor → DAL

Qué hace el worker con lo que el motor devuelve. Es la guía para G1 a G4.

| Llamada al motor | Devuelve | Se persiste en | Faltante |
|---|---|---|---|
| `run_ingest` / `run_classify_csv` | `IngestResult` (`source.sha256`, `diagnostic`, conteos) y `TopologyArtifact.metrics` | `ingestas`, `bitacora_calidad`, `series` | Columnas nuevas en el DAL (G1). `run_classify_csv` no devuelve el hash ni deposita en `raw/` (G5) |
| `SelectionRouter.route(request)` | `SelectionResult` por familia | Resultado por SKU y familia | Tablas de evidencia y catálogo de modelos (G4); `payload` de DL serializable y ensayos expuestos (G2) |
| `iterar_walk_forward` / `EjecutorGreedy.avanzar()` | `EstadoParcial` por ventana (`ultima` con sus métricas, `n_evaluadas`, `n_totales`) | Una fila de `tareas` por ventana y filas de `metricas` | El worker (G3). El motor ya expone el recorrido paso a paso (ADR-02-004) |
| Estrategias con `raiz_corrida` y `sesion` | Reanudación de estudios HPO | Solo en disco del motor | Decidir si el worker lo usa y con qué `run_id` (convención: clásica y ML `{familia}-{sku}-{sesion}`; DL `dl-` + hash) (G3) |
| Series cortas | `SerieCortaError`, `VentanaInsuficienteError` | `tareas.estado = no_ejecutable` | RF-MOD-13 exige continuar con los siguientes modelos; `Pipeline.run` aborta toda la corrida (G7) |
| Excepciones | Tipos del motor | `bitacora_calidad.codigo` y `tareas.detalle_error` | Catálogo de códigos (G6) |

## 9. Vocabularios y equivalencias

Cuatro vocabularios conviven; el modelo de lectura usa el del DAL donde existe.

| Concepto | SRS / errata | DAL | Motor | Interfaz (`lenguaje-visual.md`) |
|---|---|---|---|---|
| Estado de tarea | `estadoFinal` de ED-07: `exitoso`, `fallido`, `interrumpido` | `pendiente`, `ejecutando`, `exitosa`, `fallida`, `no_ejecutable` | Manifiesto de estudio: `nueva`, `en_progreso`, `interrumpida`, `completada`, `fallida` | Los mismos cinco del DAL |
| Estado de ejecución | — | `pendiente`, `ejecutando`, `completada`, `completada_con_fallos`, `detenida` | Etapas L1–L4: `pending`, `completed`, `blocked`, `failed` | Barra de progreso global |
| Veredicto | «veredicto categórico» (RF) | `mantiene`, `parcial`, `falla` | `hold`, `partial`, `fail` | se sostiene, se sostiene parcialmente, no se sostiene |
| Severidad | — | `info`, `advertencia`, `error` | `DiagnosticEntry`: `info`, `error` | Alertas: información, éxito, aviso, error |
| Perfil de demanda | ED-04: `tipoPerfil` (`regular`, `intermitente/lumpy`), `categoriaCombinada` (ABC-XYZ), CV, ZVI | `series.perfil_demanda` (texto libre) | `smooth`, `intermittent`, `erratic`, `lumpy` con ADI y CV² | Insignias de perfil, ABC y XYZ |
| Familia de modelos | ED-05 (errata v1.1): `estadisticos_clasicos`, `aprendizaje_automatico`, `aprendizaje_profundo_global`, `fundacionales` | `series.familia` (texto libre) | `classical`, `ml`, `dl`, `foundation` | — |
| Ensayo (trial) | — | No existe tabla | `pendiente`, `corriendo`, `completado`, `podado`, `fallido` | Sin etiqueta propia para `podado` |

Observaciones:

- El estado de estudio del motor (`interrumpida`, etc.) es interno: la plataforma ve tareas y ejecuciones, y no lo necesita en las vistas.
- **ABC/XYZ no existe en el motor ni en el DAL** (se buscó `XYZ` y `categoria_combinada` en `pred-engine` y `pred-platform`), pero `contexto-diseno-ui.md` §3 espera insignias ABC/XYZ junto a cada SKU. Queda fuera de v1 (decisión D4).
- Un ensayo `podado` **no es un fallo**: lo descartó la regla de poda y su `motivo` lo explica (por ejemplo `poda_semantica:prediccion_nula`). C2 exige distinguirlo de `fallido` (decisión D1). `motivo` es texto libre del motor y no se interpreta en v1.

## 10. Operaciones

Parámetros comunes de lista: `filters`, `sort`, `page`, `size`. Son consultas a los repositorios del DAL; cada una devuelve el modelo indicado o un [`error`](#11-errores).

| Operación | Parámetros | Devuelve |
|---|---|---|
| `get_capabilities()` | — | `capabilities` |
| `list_ingests(page, size)` | — | `ingest_list` |
| `get_ingest_report(ingest_id)` | `ingest_id` | `ingest_report` |
| `submit_ingest(file, confirm_overwrite=false)` | CSV; con `confirm_overwrite=false` y conflicto devuelve `needs_confirmation` sin tocar `raw/` | `ingest_report` |
| `get_topology_report(ingest_id, filters, sort, page, size)` | filtros `sku_class`, `q` (texto en `sku_id`); orden por `sku_id`, `adi`, `cv2`, `n_positive` | `topology_report` |
| `get_run_status(run_id, filters, page, size)` | filtros de `tasks`: `estado`, `sku`, `family` | `run_status` |
| `list_sku_selections(run_id, filters, sort, page, size)` | filtros `sku_class`, `family`, `estado`, `q`; orden por `sku_id`, `valor` | `sku_selection_list` |
| `get_sku_selection(run_id, sku_id, include_windows=false)` | `include_windows` incluye `walk_forward.windows` | `sku_selection` |
| `get_validation_verdicts(run_id)` | — | `validation_verdicts` |
| `list_synthetic_runs(page, size)` | — | `synthetic_list` |
| `get_synthetic_run(run_ref)` | `run_ref` = nombre de la bitácora sin extensión | `synthetic_run` |
| `download_synthetic_artifact(run_ref)` | verifica el SHA-256 antes de entregar | archivo `text/csv` |

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

Los textos son sugerencias; la plataforma define la copia final. El código se deduce del **tipo** de la excepción; `ingest.not_csv` y `selection.no_viable_trial` solo se distinguen por el mensaje ([G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056)).

## 12. Huecos

Cada hueco tiene su tarea en el backlog (sin asignar). Ninguno se resuelve en A3. La columna **Dueño** indica de qué repositorio es el trabajo.

| Id | Hueco | Dueño | Evidencia | Bloquea | Tarea |
|---|---|---|---|---|---|
| G1 | El DAL no guarda el informe de ingesta ni las métricas topológicas | Plataforma | `ingestas` sin estado ni ruta del Parquet; `series` sin `adi`, `cv2`, `n_positive` y con `perfil_demanda` libre. El motor ya devuelve ambos en memoria | C1, C3 | [G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778) (P1) |
| G2 | `SelectionResult` no es serializable ni expone los ensayos | Motor | `modelos_deep_learning/estrategia.py` incluye `"estudio": estudio` en el payload; clásica y ML solo devuelven contadores | C2 | [G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5) (P1) |
| G3 | No hay worker ni escritura en `ejecuciones`/`tareas` | Plataforma | `worker/__init__.py` solo tiene docstring; `pred-engine` no está conectado | Monitoreo, C2 | [G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6) (P1) |
| G4 | El DAL no guarda la selección por SKU: ensayos, evidencia, configuración elegida ni catálogo modelo → familia | Plataforma | Solo existen `metricas` y `resultados_comparativos` | C2 | [G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f) (P1) |
| G5 | `deposit_raw_csv` sobrescribe sin avisar; la ruta canónica no deposita ni devuelve el hash | Motor | `ingesta/pipeline.py` (`copy2`) | C1 | [G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f) (P1) |
| G6 | No hay catálogo de códigos de error ni mapeo desde las excepciones | Plataforma y motor | Mensajes en inglés en `pipeline.py`; dos casos sin tipo propio | Todas | [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) (P1) |
| G7 | Un SKU de serie corta aborta toda la corrida; RF-MOD-13 exige continuar | Motor y plataforma | `Pipeline.fit` y `Pipeline.evaluate` lanzan `ValueError` | Monitoreo, C2 | [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438) (P2) |
| G8 | La bitácora de la Fase 0 no declara versión de esquema | Motor | `aumentacion/bitacora.py` | C4 | [G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28) (P2) |

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
| Corrida sintética, lista y vacía | `synthetic_run.normal`, `synthetic_list.normal`, `.vacio` |
| Errores | `error.schema_barrier`, `.corrida_incompatible`, `.etapa_fallida`, `.contrato_invalido` |

**Procedencia.** La topología, la selección clásica, los ensayos, el Walk-Forward y las fechas de corte salen de una ejecución real del motor sobre un CSV mínimo de cuatro SKU (una por clase). Los ejemplos de ML, DL y foundation se construyeron a partir del código de sus estrategias y **no se ejecutaron**. La carga aceptada usa cifras reales (720 filas, 4 SKU, hash del CSV). Las tareas, las ejecuciones y el campeón son fixtures construidos con la forma del DAL: hoy nadie escribe esas tablas. Los errores, los veredictos, las capacidades y la corrida sintética también son construidos (la bitácora se instanció con el dataclass real `BitacoraCorrida`). Todos llevan `source: "fixture"`.

## 14. Decisiones abiertas

| Id | Pregunta | Quién |
|---|---|---|
| D1 | `podado` no está en los estados de la interfaz: ¿se añade una etiqueta propia para ensayos, con ícono y texto distintos de `fallido`? | Diseño |
| D2 | ¿Se acepta el catálogo de códigos de la sección 11 como el de la plataforma (`bitacora_calidad.codigo`)? | Equipo |
| D3 | Validar el contrato con el equipo y, si aplica, con los directores. | Equipo |
| D4 | ABC/XYZ y el perfil `regular`/`intermitente/lumpy` de ED-04 no existen en el motor ni en el DAL, y la UI los espera. ¿Se reemplazan por las cuatro clases del motor (ADI y CV²) o se calculan aparte? | Equipo y directores |
| D5 | Quién modifica `dal/schema.py` (G1 y G4), cómo se versionan las migraciones y qué formato tienen `tareas.corte`, `tareas.modelo` y `configuraciones.parametros`. | Dueño de la plataforma |

## 15. Cómo se verificó

- Los 11 esquemas de [`schemas/v1/`](schemas/v1/) se exportaron de los [modelos de referencia](referencia/modelos_v1.py) (Pydantic v2) y coinciden exactamente con ellos.
- Los 27 ejemplos validan contra los modelos y, de forma independiente, contra los `.schema.json` (Draft 2020-12).
- Los modelos rechazan 16 casos inválidos probados: `unavailable` sin motivo, `not_implemented` sin `blocked_by`, `source` inexistente, clase inexistente, ADI no positivo, estado de tarea o veredicto o severidad del motor en lugar del DAL, `fallida` sin error (tarea o familia), `excluida` sin exclusión, tarea en curso con fecha de fin, `evidence.family` distinta de `family`, versión mayor 2.x, campos extra y hash mal formado.
- Las reglas entre campos (sección 7) **no** se expresan en JSON Schema; viven en los modelos de referencia y B4 debe conservarlas.
- El DAL se leyó en el commit `50803e9` de `pred-platform`; si cambia, hay que revisar las secciones 4, 7 y 12.

## 16. Para B4

1. Copiar los [modelos de referencia](referencia/modelos_v1.py) a `pred-platform` y completarlos; son la fuente de los esquemas (ADR-05-001).
2. Comparar el esquema exportado de esos modelos contra [`schemas/v1/`](schemas/v1/) en una prueba, de modo que un cambio accidental falle el CI.
3. Implementar los repositorios del modo `dal` sobre `pred_platform.dal` y un modo `fixture` que lea [`ejemplos/v1/`](ejemplos/v1/); el cambio entre ambos es una configuración. Mientras G1 a G4 estén abiertos, el modo `dal` devuelve `unavailable` con el hueco que bloquea.
4. Rechazar con `platform.contract_invalid` cualquier respuesta que no valide, y con `platform.schema_version_unsupported` toda `schema_version` de otra versión mayor.
5. Tratar `availability.status = "unavailable"` como un estado de primera clase, no como un error.
6. Resolver las rutas relativas del contrato (`data/…`) contra la raíz de datos (`PRED_DATA_ROOT`, ADR-001 del motor).
7. Para `download_synthetic_artifact` en modo fixture, generar un CSV pequeño de cuatro columnas y calcular su SHA-256: los hashes y los 52 000 registros de [`synthetic_run.normal.json`](ejemplos/v1/synthetic_run.normal.json) son ilustrativos.
8. Antes de ejecutar el motor en macOS, instalar `libomp` (LightGBM); documentarlo en D3 y en el README de `pred-platform`.
