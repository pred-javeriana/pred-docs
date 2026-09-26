# ADR-02-012: Política declarativa de routing

- **Fecha:** 2026-09-19
- **Estado:** Aplicada

## Contexto & Problema

La Sección 2.2 establece que `sku_class` debe utilizarse para reducir o estructurar el conjunto de familias candidatas evaluadas para cada SKU.
Sin embargo, la clasificación no debe convertirse en una selección determinista del modelo ganador. Su función es orientar el espacio de candidatos antes de la evaluación experimental posterior.
Si las reglas `sku_class → familias candidatas` se implementan mediante condicionales distribuidos dentro del `SelectionRouter`, cualquier modificación de la política experimental obligaría a cambiar código de infraestructura y dificultaría identificar qué conjunto de reglas produjo una corrida determinada.
También es necesario distinguir entre la arquitectura del mecanismo de routing y el contenido específico de la política. La arquitectura debe permanecer estable aunque la matriz de candidatos cambie posteriormente como resultado de decisiones experimentales.

## Opciones Consideradas

- **Option A: Reglas hardcodeadas mediante `if/elif` dentro del Router.**
- *Pros:*
- Implementación inmediata.
- No requiere objetos adicionales.
- *Cons:*
- Mezcla la política experimental con la infraestructura de routing.
- Cada cambio exige modificar el código del Router.
- Dificulta versionar y reproducir distintas políticas.
- **Option B: Política declarativa e inyectable.**
Representar el routing mediante una estructura explícita que asocia cada `sku_class` con un conjunto ordenado de familias candidatas. El `SelectionRouter` recibe esta política como dependencia y únicamente la aplica.
- *Pros:*
- Desacopla mecanismo y política.
- Permite cambiar candidatos sin modificar el Router.
- Facilita pruebas parametrizadas.
- Permite registrar la política utilizada durante una corrida.
- *Cons:*
- Requiere validar la política antes de utilizarla.
- Introduce una configuración adicional que debe mantenerse bajo control de versiones.
- **Option C: Motor dinámico de reglas externo.**
Utilizar un sistema de reglas o servicio separado para determinar las familias candidatas.
- *Pros:*
- Alta flexibilidad dinámica.
- *Cons:*
- Complejidad desproporcionada para el alcance actual.
- Introduce infraestructura adicional sin una necesidad experimental demostrada.

## Decisión

Se adopta la **Option B: política declarativa e inyectable**.
El `SelectionRouter` no contendrá una matriz de routing distribuida mediante `if/elif`.
Se definirá un contrato `RoutingPolicy` que permita resolver:
`sku_class → familias candidatas`
La política deberá ser:
- explícita;
- validable;
- determinista para una misma versión;
- independiente de las implementaciones concretas de las estrategias;
- identificable dentro de los metadatos de una corrida.
La matriz concreta de familias candidatas será definida en la configuración/documentación experimental correspondiente y no queda fijada por este ADR.
Una clase de SKU desconocida, una familia no registrada o una política inválida deberá producir un error explícito en lugar de aplicar un fallback silencioso.

## Consecuencias

### Positivas

- La política experimental puede evolucionar sin modificar el código del Router.
- Las reglas utilizadas durante una corrida pueden registrarse para garantizar reproducibilidad.
- Las pruebas del Router pueden cubrir distintas políticas mediante parametrización.
- Se evita convertir accidentalmente `sku_class` en una regla determinista de selección final.

### Negativas

- La política pasa a ser un artefacto que debe versionarse y validarse.
- El sistema necesita manejar explícitamente configuraciones incompletas o familias inexistentes.
