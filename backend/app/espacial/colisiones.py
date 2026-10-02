"""Detección y resolución de colisiones (DISENO.md §10.5, decisión f).

Evento COLISION_PREVISTA / COLISION_BORDE: si la posición siguiente de una hormiga cae en
una celda ocupada por una roca o fuera del mundo:
1. se detecta la colisión (antes de moverse: la hormiga no avanza en este paso);
2. se pide un nuevo número pseudoaleatorio u;
3. la nueva dirección es u · 360°;
4. la hormiga pasa a EVITANDO_OBSTACULO durante `pasos_evasion` pasos y sigue moviéndose.
"""

import numpy as np

from app.aleatorio.servicio import Proposito
from app.aleatorio.variables import angulo
from app.comportamiento.transiciones import (
    cambiar_estado,
    nueva_direccion,
    pedir_u,
    registrar_evento,
)
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso


def _borde_cruzado(x: float, y: float, ancho: float, alto: float) -> str:
    if x < 0:
        return "oeste"
    if x >= ancho:
        return "este"
    return "sur" if y < 0 else "norte"


def resolver_colisiones(
    ctx: ContextoPaso, moviles: np.ndarray, x_nueva: np.ndarray, y_nueva: np.ndarray
) -> np.ndarray:
    """Procesa las colisiones (en orden de id) y devuelve la máscara de bloqueadas."""
    mundo = ctx.mundo
    h = ctx.hormigas
    fuera = (x_nueva < 0) | (x_nueva >= mundo.ancho) | (y_nueva < 0) | (y_nueva >= mundo.alto)
    roca = np.where(fuera, -1, mundo.rejilla.obstaculo_en(x_nueva, y_nueva))
    bloqueadas = moviles & (fuera | (roca >= 0))

    for i in np.flatnonzero(bloqueadas).tolist():
        es_borde = bool(fuera[i])
        proposito = Proposito.DIRECCION_BORDE if es_borde else Proposito.DIRECCION_COLISION
        u, indice = pedir_u(ctx, proposito, i)
        anterior = float(h.dir[i])
        direccion = angulo(u)
        nueva_direccion(ctx, i, direccion)
        if h.estado[i] != EstadoHormiga.EVITANDO_OBSTACULO:
            h.estado_previo[i] = h.estado[i]
        cambiar_estado(ctx, i, EstadoHormiga.EVITANDO_OBSTACULO)
        h.pasos_restantes[i] = ctx.parametros.pasos_evasion

        if es_borde:
            ctx.estadisticas.colisiones_borde += 1
            borde = _borde_cruzado(float(x_nueva[i]), float(y_nueva[i]), mundo.ancho, mundo.alto)
            registrar_evento(ctx, TipoEvento.COLISION_BORDE, i, indice, borde=borde, u=u,
                             direccion_anterior=anterior, direccion=direccion)
        else:
            ctx.estadisticas.colisiones += 1
            registrar_evento(ctx, TipoEvento.COLISION_PREVISTA, i, indice, roca=int(roca[i]), u=u,
                             direccion_anterior=anterior, direccion=direccion)
    return bloqueadas
