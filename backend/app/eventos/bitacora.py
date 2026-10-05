"""Bitácora de eventos.

Concepto de simulación: **registro de eventos**. El modelo avanza en pasos de tiempo fijo
y cada evento que ocurre dentro de un paso queda anotado con su tiempo de simulación,
la hormiga involucrada y el número pseudoaleatorio usado (si lo hubo).
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.eventos.tipos import TipoEvento

SIN_HORMIGA = -1
SIN_NUMERO = -1
CAPACIDAD_BITACORA = 10_000  # eventos que se conservan en memoria para la interfaz
EVENTOS_POR_HORMIGA = 50     # historia propia de cada hormiga, para seguirla en el modo didáctico


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
    """Búfer circular de eventos (los más viejos se descartan al llenarse).

    Además guarda los últimos eventos de cada hormiga: con miles de hormigas el búfer
    general cubre pocos pasos, pero la historia reciente de la hormiga seleccionada debe
    seguir disponible.
    """

    def __init__(self, capacidad: int = CAPACIDAD_BITACORA,
                 al_registrar: Callable[[Evento], None] | None = None) -> None:
        self._eventos: deque[Evento] = deque(maxlen=capacidad)
        self._al_registrar = al_registrar  # aviso opcional (p. ej. para exportar a CSV)
        self._por_hormiga: dict[int, deque[Evento]] = {}
        self._total = 0

    @property
    def total(self) -> int:
        """Eventos registrados desde el inicio (incluye los ya descartados)."""
        return self._total

    def registrar(self, evento: Evento) -> None:
        self._eventos.append(evento)
        self._total += 1
        if evento.id_hormiga != SIN_HORMIGA:
            historia = self._por_hormiga.get(evento.id_hormiga)
            if historia is None:
                historia = self._por_hormiga[evento.id_hormiga] = deque(maxlen=EVENTOS_POR_HORMIGA)
            historia.append(evento)
        if self._al_registrar is not None:
            self._al_registrar(evento)

    def ultimos(self, limite: int) -> list[Evento]:
        """Devuelve los `limite` eventos más recientes, del más viejo al más nuevo."""
        if limite <= 0:
            return []
        return list(self._eventos)[-limite:]

    def filtrar(
        self,
        limite: int,
        id_hormiga: int | None = None,
        tipo: TipoEvento | None = None,
    ) -> list[Evento]:
        """Los `limite` eventos más recientes de esa hormiga y/o tipo, del más viejo al más nuevo.

        Al filtrar por hormiga se usa su historia propia (sus últimos EVENTOS_POR_HORMIGA).
        """
        fuente = self._eventos if id_hormiga is None else self._por_hormiga.get(id_hormiga, ())
        encontrados: list[Evento] = []
        for evento in reversed(fuente):
            if len(encontrados) >= limite:
                break
            if id_hormiga is not None and evento.id_hormiga != id_hormiga:
                continue
            if tipo is not None and evento.tipo != tipo:
                continue
            encontrados.append(evento)
        encontrados.reverse()
        return encontrados

    def limpiar(self) -> None:
        self._eventos.clear()
        self._por_hormiga.clear()
        self._total = 0
