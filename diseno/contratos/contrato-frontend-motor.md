# Contrato de consumo frontend ↔ motor (v1.0.0)

- **Fecha:** 2026-10-02
- **Estado:** Propuesto (pendiente de validación del equipo)
- **Tarea:** TASK-UI-1.0-A3
- **Decisión de base:** [ADR-05-001](../ADRs/ADR%2005-001-%20Stack%20y%20repositorio%20del%20frontend%20de%20la%20plataforma.md)

## 1. Propósito y alcance

`pred-platform` presenta lo que `pred-engine` produce; no recalcula métricas, selecciones ni validaciones. Este documento fija **qué documentos lee la plataforma**, con qué forma, y **qué falta hoy en el motor** para producirlos. Con él se construyen la capa de acceso a datos con fixtures (TASK-UI-1.1-B4) y las vistas C1 a C4 sin depender de la implementación de los módulos.

Fuera de alcance: implementar API o persistencia en el motor (los huecos están en la sección 10), pantallas y textos finales de usuario.

## 2. Principios

1. **Solo lectura, local y sin red.** La plataforma lee artefactos en disco; el único comando de escritura de v1 es cargar un archivo (sección 7).
2. **El contrato no renombra el motor.** Los nombres y valores de campo son los nativos (`estado: "podado"`, `family: "classical"`, `sku_class: "lumpy"`). Las etiquetas en español y el mapeo a los estados visuales van en tablas normativas (sección 8), nunca dentro de los datos.
3. **Cada documento declara su disponibilidad.** Un dato que el motor aún no produce no rompe la pantalla: llega con `availability.status = "unavailable"` y un `reason_code`. Así las acciones se deshabilitan explicando el motivo y los estados vacíos guían al siguiente paso.
4. **Los errores se identifican por `code`**, no por el texto del motor, que mezcla español e inglés.
5. **Versionado semántico por carpeta mayor** (`schemas/v1/`). Un cambio aditivo sube la versión menor; uno incompatible crea `v2/`.

## 3. Qué existe hoy en el motor

| Origen | Ubicación | Contenido | Se lee directo desde la plataforma |
|---|---|---|---|
| Panel clasificado | `{data_root}/processed/*.parquet` | 5 columnas: `sku_id`, `timestamp`, `demand_qty` (float64), `lead_time_days` (int64), `sku_class` | Sí (`read_classified_parquet`) |
| Manifiesto de estudio | `{raiz_corrida}/{run_id}/manifiesto.json` | Estado y contadores de **un** estudio HPO (familia × SKU) | Sí, si la corrida se lanzó con `raiz_corrida` ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)) |
| Checkpoint HPO | `{raiz_corrida}/{run_id}/backend.jsonl` | Ensayos en formato de Optuna | **No**: es un formato del backend. Se expone vía [G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5) |
| Bitácora Fase 0 | `{data_root}/logs/fase0_{marca}_seed{n}.json` | Parámetros y resultados de la generación sintética | Sí |
| CSV sintético | `{data_root}/raw/panel_sintetico_fase0.csv` | Artefacto WORM de la Fase 0 | Sí |
| Resultado del pipeline | Objetos en memoria (`PipelineResult`, `TopologyArtifact`, `IngestResult`) | Etapas L1–L4, métricas topológicas, evidencia L3 | **No**: no se persisten |

La mayoría de los documentos de este contrato dependen de persistencia que aún no existe; por eso el modo **fixture** (sección 11) es la vía de desarrollo hasta que se cierren los huecos.

## 4. Sobre común

Todo documento de lectura (excepto `error`) hereda estos campos:

| Campo | Tipo | Significado |
|---|---|---|
| `schema_version` | `1.x.y` | Versión del contrato con el que se emitió |
| `generated_at` | fecha-hora UTC | Momento de generación |
| `source` | `engine` \| `fixture` | Origen: lectura real o dato de prueba |
| `availability` | objeto | Si el dato existe hoy |

`availability`: `status` (`available` \| `unavailable`), y cuando no está disponible `reason_code`, `blocked_by` (ids de hueco `G1`–`G8`) y `detail`.

| `reason_code` | Cuándo | Qué muestra la vista |
|---|---|---|
| `no_data` | Aún no hay datos (sin ingesta, sin corridas) | Estado vacío con la acción siguiente |
| `engine_gap` | El motor no produce el dato todavía; exige `blocked_by` | Estado vacío o acción deshabilitada con el motivo |
| `stage_not_implemented` | La etapa L4 o la selección de M3 no existen | Sección marcada como no disponible |
| `prerequisite_missing` | Falta un prerrequisito del flujo | Acción deshabilitada con el motivo |

Las listas paginadas añaden `page = {number, size, total}` (`number ≥ 1`, `size ≤ 500`, por defecto 50). **El filtro, el orden y la paginación se resuelven en el servidor** (RNF-DES-04).

## 5. Vistas, operaciones y documentos

| Vista (tarea) | Operaciones | Documentos |
|---|---|---|
| Carga y validación (C1) | `submit_ingest`, `get_ingest_report`, `list_ingests` | `ingest_report`, `ingest_list` |
| Selección de modelos por SKU (C2) | `list_sku_selections`, `get_sku_selection`, `get_engine_capabilities` | `sku_selection_list`, `sku_selection`, `engine_capabilities` |
| Topología de demanda (C3) | `get_topology_report` | `topology_report` |
| Datos sintéticos (C4) | `list_synthetic_runs`, `get_synthetic_run`, `download_synthetic_artifact` | `synthetic_list`, `synthetic_run` |
| Monitoreo de ejecución (sin tarea UI aún) | `get_run_status` | `run_status` |
| Validación retrospectiva (sin tarea UI aún; reservado) | `get_validation_verdicts` | `validation_verdicts` |
| Transversal | — | `error`, `engine_capabilities` |

## 6. Documentos

Cada uno tiene su [esquema JSON](schemas/v1/) y [ejemplos](ejemplos/v1/). La columna **Hoy** indica si el motor puede llenar el campo con lo que existe; `Gn` es el hueco que lo bloquea.

### 6.1 `ingest_report` (C1)

| Campo | Fuente en el motor | Hoy |
|---|---|---|
| `ingest_id` | SHA-256 del archivo fuente | La ruta canónica no lo devuelve ([G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f)); `run_ingest` sí (`IngestResult.source.sha256`) |
| `status` | `accepted` / `rejected` (diagnóstico) / `failed` (error) / `needs_confirmation` (conflicto de depósito) | Parcial ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778), G5) |
| `source_file` | `ExtractionArtifact` (`sha256`, `row_count`) | Solo en `run_ingest` |
| `deposit` | `raw/` y comparación de hash | No: `deposit_raw_csv` sobrescribe sin avisar (G5) |
| `header_diagnostic` | `HeaderDiagnostic` (`status`, entradas `field`/`severity`/`message`/`action`) | En memoria; solo la CLI lo imprime (G1) |
| `validation` | Filas validadas, filas del panel diario, SKU | En memoria (G1) |
| `published` | `publish_classified_panel` | Parquet sí; el resumen no se persiste (G1) |
| `error` | Excepción normalizada (sección 9) | Sí, con [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) para códigos estables |

Reglas que el esquema JSON no expresa: `status = needs_confirmation` exige `deposit.would_overwrite = true`; `failed` exige `error`; `rejected` exige `header_diagnostic.status = rejected`.

### 6.2 `ingest_list` (C1)

Resumen por Parquet publicado: `ingest_id`, `name`, `status`, `parquet_path`, `rows`, `n_skus`, `published_at`. Hoy solo es posible listar los Parquet de `processed/`; el resto de campos requiere [G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778) y son nulos mientras tanto.

### 6.3 `topology_report` (C3)

| Campo | Fuente | Hoy |
|---|---|---|
| `thresholds` | `ADI_THRESHOLD = 1.32`, `CV2_THRESHOLD = 0.49` (`comun/modelos/contrato.py`) | Sí |
| `summary.by_class` | Conteo de `sku_class` | Derivable del Parquet |
| `items[]` | `TopologyMetrics`: `sku_id`, `n_periods`, `n_positive`, `adi`, `cv2`, `sku_class` | **No**: solo en memoria e impresas por la CLI (G1) |

### 6.4 `run_status` (Monitoreo)

| Campo | Fuente | Hoy |
|---|---|---|
| `stages[]` | `summarize_run`: `id` L1–L4, `name`, `maturity`, `state`, `capability`, `message` | En memoria; mensajes en inglés ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6), G6) |
| `settings` | `EvaluationSettings` | En memoria (G3) |
| `studies[]` | `ManifiestoCorrida` por estudio | Solo si la estrategia recibió `raiz_corrida`; `build_pipeline` no lo hace (G3) |
| `progress` | Derivado de `studies` | Derivable de los manifiestos |
| `started_at`, `finished_at`, `run_id` | No existen | No (G3) |

El `study_id` es el `run_id` del motor. Convención actual: clásica y ML `{familia}-{sku_id}-{sesion}`; DL `dl-` + hash; foundation no genera estudio. El `run_id` del documento es otro: el de la corrida de plataforma que agrupa estudios (G3).

### 6.5 `sku_selection` y `sku_selection_list` (C2)

`sku_selection` es el detalle de un SKU; `sku_selection_list` son las filas de la tabla.

| Campo | Fuente | Hoy |
|---|---|---|
| `sku_class`, `profile`, `policy_version` | `SelectionResult` | En memoria ([G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5)) |
| `families[].family`, `state`, `exclusion` | Matriz de política `FAMILIES_BY_SKU_CLASS` y configuración de la corrida | La exclusión por política es derivable (tabla 6.5.1); el resto requiere G2 y [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438) |
| `families[].evidence` | `SelectionResult.payload`, unión discriminada por `family` | En memoria; el payload de DL incluye un objeto no serializable (G2) |
| `families[].trials[]` | `Trial`: `id`, `configuracion`, `estado`, `valor`, `n_ventanas`, `motivo`, `timestamp` | Solo en `backend.jsonl` y `ResultadoEstudio` (G2) |
| `families[].walk_forward` | `ResultadoWalkForward` sin arreglos | En memoria ([G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f)) |
| `champion` | Selección final entre familias (M3, ADR-03-003) | No existe; siempre `null` en v1 |

**Evidencia por familia** (`evidence`, discriminada por `family`):

| `family` | Campos propios | Campos comunes |
|---|---|---|
| `classical` | `order` (3 enteros), `seasonal_order` (4 enteros) | `metrica_objetivo`, `valor`, `n_ventanas`, `n_trials`, `n_completados`, `n_podados`, `n_fallidos`, `seed` |
| `ml` | `hiperparametros` | los mismos |
| `dl` | `hiperparametros` | los mismos |
| `foundation` | `configuracion` (modelo, revisión, dispositivo…), `optimizado: false` | ninguno: no hay HPO |

**6.5.1 Exclusiones.** Las familias aplicables por clase salen de la política `2.2.0-initial` y son estáticas:

| `sku_class` | Perfil | Familias permitidas |
|---|---|---|
| `smooth` | `dense_stable` | classical, ml, dl, foundation |
| `erratic` | `dense_variable` | classical, ml, dl, foundation |
| `intermittent` | `sparse_stable` | classical, ml, foundation |
| `lumpy` | `sparse_variable` | classical, foundation |

`exclusion.reason_code`: `not_in_policy_matrix` (la matriz no asigna esa familia a la clase), `not_configured` (la corrida usó un subconjunto de familias), `series_too_short` y `execution_failed` (requieren G7). Ejemplo: [`sku_selection.lumpy_solo_clasica.json`](ejemplos/v1/sku_selection.lumpy_solo_clasica.json).

Reglas que el esquema JSON no expresa: `excluded` y `not_executable` exigen `exclusion`; `failed` exige `error`; `evidence.family` debe coincidir con `family`. Están implementadas en los [modelos de referencia](referencia/modelos_v1.py).

### 6.6 `validation_verdicts` (reservado)

`hold` | `partial` | `fail` por SKU, más `audit_bundle`. La etapa L4 no existe y la selección final es de M3; en v1 el documento llega siempre con `availability.reason_code = stage_not_implemented`. El esquema queda fijado para que la pantalla de validación retrospectiva se construya contra fixtures.

### 6.7 `synthetic_run` y `synthetic_list` (C4)

`log` es espejo de `BitacoraCorrida` (`aumentacion/bitacora.py`); `artifact` describe el CSV de `raw/` con su SHA-256. La bitácora no declara versión de esquema propia ([G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28)). Ojo: el CSV de la Fase 0 tiene `demand_qty` entero (`int64`), distinto del Parquet de M1 (`float64`).

### 6.8 `engine_capabilities`

Lista qué capacidades del motor existen hoy. La interfaz la usa para habilitar o deshabilitar acciones y explicar el motivo (criterio de C2).

| Capacidad | Hoy | Bloqueo |
|---|---|---|
| `parquet_read` | Sí | — |
| `synthetic_log_read` | Sí | — |
| `ingest_report_persisted`, `topology_persisted` | No | G1 |
| `family_comparison`, `selection_results_persisted`, `trial_detail_persisted` | No | G2 |
| `run_state_persisted` | No | G3 |
| `walkforward_evidence_persisted` | No | G4 |
| `champion_selection`, `retrospective_validation` | No | `stage_not_implemented` (M3 y L4) |

La acción «ejecutar selección» de C2 se habilita solo si `parquet_read`, `family_comparison` y `selection_results_persisted` están disponibles.

## 7. Operaciones

Parámetros comunes de lista: `filters`, `sort`, `page`, `size`. Todas las operaciones devuelven el documento indicado o un [`error`](#9-errores).

| Operación | Parámetros | Devuelve |
|---|---|---|
| `get_engine_capabilities()` | — | `engine_capabilities` |
| `list_ingests(page, size)` | — | `ingest_list` |
| `get_ingest_report(ingest_id)` | `ingest_id` | `ingest_report` |
| `submit_ingest(file, confirm_overwrite=false)` | archivo CSV; con `confirm_overwrite=false` y conflicto devuelve `needs_confirmation` sin tocar `raw/` | `ingest_report` |
| `get_topology_report(ingest_id, filters, sort, page, size)` | filtros `sku_class`, `q` (texto en `sku_id`); orden por `sku_id`, `adi`, `cv2`, `n_positive` | `topology_report` |
| `get_run_status(run_id, filters, page, size)` | filtros de `studies`: `family`, `estado`, `sku_id` | `run_status` |
| `list_sku_selections(run_id, filters, sort, page, size)` | filtros `sku_class`, `family`, `state`, `q`; orden por `sku_id`, `valor` | `sku_selection_list` |
| `get_sku_selection(run_id, sku_id, include_windows=false)` | `include_windows` incluye `walk_forward.windows` | `sku_selection` |
| `get_validation_verdicts(run_id)` | — | `validation_verdicts` |
| `list_synthetic_runs(page, size)` | — | `synthetic_list` |
| `get_synthetic_run(run_ref)` | `run_ref` = nombre de la bitácora sin extensión | `synthetic_run` |
| `download_synthetic_artifact(run_ref)` | verifica el SHA-256 antes de entregar | archivo `text/csv` |

Lanzar, detener y reanudar corridas no entra en v1: no hay tarea de interfaz para esas pantallas.

## 8. Estados y mapeos

El contrato conserva los valores del motor; este es el mapeo normativo a la interfaz (`lenguaje-visual.md` §5).

**Estudio (`Study.estado`, `ManifiestoCorrida.estado`) → ciclo de tarea de la UI**

| Motor | UI | Nota |
|---|---|---|
| `nueva` | pendiente | |
| `en_progreso` | ejecutando | |
| `completada` | exitosa | |
| `fallida` | fallida | Estado terminal |
| `interrumpida` | **sin equivalente** | Propuesta: pendiente con marca «reanudable». Ver decisión D1 |
| — | no ejecutable | El motor no lo produce ([G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438)) |

**Etapa (`StageState.state`)**: `pending` → pendiente, `completed` → exitosa, `failed` → fallida, `blocked` → capacidad no disponible (no es una tarea). Decisión D2.

**Estado de familia (`FamilyEntry.state`)**: `pending` → pendiente, `running` → ejecutando, `completed` → exitosa, `failed` → fallida, `not_executable` → no ejecutable, `excluded` → «no aplica» (sin ícono de estado).

**Ensayo (`TrialRow.estado`)**: `pendiente`, `corriendo`, `completado`, `fallido` siguen el ciclo de tarea. **`podado` no es un fallo**: el ensayo se descartó por la regla de poda y su `motivo` lo explica (por ejemplo `poda_semantica:prediccion_nula`). C2 exige distinguirlo de `fallido`. Decisión D3.

**Veredicto**: `hold` → se sostiene, `partial` → se sostiene parcialmente, `fail` → no se sostiene.

`motivo` de un ensayo es texto libre del motor; no se interpreta en v1.

## 9. Errores

`error` es `{code, stage, severity, detail, field, row_index, column, source_exception, retryable}`. **La plataforma traduce `code` a un mensaje en español y a la acción sugerida** (RNF-USA-02); `detail` es el texto técnico del motor y no se muestra tal cual. `stage`: `L0` (Fase 0), `L1` a `L4`, o `platform`.

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

Los textos son sugerencias de redacción; la plataforma define la copia final. Mientras no exista [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056), el código se deduce del **tipo** de la excepción; `ingest.not_csv` y `selection.no_viable_trial` solo se distinguen por el mensaje.

## 10. Huecos del motor

Cada hueco tiene su tarea en el backlog (sin asignar). Ninguna se resuelve en A3.

| Id | Hueco | Evidencia en el código | Bloquea | Tarea |
|---|---|---|---|---|
| G1 | Informe de ingesta y métricas topológicas solo existen en memoria | `TopologyArtifact.metrics`, `IngestResult`; la CLI imprime ADI/CV² (`cli.py`) | C1, C3 | [G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778) (P1) |
| G2 | No hay servicio que lea el Parquet, compare familias y persista resultados por SKU; el payload de DL no es serializable; los ensayos solo salen en formato Optuna | `Pipeline.run` en memoria; `modelos_deep_learning/estrategia.py` (`"estudio": estudio`) | C2 | [G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5) (P1) |
| G3 | El pipeline coordinado no persiste manifiestos ni estado agregado; `run_id` inconsistente entre familias; sin tiempos | `build_pipeline` no pasa `raiz_corrida`/`sesion`; `summarize_run` | Monitoreo | [G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6) (P1) |
| G4 | La evidencia Walk-Forward no se serializa (arreglos NumPy) | `comun/dataclasses/validacion_temporal.py` | C2 (detalle) | [G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f) (P2) |
| G5 | `deposit_raw_csv` sobrescribe sin avisar; la ruta canónica no deposita ni devuelve el hash | `ingesta/pipeline.py` (`copy2`) | C1 | [G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f) (P1) |
| G6 | Excepciones sin código estable; mensajes mezclan idiomas | `*/errores.py`, `pipeline.py` | Todas | [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) (P1) |
| G7 | Un SKU inválido aborta toda la corrida; no existe `no_ejecutable` | `Pipeline.fit` / `Pipeline.evaluate` lanzan `ValueError` | Monitoreo, C2 | [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438) (P2) |
| G8 | La bitácora de la Fase 0 no declara versión de esquema | `aumentacion/bitacora.py` | C4 | [G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28) (P2) |

Ya cubierto por el backlog existente, sin tarea nueva: la selección final y los veredictos (M3, ADR-03-003) y la validación retrospectiva (L4).

## 11. Fixtures

Los [ejemplos](ejemplos/v1/) son la base de los fixtures de B4 y de las pruebas de D1. Cubren, por documento, el caso normal, el vacío o no disponible y el de error.

| Escenario | Archivos |
|---|---|
| Capacidades hoy y con todo disponible | `engine_capabilities.engine_actual`, `.todo_disponible` |
| Carga aceptada, rechazada por cabeceras, fallida por fila, y conflicto de sobrescritura | `ingest_report.accepted`, `.rejected`, `.failed`, `.needs_confirmation` |
| Lista de ingestas con datos y vacía | `ingest_list.normal`, `.vacio` |
| Topología con las cuatro clases y no disponible | `topology_report.normal`, `.vacio` |
| Corrida con etapa L4 bloqueada, con los cinco estados de estudio, y sin corrida | `run_status.normal`, `.cinco_estados`, `.vacio` |
| SKU `lumpy` con solo la familia clásica, ensayos podados y exclusiones | `sku_selection.lumpy_solo_clasica` |
| SKU `smooth` con las cuatro familias y un ensayo fallido | `sku_selection.smooth_cuatro_familias` |
| Familia fallida | `sku_selection.familia_fallida` |
| Lista de selecciones con datos y no disponible | `sku_selection_list.normal`, `.vacio` |
| Veredictos no disponibles y con veredictos | `validation_verdicts.no_disponible`, `.con_veredictos` |
| Corrida sintética, lista y vacía | `synthetic_run.normal`, `synthetic_list.normal`, `.vacio` |
| Errores | `error.schema_barrier`, `.corrida_incompatible`, `.etapa_fallida`, `.contrato_invalido` |

**Procedencia.** Los ejemplos de topología, de la política y de las etapas, la clasificación, la selección clásica, los ensayos y el Walk-Forward salen de una ejecución real del motor sobre un CSV mínimo de cuatro SKU (una por clase). Los ejemplos de ML, DL y foundation se construyeron a partir del código de sus estrategias, **no se ejecutaron**: LightGBM necesita la biblioteca `libomp` en macOS y no estaba instalada. La carga aceptada usa cifras reales (720 filas, 4 SKU, hash del CSV) y el resto de sus campos se construyó. Los ejemplos de errores, la carga rechazada o en conflicto, las capacidades, los veredictos y la corrida sintética son construidos (la bitácora se instanció con el dataclass real `BitacoraCorrida`). Todos llevan `source: "fixture"`.

## 12. Decisiones abiertas

| Id | Pregunta | Quién |
|---|---|---|
| D1 | ¿Cómo se muestra `interrumpida`? Propuesta: «pendiente» con marca «reanudable», porque el ciclo de tarea de la UI no tiene un estado propio. | Diseño |
| D2 | ¿Cómo se muestra una etapa `blocked` (L4)? Propuesta: capacidad no disponible, no un estado de tarea. | Diseño |
| D3 | `podado` no es un estado del ciclo de tarea: ¿se añade una etiqueta propia para ensayos (ícono + texto distintos de `fallido`)? | Diseño |
| D4 | ¿Se acepta el prefijo de códigos de error de la sección 9 como catálogo del motor (G6)? | Equipo del motor |
| D5 | Validar el contrato con el equipo y con los directores si aplica. | Equipo |

## 13. Cómo se verificó

- Los 11 esquemas de [`schemas/v1/`](schemas/v1/) se exportaron de los [modelos de referencia](referencia/modelos_v1.py) (Pydantic v2).
- Los 27 ejemplos validan contra esos modelos y, de forma independiente, contra los `.schema.json` publicados (Draft 2020-12).
- Se comprobó que los modelos rechazan datos inválidos (clase inexistente, ADI no positivo, `failed` sin error, `evidence.family` distinta de `family`, versión mayor 2.x, campos extra, hash mal formado).
- Las reglas entre campos (sección 6) **no** se expresan en JSON Schema; viven en los modelos de referencia y B4 debe conservarlas.

## 14. Para B4

1. Copiar los [modelos de referencia](referencia/modelos_v1.py) a `pred-platform` y completarlos; son la fuente de los esquemas (ADR-05-001).
2. Comparar el esquema exportado de esos modelos contra [`schemas/v1/`](schemas/v1/) en una prueba, de modo que un cambio accidental falle el CI.
3. Implementar el modo `fixture` leyendo [`ejemplos/v1/`](ejemplos/v1/) y el modo `engine` leyendo los artefactos de la sección 3; el cambio entre ambos es una configuración.
4. Rechazar con `platform.contract_invalid` cualquier respuesta que no valide, y con `platform.schema_version_unsupported` toda `schema_version` de otra versión mayor.
5. Tratar `availability.status = "unavailable"` como un estado de primera clase, no como un error.
6. La plataforma resuelve las rutas relativas del contrato (`data/…`) contra la raíz de datos del motor (`PRED_DATA_ROOT`, ADR-001 del motor).
7. Para `download_synthetic_artifact` en modo fixture, B4 genera un CSV pequeño de cuatro columnas y calcula su SHA-256: los hashes y los 52 000 registros de [`synthetic_run.normal.json`](ejemplos/v1/synthetic_run.normal.json) son ilustrativos y no corresponden a un archivo real.
8. Antes de ejecutar el motor en macOS, instalar `libomp` (LightGBM); documentarlo en D3 y en el README de `pred-platform`.
