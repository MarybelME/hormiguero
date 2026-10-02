"""Fuentes de alimento.

Concepto de simulación: **recurso consumible y finito**. Cada fuente tiene una cantidad
entera; las obreras la consumen y, al llegar a 0, se agota y deja de atraerlas.
"""

from dataclasses import dataclass


@dataclass
class FuenteAlimento:
    id: int
    x: float
    y: float
    radio: float
    cantidad_inicial: int
    cantidad: int

    @property
    def agotada(self) -> bool:
        return self.cantidad == 0
