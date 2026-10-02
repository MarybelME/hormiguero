# PROGRESO.md — Bitácora por etapa

| Etapa | Estado |
|---|---|
| E0 Análisis y diseño | Terminada |
| E1 Base y generadores | Terminada (pendiente de revisión) |
| E2 Modelo y motor | Pendiente |
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
