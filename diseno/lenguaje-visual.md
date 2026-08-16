# Lenguaje visual de PRED

Documento de referencia del lenguaje visual de la interfaz de PRED. Define paleta,
tipografía, íconos, componentes, estados, ritmo, alertas y estados vacíos. Cada
decisión se traza a un requisito no funcional (NFR) de la SRS, citado por su
identificador. Los NFR RNF-USA-04 y RNF-USA-05 son adiciones aprobadas (registro de
cumplimiento, erratas #13 y #14).

## Principio rector

La interfaz de PRED se demuestra ante evaluadores académicos y se usa como
instrumento operativo de análisis. Su apariencia debe ser analítica y sobria,
coherente con una herramienta de evaluación experimental, y evitar el aspecto de
producto comercial de consumo (RNF-USA-05). La legibilidad para un operador no
especialista es un requisito, no un lujo (RNF-USA-01).

## 1. Paleta

Dirección "Archivo": papel cálido, tinta grafito y verde petróleo como acento.

| Rol | Token | Valor |
| --- | --- | --- |
| Lienzo | `--canvas` | `#FAF7F0` |
| Superficie | `--surface` | `#FFFFFF` |
| Tinta (texto principal) | `--ink` | `#22201C` |
| Tinta secundaria | `--ink-2` | `#4A463F` |
| Texto atenuado | `--muted` | `#6B655C` |
| Borde | `--border` | `#E5DFD2` |
| Borde fuerte | `--border-strong` | `#D6CDBC` |
| Primario | `--primary` | `#1F5C54` |
| Primario oscuro | `--primary-dark` | `#164740` |
| Primario suave | `--primary-soft` | `#E2EDEA` |
| Éxito | `--ok` | `#3E6B4F` |
| Fallo | `--err` | `#A3402F` |
| Aviso | `--warn` | `#A0741F` |
| Información | `--info` | `#2E6E9E` |
| Datos (tendencias) | `--data` | `#1B7A8C` |

El canal `--data` es deliberadamente distinto del primario y del canal de
información, para que una línea de tendencia nunca se confunda con un color de tema
o de estado (RNF-USA-05). Contraste de tinta sobre lienzo ≈ 14:1 (AAA).

## 2. Tipografía

| Uso | Familia |
| --- | --- |
| Títulos / display | IBM Plex Serif |
| Cuerpo / interfaz | IBM Plex Sans |
| Cifras, métricas, códigos | JetBrains Mono (tabular) |

La serif en títulos refuerza el registro académico-editorial (RNF-USA-05); la sans
en cuerpo sostiene la legibilidad de pantallas densas (RNF-USA-01); la mono tabular
alinea cifras y códigos de SKU para lectura rápida de métricas (RNF-USA-01). Todas
las fuentes se venden localmente; no se usan CDN (SRS §2.4).

## 3. Íconos

SVG de línea, trazo 2, sin emojis, sin fuentes de íconos por CDN (SRS §2.4). Cada
ícono tiene un único significado (RNF-USA-01) y sirve como canal no-cromático de
estado (RNF-USA-04).

Acciones: lanzar (play), guardar (disquete), detener (cuadrado), reanudar
(rotación), cargar (flecha arriba), exportar (flecha abajo), buscar (lupa),
filtrar (embudo), volver (flecha izquierda).

Navegación: panel de pronósticos (gráfico), carga y validación (flecha arriba),
configuración (deslizadores), monitoreo (pulso), resultados (gráfico), validación
retrospectiva (escudo con verificación), administración (engranaje).

Estados: ver sección 5.

## 4. Componentes

### Botones

Tres niveles de jerarquía (RNF-USA-01, RNF-USA-02):

| Nivel | Uso | Tratamiento |
| --- | --- | --- |
| Primario | Acción principal | Fondo primario, texto blanco |
| Secundario | Acción del sistema con peso | Relleno primario suave, borde primario |
| Sutil | Ayuda de bajo impacto (filtrar, buscar) | Fondo blanco, borde tenue |

La acción destructiva (detener, restaurar) usa el rojo semántico, no el primario, de
modo que el color no es el único canal que la identifica (RNF-USA-04, RNF-USA-02).

### Formularios

Estados: por defecto, foco (borde primario), error (borde + ícono + mensaje claro)
y deshabilitado (opacidad reducida). El mensaje de error indica qué está mal y qué
hacer, en español y sin jerga (RNF-USA-02). El error nunca se comunica solo con
color (RNF-USA-04).

### Tiles de métrica

Cifra grande en mono, etiqueta en mayúsculas pequeñas. Lectura rápida de números de
portafolio (RNF-USA-01).

### Progreso de ejecución

Barra con color dinámico interpolado azul (en curso) → verde (completado), con curva
cúbica para que la transición a "completado" sea visible. El porcentaje y la
etiqueta siempre acompañan al color (RNF-USA-03, RNF-USA-04).

## 5. Estados

Ocho estados, cada uno con color + ícono + etiqueta (RNF-USA-04). El color es un
refuerzo, nunca el único canal.

Ciclo de vida de tarea:

| Estado | Ícono | Color |
| --- | --- | --- |
| pendiente | reloj | neutro |
| ejecutando | play | información |
| exitosa | verificación | éxito |
| fallida | cruz | fallo |
| no ejecutable | prohibido | aviso |

Veredicto de validación retrospectiva:

| Veredicto | Ícono | Color |
| --- | --- | --- |
| se sostiene | círculo con verificación | éxito |
| se sostiene parcialmente | círculo con guion | aviso |
| no se sostiene | círculo con cruz | fallo |

## 6. Ritmo

Escala de espaciado en múltiplos de 4px (4, 8, 16, 24). Radio de borde contenido:
4px (chips, inputs), 6px (botones, tarjetas), 8px (paneles), pill (chips de estado).
El radio contenido mantiene el registro "impreso" sobrio, sin esquinas redondeadas
de producto SaaS (RNF-USA-05).

## 7. Alertas

Cuatro niveles: información, éxito, aviso, error. Cada uno con ícono + mensaje, el
color como refuerzo (RNF-USA-02, RNF-USA-04). El mensaje describe el hecho y, cuando
es posible, la acción siguiente.

## 8. Estados vacíos

Primera visita y ausencia de datos: guían al siguiente paso en lugar de dejar la
pantalla muda. Contenido centrado en un ancho máximo con margen, con una acción
única y clara (RNF-USA-01, RNF-USA-02).

## 9. Matriz decisión → NFR

| Decisión de diseño | NFR de respaldo |
| --- | --- |
| Paleta "Archivo" (papel + tinta + petróleo) | RNF-USA-05 |
| Serif display + sans cuerpo + mono cifras | RNF-USA-05, RNF-USA-01 |
| Íconos SVG de línea, sin emojis | SRS §2.4, RNF-USA-04, RNF-USA-01 |
| Estados: color + ícono + etiqueta | RNF-USA-04 |
| Canal "datos" distinto del primario/info | RNF-USA-05 |
| Barra de progreso con color dinámico | RNF-USA-03, RNF-USA-04 |
| Tabla densa con hover de fila | RNF-DES-04, RNF-USA-01 |
| Acción destructiva en rojo, no en primario | RNF-USA-04, RNF-USA-02 |
| Tres niveles de jerarquía de botón | RNF-USA-01, RNF-USA-02 |
| Ritmo 4px y radio contenido | RNF-USA-01, RNF-USA-05 |
| Estados de formulario (foco/error/deshabilitado) | RNF-USA-02, RNF-USA-01, RNF-USA-04 |
| Alertas de cuatro niveles | RNF-USA-02, RNF-USA-04 |
| Estados vacíos guiados | RNF-USA-01, RNF-USA-02 |
