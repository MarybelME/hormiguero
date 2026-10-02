# Especificación v2 — Simulador educativo de hormiguero

> Versión refinada de `docs/ESPECIFICACION.md` (original del cliente, se conserva sin cambios).
> Esta versión ordena los requerimientos, los numera, les da criterios de aceptación
> verificables e incorpora las decisiones de diseño resueltas en la etapa 0.
> Detalle técnico (algoritmos, protocolo, estructura): `docs/DISENO.md`.

---

## 1. Propósito

Simulación web de un hormiguero para la materia **Simulación** (Ingeniería en Sistemas).
Es un **instrumento didáctico**: su objetivo es que el estudiante vea y entienda los conceptos
de sistema, entidad, atributo, variable de estado, evento, recurso, variable aleatoria,
número pseudoaleatorio y su generación, comportamiento de entidades, experimentación y
análisis estadístico.

No es un juego ni una simulación biológica realista.

## 2. Alcance

**Incluido**: nido, reina, miles de obreras, fuentes de alimento, rocas, espacio 2D acotado,
generador de cuadrados medios con registro visible, interfaz de control, estadísticas en vivo,
modo didáctico, experimentación por lote y feromonas (en la última etapa).

**Excluido**: realismo biológico (ciclo de vida, nacimientos, muerte, castas distintas de
obrera y reina), mundo 3D, multiusuario simultáneo sobre una misma simulación, persistencia
en base de datos.

## 3. Glosario

| Término | Significado en este sistema | Concepto de simulación |
|---|---|---|
| Hormiguero | El conjunto completo simulado | Sistema |
| Mundo | Rectángulo `ancho × alto` donde ocurre todo | Entorno / frontera |
| Obrera | Hormiga que sale, busca, transporta y regresa | Entidad temporal y móvil |
| Reina | Hormiga única que patrulla cerca del nido y atrae obreras | Entidad permanente especial |
| Nido | Lugar de salida, depósito de alimento y recuperación de energía | Parte del sistema / punto de servicio |
| Fuente de alimento | Depósito finito de unidades de alimento | Recurso |
| Roca | Zona circular que las hormigas no pueden atravesar | Restricción |
| Paso | Avance del reloj en `dt` segundos simulados | Avance del tiempo |
| `u` | Número pseudoaleatorio en [0, 1) | Número pseudoaleatorio |
| Evento | Cambio discreto en el estado de una entidad o del sistema | Evento |

## 4. Requisitos funcionales

Cada requisito tiene un criterio de aceptación (CA) verificable y la etapa en que se entrega.

### 4.1 Mundo y entidades

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-01 | El mundo es un rectángulo de `ancho × alto` con un nido, una reina, `num_obstaculos` rocas y `num_fuentes` fuentes de alimento. | Con los parámetros por defecto se dibujan exactamente esos elementos. | E2 |
| RF-02 | La posición y el tamaño de rocas y fuentes se generan con el generador configurado (flujo `MUNDO`), sin solaparse entre sí ni con el nido. | Misma semilla ⇒ mismo mundo; ningún par de elementos se solapa. | E2 |
| RF-03 | Cada obrera tiene: identificador, posición X, posición Y, dirección, velocidad, energía, estado y carga de alimento. | La vista de una hormiga muestra los 8 atributos. | E2 |
| RF-04 | Los estados de una obrera son: `EN_NIDO`, `BUSCANDO_COMIDA`, `SIGUIENDO_REINA`, `EVITANDO_OBSTACULO`, `TRANSPORTANDO_COMIDA`, `REGRESANDO_AL_NIDO`, y sólo cambian según la tabla de transiciones de `DISENO.md` §3. | Ninguna transición fuera de la tabla ocurre en 10 000 pasos. | E2 |
| RF-05 | La reina tiene posición, estado, dirección y radio de influencia, y patrulla lentamente alrededor del nido cambiando de rumbo con números pseudoaleatorios. | La reina se mueve sin salir de su radio de patrulla; cada cambio de rumbo queda registrado. | E2 |

### 4.2 Números pseudoaleatorios

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-10 | Generador de **cuadrados medios** con `D` dígitos (4, 6 u 8; por defecto 4). | Con semilla 5735 y D = 4 produce 0.8902, 0.2456, 0.0319, 0.1017, 0.0342, 0.1169. | E1 |
| RF-11 | Cada número muestra su cálculo: semilla → cuadrado → relleno a 2D dígitos → dígitos centrales → `u`. | La tabla de la interfaz muestra las 5 columnas para cada número. | E1 |
| RF-12 | Todo número usado por el modelo se registra con: índice, generador, estado previo, cálculo, `u`, propósito, id de hormiga y tiempo. | Cada `u` de la bitácora de eventos se encuentra en el registro con el mismo índice. | E1 |
| RF-13 | Se detecta la degeneración (valor 0 o repetición de estado, con longitud del ciclo) y se registra como evento `GENERADOR_DEGENERADO`. | Semilla 1 ⇒ cero; 2500 ⇒ ciclo de longitud 1; 6100 ⇒ ciclo de longitud 4. | E1 |
| RF-14 | Ante la degeneración se re-siembra con una regla determinista y visible; el número de re-siembras se muestra en las estadísticas. Nunca se re-siembra en silencio. | Cada re-siembra aparece en el registro con la semilla nueva; dos corridas iguales re-siembran igual. | E1 |
| RF-15 | Hay dos flujos de números con el mismo tipo de generador: `MUNDO` (generación del mundo) y `COMPORTAMIENTO` (hormigas y reina). | Cambiar el número de hormigas no cambia la posición de las rocas. | E1 |
| RF-16 | El diseño admite otros generadores (congruencial lineal, multiplicativo, NumPy como referencia) sin modificar el modelo. | Agregar un generador sólo requiere una clase nueva y su registro. | E4 |

### 4.3 Comportamiento

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-20 | Las obreras salen del nido a razón de `salidas_por_paso` por paso; al salir, su dirección es `u × 360°` (propósito `DIRECCION_SALIDA`). | La dirección de cada hormiga al salir es exactamente `u × 360` del número registrado. | E2 |
| RF-21 | Si la siguiente posición está dentro de una roca o fuera del mundo: se detecta la colisión, se genera un nuevo `u`, se asigna la dirección `u × 360°` y la hormiga continúa (estado `EVITANDO_OBSTACULO` durante `pasos_evasion` pasos). | Ninguna hormiga queda dentro de una roca ni fuera del mundo en 10 000 pasos; cada colisión consume un número. | E2 |
| RF-22 | Al **entrar** al radio de la reina una hormiga que busca comida decide seguirla con probabilidad `p_seguir_reina` (Bernoulli: `u < p`), una sola vez por entrada. Si la sigue, lo hace durante `pasos_seguimiento` pasos y luego toma una dirección aleatoria. | Con p = 0 nadie la sigue; con p = 1 todas las que entran la siguen; la proporción observada se aproxima a p. | E2 |
| RF-23 | Al encontrar alimento la hormiga: cambia a `TRANSPORTANDO_COMIDA`, recoge `min(capacidad_carga, disponible)` unidades, orienta su dirección hacia el nido, regresa y deposita al llegar. | El alimento se conserva: fuentes + transportado + depositado = inicial, en todo paso. | E2 |
| RF-24 | La energía baja en cada paso fuera del nido; bajo `umbral_regreso` la hormiga pasa a `REGRESANDO_AL_NIDO`; en el nido recupera energía y sólo sale con energía llena. No hay muerte. | Ninguna hormiga tiene energía fuera de [0, `energia_max`]. | E2 |
| RF-25 | Las fuentes son finitas; al agotarse dejan de atraer hormigas y se muestran vacías. | Una fuente agotada nunca entrega alimento. | E2 |

### 4.4 Control e interfaz

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-30 | La interfaz permite modificar todos los parámetros de la sección 6, validados en el navegador y en el servidor. | Un valor fuera de rango es rechazado por el servidor (HTTP 422) aunque se salte la validación del navegador. | E3 |
| RF-31 | Botones: **Iniciar**, **Pausar**, **Reiniciar** (vuelve a t = 0 con la misma configuración y reproduce la misma corrida), **Limpiar** (borra mundo, hormigas, registros y estadísticas; conserva los valores del formulario). | Reiniciar dos veces y correr N pasos da el mismo estado. | E3 |
| RF-32 | La velocidad de simulación (pasos por segundo) se cambia en vivo, sin reiniciar. | Cambiar la velocidad no altera el resultado tras N pasos, sólo el tiempo real que tarda. | E3 |

### 4.5 Estadísticas

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-40 | Se muestran en tiempo real: total de hormigas, buscando alimento, regresando (con y sin comida), siguiendo a la reina, alimento recolectado, colisiones, cambios de dirección, tiempo de simulación, números pseudoaleatorios generados y re-siembras del generador. | Los contadores coinciden con un conteo directo del estado del modelo. | E3 |

### 4.6 Modo didáctico

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-50 | Se puede seleccionar una hormiga con un clic y ver: ID, posición, dirección, estado, último número pseudoaleatorio usado (con su cálculo y propósito), método de generación, último evento y siguiente evento previsto. | Cada cambio de dirección de la hormiga seleccionada se puede rastrear hasta su `u` en el registro. | E3 |
| RF-51 | El "siguiente evento" es una predicción que no consume números ni altera el estado. Si el próximo evento es aleatorio, se informa como posible, con su probabilidad. | Una corrida con hormiga seleccionada es idéntica a una sin selección. | E3 |
| RF-52 | Bitácora de eventos filtrable por hormiga y tipo. | Filtrar por id muestra sólo eventos de esa hormiga. | E3 |

### 4.7 Experimentación

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-60 | Ejecutar réplicas por lote (varias semillas, sin interfaz) y obtener resultados agregados. | El mismo lote ejecutado dos veces da resultados idénticos. | E4 |
| RF-61 | Exportar a CSV el registro completo de números, la bitácora y las series de estadísticas. | El CSV se abre en una hoja de cálculo con encabezados en español. | E4 |
| RF-62 | Pruebas de uniformidad (χ², Kolmogórov-Smirnov) e independencia (corridas) sobre los números generados, y comparación entre generadores. | Los estadísticos coinciden con valores de referencia en datos de prueba conocidos. | E4 |

### 4.8 Feromonas

| ID | Requisito | Criterio de aceptación | Etapa |
|---|---|---|---|
| RF-70 | Campo de feromonas sobre el mundo con depósito, evaporación, detección y seguimiento de rutas de mayor concentración. | Se forman rutas visibles entre fuentes y nido; la simulación sigue siendo determinista. | E4 |

## 5. Requisitos no funcionales

| ID | Requisito | Criterio de aceptación |
|---|---|---|
| RNF-01 | **Reproducibilidad**: misma semilla + mismos parámetros = misma simulación. | Dos corridas producen arreglos idénticos tras N pasos. |
| RNF-02 | **Rendimiento**: miles de hormigas con interfaz fluida. | 5 000 hormigas a ≥ 30 cuadros/s en una laptop común. |
| RNF-03 | **Única fuente de verdad**: el servidor calcula todo; el navegador sólo dibuja y envía comandos. | El JavaScript no contiene lógica de movimiento ni de estados. |
| RNF-04 | **Núcleo independiente de la web**: la simulación se ejecuta desde un script o prueba sin servidor. | Los módulos del núcleo no importan FastAPI. |
| RNF-05 | **Trazabilidad didáctica**: cada componente se relaciona con un concepto de la materia. | Cada clase del dominio indica en su docstring el concepto que representa. |
| RNF-06 | **Idioma**: interfaz, código, comentarios y documentación en español. | Revisión manual. |
| RNF-07 | **Tecnología**: Python 3.11+, FastAPI, NumPy; HTML, CSS y JavaScript sin frameworks; Canvas 2D. | `requirements.txt` y `frontend/` lo cumplen. |

## 6. Parámetros de la interfaz

| Parámetro | Nombre | Unidad | Rango | Defecto |
|---|---|---|---|---|
| Número de hormigas | `num_hormigas` | hormigas | 1 – 20 000 | 2 000 |
| Semilla | `semilla` | entero de D dígitos | 1 – 10^D − 1 | 5735 |
| Generador | `generador` | — | `cuadrados_medios` (más en E4) | `cuadrados_medios` |
| Dígitos del generador | `digitos` | dígitos | 4, 6, 8 | 4 |
| Velocidad de simulación | `pasos_por_segundo` | pasos/s | 1 – 1 000 | 30 |
| Número de rocas | `num_obstaculos` | rocas | 0 – 60 | 12 |
| Número de fuentes | `num_fuentes` | fuentes | 1 – 20 | 4 |
| Alimento por fuente | `alimento_por_fuente` | unidades | 1 – 100 000 | 2 000 |
| Radio de influencia de la reina | `radio_reina` | unidades de longitud | 0 – 300 | 80 |
| Probabilidad de seguir a la reina | `p_seguir_reina` | probabilidad | 0 – 1 | 0.3 |

Parámetros avanzados (con valor por defecto, editables en un panel plegable):
`velocidad_hormiga` (5 – 40 u/s, 20), `capacidad_carga` (1 – 255, 5),
`salidas_por_paso` (1 – 100, 5), `pasos_evasion` (5), `pasos_seguimiento` (100),
`energia_max` (100), consumo por paso (0.1), `umbral_regreso` (30),
recuperación por paso (2). Fijos: `dt` = 0.1 s, mundo de 1000 × 700.

## 7. Decisiones de diseño incorporadas

| Tema | Decisión |
|---|---|
| Degeneración de cuadrados medios | Re-siembra determinista, visible y registrada (RF-13, RF-14) |
| Flujos de números | Dos: `MUNDO` y `COMPORTAMIENTO` (RF-15) |
| Reiniciar vs. limpiar | Ver RF-31 |
| Radio de la reina | Bernoulli una vez al entrar; seguimiento por N pasos (RF-22) |
| Energía | Regreso bajo umbral y recuperación en el nido, sin muerte (RF-24) |
| Borde del mundo | Se trata como obstáculo (RF-21) |
| Cantidad de alimento | Dos parámetros: fuentes y unidades por fuente (sección 6) |
| Movimiento de la reina | Patrulla aleatoria lenta (RF-05) |
| Salida del nido | Tasa constante (RF-20) |

## 8. Etapas de desarrollo

| Etapa | Contenido | Requisitos |
|---|---|---|
| E0 | Análisis y diseño: `DISENO.md` y esta especificación | — |
| E1 | Base y generadores: esqueleto web, cuadrados medios, registro, degeneración, vista de tabla | RF-10 a RF-15, RNF-04 |
| E2 | Modelo y motor: mundo con semilla, comportamiento completo, benchmark | RF-01 a RF-05, RF-20 a RF-25, RNF-01 |
| E3 | Tiempo real, interfaz y modo didáctico | RF-30 a RF-32, RF-40, RF-50 a RF-52, RNF-02, RNF-03 |
| E4 | Experimentación, feromonas y guía docente | RF-16, RF-60 a RF-62, RF-70 |

Cada etapa termina con pruebas automáticas pasando, `docs/PROGRESO.md` actualizado y
aprobación antes de empezar la siguiente.
