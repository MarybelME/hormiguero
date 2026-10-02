"""Energía de las obreras (DISENO.md, decisión e).

- Fuera del nido la energía baja `consumo_energia` por paso, sin pasar de 0.
- En el nido sube `recuperacion_energia` por paso, sin pasar de `energia_max`.
- Evento ENERGIA_BAJA: una hormiga que busca comida o sigue a la reina y queda por debajo
  de `umbral_regreso` pasa a REGRESANDO_AL_NIDO. Las que ya van al nido siguen su camino.
- No hay muerte: con energía 0 se mueve más lento (`factor_velocidad_agotada`).
"""

import numpy as np

from app.comportamiento.transiciones import (
    cambiar_estado,
    nueva_direccion,
    registrar_evento,
    rumbo_hacia_punto,
)
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso

ESTADOS_QUE_VIGILAN_ENERGIA = (EstadoHormiga.BUSCANDO_COMIDA, EstadoHormiga.SIGUIENDO_REINA)


def actualizar_energia(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    p = ctx.parametros
    en_nido = h.estado == EstadoHormiga.EN_NIDO
    fuera = ~en_nido
    h.energia[fuera] = np.maximum(h.energia[fuera] - np.float32(p.consumo_energia), np.float32(0))
    h.energia[en_nido] = np.minimum(
        h.energia[en_nido] + np.float32(p.recuperacion_energia), np.float32(p.energia_max)
    )

    vigilan = np.isin(h.estado, ESTADOS_QUE_VIGILAN_ENERGIA)
    nido = ctx.mundo.nido
    for i in np.flatnonzero(vigilan & (h.energia < np.float32(p.umbral_regreso))).tolist():
        cambiar_estado(ctx, i, EstadoHormiga.REGRESANDO_AL_NIDO)
        nueva_direccion(ctx, i, rumbo_hacia_punto(float(h.x[i]), float(h.y[i]), nido.x, nido.y))
        registrar_evento(ctx, TipoEvento.ENERGIA_BAJA, i, energia=float(h.energia[i]))
