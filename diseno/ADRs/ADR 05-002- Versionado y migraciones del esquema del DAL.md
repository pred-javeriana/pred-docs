# ADR-05-002: Versionado y migraciones del esquema del DAL

- **Fecha:** 2026-10-05
- **Estado:** Propuesto

## Contexto & Problema

La plataforma guarda sus entidades (ingestas, series, ejecuciones, tareas, métricas, resultados y reportes) en una base SQLite a través de un único DAL (SRS §3.6). El esquema vive hoy en `dal/schema.py` como sentencias `CREATE TABLE IF NOT EXISTS`, que solo crean tablas ausentes: **no modifican una tabla que ya existe**. Una columna o un índice nuevos no llegarían a las bases ya creadas, y el usuario tendría que borrar su base, con los resultados de corridas largas, para obtener el esquema nuevo.

El esquema debe cambiar pronto. Las tareas derivadas del contrato de consumo (TASK-UI-1.0-A3) necesitan, entre otras cosas:

- **G1:** estado de la ingesta, rutas de Parquet y `raw/`, y `adi`, `cv2`, `n_positive` y una clase tipada en `series`.
- **G4:** tablas para los ensayos de HPO y la evidencia de la configuración elegida por familia.
- **G3:** ajustes en `ejecuciones` y `tareas` para orquestar la corrida y reportar avance.

La decisión D5 del contrato (§7.4) ya acordó lo esencial: un número de versión dentro de SQLite (`PRAGMA user_version`) y scripts de migración numerados, aplicados en orden y dentro de una transacción, con el esquema actual como versión 1. Quedó pendiente este ADR, que fija las reglas para que las tres tareas migren de la misma manera.

Restricciones que acotan la decisión:

- **Instalación local, sin red y un solo usuario de la base** (SRS §2.4; ADR-05-001). No hay servidor de base de datos ni ventana de mantenimiento.
- **Un único DAL** y todo el SQL aislado en él (SRS §3.6, puntos 2, 5 y 6). Las migraciones son parte del DAL.
- **Transaccionalidad** (SRS §3.6, punto 5): un cambio de esquema se aplica completo o no se aplica.
- **Respaldo y restauración** (SRS §3.6, punto 8; RF-CRZ-09 y RF-CRZ-10): el Administrador puede restaurar una copia hecha con una versión anterior, así que una base vieja debe poder actualizarse.
- **Reproducibilidad** (RNF-REP): el esquema resultante no puede depender del orden en que cada persona del equipo actualizó su base.
- **Equipo reducido:** el esquema lo escribió una persona del equipo y cambia con revisión suya (D5).

## Opciones Consideradas

- **Option A: `PRAGMA user_version` y scripts SQL numerados, con un ejecutor propio.**
  Cada migración es un archivo `NNNN_descripcion.sql`; la versión de la base es el número de la última aplicada.
  - *Pros:*
  - Es lo acordado en D5, no añade dependencias y cabe en un módulo pequeño de la biblioteca estándar.
  - `user_version` está en la cabecera del archivo SQLite y se actualiza dentro de la misma transacción que el cambio: no hay estado intermedio donde el número y el esquema discrepen.
  - Los scripts son SQL plano, legible y revisable por quien escribió el esquema.
  - *Cons:*
  - Hay que escribir y probar el ejecutor.
  - Un solo entero no registra cuándo se aplicó cada migración ni detecta por sí solo que un script ya aplicado se editó.
- **Option B: Alembic (con SQLAlchemy).**
  - *Pros:*
  - Herramienta estándar, con revisiones, ramas y generación automática.
  - *Cons:*
  - Obliga a añadir SQLAlchemy a un DAL escrito con `sqlite3`, o a mantener dos formas de acceso.
  - Sus ventajas (ramas de revisiones, varios motores de base) no aportan en una base local de un solo archivo.
  - Más dependencias que fijar y vendorizar para operar sin red.
- **Option C: tabla `schema_migraciones` (versión, nombre, suma de verificación, fecha).**
  - *Pros:*
  - Deja constancia de cada migración y detecta scripts modificados después de aplicarse.
  - *Cons:*
  - Dos fuentes de verdad para la versión (la tabla y el esquema real) que pueden divergir.
  - Más código y una tabla más para un beneficio que se obtiene de otra forma (ver la decisión 3).
- **Option D: mantener `CREATE TABLE IF NOT EXISTS` y borrar la base al cambiar el esquema.**
  - *Pros:*
  - No exige ningún mecanismo.
  - *Cons:*
  - Destruye los resultados guardados, incompatible con RF-CRZ-09, RF-CRZ-10 y con la trazabilidad de corridas.
  - Cada cambio de esquema obliga a todo el equipo a recrear su base.
- **Forma de las migraciones, Option P1: scripts SQL.**
  - *Pros:* revisables, sin lógica oculta, ejecutables en cualquier cliente SQLite.
  - *Cons:* no pueden transformar datos con lógica que SQL no exprese.
- **Forma de las migraciones, Option P2: funciones Python.**
  - *Pros:* permiten transformar datos con cualquier lógica.
  - *Cons:* son más difíciles de revisar y de ejecutar fuera de la aplicación; se prestan a importar código de la aplicación que cambia con el tiempo y rompe migraciones viejas.

## Decisión

Se adopta la **Option A** con la forma **P1**, con las siguientes reglas.

1. **Versión.** La versión del esquema es el entero `PRAGMA user_version` de la base. La versión actual del código es el número de la última migración. La **versión 1** es el esquema existente de once tablas (`CREATE TABLE IF NOT EXISTS`): una base creada antes de este mecanismo (con `user_version` 0 y sus tablas) pasa a la versión 1 sin cambios, y una base vacía recibe las tablas.
2. **Scripts.** Viven en `pred_platform/dal/migrations/` como `NNNN_descripcion.sql`: cuatro dígitos, numeración consecutiva desde 0001 y sin huecos, y descripción en `snake_case`. Un script contiene SQL plano; un número repetido o un hueco es un error al cargar las migraciones, no al aplicarlas.
3. **Inmutabilidad.** Una migración ya publicada no se edita: un cambio es una migración nueva. Una prueba fija la suma SHA-256 de cada migración publicada y falla si cambia, lo que cubre la detección de ediciones que `user_version` por sí solo no ofrece (opción C).
4. **Aplicación.** El ejecutor aplica en orden las migraciones con número mayor que `user_version`. Cada una corre en su propia transacción inmediata junto con la actualización de `user_version`; si una sentencia falla, esa migración se revierte entera y el ejecutor se detiene con un error que nombra la versión y el script. Las migraciones anteriores ya confirmadas se conservan. Después de cada migración se ejecuta `PRAGMA foreign_key_check`; si informa filas, se revierte. Para las migraciones que reconstruyen una tabla (SQLite no puede cambiar restricciones con `ALTER TABLE`), el ejecutor desactiva las claves foráneas fuera de la transacción y las restablece al terminar, según el procedimiento que documenta SQLite. La versión se vuelve a leer una vez adquirido el bloqueo de escritura, de modo que dos procesos que arranquen a la vez no aplican la misma migración dos veces.
5. **Sin retroceso.** No hay migraciones inversas. Volver a una versión anterior se hace restaurando una copia (RF-CRZ-10). Una base con `user_version` **mayor** que la última migración conocida (por ejemplo, restaurada de una versión más nueva de la plataforma) se rechaza con un error claro y no se modifica.
6. **Copia previa.** Antes de aplicar migraciones a una base que ya tiene tablas, el ejecutor guarda una copia consistente con la API de respaldo de SQLite en `<base>.antes-de-v000N.bak`, donde `N` es la versión de destino; si ya existe una copia con ese nombre, se reemplaza. Si la copia falla, no se migra. Una base nueva y vacía no se respalda.
7. **Cuándo migra.** Al arrancar la aplicación con la fuente de datos `dal`, que crea la base y su carpeta si faltan y aplica lo pendiente; con la fuente `fixture` no se toca el disco. También hay un comando manual (`make migrate`, equivalente a `python -m pred_platform.dal.migrate`) con una opción para consultar el estado sin cambiar nada. Las lecturas de las vistas (`dal/lectura.py`) abren la base en solo lectura y **nunca migran**.
8. **Quién y cómo.** Cada tarea que cambie el esquema (G1, G3, G4) añade su migración, con revisión de quien escribió el esquema (D5), y una prueba que construye una base en la versión anterior con filas de muestra, migra y comprueba que los datos se conservan y que el esquema resultante es el esperado. Los campos JSON con `schema_version` (D5) que necesiten reescribir contenido lo hacen dentro de la migración. Cuando una transformación de datos no se pueda expresar en SQL, se decide en un ADR nuevo (forma P2) en lugar de mezclar ambas.
9. **Un solo lugar para el esquema.** La definición de las once tablas pasa a la migración 0001; `dal/schema.py` conserva `create_db()` (que abre la base, fija `journal_mode=WAL` y `foreign_keys=ON` y migra) y la lista `CORE_TABLES`. Así existe una sola definición del esquema por versión.
10. **Fuera de este ADR.** La función de copias de respaldo y restauración del Administrador (RF-CRZ-09 y RF-CRZ-10), el versionado de los archivos del motor (Parquet y `corrida.json`, que llevan su propio `schema_version` según el contrato) y la migración de bases que no sean de PRED.

## Consecuencias

### Positivas

- Las columnas y tablas nuevas de G1, G3 y G4 llegan a las bases existentes sin perder datos, y todas las personas del equipo terminan con el mismo esquema.
- Un cambio de esquema es atómico: se aplica completo o la base queda como estaba.
- La copia previa protege los resultados incluso ante una migración que se aplique bien pero esté mal pensada.
- El mecanismo no añade dependencias y las migraciones son SQL revisable.
- Restaurar una copia antigua (RF-CRZ-10) deja de ser un callejón sin salida: arrancar la aplicación la actualiza.

### Negativas

- Hay que mantener un ejecutor propio y sus pruebas.
- El esquema vigente ya no se lee en un solo archivo: es el resultado de aplicar todas las migraciones. La prueba de cada migración y la lista `CORE_TABLES` mitigan esta pérdida de visibilidad.
- Sin migraciones inversas, una migración defectuosa ya publicada se corrige con otra migración hacia adelante.
- Arrancar la aplicación puede modificar el archivo de la base: quien lo abra con una versión más vieja de la plataforma verá un error en lugar de datos.
- Las copias previas ocupan disco; solo se conserva una por versión de destino y se pueden borrar a mano.

### Impacto en CI y despliegue local

- **CI de `pred-platform`:** las pruebas del ejecutor y de cada migración corren con `pytest` sobre bases temporales; la prueba de inmutabilidad falla si se edita una migración publicada. El arranque de humo (smoke) con la fuente `dal` crea `data/pred.db` en el espacio de trabajo de CI.
- **Ejecución local:** un clon limpio arranca con `make run` y obtiene la base en la última versión sin pasos adicionales. `make migrate` sirve para migrar o consultar el estado sin levantar el servidor.
- **Entrega:** sin cambios; este ADR no define cómo se empaqueta la distribución final.

## Referencias

- `diseno/contratos/contrato-frontend-motor.md`, §7.4 (decisión D5) y §14.
- SRS §3.6 (puntos 1, 2, 3, 5, 6 y 8), RF-CRZ-09, RF-CRZ-10 y RNF-REP.
- ADR-05-001 (stack y repositorio del frontend) y ADR-02-014 (checkpoints versionados, atómicos e idempotentes) como antecedente de versionado atómico en el motor.
- Documentación de SQLite: `PRAGMA user_version`, «ALTER TABLE» (procedimiento de reconstrucción de tablas) y la API de respaldo en línea.
- Tareas TASK-UI-1.0-A3-G1, -G3 y -G4.
