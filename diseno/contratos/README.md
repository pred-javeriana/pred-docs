# Contratos frontend ↔ motor

Define los modelos de lectura que las vistas de `pred-platform` consumen de su base de datos (DAL) y la frontera entre el motor, el worker y el DAL. Entregable de TASK-UI-1.0-A3, sobre la decisión de [ADR-05-001](../ADRs/ADR%2005-001-%20Stack%20y%20repositorio%20del%20frontend%20de%20la%20plataforma.md).

| Ruta | Contenido |
|---|---|
| [`contrato-frontend-motor.md`](contrato-frontend-motor.md) | Documento principal: documentos, operaciones, estados, errores, huecos del motor |
| [`schemas/v1/`](schemas/v1/) | Un JSON Schema (Draft 2020-12) por documento |
| [`ejemplos/v1/`](ejemplos/v1/) | Ejemplos validados contra los esquemas; base de los fixtures |
| [`referencia/modelos_v1.py`](referencia/modelos_v1.py) | Modelos Pydantic v2 de referencia, con las reglas entre campos |

## Versión

**Contrato vigente: 1.0.0.** Cada documento lleva `schema_version`.

- Cambio aditivo (campo opcional nuevo, valor nuevo en una enumeración abierta): sube la versión menor y se mantiene `schemas/v1/`.
- Cambio incompatible (campo eliminado o renombrado, tipo distinto, valor de enumeración cerrada retirado): crea `schemas/v2/` y `ejemplos/v2/`; `v1` se conserva mientras algún consumidor lo use.
- Los consumidores rechazan cualquier `schema_version` de otra versión mayor.

## Historial

- **1.0.0** (2026-10-02): primera versión, validada por el equipo el 2026-10-04.
- **1.0.0, ajuste previo al primer consumidor** (2026-10-04, decisión D5): se fijan los formatos de `tareas.corte` (fecha ISO `AAAA-MM-DD`), `tareas.modelo` y los demás campos de modelo (`familia:algoritmo`) y `configuraciones.parametros` (JSON con `schema_version`). La versión no cambia porque todavía no hay código que consuma el contrato; si alguien ya construyó contra los ejemplos anteriores, hay que subir a 1.1.0.
- **1.0.0, segundo ajuste previo al primer consumidor** (2026-10-04, decisión D6 y cambios del motor): una tarea por unidad del motor (SKU × modelo) con `corte` igual a t\*, la reserva (`reserve`) y `t_star` como campos opcionales, la bitácora de la Fase 0 con los campos nuevos del motor como opcionales (las bitácoras anteriores siguen siendo válidas), `estudio_hpo` opcional en la evidencia y el identificador `foundation:chronos2` en lugar de `foundation:chronos-2`.

## Cómo se mantiene

Los modelos de `referencia/` son la fuente: los esquemas se exportan de ellos y los ejemplos deben validar contra ambos. Al cambiar un modelo hay que regenerar el esquema, ajustar los ejemplos afectados y actualizar la versión.

Exportar un esquema:

```bash
cd referencia
python -c "import json, modelos_v1 as m; print(json.dumps(m.DOCUMENTS['run_status'].model_json_schema(), indent=2))"
```

Requiere Python ≥ 3.12 y `pydantic>=2.6`. Las reglas entre campos (por ejemplo, `failed` exige `error`) solo se verifican con los modelos, no con el JSON Schema.
