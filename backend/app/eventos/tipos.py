"""Tipos de evento del sistema.

Concepto de simulación: **evento**, un suceso instantáneo que cambia el estado del sistema.
En la etapa E1 sólo existe la degeneración del generador; los eventos de las hormigas
(salir del nido, colisión, encontrar alimento, …) se agregan en la etapa E2.
"""

from enum import Enum


class TipoEvento(str, Enum):
    """Catálogo de eventos que se registran en la bitácora."""

    GENERADOR_DEGENERADO = "GENERADOR_DEGENERADO"
