"""Estados de las entidades y transiciones permitidas.

Concepto de simulación: **máquina de estados de una entidad**. El estado de una obrera sólo
cambia por eventos, y sólo entre los pares de esta tabla (DISENO.md §3). El motor valida
cada cambio contra ella.

Los códigos numéricos son parte del protocolo con el frontend: no se cambian sin actualizar
`api/protocolo.py`, `frontend/js/protocolo.js` y `docs/DISENO.md`.
"""

from enum import IntEnum

import numpy as np


class EstadoHormiga(IntEnum):
    EN_NIDO = 0
    BUSCANDO_COMIDA = 1
    SIGUIENDO_REINA = 2
    EVITANDO_OBSTACULO = 3
    TRANSPORTANDO_COMIDA = 4
    REGRESANDO_AL_NIDO = 5


class EstadoReina(IntEnum):
    EN_NIDO = 0
    PATRULLANDO = 1


_E = EstadoHormiga

TRANSICIONES_PERMITIDAS: dict[EstadoHormiga, frozenset[EstadoHormiga]] = {
    _E.EN_NIDO: frozenset({_E.BUSCANDO_COMIDA}),
    _E.BUSCANDO_COMIDA: frozenset({
        _E.EVITANDO_OBSTACULO, _E.SIGUIENDO_REINA, _E.TRANSPORTANDO_COMIDA, _E.REGRESANDO_AL_NIDO,
    }),
    _E.SIGUIENDO_REINA: frozenset({_E.BUSCANDO_COMIDA, _E.EVITANDO_OBSTACULO, _E.REGRESANDO_AL_NIDO}),
    _E.EVITANDO_OBSTACULO: frozenset({
        _E.BUSCANDO_COMIDA, _E.TRANSPORTANDO_COMIDA, _E.REGRESANDO_AL_NIDO, _E.EVITANDO_OBSTACULO,
    }),
    _E.TRANSPORTANDO_COMIDA: frozenset({_E.EVITANDO_OBSTACULO, _E.EN_NIDO}),
    _E.REGRESANDO_AL_NIDO: frozenset({_E.EVITANDO_OBSTACULO, _E.EN_NIDO}),
}

# Misma tabla como matriz booleana [origen, destino], útil para comprobaciones vectorizadas.
MATRIZ_TRANSICIONES = np.zeros((len(EstadoHormiga), len(EstadoHormiga)), dtype=np.bool_)
for _origen, _destinos in TRANSICIONES_PERMITIDAS.items():
    for _destino in _destinos:
        MATRIZ_TRANSICIONES[_origen, _destino] = True


class TransicionInvalida(RuntimeError):
    """El motor intentó un cambio de estado que no está en la tabla."""


def transicion_valida(origen: int, destino: int) -> bool:
    return bool(MATRIZ_TRANSICIONES[origen, destino])
