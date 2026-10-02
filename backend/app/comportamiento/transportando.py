"""Comportamiento en TRANSPORTANDO_COMIDA y REGRESANDO_AL_NIDO: rumbo al nido.

Las hormigas que vuelven al nido (con o sin comida) recalculan cada paso su dirección hacia
el centro del nido (vectorizado). Es un cambio continuo y determinista: no consume números.
"""

import numpy as np

from app.comportamiento.transiciones import rumbo_hacia
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso

ESTADOS_RUMBO_AL_NIDO = (EstadoHormiga.TRANSPORTANDO_COMIDA, EstadoHormiga.REGRESANDO_AL_NIDO)


def orientar_al_nido(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    nido = ctx.mundo.nido
    volviendo = np.isin(h.estado, ESTADOS_RUMBO_AL_NIDO)
    h.dir[volviendo] = rumbo_hacia(h.x[volviendo], h.y[volviendo], nido.x, nido.y)
