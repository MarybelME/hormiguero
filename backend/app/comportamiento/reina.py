"""Comportamiento de la reina: patrulla aleatoria lenta (DISENO.md, decisiones h y l).

Evento CAMBIO_RUMBO_REINA: cada `pasos_rumbo_reina` pasos la reina toma la dirección
u · 360° (propósito MOVIMIENTO_REINA): la misma fuente de números mueve a otra entidad.
Si su siguiente posición saliera de la zona de patrulla, gira hacia el nido (determinista,
sin consumir números). La zona de patrulla no tiene rocas, así que la reina no choca.
"""

import math

from app.aleatorio.servicio import Proposito
from app.aleatorio.variables import angulo
from app.comportamiento.transiciones import registrar_evento, rumbo_hacia_punto
from app.eventos.tipos import TipoEvento
from app.nucleo.contexto import ContextoPaso


def _siguiente(x: float, y: float, direccion: float, avance: float) -> tuple[float, float]:
    radianes = math.radians(direccion)
    return x + avance * math.cos(radianes), y + avance * math.sin(radianes)


def mover_reina(ctx: ContextoPaso) -> None:
    reina = ctx.mundo.reina
    nido = ctx.mundo.nido

    reina.pasos_para_rumbo -= 1
    if reina.pasos_para_rumbo <= 0:
        u = ctx.aleatorio.obtener(Proposito.MOVIMIENTO_REINA)
        reina.dir = angulo(u)
        reina.pasos_para_rumbo = ctx.parametros.pasos_rumbo_reina
        registrar_evento(ctx, TipoEvento.CAMBIO_RUMBO_REINA, indice_u=ctx.aleatorio.ultimo_indice,
                         u=u, direccion=reina.dir)

    avance = reina.vel * ctx.dt
    x, y = _siguiente(reina.x, reina.y, reina.dir, avance)
    if math.dist((x, y), (nido.x, nido.y)) > reina.radio_patrulla:
        reina.dir = rumbo_hacia_punto(reina.x, reina.y, nido.x, nido.y)
        x, y = _siguiente(reina.x, reina.y, reina.dir, avance)
    reina.x, reina.y = x, y
