"""Interfaz común de los generadores de números pseudoaleatorios.

Concepto de simulación: **generador de números pseudoaleatorios**, un algoritmo
determinista que, a partir de una semilla, produce una sucesión de números en [0, 1)
que se comporta "como si" fuera aleatoria. Misma semilla ⇒ misma sucesión.

Cualquier generador nuevo (congruencial lineal, multiplicativo, NumPy de referencia)
sólo debe implementar esta interfaz; el modelo no cambia.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

PASO_RESIEMBRA = 7919  # número primo: desplaza la semilla lejos de la anterior


class TipoDegeneracion(str, Enum):
    """Formas en que un generador deja de servir."""

    CERO = "CERO"    # cayó en 0: desde ahí sólo produciría ceros
    CICLO = "CICLO"  # repitió un estado: desde ahí repetiría la misma sucesión


@dataclass(frozen=True)
class Degeneracion:
    """Qué degeneró y cómo se corrigió."""

    tipo: TipoDegeneracion
    estado: int                 # valor de x que reveló la degeneración
    longitud_ciclo: int | None  # sólo para CICLO
    numero_resiembra: int       # k usado en la fórmula
    semilla_nueva: int


def calcular_resiembra(semilla_original: int, k_anterior: int, modulo: int,
                       estado_degenerado: int) -> tuple[int, int]:
    """Regla de re-siembra visible (DISENO.md, decisión a), común a todos los generadores:

        nueva_semilla = (semilla_original + k · PASO_RESIEMBRA) mod m

    con el primer k > k_anterior cuyo resultado no sea 0 ni el estado que degeneró.
    Devuelve (k, nueva_semilla).
    """
    for k in range(k_anterior + 1, k_anterior + 1 + 2 * modulo):
        nueva = (semilla_original + k * PASO_RESIEMBRA) % modulo
        if nueva not in (0, estado_degenerado):
            return k, nueva
    raise ValueError(f"no hay semilla de re-siembra válida con módulo {modulo}")


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

    @property
    @abstractmethod
    def modulo(self) -> int:
        """Cantidad de estados posibles m: el estado vive en [0, m). Da la escala de la semilla."""

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

    @property
    def resiembras(self) -> int:
        """Veces que se re-sembró desde el inicio (0 si el método nunca degenera)."""
        return 0
