"""Bitácora de eventos.

Concepto de simulación: **registro de eventos**. El modelo avanza en pasos de tiempo fijo
y cada evento que ocurre dentro de un paso queda anotado con su tiempo de simulación,
la hormiga involucrada y el número pseudoaleatorio usado (si lo hubo).
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.eventos.tipos import TipoEvento

SIN_HORMIGA = -1
SIN_NUMERO = -1
CAPACIDAD_BITACORA = 10_000  # eventos que se conservan en memoria para la interfaz


@dataclass(frozen=True)
class Evento:
    """Una entrada de la bitácora."""

    tick: int
    tiempo: float
    tipo: TipoEvento
    id_hormiga: int = SIN_HORMIGA
    indice_aleatorio: int = SIN_NUMERO
    detalle: dict[str, Any] = field(default_factory=dict)


class Bitacora:
    """Búfer circular de eventos (los más viejos se descartan al llenarse)."""

    def __init__(self, capacidad: int = CAPACIDAD_BITACORA) -> None:
        self._eventos: deque[Evento] = deque(maxlen=capacidad)
        self._total = 0

    @property
    def total(self) -> int:
        """Eventos registrados desde el inicio (incluye los ya descartados)."""
        return self._total

    def registrar(self, evento: Evento) -> None:
        self._eventos.append(evento)
        self._total += 1

    def ultimos(self, limite: int) -> list[Evento]:
        """Devuelve los `limite` eventos más recientes, del más viejo al más nuevo."""
        if limite <= 0:
            return []
        return list(self._eventos)[-limite:]

    def limpiar(self) -> None:
        self._eventos.clear()
        self._total = 0
