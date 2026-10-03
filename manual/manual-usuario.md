# Manual de usuario de PRED

PRED compara modelos de pronóstico de demanda para cada producto (SKU) de un inventario y entrega, por SKU, los mejores candidatos de cada familia de modelos con su evidencia. Este manual explica cómo instalar PRED, cómo ejecutar una corrida y cómo leer el resultado.

Hoy PRED se usa desde la terminal, con el comando `pred-engine`. La plataforma web existe, pero solo muestra una página de inicio: las pantallas todavía no están construidas (ver [Abrir la plataforma web](#9-abrir-la-plataforma-web)).

**Qué cubre este manual:**

1. [Instalar el motor](#1-instalar-el-motor)
2. [Preparar los datos](#2-preparar-los-datos)
3. [Hacer una corrida completa desde una semilla](#3-hacer-una-corrida-completa-desde-una-semilla)
4. [Hacer una corrida con un panel propio](#4-hacer-una-corrida-con-un-panel-propio)
5. [Leer el resultado de una corrida](#5-leer-el-resultado-de-una-corrida)
6. [Retomar o repetir una corrida](#6-retomar-o-repetir-una-corrida)
7. [Comprobar que el equipo funciona](#7-comprobar-que-el-equipo-funciona)
8. [Usar archivos con cabeceras propias](#8-usar-archivos-con-cabeceras-propias)
9. [Abrir la plataforma web](#9-abrir-la-plataforma-web)
10. [Resolver problemas frecuentes](#10-resolver-problemas-frecuentes)

## Términos

| Término | Significado |
|---|---|
| **SKU** | Un producto del inventario. PRED pronostica la demanda de cada SKU por separado. |
| **Semilla** | El CSV original con el historial de demanda. PRED puede generar a partir de ella series sintéticas parecidas. |
| **Panel** | La tabla de demanda diaria de todos los SKU, con cuatro columnas: `sku_id`, `timestamp`, `demand_qty` y `lead_time_days`. |
| **Corrida** | Una ejecución completa de PRED sobre un panel. Cada corrida tiene un identificador `run_id` y una carpeta propia. |
| **Clase de demanda** | La forma de la demanda de un SKU: `smooth`, `erratic`, `intermittent` o `lumpy`. Decide qué familias de modelos se prueban. |
| **Familia** | Un tipo de modelo: clásica (`classical`, SARIMA), aprendizaje automático (`ml`, LightGBM), aprendizaje profundo (`dl`) o fundacional (`foundation`, Chronos-2). |
| **Unidad** | Un par SKU × familia. Cada unidad se procesa por separado; si una falla, las demás siguen. |
| **Reserva** | El último 20 % de los días del panel. PRED no lo usa para elegir modelos: queda guardado para juzgarlos después. La fecha de corte se llama t*. |
| **Candidato** | La mejor configuración de una familia para un SKU. Los candidatos se guardan en `candidatos.json`. |

## 1. Instalar el motor

**Necesita:** Git, Python 3.12 o posterior y [uv](https://docs.astral.sh/uv/). La instalación descarga dependencias; después, PRED funciona sin red.

1. Clone el repositorio del motor:

   ```bash
   git clone https://github.com/pred-javeriana/pred-engine.git
   cd pred-engine
   ```

2. Instale las dependencias fijadas:

   ```bash
   uv sync --extra dev
   ```

3. Compruebe que el comando responde:

   ```bash
   uv run pred-engine --help
   ```

   Debe ver la lista de subcomandos: `models`, `probe`, `ingest`, `classify`, `verify`, `run` y `telemetry`.

Ejecute todos los comandos de este manual desde la carpeta `pred-engine`. Las rutas relativas, como `data`, se resuelven desde ahí.

## 2. Preparar los datos

PRED acepta dos tipos de archivo CSV. Elija según lo que tenga:

- **Una semilla con sus propios nombres de columna.** Use la [corrida completa](#3-hacer-una-corrida-completa-desde-una-semilla) e indique qué columna corresponde a cada campo.
- **Un panel con las cuatro columnas canónicas.** Use la [corrida con un panel propio](#4-hacer-una-corrida-con-un-panel-propio).

Un panel canónico se ve así:

```csv
sku_id,timestamp,demand_qty,lead_time_days
100,2024-10-07,242,29
100,2024-10-17,177,27
101,2024-10-07,35,12
```

| Columna | Qué contiene | Regla |
|---|---|---|
| `sku_id` | Identificador del producto | Texto o número |
| `timestamp` | Fecha de la observación | Formato `AAAA-MM-DD` |
| `demand_qty` | Unidades demandadas ese día | Número mayor o igual a 0 |
| `lead_time_days` | Días de reposición | Número |

No necesita una fila por día. PRED completa los días sin registro con demanda 0. Por ejemplo, un archivo de 3 SKU con 72 filas se convirtió en un panel diario de 692 filas.

Coloque el archivo dentro de la carpeta `pred-engine`, por ejemplo en `entradas/`. Si el archivo está en otra carpeta, use su ruta completa.

## 3. Hacer una corrida completa desde una semilla

Este comando hace todo en un solo paso: genera series sintéticas a partir de la semilla (M0), valida y clasifica la demanda (M1), y busca, ajusta y evalúa modelos por SKU (M2).

1. Lance la corrida. En `--m0-columna`, escriba primero el nombre canónico y después el de su archivo. Este ejemplo usa el inventario de Kaggle "Hospital Supply Chain":

   ```bash
   uv run pred-engine run --seed-csv entradas/inventory_data.csv --data-root data \
     --m0-metodo mbb-directo \
     --m0-columna sku_id=Item_ID --m0-columna timestamp=Date \
     --m0-columna demand_qty=Avg_Usage_Per_Day \
     --m0-columna lead_time_days=Restock_Lead_Time \
     > corrida.log
   ```

   La redirección `> corrida.log` guarda la salida en un archivo. Sin ella, la terminal se llena de mensajes de registro.

2. Espere a que termine. En un equipo de 24 núcleos, una semilla de 3 SKU tardó unos 30 segundos y la semilla completa de Kaggle, unos 2 minutos y medio.

3. Compruebe el código de salida:

   ```bash
   echo $?
   ```

   | Código | Qué significa | Qué hacer |
   |---|---|---|
   | 7 | La corrida terminó sin fallas. | Lea el resultado. |
   | 8 | La corrida terminó, pero algunas unidades fallaron de forma aislada. | Lea el resultado y revise las fallas. |
   | 1 | La corrida no pudo completarse. | Lea el mensaje de error en la terminal. |

   Los códigos 7 y 8 son resultados normales. PRED no devuelve 0 porque la validación retrospectiva (L4) todavía no está implementada.

4. Continúe con [Leer el resultado de una corrida](#5-leer-el-resultado-de-una-corrida).

**Elija `--m0-metodo` según la semilla.** Use `mbb-directo` si la demanda es intermitente, como la de Kaggle: conserva las rachas de días sin demanda. El valor por defecto, `stl-mbb`, rellena esos días con valores pequeños, y la serie sintética deja de ser intermitente.

**Si la semilla es pequeña,** M0 puede generar menos filas de las exigidas. El error dice, por ejemplo, `el artefacto tiene 7612 filas; se exigen al menos 50000`. Para una prueba, baje el mínimo con `--m0-minimo-filas 5000`. Para una corrida de tesis, use una semilla más grande.

### Opciones útiles de la corrida

| Opción | Por defecto | Para qué sirve |
|---|---|---|
| `--families` | `classical ml dl` | Elegir qué familias probar. `foundation` requiere instalar el extra `foundation` y los pesos de Chronos-2. |
| `--workers` | núcleos − 1 | Limitar cuántos procesos usa la corrida. |
| `--metric` | `mase` | Elegir la métrica de selección: `mae`, `rmse`, `smape` o `mase`. |
| `--seed` | 0 | Cambiar la semilla aleatoria de la búsqueda y de los modelos. |
| `--trials` | según la clase de demanda | Fijar cuántas configuraciones probar por estudio. Un número bajo deja muchas unidades sin candidato. |
| `--m0-n-series` | 10 | Cambiar cuántas series sintéticas se generan por SKU. |

Deje `--trials` en su valor por defecto salvo que quiera una prueba rápida. Por ejemplo, una corrida de 33 SKU con `--trials 4` dejó 25 de 33 unidades clásicas sin candidato.

## 4. Hacer una corrida con un panel propio

Use este procedimiento si su archivo ya tiene las cuatro columnas canónicas y no quiere generar series sintéticas.

**Opción A: todo en un comando.**

```bash
uv run pred-engine run --csv entradas/ventas.csv --data-root data > corrida.log
```

**Opción B: validar primero y correr después.** Esta opción sirve para revisar la clasificación antes de gastar tiempo en modelos.

1. Clasifique el panel:

   ```bash
   uv run pred-engine classify --csv entradas/ventas.csv --data-root data
   ```

   La salida muestra una tabla con `sku_id`, `adi`, `cv2` y `sku_class`, y termina con `contrato_1_4: accepted` y la ruta del Parquet publicado.

2. Opcional: vuelva a comprobar el Parquet publicado:

   ```bash
   uv run pred-engine verify --parquet data/processed/ventas.parquet
   ```

3. Lance la corrida sobre el Parquet:

   ```bash
   uv run pred-engine run --parquet data/processed/ventas.parquet \
     --data-root data > corrida.log
   ```

Los códigos de salida son los mismos de la corrida completa.

## 5. Leer el resultado de una corrida

### Ver el resumen

La última línea de `corrida.log` es un informe en JSON. Muéstrelo con formato:

```bash
tail -n 1 corrida.log | uv run python -m json.tool
```

Revise estos campos:

| Campo | Qué indica |
|---|---|
| `stages` | El estado de cada etapa. L1, L2 y L3 deben estar en `completed`. L4 siempre aparece `blocked`. |
| `reserve` | La fecha de corte `t_star` y cuántos días quedaron reservados. |
| `units` | Cuántas unidades terminaron y cuántas fallaron en L2 y L3. |
| `failures` | El SKU, la familia y el error de cada unidad fallida. |
| `run_dir` | La carpeta de la corrida, por ejemplo `data/runs/r-b2e13b696552471a`. |

### Comparar los modelos

El archivo `evaluacion.parquet` tiene una fila por candidato. La columna `valor_agregado` es la métrica de selección: cuanto menor, mejor. Para ver los candidatos de cada SKU ordenados, reemplace `<run_id>` y ejecute:

```bash
uv run python - <<'EOF'
import pandas as pd

e = pd.read_parquet("data/runs/<run_id>/evaluacion.parquet")
columnas = ["sku_id", "sku_class", "familia", "modelo", "valor_agregado"]
print(e[columnas].sort_values(["sku_id", "valor_agregado"]).to_string(index=False))
EOF
```

Ejemplo de salida:

```text
     sku_id    sku_class   familia   modelo  valor_agregado
        100 intermittent        ml lightgbm        0.569913
100::syn000 intermittent        ml lightgbm        0.804211
100::syn000 intermittent classical   sarima        0.868868
```

En este ejemplo, para el SKU `100::syn000` el candidato LightGBM tuvo menor error que SARIMA. El SKU `100` solo tiene un candidato porque su unidad clásica falló. Los SKU con `::syn` en el nombre son series sintéticas generadas por M0.

Esta comparación es evidencia de la etapa de selección. No es el veredicto final: la comparación sobre los días reservados corresponde a M3 y a la validación retrospectiva, que aún no existen.

### Archivos de la corrida

Todo queda en `data/runs/<run_id>/`:

| Archivo | Para qué abrirlo |
|---|---|
| `evaluacion.parquet` | Comparar candidatos: métrica de selección y medias de MAE, RMSE, sMAPE y MASE. |
| `pronosticos.parquet` | Ver el pronóstico diario de cada candidato para los días reservados. |
| `walk_forward.parquet` | Ver el valor real y el pronóstico de cada día de cada ventana de evaluación. |
| `candidatos.json` | Entregar los candidatos a M3. No lo edite. |
| `unidades.jsonl` | Revisar cada unidad: estado, duración y error. |
| `corrida.json` | Consultar entradas, opciones, tiempos, versiones y procedencia de cada candidato. |
| `recursos.jsonl` | Revisar el uso de CPU y memoria durante la corrida. |
| `hpo/` | Uso interno: permite retomar la búsqueda. |

### Ver el uso de recursos

Genere un gráfico de la corrida:

```bash
uv run pred-engine telemetry data/runs/<run_id>
```

El comando escribe `data/runs/<run_id>/telemetria.svg`. Ábralo en un navegador. Muestra las etapas, la CPU y la memoria, y una barra por unidad coloreada por modelo. Pase el puntero sobre una barra para ver su SKU, duración y estado.

## 6. Retomar o repetir una corrida

**Para retomar una corrida interrumpida,** repita exactamente el mismo comando. PRED reconoce la corrida por su `run_id`: reutiliza las series sintéticas, reconstruye las búsquedas terminadas sin reentrenar y continúa las demás. En la prueba de 3 SKU, la repetición tardó 8 segundos frente a 30 de la primera vez.

**Si el código del motor cambió** (por ejemplo, tras un `git pull`), el `run_id` también cambia y PRED empieza una corrida nueva. Para continuar la anterior, pase su identificador con `--run-id`.

**Para generar otras series sintéticas** con otras opciones de M0, use otro nombre con `--m0-nombre` u otra carpeta con `--data-root`. PRED no sobrescribe un panel sintético ya depositado.

## 7. Comprobar que el equipo funciona

Use esta prueba después de instalar o si una corrida falla sin razón clara. No necesita datos propios ni red.

```bash
uv run python -m pred_engine.verify
```

La prueba tarda pocos segundos. Si todo funciona, la última línea contiene `"verification": "passed"` y el comando devuelve 0.

## 8. Usar archivos con cabeceras propias

Si sus columnas no se llaman como las canónicas, tiene dos opciones:

- **Renombrar las columnas** en el archivo a `sku_id`, `timestamp`, `demand_qty` y `lead_time_days`. Es lo más simple.
- **Usar el mapeo de M0** con `--m0-columna`, como en la [corrida completa](#3-hacer-una-corrida-completa-desde-una-semilla).

El motor también ofrece `pred-engine probe` e `ingest`, que usan un modelo de lenguaje externo para reconocer cabeceras desconocidas. Esa vía requiere una clave de API y conexión a red. Para ver qué modelos acepta cada proveedor, ejecute `uv run pred-engine models --provider gemini`. La configuración de la clave está en el [README de pred-engine](https://github.com/pred-javeriana/pred-engine#l12-semantic-alignment).

## 9. Abrir la plataforma web

La plataforma todavía no permite cargar datos ni ver resultados. Sirve para comprobar que la instalación web funciona.

1. Clone e instale la plataforma, en una carpeta distinta de `pred-engine`:

   ```bash
   git clone https://github.com/pred-javeriana/pred-platform.git
   cd pred-platform
   uv sync --extra dev --locked
   ```

2. Arranque el servidor:

   ```bash
   make run
   ```

3. Abra <http://localhost:8000> en el navegador. Debe ver el título PRED y el texto "Plataforma en construcción".

4. Detenga el servidor con `Ctrl+C`.

Las pantallas previstas son carga y validación de datos, topología de demanda, selección de modelos por SKU, datos sintéticos y monitoreo de ejecución. Leerán la base de datos de la plataforma según el [contrato frontend ↔ motor](../diseno/contratos/contrato-frontend-motor.md).

## 10. Resolver problemas frecuentes

| Mensaje o síntoma | Causa | Qué hacer |
|---|---|---|
| `faltan columnas canonicas [...]` | Las cabeceras del CSV no son las canónicas. | Renombre las columnas o use `--m0-columna` con `--seed-csv`. |
| `demand_qty no numerica: 'abc'` | Una fila tiene texto en la demanda. | Corrija esa fila en el archivo y repita el comando. |
| `demand_qty negativa: -4.0` | Una fila tiene demanda negativa. | Corrija esa fila en el archivo y repita el comando. |
| `el artefacto tiene N filas; se exigen al menos 50000` | La semilla es pequeña para el mínimo de M0. | Use `--m0-minimo-filas` con un valor menor o una semilla más grande. |
| `Politica WORM: el artefacto ya existe y no puede reescribirse` | Cambió opciones de M0 sobre la misma carpeta de datos. | Use otro `--m0-nombre` u otro `--data-root`. |
| `ningun trial de HPO completo` en `failures` | Ninguna configuración de esa familia se ajustó en todas las ventanas. | Si usó `--trials`, quítelo o súbalo. Si persiste, el SKU queda sin esa familia. |
| El comando termina con código 7 u 8 | Es el resultado normal: L4 aún no existe. | Lea el resultado. |

`classify` y `verify` usan sus propios códigos de salida: 0 indica éxito, 3 una fila inválida y 5 un problema de columnas o de clasificación.
