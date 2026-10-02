"""Tipos de evento del sistema.

Concepto de simulación: **evento**, un suceso instantáneo que cambia el estado del sistema.
Los códigos numéricos se guardan en la columna `ultimo_evento` (uint8) de `Hormigas`.
"""

from enum import IntEnum


class TipoEvento(IntEnum):
    """Catálogo de eventos que se registran en la bitácora (DISENO.md §7)."""

    NINGUNO = 0
    SALIDA_NIDO = 1
    COLISION_PREVISTA = 2
    COLISION_BORDE = 3
    FIN_EVASION = 4
    ENTRADA_RADIO_REINA = 5
    FIN_SEGUIMIENTO = 6
    ENCONTRAR_ALIMENTO = 7
    FUENTE_AGOTADA = 8
    ENERGIA_BAJA = 9
    LLEGADA_NIDO = 10
    DEPOSITO_ALIMENTO = 11
    CAMBIO_RUMBO_REINA = 12
    GENERADOR_DEGENERADO = 13
