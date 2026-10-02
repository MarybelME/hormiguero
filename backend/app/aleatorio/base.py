"""Interfaz común de los generadores de números pseudoaleatorios.

Concepto de simulación: **generador de números pseudoaleatorios**, un algoritmo
determinista que, a partir de una semilla, produce una sucesión de números en [0, 1)
que se comporta "como si" fuera aleatoria. Misma semilla ⇒ misma sucesión.

Cualquier generador nuevo (congruencial lineal, multiplicativo, NumPy de referencia)
sólo debe implementar esta interfaz; el modelo no cambia.
"""

from abc import ABC, abstractmethod
from typing import Any


class GeneradorPseudoaleatorio(ABC):
    """Contrato que cumplen todos los generadores del simulador."""

    @property
    @abstractmethod
    def nombre(self) -> str:
        """Nombre del método, para mostrarlo en la interfaz y en el registro."""

    @property
    @abstractmethod
    def semilla(self) -> int:
        """Semilla original con la que se configuró el generador."""

    @abstractmethod
    def siguiente(self) -> float:
        """Produce el siguiente número u en [0, 1)."""

    @abstractmethod
    def reiniciar(self) -> None:
        """Vuelve al estado inicial: la sucesión se repite desde el primer número."""

    @abstractmethod
    def estado_interno(self) -> dict[str, Any]:
        """Detalle del último cálculo, para mostrarlo paso a paso."""

    @abstractmethod
    def degenerado(self) -> bool:
        """True si el último número producido reveló una degeneración (cero o ciclo)."""
