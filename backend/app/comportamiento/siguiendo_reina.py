"""Influencia de la reina y estado SIGUIENDO_REINA (DISENO.md §10.8, decisión d).

Evento ENTRADA_RADIO_REINA: cuando una hormiga que busca comida pasa de fuera a dentro del
radio de influencia, decide **una sola vez** si sigue a la reina: variable aleatoria
**Bernoulli** con `u < p_seguir_reina` (propósito SEGUIR_REINA). Para volver a decidir
tiene que salir del radio y entrar otra vez.

Si la sigue, apunta hacia la reina durante `pasos_seguimiento` pasos. Evento
FIN_SEGUIMIENTO: al terminar vuelve a buscar con dirección u · 360°.
"""

import numpy as np

from app.aleatorio.servicio import Proposito
from app.aleatorio.variables import angulo, bernoulli
from app.comportamiento.transiciones import (
    cambiar_estado,
    nueva_direccion,
    pedir_u,
    registrar_evento,
    rumbo_hacia,
)
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso


def orientar_hacia_reina(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    reina = ctx.mundo.reina
    siguiendo = h.estado == EstadoHormiga.SIGUIENDO_REINA
    h.dir[siguiendo] = rumbo_hacia(h.x[siguiendo], h.y[siguiendo], reina.x, reina.y)


def detectar_radio_reina(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    p = ctx.parametros
    reina = ctx.mundo.reina
    moviles = h.estado != EstadoHormiga.EN_NIDO
    dentro = moviles & ((h.x - reina.x) ** 2 + (h.y - reina.y) ** 2 <= reina.radio_influencia**2)
    entraron = dentro & ~h.en_radio_reina & (h.estado == EstadoHormiga.BUSCANDO_COMIDA)

    for i in np.flatnonzero(entraron).tolist():
        u, indice = pedir_u(ctx, Proposito.SEGUIR_REINA, i)
        sigue = bernoulli(u, p.p_seguir_reina)
        ctx.estadisticas.decisiones_seguir += 1
        if sigue:
            cambiar_estado(ctx, i, EstadoHormiga.SIGUIENDO_REINA)
            h.pasos_restantes[i] = p.pasos_seguimiento
            ctx.estadisticas.seguimientos += 1
        registrar_evento(ctx, TipoEvento.ENTRADA_RADIO_REINA, i, indice,
                         u=u, p=p.p_seguir_reina, sigue=sigue)
    h.en_radio_reina[:] = dentro


def terminar_seguimientos(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    siguiendo = h.estado == EstadoHormiga.SIGUIENDO_REINA
    h.pasos_restantes[siguiendo] -= 1
    for i in np.flatnonzero(siguiendo & (h.pasos_restantes <= 0)).tolist():
        u, indice = pedir_u(ctx, Proposito.DIRECCION_FIN_SEGUIMIENTO, i)
        direccion = angulo(u)
        nueva_direccion(ctx, i, direccion)
        cambiar_estado(ctx, i, EstadoHormiga.BUSCANDO_COMIDA)
        h.pasos_restantes[i] = 0
        registrar_evento(ctx, TipoEvento.FIN_SEGUIMIENTO, i, indice, u=u, direccion=direccion)
