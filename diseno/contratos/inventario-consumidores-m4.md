# Inventario previo de consumidores M4

Consulta del 2026-10-27, antes de definir el [contrato v2](contrato-lectura-m3-v2.md). Base: `pred-platform` `6ef53bc`, `pred-docs` `f6b157b` y `pred-engine` `f8678bf`. Se contrastaron los ejemplos y el código real; no se dedujo el consumo solo de los requisitos.

## Consumidores y datos de prueba existentes

| Consumidor en pred-platform | Uso observado | Correspondencia v2 |
|---|---|---|
| `data/repository.py` | `list_sku_selections`, `get_sku_selection`, `get_validation_verdicts`, `get_run_status`; no hay operaciones M4 | Operaciones `get_m3_*` y `list_m3_runs` del contrato v2 |
| `data/fixtures.py` y `data/scenarios.py` | Escenarios `normal`, `vacio`, `errores`; cargan ejemplos v1. El detalle solo tiene `FIL-0001` y `FIL-0004`. La reconstrucción tras filtros valida el modelo. `latest` admite documentos sin identificador | Ejemplos v2 con corrida exacta y tipos M3; ningún documento sin corrida representa evidencia disponible |
| `contract/models.py`, `contract/examples/v1/`, `contract/schemas/v1/` | Copias bloqueadas por hash de pred-docs. `Veredicto` tiene tres valores, `SkuVerdict.detalle` y `audit_bundle` son JSON libre; `Champion` representa la tabla antigua | Modelos autónomos v2, cinco etiquetas cerradas y campos M3 explícitos; sin importar ni adaptar el modelo antiguo |
| `scripts/sync_contract.py`, `contract/loader.py`, `contract/resources.py` | La sincronización y carga apuntan a `modelos_v1.py`, `schemas/v1` y `examples/v1` | La migración de plataforma debe seleccionar v2 para M3 y regenerar su lock; copiar solo JSON no cambia el consumidor |
| `data/dal.py`, `data/capabilities.py` | `get_validation_verdicts` no entrega veredictos y anuncia L4 no implementada; `champion_selection` y `retrospective_validation` están deshabilitadas | Disponibilidad de lectura M3, no inexistencia de la etapa; se habilitan cuando el repositorio cumpla v2 en ambos modos |
| `dal/lectura.py` | El campeón se busca en `resultados_comparativos` | Campeón desde `m3_veredictos.familia_campeona/candidato_campeon`, sin segunda fuente |
| `dal/evidencia.py` | Devuelve diccionarios de tablas `m3_*` filtrados a PUBLICADA. Una referencia M2 puede devolver varias corridas. Con SKU omite `m3_corridas`; no devuelve la vista `evidencia_publicada`. `m3_run_status` omite identidad, SHA, política y fecha de creación | Una corrida exacta, filas tipadas, vista pública y unión de la ingesta/origen también en lecturas por SKU |
| `app/routers/results.py`, `app/seleccion.py` | Solo las operaciones de selección M2 alimentan Por SKU. Resumen y Por clase están reservadas. Filtros/orden/paginación se delegan al repositorio | Se conserva esa separación; la evidencia retrospectiva usa las operaciones y filtros v2 |
| `templates/partials/results_sku_list.html` | Tabla SKU, clase, campeón y evidencia por familia; distingue estado de familia de veredicto global | Tabla M4 con etiqueta exacta, justificación, números decisivos y significancia separada; no se convierte el estado de familia en veredicto |
| `templates/pages/results_sku.html`, `partials/results_scope.html` | Detalle con campeón, familia, HPO, Walk-Forward, topología e identificadores. Advierte que los contrastes retrospectivos no están disponibles | La evidencia M2 permanece como contexto separado; M3 suministra su propio campeón y evidencia reservada |
| `app/ejecucion.py`, `worker/service.py`, `worker/engine.py` | `data_origin` real/synthetic/unknown se convierte en `datos_sinteticos=False/True/None` y llega al motor | Se preserva el origen publicado, no el valor actual del formulario; los dos bits de M3 distinguen real y desconocido |
| `app/presentation.py`, `tests/test_components.py`, `tests/test_presentation.py` | El catálogo `verdict` traduce los tres valores v1 a «se sostiene» y variantes | Las etiquetas M3 se muestran literalmente; el catálogo antiguo no se reutiliza |
| `tests/test_resultados.py`, `tests/test_seleccion.py`, `tests/test_evidencia_m3.py` | `RecordingRepository` deriva del fixture v1; una prueba inserta el campeón antiguo a mano. La base M3 simulada usa SHA `source`, protocolo `{}` y mapas de conteos vacíos | Los escenarios de integración de lectura necesitan SHA real, política y conteos completos v2; no basta con cambiar el tipo de retorno |
| Topología y sus fixtures | `sku_class`, ADI, CV², perfil y conteos; clasificación previa a la reserva | El segmento M4 reutiliza la clase Syntetos-Boylan, sin inventar ABC-XYZ ni recalcular topología |

La implementación de Tomás Pinilla ya distingue deliberadamente los estados familiares y el alcance de M2:

- [Cambio de jerarquía y accesibilidad](https://github.com/pred-javeriana/pred-platform/pull/34), integrado el 2026-10-25: detalle progresivo, tabla de cuatro columnas, filtros, ensayos y ventanas. No introdujo un contrato retrospectivo distinto.
- [Navegación, topología y origen](https://github.com/pred-javeriana/pred-platform/pull/40), integrado el 2026-10-26: conserva los mismos modelos de selección; añade el selector de origen de tres opciones, corrige la leyenda ADI/CV² y permite la familia fundacional. El texto actual no afirma que los estados familiares sean veredictos M3.

## Ramas remotas de compañeros

Se consultaron las cabeceras remotas y se comparó su contenido con las bases anteriores.

- Plataforma: `feat/c2-seleccion-sku`, `feat/c4-ejecucion`, `feat/g1-dal-ingesta`, `feat/g3-worker`, `feat/g4-seleccion-dal`, `feat/g6-g7-codigos-error`, `feat/migracion-evidencia-m3` y `prueba-producto`. No contienen un contrato M4 adicional que no esté en `main`; `prueba-producto` coincide con `main`. Las ramas antiguas de selección usan el mismo vocabulario v1.
- Documentación: `docs/c4-ejecucion`, `docs/g1-g5-d4`, `docs/g2-g4-seleccion`, `docs/g3-progreso-y-ejecucion`, `docs/g6-g7-codigos-error`, `feat/c2-seleccion` y `fm/pred-docs-engineering-name`. No hay otro modelo M4. `docs/g6-g7-codigos-error` conserva un cambio de catálogo `eligibility.*` en `3295a16`, no un contrato de resultados M3.

No se encontraron otros datos simulados o stubs M4 en esas ramas. Esta observación no cubre cambios locales sin publicar ni ramas creadas después de la consulta.

## Incompatibilidades que la migración debe resolver

Los siguientes puntos pertenecen a la migración de consumidores en **pred-platform**. Este cambio publica sus tipos y reglas en **pred-docs**; no declara que la plataforma ya los use.

1. **Veredictos:** sustituir `mantiene/parcial/falla`, el modelo `ValidationVerdicts` y el catálogo de presentación `_VERDICT`; no traducir los cinco valores M3 a tres etiquetas.
2. **Campeón:** retirar la lectura `resultados_comparativos` y el antiguo `Champion`. Usar familia/candidato de `m3_veredictos`, incluso `seasonal_naive` o un candidato nulo. No exigir el identificador v1 `familia:algoritmo` a un `candidato_id` M3.
3. **Identificador de corrida:** `run_id` de selección/ejecución es M2. El detalle M4, enlaces y CSV deben conservar un M3 exacto y su vínculo `run_id_m2` por separado.
4. **`latest` y duplicados:** resolver la PUBLICADA más nueva antes de paginar, fijar el resultado y avisar cuando varias PUBLICADA comparten identidad. No unir sus filas ni ocultar la duplicación.
5. **Publicación:** las tablas de selección M2 pueden estar disponibles antes de M3. Ninguna fila de evidencia M3 puede filtrarse por esa disponibilidad; exige PUBLICADA en una instantánea común.
6. **Estados:** el `estado` de familia, los cinco estados de ejecución M2 y los estados de corrida M3 son conceptos distintos. Sus filtros y rótulos no se reutilizan para fabricar un veredicto.
7. **Ventanas y métricas:** HPO y Walk-Forward de la misma historia no son evaluación sobre la reserva. Separarlos de `n_ventanas`, `n_min` y las métricas M3. Quitar sMAPE del consumo M4 y preservar ME y `razon_sn` con causas de nulidad.
8. **Significancia:** no existe una columna tipada equivalente en v1. Mostrar HLN-DM, p BH y `dm_causa` por separado; no usar `statistical_comparison_available` de M2 ni llamar significativo a `VALIDADO`.
9. **Origen:** `source: fixture` no dice si los datos científicos son sintéticos. Conservar `datos_sinteticos` y `origen_declarado`; un cero sin declaración no es real. No sustituir la procedencia publicada por la selección actual del formulario.
10. **Trazas:** las vistas obtienen hoy la ingesta del encabezado M2 y varias filas v1 no la incluyen. Cada fila v2 conserva el SHA y M3 exactos, con `sku: null` solo para agregados.
11. **Clase:** el perfil descriptivo v1 y la leyenda ADI/CV² no son un segmento ABC-XYZ. Filtrar M4 por `sku_class` de Syntetos-Boylan publicado por M3.
12. **Comparación incompleta:** las exclusiones/fallos de familia M2 se conservan como contexto. M4 muestra `comparacion_incompleta`, `justificacion`, `cobertura` y los fallos publicados, sin derivar de ellos otro veredicto.
13. **Embudo:** los totales de la página y de tareas no cuentan todos los productos. Incorporar el embudo global, las exclusiones tardías por corrida y los dos grupos, con los cinco conteos exactos. No sustituir metadatos ausentes por cero.
14. **DAL:** devolver la vista pública o su proyección equivalente y unir `m3_corridas` para origen, identidad y SHA en lecturas por SKU. Completar también los metadatos de `m3_run_status` con identidad, SHA, política y fecha de creación. Una búsqueda M2 debe resolverse antes de construir un documento de evidencia.
15. **Fixtures y carga:** cambiar los escenarios, validadores, cargador, sincronización y lock a los documentos M3 v2. Los ejemplos v1 no son una segunda vía M4 ni una prueba de que M3 no exista. Se mantienen archivados para los consumidores existentes de otras operaciones.
16. **Capacidades y texto:** habilitar las capacidades al completar la lectura, y sustituir los textos que atribuyen la indisponibilidad a la inexistencia de M3/L4. El texto obsoleto del campeón en los modelos de referencia v1 se corrige aquí sin cambiar sus campos ni ejemplos.
17. **Datos simulados de pruebas:** `tests/test_seleccion.py` inserta `resultados_comparativos` y exige su campeón antiguo. `tests/test_evidencia_m3.py` usa SHA `source` en vez de 64 caracteres, protocolo sin política y conteos/porcentajes vacíos. `tests/test_data_fixtures.py` espera `stage_not_implemented` para los veredictos vacíos. Esos casos deben representar la fuente M3 y la disponibilidad v2, no relajar el contrato para que acepte los stubs incompletos.
