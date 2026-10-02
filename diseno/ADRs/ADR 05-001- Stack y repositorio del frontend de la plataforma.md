# ADR-05-001: Stack y repositorio del frontend de la plataforma

- **Fecha:** 2026-10-02
- **Estado:** Propuesto

## Contexto & Problema

PRED necesita una interfaz de navegador con dos roles (Operador y Administrador) para cargar y validar datos, lanzar y monitorear corridas, y consultar resultados por SKU. La tarea TASK-UI-1.0-A2 exige decidir el stack y la ubicación del código antes de inicializar el proyecto (TASK-UI-1.1-B1), para no construir las pantallas y rehacerlas después.

Las restricciones del proyecto ya acotan la decisión:

- **Instalación local, sin red y solo CPU.** La SRS §2.4 declara el sistema monolítico y local, sin esquema cliente-servidor distribuido, y su descripción de interfaces excluye la comunicación en red.
- **Reproducibilidad desde un clon limpio** y dependencias fijadas (RNF-REP-01).
- **Contexto de diseño de la interfaz** (`diseno/contexto-diseno-ui.md`, §7): servidor que renderiza HTML con FastAPI, Jinja2 y HTMX; base de Pico.css vendorizada más una capa de marca escrita a mano; sin framework SPA y sin cadena de compilación en el cliente; fuentes e íconos autoalojados; escritorio con viewport mínimo de 1366×768.
- **Estructura del proyecto** (`README.md` de pred-docs): tres repositorios. `pred-engine` es la biblioteca Python de modelado y evaluación; `pred-platform` es el producto entregable con FastAPI, Jinja y HTMX; `pred-docs` reúne documentación y gobernanza.
- **Lenguaje visual** (`diseno/lenguaje-visual.md`): estados con color, ícono y etiqueta (RNF-USA-04), apariencia analítica (RNF-USA-05) y sin CDN.

El backlog describía el stack como abierto («SPA/Next.js frente a una UI en Python»). Esa redacción contradice lo ya establecido en los documentos del repositorio, de modo que este ADR formaliza lo vigente y registra por qué se descartan las alternativas, en lugar de reabrir la decisión.

## Opciones Consideradas

- **Option A: Renderizado en servidor con FastAPI + Jinja2 + HTMX + Pico.css, en un repositorio separado (`pred-platform`).**
  Las rutas devuelven HTML completo o fragmentos; HTMX hace las actualizaciones parciales (por ejemplo, el sondeo del monitoreo de ejecución). El motor se consume como biblioteca Python.
  - *Pros:*
  - Un solo lenguaje y un solo entorno (`uv`, Python ≥ 3.12) que ya usa `pred-engine`.
  - Sin Node, sin `node_modules` ni empaquetado: menos dependencias que fijar y vendorizar para operar sin red.
  - Los modelos Pydantic del motor se reutilizan para validar el contrato en lugar de duplicar tipos.
  - Las pruebas de vistas corren con `pytest` y el cliente de pruebas de FastAPI.
  - Coincide con el contexto de diseño y con la estructura de tres repositorios.
  - *Cons:*
  - Interactividad del lado del cliente más limitada que en una SPA.
  - Las plantillas Jinja no se verifican con tipos.
  - Las tablas de miles de filas exigen paginación, orden y filtro en el servidor.
- **Option B: SPA con React/Next.js.**
  - *Pros:*
  - Ecosistema amplio de componentes y de tablas interactivas.
  - Tipado de extremo a extremo con TypeScript.
  - *Cons:*
  - Contradice la restricción de no usar SPA ni cadena de compilación en el cliente.
  - Introduce Node y npm: instalar sin red exige vendorizar un árbol grande de dependencias.
  - Obliga a construir una API JSON completa, hoy inexistente en el motor, y a mantener los tipos en dos lenguajes.
  - Añade un segundo conjunto de herramientas de CI y pruebas para un equipo que trabaja en Python.
- **Option C: Interfaz Python con un framework de paneles (por ejemplo Streamlit, Dash o NiceGUI).**
  - *Pros:*
  - Prototipado rápido y un solo lenguaje.
  - *Cons:*
  - Poco control sobre el lenguaje visual propio (paleta, tipografía, estados con ícono), que es un requisito (RNF-USA-04, RNF-USA-05).
  - El modelo de ejecución con estado de sesión dificulta pruebas reproducibles y la separación por rol.
  - Menos dependencias vendorizables para operar sin red y menos control sobre ellas.
- **Ubicación del código, Option A1: monorepo** con motor y plataforma juntos.
  - *Pros:*
  - Un solo cambio puede tocar motor e interfaz.
  - *Cons:*
  - Contradice la estructura de tres repositorios ya establecida.
  - Acopla el ciclo de versiones de la biblioteca con el del producto y mezcla el CI de ambos.
- **Ubicación del código, Option A2: repositorio separado `pred-platform`.**
  - *Pros:*
  - Respeta la estructura vigente.
  - Mantiene el motor como biblioteca pura, sin dependencias de interfaz.
  - Cada repositorio tiene su propio CI y lockfile.
  - *Cons:*
  - Los cambios que cruzan ambos repositorios exigen coordinar versiones del contrato.

## Decisión

Se adopta la **Option A** con la ubicación **A2**.

1. **Stack.** `pred-platform` es una aplicación FastAPI que renderiza con Jinja2 y actualiza parcialmente con HTMX. Los estilos son Pico.css vendorizado más una capa de marca propia que implementa los tokens de `lenguaje-visual.md`. Fuentes (Archivo, JetBrains Mono) e íconos (SVG de línea en línea) se sirven localmente. No se usa framework SPA, bundler ni CDN.
2. **Repositorio.** El código vive en `pred-platform`, separado de `pred-engine` y de `pred-docs`. No hay monorepo.
3. **Relación con el motor.** `pred-platform` consume `pred-engine` como dependencia Python con versión o referencia fijada en el lockfile. La plataforma no recalcula métricas, selecciones ni validaciones: presenta artefactos y estados que produce el motor. El mecanismo concreto de instalación se fija en TASK-UI-1.1-B1.
4. **Contrato de consumo.** Los esquemas de TASK-UI-1.0-A3 se implementan como modelos Pydantic v2, con esquemas JSON versionados exportables a partir de ellos. La capa de acceso a datos (TASK-UI-1.1-B4) opera en modo real y en modo fixture, y rechaza respuestas inválidas con un error explícito.
5. **Herramientas.** Las del motor: `uv` con lockfile, Python ≥ 3.12, `ruff` (lint y formato), `pyright` (tipos) y `pytest` con umbral de cobertura. Un comando único levanta la aplicación en local.
6. **Gráficos.** Las visualizaciones simples (pronóstico frente a real, ADI–CV²) se generan como SVG en el servidor. Si una vista exigiera una librería de gráficos, se vendoriza y se justifica en un ADR propio.
7. **Fuera de este ADR.** Autenticación y roles completos, la forma de empaquetar la distribución final y la numeración de versiones del contrato.

## Consecuencias

### Positivas

- Se cumple la ejecución local sin red con un solo árbol de dependencias, fijado por lockfile.
- El equipo trabaja en un solo lenguaje, con las herramientas y convenciones del motor.
- El backlog de frontend deja de depender de una API JSON del motor que aún no existe.
- La decisión se alinea con el contexto de diseño, el lenguaje visual y la estructura de tres repositorios.

### Negativas

- Las plantillas Jinja no pasan por el verificador de tipos; las pruebas de humo de cada vista (TASK-UI-1.3-D1) compensan esa falta.
- Las tablas densas dependen de paginación y filtro en el servidor para cumplir RNF-DES-04.
- Los cambios que afectan el contrato entre motor y plataforma exigen coordinar versiones entre dos repositorios.
- La interactividad se limita a lo que HTMX ofrece; cualquier necesidad mayor requiere un ADR nuevo.

### Impacto en CI y despliegue local

- **CI de `pred-platform`:** `ruff check`, `ruff format --check`, `pyright` y `pytest` con umbral de cobertura. Una prueba rota o un error de lint o de tipos debe fallar el pipeline.
- **Ejecución local:** un clon limpio instala con `uv sync` y arranca con un único comando documentado (por ejemplo `make run`, definido en TASK-UI-1.1-B1). No se requiere red tras la instalación.
- **Entrega:** la distribución final se resuelve fuera de este ADR; no se define aquí un Dockerfile.

## Referencias

- `diseno/contexto-diseno-ui.md`, §7 «Binding technical constraints».
- `diseno/lenguaje-visual.md` y `diseno/requisitos-no-funcionales-visuales.md` (RNF-USA-04, RNF-USA-05).
- `README.md` de pred-docs («three-repo fleet»).
- SRS §2.4 (restricciones) y RNF-REP-01, RNF-DES-04, RNF-USA-01.
- Tareas TASK-UI-1.0-A2, TASK-UI-1.0-A3, TASK-UI-1.1-B1 y TASK-UI-1.1-B4.
