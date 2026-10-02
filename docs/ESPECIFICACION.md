Quiero desarrollar una simulación web educativa de un hormiguero para una materia universitaria de Ingeniería en Sistemas llamada Simulación.

OBJETIVO PRINCIPAL

La simulación debe servir para enseñar conceptos de simulación, especialmente:

- sistemas
- entidades
- atributos
- variables de estado
- eventos
- recursos
- variables aleatorias
- números pseudoaleatorios
- generación de números pseudoaleatorios
- comportamiento de entidades
- experimentación
- análisis estadístico

TECNOLOGÍAS

Quiero utilizar:

Backend:
- Python
- FastAPI

Frontend:
- HTML
- CSS
- JavaScript
- Canvas para la visualización

Quiero que la arquitectura permita manejar miles de hormigas sin que la interfaz se vuelva innecesariamente lenta.

IMPORTANTE

No quiero que generes todo el proyecto de una sola vez.

Primero analiza los requerimientos y propón la arquitectura completa.

Después desarrollaremos el proyecto por etapas.

SIMULACIÓN

El sistema representa un hormiguero con:

1. Un nido.
2. Una hormiga reina.
3. Miles de hormigas obreras.
4. Fuentes de alimento.
5. Rocas y obstáculos.
6. Espacio de simulación.
7. Feromonas como elemento opcional de una segunda etapa.

HORMIGAS

Cada hormiga debe tener como mínimo:

- identificador
- posición X
- posición Y
- dirección
- velocidad
- energía
- estado
- cantidad de alimento transportado

Estados posibles:

- EN_NIDO
- BUSCANDO_COMIDA
- SIGUIENDO_REINA
- EVITANDO_OBSTACULO
- TRANSPORTANDO_COMIDA
- REGRESANDO_AL_NIDO

MOVIMIENTO ALEATORIO

Quiero implementar inicialmente el método de CUADRADOS MEDIOS para generar números pseudoaleatorios.

El número generado debe utilizarse para determinar la dirección inicial de las hormigas cuando salen del hormiguero.

Por ejemplo:

número pseudoaleatorio → 0 a 1

y posteriormente:

dirección = número × 360°

Quiero que el programa conserve y muestre los números generados para poder utilizarlos con fines didácticos.

OBSTÁCULOS

Debe existir detección de colisiones.

Cuando una hormiga detecte que su trayectoria está bloqueada por una roca u otro obstáculo:

1. Detectar la posible colisión.
2. Generar un nuevo número pseudoaleatorio.
3. Determinar una nueva dirección.
4. Continuar el movimiento.

REINA

Debe existir una hormiga reina.

La reina tendrá:

- posición
- estado
- radio de influencia

Cuando una hormiga obrera se encuentre dentro del radio de influencia de la reina, deberá existir una probabilidad configurable de que siga a la reina.

Los parámetros deben poder modificarse desde la interfaz.

ALIMENTO

Debe haber diferentes fuentes de alimento.

Cuando una hormiga encuentre alimento:

1. Cambia de estado.
2. Recoge una cantidad determinada.
3. Cambia de dirección.
4. Regresa al hormiguero.
5. Deposita el alimento.

FEROMONAS

No implementarlas todavía en la primera versión.

Diseña la arquitectura de forma que posteriormente podamos agregar:

- depósito de feromonas
- evaporación
- detección de feromonas
- seguimiento de rutas con mayor concentración

INTERFAZ

Quiero una interfaz web donde pueda modificar:

- número de hormigas
- semilla
- generador pseudoaleatorio
- velocidad de simulación
- cantidad de obstáculos
- cantidad de alimento
- radio de influencia de la reina
- probabilidad de seguir a la reina

Debe existir:

- iniciar
- pausar
- reiniciar
- limpiar
- velocidad de simulación

ESTADÍSTICAS

Mostrar en tiempo real:

- número total de hormigas
- hormigas buscando alimento
- hormigas regresando
- hormigas siguiendo a la reina
- alimento recolectado
- número de colisiones
- cambios de dirección
- tiempo de simulación
- cantidad de números pseudoaleatorios generados

MODO DIDÁCTICO

Quiero un modo didáctico que permita seleccionar una hormiga y mostrar:

- ID
- posición
- dirección
- estado
- número pseudoaleatorio utilizado
- método de generación
- último evento
- siguiente evento

Esto servirá para explicar el funcionamiento de la simulación a estudiantes.

ARQUITECTURA DIDÁCTICA

Cada componente del programa debe poder relacionarse con conceptos de la materia.

Por ejemplo:

Hormiga = entidad

Posición = variable de estado

Alimento = recurso

Encontrar alimento = evento

Dirección = variable aleatoria

Generador de cuadrados medios = generador pseudoaleatorio

Nido = parte del sistema

Roca = restricción/obstáculo

Reina = entidad especial

Quiero que antes de programar me entregues:

1. Arquitectura general.
2. Diagrama de componentes.
3. Modelo conceptual.
4. Entidades.
5. Atributos.
6. Variables de estado.
7. Eventos.
8. Recursos.
9. Variables aleatorias.
10. Algoritmos necesarios.
11. Estructura de carpetas.
12. Flujo de datos entre Python y JavaScript.
13. Estrategia para manejar miles de hormigas.
14. Plan de desarrollo por etapas.

NO escribas todavía todo el código.

Primero quiero revisar y comprender el diseño.