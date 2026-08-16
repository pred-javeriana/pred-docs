# Requisitos No Funcionales - Lenguaje Visual

Adición a la SRS v1.1 (erratas #13 y #14 del registro de cumplimiento). Los
requerimientos RNF-USA-04 y RNF-USA-05 se incorporan a la sección 3.5.6 (Usabilidad)
de la SRS.

## RNF-USA-04 - Accesibilidad perceptiva

| Campo | Detalle |
| --- | --- |
| # Requerimiento | RNF-USA-04 |
| Tipo | Usabilidad |
| Descripción | El sistema debe representar los estados de ejecución y los veredictos de validación de manera que sean distinguibles sin depender únicamente del color. |
| Razón | Parte de los usuarios puede tener dificultad en la percepción del color, y la interfaz se exhibe ante evaluadores, posiblemente sobre un proyector. Una codificación basada solo en el color vuelve ilegibles los estados críticos para estos lectores. |
| Criterio de medición | Al presentar los cinco estados del ciclo de vida de una tarea (pendiente, ejecutando, exitosa, fallida, no ejecutable) y los tres veredictos de validación retrospectiva (se sostiene, se sostiene parcialmente, no se sostiene) en una representación sin color, cada estado debe permanecer distinguible mediante un canal distinto del color, como un ícono, una etiqueta textual o un patrón. |
| Prioridad | Alta |
| Módulo | Transversal |
| Versión | 1.1 |
| Fecha | 16 de agosto de 2026 |

## RNF-USA-05 - Apariencia analítica

| Campo | Detalle |
| --- | --- |
| # Requerimiento | RNF-USA-05 |
| Tipo | Usabilidad |
| Descripción | El sistema debe presentar una apariencia visual analítica y sobria, coherente con una herramienta de evaluación experimental, y debe evitar una apariencia de producto comercial de consumo o de tipo SaaS. |
| Razón | La interfaz se demuestra ante evaluadores académicos y se usa como instrumento operativo de análisis. Una apariencia de producto de consumo comprometería la credibilidad de los resultados y del ejercicio académico. |
| Criterio de medición | El equipo debe mantener una guía de lenguaje visual que documente la paleta, la tipografía y los componentes, vinculando cada decisión a su requisito de origen; una revisión del prototipo contra dicha guía debe confirmar la ausencia de patrones de marketing de consumo, como paletas lúdicas, animaciones decorativas o contenido promocional. |
| Prioridad | Alta |
| Módulo | Transversal |
| Versión | 1.1 |
| Fecha | 16 de agosto de 2026 |
