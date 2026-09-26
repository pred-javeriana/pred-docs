# ADR-02-014: Checkpoints versionados, atómicos e idempotentes

- **Fecha:** 2026-09-19
- **Estado:** Aplicada

## Contexto & Problema

Persistir un checkpoint no garantiza por sí mismo que una corrida pueda ser reanudada correctamente.
Una ejecución posterior podría intentar cargar estado producido con otro espacio de búsqueda, otra seed, otra métrica, otra configuración de Walk-Forward o una versión incompatible del esquema.
Además, una interrupción durante la escritura del checkpoint podría dejar un archivo incompleto. Si ese archivo sustituye al último checkpoint válido, la reanudación podría fallar o, peor aún, continuar desde un estado parcialmente escrito.
Finalmente, invocar más de una vez una operación de reanudación no debe duplicar trials ni repetir trabajo previamente finalizado.

## Opciones Consideradas

- **Option A: Sobrescribir directamente un archivo de estado sin validación de compatibilidad.**
- *Pros:*
- Implementación mínima.
- Bajo número de archivos.
- *Cons:*
- Riesgo de corrupción ante interrupciones durante escritura.
- No permite detectar que el checkpoint pertenece a otra configuración.
- Facilita reanudaciones silenciosamente incorrectas.
- **Option B: Manifiesto versionado, fingerprint de configuración y escritura atómica.**
Cada corrida mantiene un manifiesto con versión de esquema y fingerprint determinista de los parámetros relevantes.
Las actualizaciones se escriben primero en un artefacto temporal y solo sustituyen el checkpoint vigente cuando la escritura finaliza correctamente.
La reanudación valida el fingerprint antes de restaurar el backend.
- *Pros:*
- Detecta configuraciones incompatibles.
- Evita sustituir un checkpoint válido por uno parcialmente escrito.
- Permite evolucionar el esquema mediante `schema_version`.
- Facilita comportamiento idempotente.
- *Cons:*
- Requiere más lógica de persistencia y validación.
- Debe definirse qué propiedades participan en el fingerprint.
- **Option C: Persistencia transaccional mediante base de datos.**
- *Pros:*
- Transacciones y concurrencia robustas.
- Mayor capacidad para múltiples procesos distribuidos.
- *Cons:*
- Introduce infraestructura operativa adicional.
- No está justificada para el alcance actual del motor experimental.

## Decisión

Se adopta la **Option B**.
Cada corrida tendrá un manifiesto versionado que incluirá un `fingerprint_configuracion`.
El fingerprint deberá construirse de manera determinista a partir de los parámetros que afectan la reproducibilidad del estudio, incluyendo como mínimo:
- espacio de búsqueda;
- seed;
- métrica objetivo;
- parámetros de Walk-Forward Validation;
- familia;
- configuración relevante del optimizador.
Antes de reanudar, el fingerprint almacenado debe coincidir con el calculado para la nueva solicitud.
Una incompatibilidad producirá un error explícito y nunca un reinicio silencioso.
Los checkpoints se actualizarán mediante escritura atómica: primero se genera el nuevo artefacto y posteriormente se reemplaza la versión vigente.
La reanudación será idempotente. Los trials finalizados no se volverán a crear ni ejecutar.
La granularidad garantizada inicialmente será la frontera de trial: un trial que estaba ejecutándose exactamente durante la interrupción podrá ser reejecutado, pero los trials anteriormente finalizados permanecerán preservados.

## Consecuencias

### Positivas

- Se evita reutilizar estado incompatible de forma silenciosa.
- Una interrupción durante la persistencia no destruye necesariamente el último checkpoint válido.
- Las ejecuciones pueden auditar qué configuración produjo cada checkpoint.
- Reintentar una recuperación no duplica trabajo terminado.
- El esquema puede evolucionar explícitamente mediante versionado.

### Negativas

- Es necesario definir y mantener una serialización canónica para calcular el fingerprint.
- Una modificación legítima de parámetros invalida el checkpoint anterior y exige iniciar una nueva corrida.
- La recuperación inicial no continúa exactamente dentro de una ventana en ejecución; la garantía se establece en la frontera entre trials.
