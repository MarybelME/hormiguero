"""Comportamiento en el estado BUSCANDO_COMIDA: encontrar alimento.

Sin feromonas, buscar es avanzar en línea recta y cambiar de dirección sólo al chocar.
En la etapa E4 esta regla consultará `ctx.campos["feromonas"]`.

Evento ENCONTRAR_ALIMENTO (DISENO.md §10.6): una hormiga que busca y está sobre una fuente
con alimento recoge `min(capacidad_carga, disponible)` unidades, cambia a
TRANSPORTANDO_COMIDA y orienta su dirección hacia el nido. Si varias llegan en el mismo
paso se atienden en orden de id. Si la fuente queda en 0 ocurre FUENTE_AGOTADA.
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


def detectar_alimento(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    mundo = ctx.mundo
    fuente_bajo = mundo.rejilla.fuente_en(h.x, h.y)
    llegaron = np.flatnonzero((h.estado == EstadoHormiga.BUSCANDO_COMIDA) & (fuente_bajo >= 0))
    for i in llegaron.tolist():
        fuente = mundo.fuentes[int(fuente_bajo[i])]
        cantidad = min(ctx.parametros.capacidad_carga, fuente.cantidad)
        if cantidad == 0:
            ctx.estadisticas.llegadas_sin_alimento += 1
            continue
        fuente.cantidad -= cantidad
        h.carga[i] = cantidad
        cambiar_estado(ctx, i, EstadoHormiga.TRANSPORTANDO_COMIDA)
        nido = mundo.nido
        nueva_direccion(ctx, i, rumbo_hacia_punto(float(h.x[i]), float(h.y[i]), nido.x, nido.y))
        registrar_evento(ctx, TipoEvento.ENCONTRAR_ALIMENTO, i, fuente=fuente.id,
                         cantidad=cantidad, restante=fuente.cantidad)
        if fuente.agotada:
            _agotar(ctx, fuente.id)


def _agotar(ctx: ContextoPaso, id_fuente: int) -> None:
    ctx.mundo.rejilla.borrar_fuente(id_fuente)
    ctx.mundo.version_estatica += 1
    ctx.estadisticas.fuentes_agotadas += 1
    registrar_evento(ctx, TipoEvento.FUENTE_AGOTADA, fuente=id_fuente)
