"""Nido.

Concepto de simulación: **parte del sistema / punto de servicio**. Las obreras salen de
aquí, depositan el alimento y recuperan energía. Se puede ver como un servidor sin cola
(capacidad ilimitada).
"""

from dataclasses import dataclass


@dataclass
class Nido:
    x: float
    y: float
    radio: float
    alimento_almacenado: int = 0  # variable de estado del sistema (entera: conservación exacta)

    def contiene(self, x: float, y: float) -> bool:
        return (x - self.x) ** 2 + (y - self.y) ** 2 <= self.radio**2
