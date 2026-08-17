# Lenguaje visual de PRED

Documento de referencia del lenguaje visual de la interfaz de PRED. Define paleta,
tipografía, íconos, componentes, estados, ritmo, alertas y estados vacíos. Cada
decisión se traza a un requisito no funcional (NFR) de la SRS, citado por su
identificador. Los NFR RNF-USA-04 y RNF-USA-05 son adiciones aprobadas (registro de
cumplimiento, erratas #13 y #14).

## Principio rector

La interfaz de PRED se demuestra ante evaluadores académicos y se usa como
instrumento operativo de análisis. Su apariencia debe ser analítica, sobria y
estructurada por reglas, coherente con una herramienta de evaluación experimental,
y evitar el aspecto de producto comercial de consumo (RNF-USA-05). La legibilidad
para un operador no especialista es un requisito, no un lujo (RNF-USA-01).

## 1. Paleta

La base es un neutral frío que deja que la información tenga prioridad visual. Cada
color se usa por su rol semántico, no como decoración; `--primary` queda reservado
para una sola acción principal por vista.

| Rol | Token | Valor |
| --- | --- | --- |
| Lienzo | `--canvas` | `#EFEFEC` |
| Superficie | `--surface` | `#FFFFFF` |
| Tinta principal | `--ink` | `#14161A` |
| Tinta ordinaria | `--ink-soft` | `#2C2F34` |
| Texto atenuado | `--muted` | `#6B6F76` |
| Borde | `--border` | `#DBDCD7` |
| Borde fuerte | `--border-strong` | `#C7C9C5` |
| Primario | `--primary` | `#1F5C54` |
| Primario oscuro | `--primary-dark` | `#164740` |
| Éxito | `--ok` | `#3E6B4F` |
| Fallo | `--err` | `#A3402F` |
| Aviso | `--warn` | `#A0741F` |
| Información | `--info` | `#2E6E9E` |
| Datos | `--data` | `#1B7A8C` |

Los valores numéricos usan `--data` directamente. Los conteos con significado de
aprobación usan el rol correspondiente, como `--ok`; un conteo neutro usa
`--ink-soft`. Los estados conservan color, ícono y etiqueta, de modo que siguen
siendo distinguibles sin color (RNF-USA-04, RNF-USA-05).

## 2. Tipografía

| Uso | Familia y pesos |
| --- | --- |
| Display y cuerpo | Archivo, 400/500/600/700/800; italic 400 cuando corresponda |
| Cifras, métricas, códigos | JetBrains Mono, solo para datos y mediciones |

Archivo unifica display e interfaz y permite una escala realmente contrastada: los
encabezados primarios son grandes, pesados y tienen tracking entre `-0.02em` y
`-0.025em`; el cuerpo es más pequeño y denso. JetBrains Mono aporta cifras
(tabulares), valores de métricas y códigos SKU, nunca una apariencia técnica
decorativa (RNF-USA-01, RNF-USA-05). Las fuentes se sirven localmente, sin CDN
(SRS §2.4).

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

Se conservan tres niveles de jerarquía (RNF-USA-01, RNF-USA-02): primario relleno
para la única acción principal de la vista, secundario y sutil. Son planos, con
esquinas de 0-2px. La acción destructiva usa `--err`, y el color no es su único
canal (RNF-USA-04, RNF-USA-02).

### Formularios

Estados: por defecto, foco (`:focus-visible` con anillo `--primary`), error (borde
+ ícono + mensaje claro) y deshabilitado. Los controles tienen radio máximo de 2px.
El error nunca se comunica solo con color (RNF-USA-02, RNF-USA-04).

### Métricas y estructura

No se usan tarjetas anidadas ni tarjetas de héroe como plantilla. Las secciones y
filas se separan con reglas de 1px `--border`; una fila KPI es plana, con pares
etiqueta/valor separados por espacio o una hairline. En tablas, los números son
columnas alineadas, color `--data` y `font-variant-numeric: tabular-nums`
(RNF-USA-01). No se usa `box-shadow` como elevación por defecto; un popover real
declara una sola vez borde o sombra, nunca ambos.

### Progreso de ejecución

Barra con color dinámico interpolado azul (en curso) → verde (completado), con curva
cúbica para que la transición a "completado" sea visible. El porcentaje y la
etiqueta siempre acompañan al color (RNF-USA-03, RNF-USA-04).

## 5. Estados

Ocho estados, cada uno con color + ícono + etiqueta (RNF-USA-04). El color es un
refuerzo, nunca el único canal.

| Estado | Ícono | Color |
| --- | --- | --- |
| pendiente | reloj | neutro |
| ejecutando | play | información |
| exitosa | verificación | éxito |
| fallida | cruz | fallo |
| no ejecutable | prohibido | aviso |

| Veredicto | Ícono | Color |
| --- | --- | --- |
| se sostiene | círculo con verificación | éxito |
| se sostiene parcialmente | círculo con guion | aviso |
| no se sostiene | círculo con cruz | fallo |

## 6. Ritmo

Escala de espaciado en múltiplos de 4px (4, 8, 16, 24). Las divisiones son reglas
finas y el radio de controles es 0-2px. La ausencia de cajas y sombras superpuestas
mantiene el registro sobrio y analítico (RNF-USA-01, RNF-USA-05).

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
| Neutral frío y roles semánticos de color | RNF-USA-05 |
| Archivo unificado + mono solo para datos | RNF-USA-05, RNF-USA-01 |
| Íconos SVG de línea, sin emojis | SRS §2.4, RNF-USA-04, RNF-USA-01 |
| Estados: color + ícono + etiqueta | RNF-USA-04 |
| Canal `--data` distinto del primario/info | RNF-USA-05 |
| Divisores hairline, controles afilados, sin tarjetas anidadas | RNF-USA-01, RNF-USA-05 |
| Barra de progreso con color dinámico | RNF-USA-03, RNF-USA-04 |
| Tabla densa con hover de fila | RNF-DES-04, RNF-USA-01 |
| Acción destructiva en rojo, no en primario | RNF-USA-04, RNF-USA-02 |
| Tres niveles de jerarquía de botón | RNF-USA-01, RNF-USA-02 |
| Ritmo 4px y radio contenido | RNF-USA-01, RNF-USA-05 |
| Estados de formulario (foco/error/deshabilitado) | RNF-USA-02, RNF-USA-01, RNF-USA-04 |
| Alertas de cuatro niveles | RNF-USA-02, RNF-USA-04 |
| Estados vacíos guiados | RNF-USA-01, RNF-USA-02 |
