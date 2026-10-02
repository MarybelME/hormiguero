"""Comportamiento en EVITANDO_OBSTACULO: fin de la evasión.

La hormiga entra a este estado al chocar (ver `espacial/colisiones.py`) y avanza
`pasos_evasion` pasos en la nueva dirección. Evento FIN_EVASION: vuelve al estado que tenía
antes del choque; si seguía a la reina, la pierde y vuelve a BUSCANDO_COMIDA. Una hormiga
que iba al nido recupera el rumbo en el paso siguiente (sin consumir números).
"""

import numpy as np

from app.comportamiento.transiciones import cambiar_estado, registrar_evento
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso


def estado_tras_evasion(estado_previo: int) -> EstadoHormiga:
    if estado_previo == EstadoHormiga.SIGUIENDO_REINA:
        return EstadoHormiga.BUSCANDO_COMIDA
    return EstadoHormiga(estado_previo)


def terminar_evasiones(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    evitando = h.estado == EstadoHormiga.EVITANDO_OBSTACULO
    h.pasos_restantes[evitando] -= 1
    for i in np.flatnonzero(evitando & (h.pasos_restantes <= 0)).tolist():
        destino = estado_tras_evasion(int(h.estado_previo[i]))
        cambiar_estado(ctx, i, destino)
        h.pasos_restantes[i] = 0
        registrar_evento(ctx, TipoEvento.FIN_EVASION, i, estado_restaurado=destino.name)
