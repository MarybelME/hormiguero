# Prompts para Claude Code — Simulador de hormiguero

## Preparación (una sola vez)

1. Crea la carpeta del proyecto y coloca `CLAUDE.md` en la raíz.
2. Crea `docs/ESPECIFICACION.md` y pega ahí tu especificación original completa.
3. `git init` y un primer commit.
4. Abre Claude Code en esa carpeta. Para la etapa 0 conviene activar el **modo plan**
   (Shift+Tab hasta "plan mode") para que analice sin escribir código.

---

## Prompt de la etapa 0 (análisis y diseño)

```
Lee CLAUDE.md y docs/ESPECIFICACION.md completos. Estamos en la ETAPA 0: análisis y diseño.
No escribas código de la aplicación en esta etapa.

Tu tarea es producir docs/DISENO.md con estas 14 secciones, en este orden:

1. Arquitectura general: capas, responsabilidades y por qué el núcleo es independiente de FastAPI.
2. Diagrama de componentes: en Mermaid (graph) y una versión ASCII.
3. Modelo conceptual: el sistema, su frontera, entradas (parámetros), salidas (estadísticas)
   y un diagrama de estados de la hormiga en Mermaid (stateDiagram) con TODAS las transiciones
   y la condición/evento que dispara cada una.
4. Entidades: obreras, reina; distingue entidades temporales/permanentes y móviles/fijas.
5. Atributos: tabla por entidad y elemento (nombre en código, tipo NumPy, unidad, rango, valor inicial).
6. Variables de estado: de cada entidad y del sistema; indica cuáles cambian por evento y cuáles por paso.
7. Eventos: tabla con nombre, condición de disparo, cambios de estado que produce, si consume
   un número pseudoaleatorio y qué datos se registran en la bitácora.
8. Recursos: alimento (y el nido como punto de depósito); cómo se modela su agotamiento.
9. Variables aleatorias: cada una con su distribución, el mapeo desde u ∈ [0,1) y el propósito
   con el que se registra (DIRECCION_SALIDA, DIRECCION_COLISION, SEGUIR_REINA, MUNDO...).
10. Algoritmos: cuadrados medios con un ejemplo numérico paso a paso (semilla 5735, 6 números),
    detección de degeneración, movimiento, detección de colisión con rejilla espacial, búsqueda
    de alimento, regreso al nido, influencia de la reina y predicción del "siguiente evento".
    Usa pseudocódigo, no Python.
11. Estructura de carpetas: confirma o ajusta la de CLAUDE.md justificando cada cambio.
12. Flujo de datos Python ↔ JavaScript: endpoints REST (método, ruta, cuerpo, respuesta),
    mensajes WebSocket y el formato binario del cuadro descrito byte a byte; incluye un diagrama
    de secuencia Mermaid para "iniciar simulación" y para "seleccionar una hormiga".
13. Estrategia para miles de hormigas: SoA con NumPy, rejilla, desacople de velocidad y envío,
    render por capas; estimación del tamaño de cada cuadro para 5 000 y 20 000 hormigas.
14. Plan de desarrollo por etapas: para cada etapa de CLAUDE.md, objetivo, entregables,
    pruebas y "criterio de terminado" verificable.

Añade al final:
- Tabla "Componente del programa → Concepto de simulación" (amplía el glosario de CLAUDE.md).
- Sección "Decisiones abiertas" con lo que la especificación no define. Como mínimo:
  a) política ante la degeneración de cuadrados medios (detener, re-sembrar con regla visible,
     cambiar de generador...);
  b) si todos los números aleatorios (también reina y generación del mundo) usan el generador
     elegido o flujos separados;
  c) diferencia exacta entre "reiniciar" y "limpiar";
  d) qué hace una hormiga al entrar al radio de la reina (la sigue cuánto tiempo, cuándo deja de seguirla,
     si se evalúa la probabilidad una vez o en cada paso);
  e) cómo se consume y recupera la energía, y qué pasa al llegar a cero;
  f) qué hace la hormiga al llegar al borde del mundo;
  g) qué significa "cantidad de alimento" en la interfaz (número de fuentes o unidades por fuente).
  Para cada una da 2–3 opciones, su valor didáctico y tu recomendación.

Cuando termines, muéstrame un resumen de una página y la lista de decisiones abiertas,
y detente. No pases a la etapa 1 hasta que yo apruebe el diseño y responda las decisiones.
```

---

## Prompt para resolver las decisiones abiertas

```
Estas son mis decisiones sobre los puntos abiertos:
a) ...
b) ...
(...)
Actualiza docs/DISENO.md incorporándolas (elimina la sección de decisiones abiertas o
márcalas como resueltas con su justificación), crea docs/PROGRESO.md con la etapa 0
como terminada y propón el mensaje de commit. No empieces la etapa 1.
```

---

## Prompt genérico para cada etapa siguiente

Cambia el número y nombre de la etapa:

```
Iniciamos la ETAPA N: <nombre> según CLAUDE.md y docs/DISENO.md.

1. Lee CLAUDE.md, docs/DISENO.md y docs/PROGRESO.md.
2. Preséntame un plan: archivos a crear o modificar, pruebas que escribirás, cómo lo probaré
   manualmente y riesgos. Espera mi aprobación.
3. Después de aprobado, implementa sólo esta etapa. Escribe primero las pruebas del
   criterio de terminado.
4. Ejecuta pytest y corrige hasta que pase.
5. Actualiza docs/PROGRESO.md y, si hubo cambios de diseño, docs/DISENO.md.
6. Explícame qué conceptos de la materia se pueden enseñar con lo que se construyó en esta
   etapa y cómo demostrarlos en clase en 5 minutos.
7. Propón el mensaje de commit y detente.
```

---

## Prompts complementarios útiles

**Revisión antes de cerrar una etapa**
```
Antes de cerrar la etapa, revisa el código contra CLAUDE.md: reglas de la sección 11,
determinismo, uso del ServicioAleatorio, nombres del glosario y ausencia de números mágicos.
Lista lo que no cumple y corrígelo.
```

**Verificación de rendimiento (etapas E2 a E4)**
```
Ejecuta backend/scripts/benchmark.py (y con --feromonas) para 1 000, 5 000 y 20 000 hormigas. Reporta pasos por segundo,
tamaño del cuadro enviado y, si no se alcanza la meta de CLAUDE.md, perfila y propón optimizaciones
antes de aplicarlas.
```

**Explicación para clase**
```
Explícame, como se lo explicaría a estudiantes de Simulación, cómo fluye un número de cuadrados
medios desde que se genera hasta que cambia la dirección de una hormiga en pantalla, citando
los archivos y funciones involucrados.
```
