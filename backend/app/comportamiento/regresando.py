"""Llegada al nido (DISENO.md §10.7).

Evento LLEGADA_NIDO: una hormiga que transporta comida o regresa entra en el radio del nido;
pasa a EN_NIDO y queda en el centro (no se dibuja).
Evento DEPOSITO_ALIMENTO: si traía carga, el nido la almacena.
"""

import numpy as np

from app.comportamiento.transiciones import cambiar_estado, registrar_evento
from app.comportamiento.transportando import ESTADOS_RUMBO_AL_NIDO
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso


def detectar_llegada_nido(ctx: ContextoPaso) -> None:
    h = ctx.hormigas
    nido = ctx.mundo.nido
    dentro = (h.x - nido.x) ** 2 + (h.y - nido.y) ** 2 <= nido.radio**2
    llegaron = np.flatnonzero(np.isin(h.estado, ESTADOS_RUMBO_AL_NIDO) & dentro)
    for i in llegaron.tolist():
        carga = int(h.carga[i])
        if carga > 0:
            nido.alimento_almacenado += carga
            h.carga[i] = 0
            ctx.estadisticas.alimento_recolectado += carga
            registrar_evento(ctx, TipoEvento.DEPOSITO_ALIMENTO, i, cantidad=carga)
        cambiar_estado(ctx, i, EstadoHormiga.EN_NIDO)
        h.x[i], h.y[i] = nido.x, nido.y
        h.pasos_restantes[i] = 0
        h.en_radio_reina[i] = False
        ctx.estadisticas.llegadas_nido += 1
        registrar_evento(ctx, TipoEvento.LLEGADA_NIDO, i)
