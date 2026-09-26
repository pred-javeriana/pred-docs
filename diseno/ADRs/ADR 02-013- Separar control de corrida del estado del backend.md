# ADR-02-013: Separar control de corrida del estado del backend

- **Fecha:** 2026-09-19
- **Estado:** Aplicada

## Contexto & Problema

El Módulo 2 necesita reanudar estudios interrumpidos sin perder los trials previamente evaluados y debe distinguir estados como configuración completada, podada o fallida.
El backend vigente de HPO es Optuna. ADR-02-010 ya establece que `optuna.Study` es la fuente de verdad para los trials y que la serialización/reconstrucción específica de `FrozenTrial` pertenece al adaptador de Optuna.
Sin embargo, el proyecto necesita además controlar conceptos que no pertenecen al backend de HPO: identidad de la corrida, estado global de ejecución, compatibilidad de configuración, referencia al checkpoint, seed, métrica y parámetros del protocolo experimental.
Si el Control de Reanudación importa directamente Optuna y reconstruye sus estructuras internas, la lógica de ejecución de PRED quedaría nuevamente acoplada al backend concreto y duplicaría responsabilidades ya asignadas al adaptador.

## Opciones Consideradas

- **Option A: Control de Reanudación específico para Optuna.**
El componente importa `optuna`, inspecciona `Study` y serializa directamente sus trials.
- *Pros:*
- Menor número inicial de capas.
- Acceso directo a todos los detalles del backend.
- *Cons:*
- Duplica lógica existente en `adaptador_optuna.py`.
- Acopla el ciclo de vida de PRED a una librería concreta.
- Un cambio de backend exigiría modificar el controlador de reanudación.
- Crea dos componentes responsables de serializar el mismo estado.
- **Option B: Separar estado de corrida y estado del backend mediante un puerto/adaptador.**
El Control de Reanudación administra únicamente el estado del experimento PRED y utiliza un contrato abstracto para solicitar al backend que persista o reconstruya su propio estado.
- *Pros:*
- Mantiene una sola fuente de verdad para los trials.
- Evita duplicar serialización específica de Optuna.
- Permite cambiar el backend sin modificar la lógica de ciclo de vida.
- Facilita pruebas del controlador usando un adaptador simulado.
- *Cons:*
- Requiere definir un contrato adicional entre el controlador y el backend.
- La integración debe mantener sincronizados el manifiesto de corrida y el checkpoint del backend.

## Decisión

Se adopta la **Option B**.
El Control de Reanudación manejará exclusivamente conceptos pertenecientes al ciclo de vida de PRED:
- `run_id`;
- estado global de la corrida;
- SKU y familia;
- configuración experimental;
- seed;
- métrica;
- fingerprint de compatibilidad;
- referencia al checkpoint del backend.
El backend continuará siendo responsable de representar y reconstruir sus propios trials.
Para Optuna, las operaciones de serialización/reanudación permanecerán encapsuladas en su adaptador.
El módulo genérico `control_reanudacion` no podrá importar `optuna`.

## Consecuencias

### Positivas

- Se conserva la frontera arquitectónica ya establecida alrededor de Optuna.
- No se mantienen dos representaciones independientes del estado de los trials.
- El Control de Reanudación puede probarse sin ejecutar Optuna.
- La sustitución futura del backend queda localizada en un adaptador.

### Negativas

- Se requiere coordinar dos artefactos conceptualmente distintos: manifiesto de corrida y checkpoint del backend.
- El contrato entre controlador y adaptador debe mantenerse estable.
