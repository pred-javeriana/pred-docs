# ADR-02-003: Implementación de Patrón Router + Strategy para Módulo de Selección

- **Fecha:** 2026-08-31
- **Estado:** Aplicada

## Contexto & Problema

El Módulo 1 entrega series temporales enriquecidas con la clasificación `sku_class` (`Smooth`, `Intermittent`, `Erratic`, `Lumpy`). A partir de esta información, el Módulo 2 debe determinar qué familias de predictores serán consideradas para cada SKU y delegar el proceso de configuración a la estrategia correspondiente.
Actualmente las familias poseen comportamientos distintos:
- Modelos clásicos: selección de configuración mediante HPO y Walk-Forward Validation.
- Machine Learning: selección de hiperparámetros mediante HPO y Walk-Forward Validation.
- Deep Learning: selección de hiperparámetros mediante HPO y Walk-Forward Validation.
- Modelos fundacionales: se utilizan como predictores preentrenados y no realizan HPO dentro del Módulo 2.
Si la lógica de enrutamiento se mezcla con la implementación de HPO, Walk-Forward Validation o con los modelos concretos, el componente encargado de decidir "qué estrategia ejecutar" pasaría también a conocer "cómo se ejecuta cada estrategia". Esto produciría alto acoplamiento y dificultaría sustituir optimizadores, agregar nuevas familias o probar cada componente de forma aislada.
Adicionalmente, el `sku_class` no debe convertirse en una regla determinista de selección de modelo. La clasificación reduce o estructura el conjunto de candidatos, pero la evaluación experimental posterior continúa siendo responsable de determinar su desempeño.

## Opciones Consideradas

- **Option A: Router monolítico con lógica de ejecución interna.**
El `SelectionRouter` contiene condicionales sobre `sku_class` y ejecuta directamente HPO, Walk-Forward y las implementaciones concretas de cada familia.
- *Pros:*
- Menor número inicial de abstracciones.
- Implementación directa para un número pequeño de modelos.
- *Cons:*
- Acopla routing, optimización y ejecución de modelos.
- Cualquier cambio de optimizador obliga a modificar el router.
- Dificulta probar el routing de forma independiente.
- Incrementa el riesgo de que reglas experimentales queden codificadas como comportamiento arquitectónico.
- **Option B: Arquitectura Router + Strategy sin estado.**
El `SelectionRouter` recibe una representación tipada del SKU, consulta una política de routing y delega la ejecución a estrategias que satisfacen un contrato común.
El router no implementa HPO, Walk-Forward Validation ni lógica específica de modelos.
La lectura del artefacto físico de entrada pertenece a la frontera de I/O del sistema; el router recibe los datos necesarios ya representados mediante contratos internos.
- *Pros:*
- Separa decisión de routing de ejecución matemática.
- Permite sustituir HPO sin modificar el router.
- Permite agregar estrategias sin alterar las existentes.
- Facilita pruebas unitarias mediante estrategias simuladas.
- Mantiene una frontera estable entre el Módulo 1 y las estrategias del Módulo 2.
- *Cons:*
- Requiere definir explícitamente los contratos entre Router y Strategies.
- Introduce una capa adicional de abstracción.

## Decisión

Se adopta la **Option B: Router + Strategy sin estado**.
El `SelectionRouter` tendrá exclusivamente las siguientes responsabilidades:
1. recibir la información tipada requerida de un SKU, incluyendo `sku_class`;
2. consultar la política de routing vigente;
3. identificar las familias candidatas;
4. resolver la estrategia registrada para cada familia;
5. delegar la selección/configuración;
6. devolver resultados mediante un contrato común.
El `SelectionRouter` no será responsable de:
- leer o escribir archivos Parquet;
- ejecutar directamente Optuna;
- implementar Walk-Forward Validation;
- decidir poda ASHA;
- entrenar modelos concretos;
- seleccionar el ganador final del benchmark.
Las estrategias serán inyectadas mediante contratos abstractos, de modo que el router dependa de interfaces estables y no de implementaciones concretas.

## Consecuencias

### Positivas

- La lógica de routing puede probarse sin ejecutar modelos ni HPO.
- Los cambios dentro de Optuna, ASHA o Walk-Forward no afectan al router.
- Nuevas familias de predictores pueden incorporarse mediante nuevas estrategias.
- Se conserva la separación de responsabilidades entre ingestión, routing, optimización y evaluación.
- La arquitectura permite mantener contratos internos estables aunque cambien las implementaciones concretas.

### Negativas

- Es necesario mantener un registro explícito de estrategias disponibles.
- Los contratos de entrada y salida deben diseñarse antes de implementar el router.
- Una configuración incorrecta del registro de estrategias o de la política de routing debe detectarse explícitamente para evitar fallos silenciosos.
