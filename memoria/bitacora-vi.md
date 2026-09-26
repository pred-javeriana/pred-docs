# Bitácora de Desarrollo — Capítulo VI

**Propósito**: Este archivo es el registro de desarrollo (bitácora) que alimenta el Capítulo VI de la tesis (Desarrollo de la Solución). Se registra un evento por hecho notable: decisiones de diseño sobre la marcha, errores descubiertos, cambios de plan, hallazgos de referencias, y cambios de alcance en cada sprint.

**Fuente**: Registro mantenido por el equipo durante el desarrollo; una entrada por evento notable de cada sprint.

**Publicación**: Capitulo VI se ensambla en S6 a partir de esta bitácora, extracciones de notas de revisión de sprint (actas/), y capturas de pantalla del prototipo.

---

## Plantilla de Entrada

```
### S{n} · {Semana / Hito} · {Fecha YYYY-MM-DD}

**Evento**: {Descripción breve del hecho notable}

**Impacto**: {Cómo afecta al diseño, alcance, o línea de tiempo}

**Referencia**: {PRED-ID si aplica, link a decisión, o PR si aplica}
```

---

## Entradas

### S? · Definición previa al S0: selección por categoría · 2026-07-13

**Evento**: *Cambio de alcance y decisión de diseño.* En la reunión del 12 de julio se propuso sustituir la selección de un modelo por SKU por la selección de un campeón por categoría; el 13 de julio se precisó que las categorías se derivarían de la caracterización de las series de L1 (cruce de volumen y valor con variabilidad e intermitencia), no de etiquetas comerciales fijas. L4 validaría el campeón en cada SKU y reportaría la dispersión dentro de cada categoría. La evaluación de la categoría completa quedó como opción predeterminada; el muestreo se reservó para candidatos de aprendizaje automático de costo alto. La dirección se aprobó, pero quedó pendiente elevarla al director antes de implementarla.

**Impacto**: La propuesta cambió la unidad de selección y validación: el costo de ajuste de los candidatos no aumentaba frente al diseño por SKU, mientras que comprobar cada campeón requería un modelo por SKU y se consideró viable con las máquinas virtuales universitarias disponibles. La delimitación del 7 de septiembre acotó después el uso de `sku_class` a reducir candidatos, sin imponer por sí sola un modelo; por ello, la selección por categoría de esta entrada se conserva como dirección histórica, no como regla vigente. El plan de trabajo ubicó S0 en la segunda mitad de julio; estos acuerdos precedieron ese intervalo, por lo que no se asignó un sprint.

**Referencia**: Reunión del equipo del 2026-07-12 y decisión de selección del 2026-07-13 (identificadores y enlaces no disponibles); delimitación posterior del modelamiento del 2026-09-07 (referencia no disponible).

### S? · Definición previa al S0: estrategia de datos · 2026-07-13

**Evento**: *Cambio de alcance.* Se fijó un conjunto de datos público como instrumento principal de desarrollo; la búsqueda de datos empresariales continuaría, principalmente entre consultorios clínicos, y se mantuvo como alternativa la empresa del padre de Juan Camilo Alba. La decisión dejó atrás el caso D0 del distribuidor de repuestos para filtros de agua y requirió una errata explícita en la SRS. Si no se obtenían datos empresariales, el proyecto continuaría con el conjunto público y declararía esa limitación.

**Impacto**: Cambió la fuente de datos prevista para el desarrollo y desplazó el caso empresarial que hasta entonces se había descrito. La sección 1 de `diseno/contexto-diseno-ui.md` todavía presenta el distribuidor de filtros de agua como caso de referencia, por lo que la documentación conserva una discrepancia que requiere validación editorial.

**Referencia**: Decisión sobre selección y estrategia de datos del 2026-07-13 (identificador y enlace no disponibles); `diseno/contexto-diseno-ui.md`, §1.

### S2 · Criterio común de optimización · 2026-08-31

**Evento**: *Decisión de diseño sobre la marcha.* En el seguimiento con el director se acordó optimizar las familias de modelos estadísticos clásicos, de aprendizaje automático, de aprendizaje profundo y fundacionales hacia el mismo objetivo de capacidad predictiva, y evaluarlas mediante validación walk-forward. Los modelos clásicos no se seleccionarían únicamente por AIC/BIC antes de compararlos con modelos de aprendizaje automático o profundo. Se mantendrían parámetros propios de cada familia con una salida de evaluación común; para los modelos fundacionales se considerarían principalmente el diseño de instrucciones de entrada, el contexto y la temperatura cuando correspondiera.

**Impacto**: La decisión alineó la comparación de las familias con el desempeño predictivo y llevó a revisar las decisiones que aún respaldaban la selección por AIC. Quedaron por precisar la aplicación concreta de HPO a los modelos clásicos, la configuración de los modelos fundacionales y el contrato común de parámetros y resultados.

**Referencia**: Reunión de seguimiento con el director del 2026-08-31 (identificador y enlace no disponibles); ADR-02-009, que adoptó posteriormente HPO para modelos clásicos.

### S2 · Ajuste del aumento de datos y la ingesta · 2026-08-31

**Evento**: *Cambio de alcance y decisión de diseño.* Se sustituyó la propuesta de construir una sola serie artificial muy larga por la generación de múltiples series sintéticas que conservaran las características estadísticas del conjunto original. El Módulo 0 quedó desacoplado del flujo operativo: atendería la necesidad particular de aumentar el conjunto de desarrollo y no sería una etapa obligatoria del producto final. El Módulo 1 asumiría un archivo previamente preparado, verificaría sus requisitos y recomendaría ajustes cuando el formato fuera incompatible, sin modificar automáticamente el archivo original.

**Impacto**: Cambiaron los supuestos sobre la forma del conjunto aumentado y el lugar del Módulo 0 dentro de la solución, por lo que las pruebas y el entrenamiento podían requerir ajustes posteriores. En la ingesta, la revisión y corrección del archivo quedaron bajo control del usuario.

**Referencia**: Reunión de seguimiento con el director del 2026-08-31 (identificador y enlace no disponibles).

### S2 · Configuración de los recursos de cómputo · 2026-08-31

**Evento**: *Decisión de diseño sobre la marcha.* Se acordó usar inicialmente el computador personal de Derek, documentar sus capacidades y limitaciones y permitir configuraciones seleccionables según los recursos disponibles, en lugar de presuponer una infraestructura única. El equipo debía hacer explícito el equilibrio entre capacidad de cómputo, tiempo, costo y calidad de la exploración.

**Impacto**: Los recursos pasaron a ser una variable explícita del diseño experimental. La comparación cuantitativa con alternativas y la definición de perfiles concretos quedaron pendientes.

**Referencia**: Reunión de seguimiento con el director del 2026-08-31 (identificador y enlace no disponibles).

### S? · Delimitación del Módulo 2 · 2026-09-07

**Evento**: *Decisión de diseño sobre la marcha.* Se delimitó que el Módulo 2 consumiría el Parquet inmutable de cinco columnas del Módulo 1 (`sku_id`, `timestamp`, `demand_qty`, `lead_time_days`, `sku_class`), sin volver a leer archivos CSV, recalcular ADI/CV2 ni modificar el panel. `sku_class` reduciría el conjunto de candidatos, pero no impondría un modelo. Router y Strategy se mantendrían separados, con orquestación sin estado alrededor de colaboradores inyectados; los modelos clásicos usarían HPO evaluado con walk-forward, mientras que los modelos fundacionales preentrenados participarían como candidatos sin AICc ni HPO. TPE propondría configuraciones y ASHA asignaría recursos y podaría, sin aplicar poda voraz antes de completar cuatro ventanas; walk-forward sería la única comparación predictiva. La estrategia de aprendizaje profundo sería un adaptador delgado que declararía su espacio de búsqueda para los hiperparámetros de entrenamiento y arquitectura, y delegaría la selección en TPE, ASHA y walk-forward; no incorporaría un marco de entrenamiento, otro protocolo de resultados ni ranking por AICc/BIC. La reanudación tendría un único coordinador para los puntos de control y el estado de ejecución, que registrara las podas aparte de las fallas de entrenamiento y cerrara ante identidades discordantes, sin decidir podas, ajustar modelos ni convertirse en una base de datos general; todas las familias compartirían un resultado tipado.

**Impacto**: Estos límites precisaron las entradas, responsabilidades y resultados compartidos para el modelamiento. Quedaron sin resolver los contratos concretos de Router, Strategy, TPE y ASHA, la métrica objetivo, la política para series cortas y los catálogos de candidatos por clase. El registro se fechó el 7 de septiembre y atribuyó su origen a las secciones 7 y 9 del Sprint 2; el plan de trabajo sitúa S3 en la primera mitad de septiembre, por lo que el sprint de origen no quedó confirmado.

**Referencia**: Delimitación del Módulo 2 fechada el 2026-09-07; referencia pública no disponible. El registro atribuyó el origen a las secciones 7 y 9 del Sprint 2.

### S? · Corrección de criterios de selección · 2026-09-09

**Evento**: *Defecto de especificación documental previo a la implementación.* Al contrastar la documentación de selección con las decisiones aceptadas en ADR-02-009 y ADR-02-010, se encontraron cinco páginas que aún presentaban BIC/AICc como mecanismo vigente para seleccionar modelos clásicos o ubicaban el ordenamiento por walk-forward después de AICc. Tras la aprobación del capitán, se reemplazó únicamente esa redacción y se verificó cada cambio; se conservaron el historial de las decisiones, las referencias bibliográficas y los contratos pendientes.

**Impacto**: La contradicción podía orientar el diseño hacia un criterio que ya había sido sustituido. La corrección alineó las cinco descripciones con HPO y la evaluación walk-forward, sin alterar contratos ni modificar el contenido histórico de las decisiones. El barrido de las demás páginas no identificó otras afirmaciones vigentes que justificaran ampliar el ajuste.

**Referencia**: ADR-02-009 (3cefbd1b-ee46-80b6-9ed0-d06a2a78cbc4) y ADR-02-010 (3d5fbd1b-ee46-8061-9707-ee29baa8deac); «2. Selección de configuración y modelo» (3a5fbd1b-ee46-8082-bef8-d3f53871fb5d), «2.1 Arquitectura del Motor de Selección y Optimización» (3b1fbd1b-ee46-805d-84fd-c50255369f14), «1. SelectionRouter» (3c6fbd1b-ee46-80a2-9255-c124649eaf2a), «2.8 Estrategia de Validación Temporal» (3b1fbd1b-ee46-8083-b3ba-c77ff1ad2f00) y «8.1 WalkForwardValidation» (3c6fbd1b-ee46-8084-9afb-cea929815f05). El calendario de sprints no estaba disponible para confirmar el número; el plan de trabajo ubicó S3 en la primera mitad de septiembre.
