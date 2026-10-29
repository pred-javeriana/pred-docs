# Contratos frontend ↔ motor

Define los modelos de lectura de `pred-platform` desde su DAL y la frontera motor-worker-DAL. La lectura de evidencia M3 para M4 usa **v2**, sin recalcular resultados. Las operaciones de ingesta, selección M2 y monitoreo conservan sus documentos v1 existentes.

| Ruta | Contenido |
|---|---|
| [`contrato-lectura-m3-v2.md`](contrato-lectura-m3-v2.md) | Lectura M3 vigente: publicación, corrida exacta, cinco veredictos, significancia, métricas y embudo |
| [`inventario-consumidores-m4.md`](inventario-consumidores-m4.md) | Consumidores, fixtures y ramas contrastados antes del diseño; incompatibilidades de migración |
| [`schemas/v2/`](schemas/v2/), [`ejemplos/v2/`](ejemplos/v2/) | Once documentos M3, con esquemas Draft 2020-12 y casos completos |
| [`referencia/modelos_v2.py`](referencia/modelos_v2.py) | Fuente de los esquemas v2 y las reglas entre campos |
| [`contrato-frontend-motor.md`](contrato-frontend-motor.md) | Especificación histórica v1; operaciones no M3 aún usadas |
| [`schemas/v1/`](schemas/v1/), [`ejemplos/v1/`](ejemplos/v1/), [`referencia/modelos_v1.py`](referencia/modelos_v1.py) | Contrato histórico conservado para consumidores existentes |

## Versión

**Contrato vigente de lectura M3/M4: 2.2.0.** Cada documento lleva `schema_version`. v2 sustituye los modelos de campeón y validación retrospectiva v1. No importa v1 ni mantiene una vía alternativa con su vocabulario. Publicar estos tipos no migra el código de `pred-platform`; esa migración debe reemplazar sus consumidores y su copia bloqueada por hash.

- Cambio aditivo (campo opcional nuevo, valor nuevo en una enumeración abierta): sube la versión menor y conserva la carpeta de esa versión mayor.
- Cambio incompatible (campo eliminado o renombrado, tipo distinto, valor de enumeración cerrada retirado): crea la siguiente carpeta mayor de esquemas y ejemplos. El paso de v1 a v2 usa `schemas/v2/` y `ejemplos/v2/`; v1 se conserva mientras algún consumidor lo use.
- Los consumidores rechazan cualquier `schema_version` de otra versión mayor.

## Historial

- **2.2.0**: `M3Evidence.eligibility_exclusions` y `M3Funnel.eligibility_excluded_count` (opcionales) cuentan y listan los productos que M2 excluyó de la competencia, desde la tabla SQLite `m3_exclusiones`, con clase, código `eligibility.*` y causa. Los documentos 2.1 siguen siendo válidos.
- **2.1.0** (2026-10-27): incorporación de los documentos `m3_observations` (demanda observada de la reserva) y `m3_champions` (distribución de campeones por familia y cartera); el origen de las exclusiones tardías pasa a las tablas SQLite `m3_cortes` y `m3_lanzamientos_tardios`.
- **2.0.0** (2026-10-27): lectura de M3 por corrida exacta, cinco veredictos publicados, campeón desde `m3_veredictos`, métricas MAE/RMSE/MASE/ME/r, significancia separada, origen declarado, exclusiones tardías y embudo completo. Se conserva v1 para consumidores existentes; no se usa para nuevas lecturas M3.
- **1.1.0** (2026-10-27): campos `TopologyReport.thresholds` y `RunSettings.aggregation`/`trim` pasan a ser anulables (único consumidor: pred-platform, que migra en el mismo cambio; una carpeta mayor nueva chocaría con `v2`).
- **1.0.0** (2026-10-02): primera versión, validada por el equipo el 2026-10-04.
- **1.0.0, ajuste previo al primer consumidor** (2026-10-04, decisión D5): se fijan los formatos de `tareas.corte` (fecha ISO `AAAA-MM-DD`), `tareas.modelo` y los demás campos de modelo (`familia:algoritmo`) y `configuraciones.parametros` (JSON con `schema_version`). La versión no cambia porque todavía no hay código que consuma el contrato; si alguien ya construyó contra los ejemplos anteriores, hay que subir a 1.1.0.
- **1.0.0, segundo ajuste previo al primer consumidor** (2026-10-04, decisión D6 y cambios del motor): una tarea por unidad del motor (SKU × modelo) con `corte` igual a t\*, la reserva (`reserve`) y `t_star` como campos opcionales, la bitácora de la Fase 0 con los campos nuevos del motor como opcionales (las bitácoras anteriores siguen siendo válidas), `estudio_hpo` opcional en la evidencia y el identificador `foundation:chronos2` en lugar de `foundation:chronos-2`.

## Cómo se mantiene

Los modelos de `referencia/` son la fuente. Los esquemas se exportan de ellos y los ejemplos validan contra ambos. Al cambiar un modelo hay que exportar el esquema, ajustar los ejemplos y actualizar la versión. No se editan esquemas a mano.

Desde la raíz del repositorio, con Python ≥ 3.12, `pydantic==2.13.4`, `jsonschema==4.26.0` y `pytest`:

```bash
python diseno/contratos/referencia/exportar_schemas.py
python .github/scripts/validar_ejemplos.py
pytest -q .github/scripts/test_contratos.py
```

El exportador genera v1 y v2. La versión de Pydantic coincide con la usada por la plataforma al contrastar este contrato. CI comprueba todas las versiones: esquemas válidos y sin diferencias frente a sus modelos, ejemplos presentes para cada documento y validación de tipos, formatos y reglas entre campos. Estas últimas, como publicación o conservación del embudo, se comprueban con Pydantic, no solo con JSON Schema.
