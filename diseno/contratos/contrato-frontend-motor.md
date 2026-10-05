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
| `t_star` | Corte de la reserva (`ReserveCut`): el motor clasifica cada SKU solo con la historia hasta t\* (ADR-019 del motor) | Se calcula del calendario del panel; no se guarda |
| `items[]` | `TopologyMetrics`: `sku_id`, `n_periods`, `n_positive`, `adi`, `cv2`, `sku_class` | `run_classify_csv` y `run_ingest` los devuelven en memoria, pero `Pipeline.ingest` los descarta y `pred-engine run` no los guarda; `series` solo guarda `sku`, `familia`, `perfil_demanda` y `n_obs`. Faltan `adi`, `cv2`, `n_positive` y una clase tipada ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778)) |

### 7.4 `run_status` (monitoreo)

Una ejecución y sus tareas, con el vocabulario de `ejecuciones` y `tareas`.

| Campo | Fuente | Hoy |
|---|---|---|
| `ejecucion` | `ejecuciones`: `estado` (`pendiente`, `ejecutando`, `completada`, `completada_con_fallos`, `detenida`), `seed`, `iniciada_en`, `finalizada_en` | Tabla existe; nadie la escribe ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)) |
| `settings` | `configuraciones.parametros` (ventanas, métrica, familias, versión de política) | Tabla existe; el formato de `parametros` ya está acordado (7.4) y falta escribirlo (G3) |
| `reserve` | `summarize_run().reserve` y `corrida.json`: `fraction`, `t_star`, `first_reserved`, `last_observed`, `reserved_days` | El motor lo calcula y lo guarda en `corrida.json`; el DAL no tiene dónde guardarlo (G3) |
| `tasks[]` | `tareas`: una por unidad del motor (SKU × modelo), con `estado` (`pendiente`, `ejecutando`, `exitosa`, `fallida`, `no_ejecutable`), `tiempo_pared_s`, `detalle_error`, `corte` | Tabla existe; nadie la escribe. El motor deja la traza por unidad en `unidades.jsonl` (G3) |
| `progress` | Derivado del conteo de tareas por estado | Derivable |

Cada **unidad del motor** (SKU × modelo) es una tarea (decisión D6). Las ventanas de Walk-Forward no son tareas: son evidencia dentro de `sku_selection` (`walk_forward.windows`). La clave de `tareas` sigue siendo (ejecución, SKU, modelo, corte); como el corte es el mismo para toda la ejecución, no se repite ninguna fila.

**Estado de una tarea a partir de lo que deja el motor:**

| En el motor | Estado de la tarea |
|---|---|
| Unidad `completada` en L2 y en L3 | `exitosa` |
| Unidad `fallida` en L2 o en L3 | `fallida`, con su `error` |
| SKU en `exclusions` (por ejemplo, historia insuficiente) | `no_ejecutable` para todos sus modelos, con la causa |
| Unidad que aún no terminó | `pendiente` o `ejecutando`: **el motor todavía no lo informa en vivo**, porque escribe sus archivos al terminar ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)) |

**Formatos acordados (decisión D5):**

| Campo | Formato | Ejemplo |
|---|---|---|
| `tareas.corte` | Texto ISO 8601 `AAAA-MM-DD`, sin hora: la fecha de corte t\* de la reserva (decisión D6), la misma para todas las tareas de una ejecución. Los cortes de cada ventana de Walk-Forward están en `walk_forward.windows[].corte`. Como texto ordena bien | `2026-06-29` |
| `tareas.modelo` | `familia:algoritmo` en minúsculas. La familia se deduce del prefijo, así que no hace falta un catálogo de modelos | `classical:sarima`, `ml:lightgbm`, `dl:mlp`, `foundation:chronos2` (los nombres de modelo son los del motor) |
| `configuraciones.parametros` | JSON con `schema_version` (entero) y los ajustes de la corrida (`RunSettings`). Los umbrales de perfil se añadirán cuando se cierre la decisión D4 | `{"schema_version": 1, "min_train": 60, …}` |
| `tareas.detalle_error` | JSON de un `ErrorInfo` (hoy es texto libre, [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056)) | `{"code": "model.fit_failed", …}` |

El identificador `modelo` se usa también en `families[].modelo`, `champion.modelo` y `modelo_campeon`, y `family` solo puede coincidir con su prefijo. El nombre que ve el usuario (por ejemplo «SARIMA») lo define la plataforma a partir del identificador.

**Quién cambia el esquema y cómo se versiona (decisión D5).** Los cambios a `dal/schema.py` para G1, G3 y G4 los hace quien tenga esas tareas, con revisión del autor del esquema. Hoy el esquema usa `CREATE TABLE IF NOT EXISTS`, que no modifica las tablas ya creadas: una columna nueva no llegaría a las bases que ya existen. Lo acordado es guardar un número de versión dentro de SQLite (`PRAGMA user_version`) y aplicar al arrancar scripts de migración numerados, en orden y dentro de una transacción, con el esquema actual como versión 1. Falta escribir el ADR-05-002 que lo formalice.

### 7.5 `sku_selection` y `sku_selection_list` (C2)

`sku_selection` es el detalle de un SKU y `sku_selection_list` son las filas de la tabla.

| Campo | Fuente | Hoy |
|---|---|---|
| `sku_class`, `profile`, `policy_version` | `SelectionResult` del motor | En memoria; el DAL no los guarda (G4) |
| `families[].estado` | Tareas del SKU agrupadas por modelo; `excluida` si la política o la configuración no la incluye; `no_ejecutable` si el motor excluyó el SKU | Derivable cuando exista G3; la exclusión por política ya es derivable (tabla 7.5.1) |
| `families[].evidence` | `SelectionResult.payload`, unión discriminada por `family` | El payload ya es serializable (DL dejó de incluir el objeto `estudio`) y trae `estudio_hpo`, la referencia al estudio persistido; falta guardarlo en el DAL (G4) |
| `families[].trials[]` | `Trial`: `id`, `configuracion`, `estado`, `valor`, `n_ventanas`, `motivo`, `timestamp` | El motor no los expone en el resultado: están en `hpo/<estudio_hpo>/` en formato de Optuna ([G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5)); el DAL no tiene tabla (G4) |
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
| `run_ingest` / `run_classify_csv` | `IngestResult` (`source.sha256`, `diagnostic`, conteos) y `TopologyArtifact.metrics` | `ingestas`, `bitacora_calidad`, `series` | Columnas nuevas en el DAL y que el motor deje disponibles las métricas: `Pipeline.ingest` las descarta y `pred-engine run` no las guarda ([G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778)). `run_classify_csv` no devuelve el hash ni deposita en `raw/` ([G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f)) |
| `pred-engine run` o `Pipeline.run(workers=N)` | Corrida de L1 a L3 con unidades SKU × familia, fallos aislados y SKU excluidos con causa | `ejecuciones` y `tareas` (una por SKU × modelo) | El worker que la lanza y lee su resultado; el motor escribe `corrida.json` y `unidades.jsonl` solo al terminar, sin progreso en vivo ([G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6)) |
| `unidades.jsonl` y `corrida.json` | Por unidad: etapa, SKU, familia, modelo, estado (`completada`/`fallida`), segundos, CPU y error. Por corrida: etapas con tiempos, t\*, exclusiones y fallas | `tareas` (estado, tiempo, error) y `ejecuciones` (inicio y fin) | Mapeo de estados de 7.4 |
| `candidatos.json`, `evaluacion.parquet`, `walk_forward.parquet` y los `candidates` de `corrida.json` | Configuración completa del candidato, métrica agregada, valores por ventana y procedencia (estudio HPO y contadores) | Resultado por SKU y familia, y `metricas` | Tablas de evidencia ([G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f)). Los ensayos solo están en `hpo/` ([G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5)) |
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
| Ensayo (trial) | — | No existe tabla | `pendiente`, `corriendo`, `completado`, `podado`, `fallido` | pendiente, ejecutando, completada, **podada**, fallida (D1) |

Observaciones:

- El estado de estudio del motor (`interrumpida`, etc.) es interno: la plataforma ve tareas y ejecuciones, y no lo necesita en las vistas.
- **ABC/XYZ no existe en el motor ni en el DAL** (se buscó `XYZ` y `categoria_combinada` en `pred-engine` y `pred-platform`), pero `contexto-diseno-ui.md` §3 espera insignias ABC/XYZ junto a cada SKU. Mientras la decisión D4 siga abierta queda fuera de v1: el contrato no define campos de la SRS para el perfil (CV, ZVI, ABC-XYZ, `regular`/`intermitente/lumpy`).
- Un ensayo `podado` **no es un fallo**: la configuración sí corrió y la regla de poda la detuvo porque ya no era competitiva; su `motivo` lo explica (por ejemplo `poda_semantica:prediccion_nula`). La interfaz lo muestra con un estado propio, «podada», distinto de «fallida» (decisión D1). Equivalencias de los ensayos: `corriendo` → ejecutando, `completado` → completada, `podado` → podada, `fallido` → fallida. `motivo` es texto libre del motor y no se interpreta en v1.

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

Cada hueco tiene su tarea en el backlog. Ninguno se resuelve en A3. La columna **Dueño** indica de qué repositorio es el trabajo. Revisada el 2026-10-04 contra el motor tras el cierre de M0 a M2.

| Id | Hueco | Dueño | Evidencia | Bloquea | Tarea |
|---|---|---|---|---|---|
| G1 | El DAL no guarda el informe de ingesta ni las métricas topológicas, y el motor tampoco las deja disponibles en la corrida | Plataforma y motor | `ingestas` sin estado ni ruta del Parquet; `series` sin `adi`, `cv2`, `n_positive` y con `perfil_demanda` libre. `Pipeline.ingest` descarta `TopologyArtifact` y `pred-engine run` no lo guarda | C1, C3 | [G1](https://app.notion.com/p/3ed7ff922a7281f2bef4d2ce9823d778) (P1) |
| G2 | Los ensayos de cada familia no salen del motor | Motor | El payload ya es serializable y trae `estudio_hpo`, pero los ensayos solo están en `hpo/`, en formato de Optuna | C2 | [G2](https://app.notion.com/p/3ed7ff922a7281338fb7c24bbc0e7bf5) (P1) |
| G3 | Falta el worker que lance y lea corridas y escriba `ejecuciones` y `tareas`; el motor no informa progreso en vivo | Plataforma y motor | `worker/__init__.py` solo tiene docstring. El motor guarda `corrida.json` y `unidades.jsonl` solo al terminar la corrida | Monitoreo, C2 | [G3](https://app.notion.com/p/3ed7ff922a7281c98773cdb894111df6) (P1) |
| G4 | El DAL no guarda la selección por SKU: ensayos, evidencia ni configuración elegida | Plataforma | Solo existen `metricas` y `resultados_comparativos` | C2 | [G4](https://app.notion.com/p/3ed7ff922a728108b012c72ffab4c09f) (P1) |
| G5 | `deposit_raw_csv` sobrescribe sin avisar; la ruta canónica no deposita ni devuelve el hash | Motor | `ingesta/pipeline.py` (`copy2`) | C1 | [G5](https://app.notion.com/p/3ed7ff922a7281e5a671f18a3054f08f) (P1) |
| G6 | No hay catálogo de códigos de error ni mapeo desde las excepciones | Plataforma y motor | Las unidades fallidas guardan `NombreDeClase: mensaje`, lo que permite mapear por clase; dos casos siguen sin tipo propio | Todas | [G6](https://app.notion.com/p/3ed7ff922a7281d18e08e455074c6056) (P1) |
| G7 | Las exclusiones y las fallas del motor son texto libre | Motor y plataforma | El motor ya excluye los SKU con causa y aísla los fallos por unidad (RF-MOD-13); falta un código por causa | Monitoreo, C2 | [G7](https://app.notion.com/p/3ed7ff922a7281da9f57ec0027785438) (P2) |
| G8 | La bitácora de la Fase 0 no declara versión de esquema y ganó campos | Motor | `aumentacion/bitacora.py` ahora incluye método, mapeo de columnas, huella de la corrida y configuración | C4 | [G8](https://app.notion.com/p/3ed7ff922a728142bc4dd31d3d097e28) (P2) |

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
| D4 | La SRS (RF-ING-10 a 13) exige calcular CV, ZVI y ABC-XYZ y etiquetar el perfil como `regular` o `intermitente/lumpy`. El motor clasifica con Syntetos-Boylan (ADI y CV², cuatro clases) y no calcula nada de lo anterior; además, ABC necesita costo unitario, que no entra en el contrato de datos del motor. | Equipo y directores | **Abierta**: el equipo la está consultando. Mientras tanto el contrato mantiene las cuatro clases del motor |
| D5 | Quién modifica `dal/schema.py`, cómo se versionan los cambios y qué formato tienen `tareas.corte`, `tareas.modelo`, `configuraciones.parametros` y `tareas.detalle_error`. | Dueño de la plataforma | **Resuelta** (2026-10-04): ver 7.4. El significado de `corte` se ajustó con D6. Falta el ADR-05-002 de migraciones |
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
