"""Comportamiento en el estado EN_NIDO: salida del nido.

Evento SALIDA_NIDO (DISENO.md, decisión i): en cada paso salen, como máximo,
`salidas_por_paso` hormigas, las de menor id que estén en el nido con la energía llena.
Al salir, la dirección es la **variable aleatoria** `u · 360°` (propósito DIRECCION_SALIDA)
y la hormiga aparece en el borde del nido, en esa dirección.
"""

import math

import numpy as np

from app.aleatorio.servicio import Proposito
from app.aleatorio.variables import angulo
from app.comportamiento.transiciones import cambiar_estado, pedir_u, registrar_evento
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso


def salidas_del_nido(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    nido = ctx.mundo.nido
    energia_llena = np.float32(ctx.parametros.energia_max)
    listas = np.flatnonzero((h.estado == EstadoHormiga.EN_NIDO) & (h.energia >= energia_llena))
    for i in listas[: ctx.parametros.salidas_por_paso].tolist():
        u, indice = pedir_u(ctx, Proposito.DIRECCION_SALIDA, i)
        direccion = angulo(u)
        h.dir[i] = direccion  # dirección inicial: no cuenta como cambio de dirección
        h.x[i] = nido.x + nido.radio * math.cos(math.radians(direccion))
        h.y[i] = nido.y + nido.radio * math.sin(math.radians(direccion))
        cambiar_estado(ctx, i, EstadoHormiga.BUSCANDO_COMIDA)
        ctx.estadisticas.salidas += 1
        registrar_evento(ctx, TipoEvento.SALIDA_NIDO, i, indice, u=u, direccion=direccion)
