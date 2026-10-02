# CLAUDE.md — Simulador educativo de hormiguero

Este archivo es la guía permanente del proyecto. Léelo completo al iniciar cada sesión.
La especificación vigente es `docs/ESPECIFICACION_v2.md` (requisitos numerados); la original
del cliente se conserva en `docs/ESPECIFICACION.md`. El diseño está en `docs/DISENO.md` y el
avance en `docs/PROGRESO.md`. Si alguno contradice a este
archivo, **detente y pregunta** antes de continuar.

---

## 1. Qué es este proyecto

Una simulación web de un hormiguero para la materia **Simulación** (Ingeniería en Sistemas).
No es un juego ni una simulación biológica realista: es un **instrumento didáctico**.

Cada decisión de código debe responder a esta pregunta:
> ¿Esto ayuda a que un estudiante vea y entienda un concepto de simulación?

Conceptos que el programa debe hacer visibles: sistema, entidades, atributos, variables de
estado, eventos, recursos, variables aleatorias, números pseudoaleatorios y su generación,
comportamiento de entidades, experimentación y análisis estadístico.

Prioridades, en orden:
1. **Corrección y reproducibilidad** (misma semilla + mismos parámetros = misma simulación).
2. **Claridad didáctica** (el código y la interfaz se pueden explicar en clase).
3. **Rendimiento** (miles de hormigas con interfaz fluida).
4. Estética.

---

## 2. Reglas de trabajo (obligatorias)

- **Se trabaja por etapas** (sección 10). No implementes nada de una etapa futura, aunque
  parezca fácil o "ya que estamos". Si algo de una etapa futura condiciona el diseño actual,
  deja el punto de extensión (interfaz, hook, campo reservado) y anótalo en `docs/PROGRESO.md`.
- **Al iniciar cada etapa**: lee `docs/DISENO.md` y `docs/PROGRESO.md`, presenta un plan
  breve (archivos a crear/modificar, pruebas, riesgos) y **espera aprobación** antes de escribir código.
- **Al terminar cada etapa**: ejecuta pruebas, actualiza `docs/PROGRESO.md` (qué se hizo,
  decisiones tomadas, pendientes, cómo probarlo manualmente) y propón el mensaje de commit.
  Luego detente y espera.
- **Decisiones abiertas**: si una decisión de diseño no está resuelta en la especificación ni en
  `docs/DISENO.md`, no la inventes en silencio. Pregunta, ofreciendo 2–3 opciones con su
  ventaja didáctica y técnica, e indica cuál recomiendas.
- No agregues dependencias fuera de las de la sección 4 sin preguntar.
- No reescribas archivos completos para cambios pequeños; edita lo necesario.
- Explica en español. Código, comentarios, docstrings y mensajes de interfaz en español.

---

## 3. Glosario didáctico (fuente de verdad de nombres)

Usa exactamente estos nombres en código, interfaz y documentación. Cada clase o módulo del
dominio debe indicar en su docstring qué concepto de simulación representa.

| Elemento del hormiguero | Concepto de simulación | Nombre en código |
|---|---|---|
| Hormiguero completo | Sistema | `Mundo` / `Simulacion` |
| Espacio 2D con límites | Entorno / frontera del sistema | `Mundo.ancho`, `Mundo.alto` |
| Hormiga obrera | Entidad (temporal, móvil) | `Hormigas` (colección), fila `id` |
| Reina | Entidad especial (permanente) | `Reina` |
| Nido | Parte del sistema / punto de servicio | `Nido` |
| Fuente de alimento | Recurso (consumible, finito) | `FuenteAlimento` |
| Roca | Restricción / obstáculo | `Obstaculo` |
| Posición, dirección, energía, estado, carga | Atributos y variables de estado | columnas de `Hormigas` |
| Alimento almacenado, contadores globales | Variables de estado del sistema | `Estadisticas` |
| Salir del nido, colisión, encontrar alimento, depositar, entrar al radio de la reina | Eventos | `TipoEvento` |
| Dirección inicial / nueva dirección | Variable aleatoria | `angulo = u * 360` |
| Cuadrados medios | Generador de números pseudoaleatorios | `GeneradorCuadradosMedios` |
| Seguir a la reina con probabilidad p | Variable aleatoria Bernoulli | `u < p_seguir_reina` |
| Feromona (etapa futura) | Variable de estado del entorno (campo) | `CampoFeromonas` |

### Estados de la hormiga (enum `EstadoHormiga`, entero de 8 bits)

```
0 EN_NIDO
1 BUSCANDO_COMIDA
2 SIGUIENDO_REINA
3 EVITANDO_OBSTACULO
4 TRANSPORTANDO_COMIDA
5 REGRESANDO_AL_NIDO
```

Los códigos numéricos son parte del protocolo con el frontend: **no los cambies** sin actualizar
`backend/app/api/protocolo.py`, `frontend/js/protocolo.js` y `docs/DISENO.md` a la vez.

---

## 4. Tecnología

- **Backend**: Python 3.11+, FastAPI, Uvicorn, NumPy, Pydantic v2. Pruebas con pytest y httpx
  (para el `TestClient` de FastAPI).
- **Frontend**: HTML, CSS y JavaScript sin frameworks ni bundler (módulos ES nativos).
  Visualización con `<canvas>` 2D.
- **Comunicación**: REST para configuración y control; WebSocket para el flujo de cuadros.

Comandos:
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend       # sirve también el frontend en /
pytest backend/tests -q
```

---

## 5. Arquitectura (principios no negociables)

```
┌──────────────────────── Frontend (navegador) ────────────────────────┐
│ controles.js ─REST─┐                    ┌─ render.js (Canvas)          │
│ panelDidactico.js  │                    ├─ estadisticas.js             │
│                    │   WebSocket binario│                              │
└────────────────────┼────────────────────┼──────────────────────────────┘
                     ▼                    │
┌──────────────────────── Backend (FastAPI) ───────────────────────────┐
│ api/  (rutas REST, WebSocket, protocolo de serialización)             │
│   └─► servicio/ControladorSimulacion (bucle asyncio, velocidad, pausa)│
│          └─► nucleo/Simulacion.paso(dt)  ← Python puro + NumPy        │
│                 ├─ modelo/ (Mundo, Hormigas, Reina, Nido, Alimento,   │
│                 │           Obstaculos)                                │
│                 ├─ comportamiento/ (reglas por estado)                 │
│                 ├─ espacial/ (rejilla para colisiones y vecindad)      │
│                 ├─ aleatorio/ (generadores + registro de números)      │
│                 ├─ eventos/ (tipos, bitácora, próximo evento)          │
│                 └─ estadisticas/                                       │
└──────────────────────────────────────────────────────────────────────┘
```

1. **El núcleo (`nucleo/`, `modelo/`, `comportamiento/`, `aleatorio/`, `eventos/`, `espacial/`,
   `estadisticas/`) no importa FastAPI ni sabe que existe una web.** Debe poder ejecutarse
   desde un script o una prueba sin servidor. Esto también permite correr experimentos por lotes.
2. **El servidor es la única fuente de verdad.** El frontend sólo dibuja y envía comandos;
   nunca calcula movimiento ni estados.
3. **Avance del tiempo**: paso de tiempo fijo (`dt`) con **registro de eventos**. Los eventos
   ocurren dentro de los pasos y se registran con tiempo de simulación, hormiga, tipo y número
   pseudoaleatorio usado. Explícalo así en la documentación: es un modelo de tiempo discreto
   con bitácora de eventos, no un simulador de eventos discretos puro. El "siguiente evento"
   del modo didáctico es una **predicción** (ej. "colisión prevista con roca 3 en ~4 pasos",
   "llegará al alimento 2", "llegará al nido") calculada sólo para la hormiga seleccionada.
4. **La velocidad de simulación** (pasos por segundo) es independiente de la tasa de envío al
   navegador (máx. ~30 cuadros/s). A alta velocidad se simulan varios pasos por cuadro enviado.
5. **Las feromonas** se agregarán como un `CampoFeromonas` (rejilla NumPy 2D) con métodos
   `depositar`, `evaporar`, `muestrear`. Desde la etapa E2 el mundo debe tener el lugar para
   "campos del entorno" y los comportamientos deben recibir un objeto de contexto donde luego
   se pueda consultar ese campo, sin implementarlo todavía.

---

## 6. Números pseudoaleatorios (corazón didáctico)

- Interfaz común `GeneradorPseudoaleatorio` con: `nombre`, `semilla`, `siguiente() -> float en [0,1)`,
  `reiniciar()`, `estado_interno()` (para mostrar el cálculo), `degenerado() -> bool`.
- **Todo** número aleatorio del modelo sale de un generador configurado. Prohibido usar
  `random`, `numpy.random` o `Math.random()` directamente en la lógica del modelo.
  (Excepción: pruebas que comparan contra referencias.)
- Las peticiones pasan por `ServicioAleatorio.obtener(proposito, id_hormiga)` que **registra**:
  índice global, semilla/estado previo, cuadrado, dígitos centrales, `u`, propósito
  (`DIRECCION_SALIDA`, `DIRECCION_COLISION`, `SEGUIR_REINA`, `MUNDO`, …), id de hormiga y tiempo.
- **Cuadrados medios**: semilla de `D` dígitos (D par, configurable, por defecto 4);
  `x²` se rellena con ceros a `2D` dígitos, se toman los `D` centrales, `u = x / 10^D`.
  Debe mostrar paso a paso: `semilla → cuadrado → relleno → centrales → u`.
- **Degeneración**: cuadrados medios cae rápido en 0 o en ciclos. Esto es contenido de clase,
  no un error a ocultar. Detecta valor 0 y repetición de estado (ciclo, con su longitud), regístralo
  como evento `GENERADOR_DEGENERADO` y aplica la política elegida en `docs/DISENO.md`.
  Nunca re-siembres en silencio.
- El diseño debe admitir más generadores (congruencial lineal, congruencial multiplicativo,
  el de NumPy como referencia) sin tocar el modelo.
- El registro completo puede crecer mucho: guarda en memoria un búfer circular para la
  interfaz y permite exportar el registro completo a CSV.
- Mapeos de variables aleatorias en funciones puras y probadas: `angulo = u * 360`,
  `bernoulli(u, p) = u < p`, etc.

---

## 7. Rendimiento con miles de hormigas

- **Estructura de arreglos (SoA) con NumPy**, no una lista de objetos `Hormiga`:
  `x, y, dir, vel, energia (float32)`, `estado, carga (uint8/float32)`, `id (int32)`.
  La clase `Hormigas` encapsula esos arreglos y ofrece `vista(id)` para el modo didáctico.
- Movimiento vectorizado por máscaras de estado. Los bucles Python por hormiga sólo se permiten
  para las hormigas que tienen un evento en ese paso (salir del nido, colisión, recoger comida),
  que son pocas por paso.
- **Rejilla espacial** (celdas uniformes) precalculada para obstáculos y alimento; la detección
  de colisión consulta la celda de la posición siguiente, no todos los obstáculos.
- **Protocolo binario por WebSocket**: encabezado fijo (versión, tick, n) + `Float32Array` x,
  `Float32Array` y, `Uint8Array` estado (y dirección si hace falta). Estadísticas en JSON con
  menor frecuencia (~4 por segundo). Lo estático (nido, rocas, alimento) se envía sólo al cambiar.
- **Frontend**: dos canvas apilados (capa estática y capa dinámica); dibujar hormigas agrupadas
  por estado (un `fillStyle` por grupo, `fillRect` de 2×2 px); `requestAnimationFrame`;
  sin reconstruir el DOM en cada cuadro.
- Meta mínima: 5 000 hormigas a ≥ 30 cuadros/s en una laptop común. Incluye un script
  `backend/scripts/benchmark.py` que mida pasos por segundo sin servidor.

---

## 8. Estructura de carpetas

```
hormiguero/
├── CLAUDE.md
├── README.md
├── docs/
│   ├── ESPECIFICACION.md      # requerimientos originales (no editar)
│   ├── ESPECIFICACION_v2.md   # especificación vigente: requisitos numerados
│   ├── DISENO.md              # diseño aprobado en la etapa 0
│   ├── PROGRESO.md            # bitácora por etapa
│   └── guia_docente.md        # cómo usar el simulador en clase (etapa final)
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # crea FastAPI y sirve frontend/
│   │   ├── config.py          # ParametrosSimulacion (Pydantic) con valores por defecto y rangos
│   │   ├── api/               # rutas_rest.py, ws.py, protocolo.py
│   │   ├── servicio/          # controlador.py (bucle asyncio, pausa, velocidad)
│   │   ├── nucleo/            # simulacion.py (paso, reloj), contexto.py
│   │   ├── modelo/            # mundo.py, hormigas.py, reina.py, nido.py, alimento.py, obstaculos.py, estados.py
│   │   ├── comportamiento/    # una función por estado + transiciones
│   │   ├── espacial/          # rejilla.py, colisiones.py
│   │   ├── aleatorio/         # base.py, cuadrados_medios.py, congruencial.py, servicio.py, registro.py, pruebas_estadisticas.py
│   │   ├── eventos/           # tipos.py, bitacora.py, prediccion.py
│   │   └── estadisticas/      # contadores.py, series.py, exportar.py
│   ├── scripts/               # benchmark.py, experimento_lote.py
│   └── tests/
└── frontend/
    ├── index.html
    ├── css/estilos.css
    └── js/                    # main.js, api.js, ws.js, protocolo.js, render.js, controles.js, estadisticas.js, panelDidactico.js
```

---

## 9. Calidad y pruebas

- Pruebas obligatorias por etapa. Mínimos:
  - Cuadrados medios contra una tabla calculada a mano (incluida en la prueba como comentario).
  - Detección de degeneración (semillas conocidas que llegan a 0 y que ciclan).
  - **Determinismo**: dos simulaciones con la misma configuración producen arreglos idénticos tras N pasos.
  - Colisiones: una hormiga apuntando a una roca nunca queda dentro de ella.
  - Conservación del recurso: alimento en fuentes + transportado + depositado = alimento inicial.
  - Transiciones de estado válidas (tabla de transiciones permitidas en `modelo/estados.py`).
  - Serialización del protocolo: lo que el backend empaqueta, el formato documentado lo describe byte a byte.
- Tipado con anotaciones en Python; funciones cortas; sin "números mágicos" (todo parámetro
  vive en `config.py` con descripción, unidad y rango).
- Toda validación de parámetros de la interfaz se hace también en el backend (Pydantic).
- Antes de declarar una etapa terminada, ejecuta `pytest` y verifica manualmente lo que se pueda.

---

## 10. Etapas

| # | Etapa | Entregable principal |
|---|---|---|
| E0 | Análisis y diseño | `docs/DISENO.md` con los 14 puntos y `docs/ESPECIFICACION_v2.md`. **Sin código.** |
| E1 | Base y generadores | Esqueleto (FastAPI sirviendo frontend, `/api/salud`, pytest) + cuadrados medios, registro, degeneración y re-siembra, vista de tabla |
| E2 | Modelo y motor | Mundo generado con semilla y render estático + paso de tiempo, comportamiento, colisiones, alimento, energía, reina, benchmark |
| E3 | Tiempo real, interfaz y modo didáctico | Controlador asyncio, WebSocket binario, controles, panel de parámetros, estadísticas en vivo, selección de hormiga y bitácora |
| E4 | Experimentación, feromonas y pulido | Réplicas por lote, CSV, pruebas estadísticas, comparación de generadores, `CampoFeromonas`, `guia_docente.md` |

Cada etapa se divide en hitos (ver `docs/DISENO.md` §14); al cerrar cada hito `pytest` debe pasar.

Estado actual: ver `docs/PROGRESO.md`.

---

## 11. Lo que NO debes hacer

- Generar todo el proyecto de una vez o adelantar etapas.
- Usar generadores aleatorios del lenguaje en la lógica del modelo.
- Ocultar o "arreglar" en silencio la degeneración de cuadrados medios.
- Mover lógica de simulación al JavaScript.
- Enviar JSON por hormiga en cada cuadro.
- Crear objetos Python por hormiga dentro del bucle principal.
- Cambiar nombres del glosario o códigos de estado sin actualizar todos los lugares y la documentación.
- Tomar decisiones de diseño abiertas sin preguntar.
