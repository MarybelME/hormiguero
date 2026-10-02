# PROGRESO.md — Bitácora por etapa

| Etapa | Estado |
|---|---|
| E0 Análisis y diseño | Terminada |
| E1 Base y generadores | Terminada |
| E2 Modelo y motor | Terminada (pendiente de revisión) |
| E3 Tiempo real, interfaz y modo didáctico | Pendiente |
| E4 Experimentación, feromonas y pulido | Pendiente |

---

## E0 — Análisis y diseño (2026-10-01)

**Qué se hizo**
- `docs/DISENO.md` con las 14 secciones, anexo de componentes ↔ conceptos y decisiones.
- `docs/ESPECIFICACION_v2.md`: requisitos numerados (RF/RNF) con criterio de aceptación,
  parámetros con rangos y alcance por etapa. `docs/ESPECIFICACION.md` queda intacta.
- El plan pasó de 11 etapas a 4 (E1–E4) agrupadas por capas, cada una dividida en hitos.
  Actualizado en `CLAUDE.md` §10 y `DISENO.md` §14.
- Entorno: `.venv` con Python 3.13, fastapi, uvicorn[standard], numpy, pydantic 2, pytest.

**Decisiones tomadas** (detalle en `DISENO.md`, "Decisiones de diseño")
- a) Degeneración: re-siembra determinista y visible; D ∈ {4, 6, 8}.
- b) Dos flujos de números: `MUNDO` y `COMPORTAMIENTO`.
- c) Reiniciar = misma corrida desde t = 0; limpiar = vaciar todo conservando el formulario.
- d) Reina: Bernoulli una vez al entrar al radio; seguimiento por `pasos_seguimiento`.
- e) Energía: regreso bajo umbral, recuperación en el nido, sin muerte.
- f) Borde = obstáculo con nueva dirección aleatoria.
- g) Alimento: `num_fuentes` y `alimento_por_fuente`.
- h) Reina patrulla aleatoriamente cerca del nido.
- i) Salida del nido a tasa constante.
- j) `httpx` se agrega a `requirements.txt` (se instala en E1).

**Pendientes**
- `PROMPTS_CLAUDE_CODE.md` sigue mencionando la numeración anterior de etapas.

**Cómo revisarlo**: leer `docs/ESPECIFICACION_v2.md` y luego `docs/DISENO.md`.

Commit: `038e432 docs: etapa 0 — diseño, especificación v2 y plan en 4 etapas` (subido a GitHub).

---

## E1 — Base y generadores (2026-10-01)

Requisitos cubiertos: RF-10 a RF-15 y RNF-04.

**Qué se hizo**
- *Hito 1.1 — Esqueleto*: `backend/requirements.txt` (con `httpx`), `pytest.ini`
  (`pythonpath = backend`), `.gitignore`, `README.md`, `app/main.py` (FastAPI que sirve
  `frontend/` en `/`), `GET /api/salud`, `index.html` con los dos canvas apilados (vacíos).
- *Hito 1.2 — Generadores*:
  - `aleatorio/base.py`: interfaz `GeneradorPseudoaleatorio`.
  - `aleatorio/cuadrados_medios.py`: `GeneradorCuadradosMedios` (D ∈ {4, 6, 8}), cálculo
    paso a paso (`PasoCuadradosMedios`), detección de cero y de ciclo con su longitud,
    re-siembra `(semilla + k·7919) mod 10^D`.
  - `aleatorio/registro.py`: `RegistroAleatorio`, búfer circular con índice global continuo.
  - `aleatorio/servicio.py`: `ServicioAleatorio.obtener(proposito, id_hormiga)` con dos
    flujos (`MUNDO`, `COMPORTAMIENTO`), enum `Proposito` y evento `GENERADOR_DEGENERADO`
    en la bitácora.
  - `aleatorio/variables.py`: `angulo`, `bernoulli`, `uniforme`.
  - `eventos/tipos.py` y `eventos/bitacora.py` (mínimos; se amplían en E2).
  - `POST /api/aleatorio/vista-previa` (generador temporal, no toca ninguna simulación).
  - `frontend/js/tablaAleatorios.js`: tabla i · xᵢ · xᵢ² · relleno (centrales resaltados)
    · centrales · u · dirección; filas degeneradas en rojo y fila de re-siembra con la fórmula.
- Pruebas: 64 (`test_cuadrados_medios`, `test_servicio_aleatorio`, `test_variables`,
  `test_api`, `test_nucleo_independiente`). Todas pasan.

**Decisiones tomadas**
- El número degenerado se entrega y se marca; la re-siembra rige desde el número siguiente.
- Tras re-sembrar se vacía el historial de estados vistos (empieza una sucesión nueva). Si la
  nueva semilla da 0 o el estado que degeneró, se usa k + 1.
- Semilla válida: 1 ≤ semilla < 10^D (422 si no).
- `ServicioAleatorio` recibe los dos generadores ya creados; así E1 no necesita la regla de
  la semilla de `COMPORTAMIENTO`.
- `GET /api/aleatorio/registro` se pospone a E3: en E1 no hay simulación cuyo registro
  paginar. El núcleo ya ofrece `RegistroAleatorio.pagina(desde, limite)` probado.
- La prueba de independencia del núcleo también verifica que no se importe `random` ni
  `numpy.random`.

**Pendientes**
- **Decisión abierta para E2**: regla para la semilla del flujo `COMPORTAMIENTO`
  (recomendada: `(semilla + 10^D/2) mod 10^D`, y 1 si da 0).
- Aviso de Starlette: el `TestClient` con `httpx` está obsoleto y sugiere `httpx2`. No
  afecta a las pruebas; cambiar de dependencia requiere aprobación.
- `PROMPTS_CLAUDE_CODE.md` sigue con la numeración vieja.

**Cómo probarlo manualmente**
1. `uvicorn app.main:app --reload --app-dir backend` y abrir <http://127.0.0.1:8000>.
2. El encabezado debe decir "Servidor en línea · v0.1.0".
3. La tabla inicial (semilla 5735, D = 4) debe empezar 0.8902, 0.2456, 0.0319, 0.1017,
   0.0342, 0.1169 (DISENO.md §10.1). Con 40 números, la fila 31 degenera (ciclo de
   longitud 4) y aparece la re-siembra con semilla 3654.
4. Probar semillas 1 (cero), 2500 (ciclo 1) y 6100 (ciclo 4); probar semilla 0 → mensaje de error.
5. `pytest backend/tests -q` → 64 pruebas pasan.

Commit: `f32b55f feat: etapa 1 — esqueleto web y generador de cuadrados medios con registro y degeneración`.

---

## E2 — Modelo y motor (2026-10-02)

Requisitos cubiertos: RF-01 a RF-05, RF-20 a RF-25 y RNF-01.

**Qué se hizo**
- *Hito 2.1 — Mundo*:
  - `config.py`: `ParametrosSimulacion` con descripción, unidad y rango de los 24 parámetros
    (principales y avanzados) y constantes fijas (`DT`, mundo 1000 × 700, radios, celda 4).
  - `modelo/`: `estados.py` (enums y tabla de transiciones), `hormigas.py` (15 columnas
    NumPy y `vista(id)`), `nido.py`, `reina.py`, `alimento.py`, `obstaculos.py`, `mundo.py`
    (`campos = {}` reservado para feromonas) y `generacion_mundo.py` (aceptación-rechazo con
    el flujo `MUNDO`; cuenta candidatos, rechazados y números usados).
  - `espacial/rejilla.py`: mapas de rocas y alimento.
  - `nucleo/contexto.py`: `ContextoPaso`, con acceso a `campos`.
  - API: `GET /api/parametros`, `POST /api/simulacion/configurar`, `GET /api/mundo`.
  - Frontend: formulario "Generar mundo" (semilla, D, rocas, fuentes), `render.js` con la
    capa estática (zona de patrulla, nido, reina y radio, rocas, fuentes con su cantidad) y leyenda.
- *Hito 2.2 — Motor*:
  - `nucleo/simulacion.py`: `Simulacion.paso()` con las fases de §10.3 en orden fijo,
    `reiniciar()`, `alimento_total()`, `resumen()`.
  - `comportamiento/`: una regla por estado, más `energia.py`, `movimiento.py`, `reina.py`
    y `transiciones.py` (valida cada cambio de estado contra la tabla).
  - `espacial/colisiones.py`: rocas y borde, nuevo `u · 360°`, estado `EVITANDO_OBSTACULO`.
  - `eventos/tipos.py` (14 tipos, códigos uint8), `eventos/prediccion.py`.
  - `estadisticas/contadores.py`: contadores que incrementan los eventos y conteo por estado.
  - `scripts/benchmark.py`.
- Pruebas: 172 en total (108 nuevas). Todas pasan en ~15 s.

**Benchmark** (esta máquina, calentamiento con `salidas_por_paso = 100`):

| Hormigas | Fuera del nido | Pasos/s | ms/paso |
|---|---|---|---|
| 1 000 | 879 | 2 318 | 0.43 |
| 5 000 | 4 537 | 689 | 1.45 |
| 20 000 | 19 376 | 212 | 4.73 |

La meta (5 000 hormigas a ≥ 30 pasos/s) se supera con margen; el envío al navegador (E3)
será el cuello de botella, no el núcleo.

**Decisiones tomadas**
- k) Semilla de `COMPORTAMIENTO` = `(semilla + 10^D/2) mod 10^D` (1 si da 0). Ej.: 5735 → 735.
- l) Zona de patrulla de la reina libre de rocas y fuentes; la reina gira hacia el nido si
  va a salir de ella (sin consumir `u`).
- Detalles aprobados con el plan: al salir, la hormiga aparece en el borde del nido; al
  llegar queda en el centro; con energía 0 va a mitad de velocidad
  (`factor_velocidad_agotada`); `ENERGIA_BAJA` sólo en `BUSCANDO` y `SIGUIENDO`;
  `distancia_minima_reina = 10`; la reina cambia de rumbo cada 50 pasos.
- `TipoEvento` pasó de `str` a `IntEnum` para guardarlo en la columna `ultimo_evento` (uint8).
- Un "cambio de dirección" es una dirección asignada por un evento (colisión, borde, fin de
  seguimiento, alimento, energía baja); no cuenta la dirección de salida ni la corrección
  continua del rumbo.
- La rejilla marca una celda si el círculo la toca (margen = media diagonal): garantiza que
  ninguna hormiga quede dentro de una roca.
- `Simulacion` acepta capacidades de registro y bitácora (las pruebas usan búferes grandes);
  `RegistroAleatorio.buscar(indice)` devuelve `None` si el número ya salió del búfer.
- Se agregaron `comportamiento/energia.py` y `comportamiento/movimiento.py` (DISENO.md §11).

**Pendientes / para E3**
- Las rutas de control (iniciar, pausar, …), el WebSocket y la capa dinámica (hormigas en
  movimiento) son de E3; hoy la simulación sólo corre desde pruebas o scripts.
- El aviso de Starlette sobre `httpx2` sigue (sin efecto).
- `PROMPTS_CLAUDE_CODE.md` sigue con la numeración vieja.

**Cómo probarlo manualmente**
1. `pytest backend/tests -q` → 172 pruebas pasan.
2. `python backend/scripts/benchmark.py` → tabla de pasos/s.
3. `uvicorn app.main:app --reload --app-dir backend`, abrir <http://127.0.0.1:8000>:
   se dibuja el mundo de la semilla 5735 (12 rocas, 4 fuentes con 2000, zona de patrulla
   punteada, nido y reina). "Generar mundo" dos veces con la misma semilla da el mismo
   dibujo; otra semilla, otro mundo; cambiar D también cambia el mundo.
4. 60 rocas y 20 fuentes no caben → mensaje de error en rojo.
