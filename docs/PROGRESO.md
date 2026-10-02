# PROGRESO.md — Bitácora por etapa

| Etapa | Estado |
|---|---|
| E0 Análisis y diseño | Terminada (pendiente de aprobación final del diseño) |
| E1 Base y generadores | Pendiente |
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
- Git no está instalado; la carpeta aún no es un repositorio.
- `PROMPTS_CLAUDE_CODE.md` sigue mencionando la numeración anterior de etapas.

**Cómo revisarlo**: leer `docs/ESPECIFICACION_v2.md` y luego `docs/DISENO.md`.
