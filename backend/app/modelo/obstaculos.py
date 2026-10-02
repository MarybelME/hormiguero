"""Rocas.

Concepto de simulación: **restricción**. Zonas circulares que las obreras no pueden
atravesar; al encontrarlas cambian de dirección con un número pseudoaleatorio.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Obstaculo:
    id: int
    x: float
    y: float
    radio: float
