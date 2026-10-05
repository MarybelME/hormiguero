"""Generador de referencia de NumPy (PCG64).

Concepto de simulación: **generador de referencia**. Es un generador moderno, de periodo
2^128 y con buenas propiedades estadísticas, contra el que se comparan los métodos
clásicos. Para el estudiante es una "caja negra": no se muestra su cálculo interno, sólo el
número que produce.

Es la única excepción a la regla "no usar numpy.random" (CLAUDE.md §6): se usa detrás de la
misma interfaz, con semilla configurada y con cada número registrado como cualquier otro.
La prueba de independencia del núcleo verifica que ningún otro archivo lo importe.
"""

from typing import Any

import numpy as np

from app.aleatorio.base import GeneradorPseudoaleatorio

METODO = "numpy"
ALGORITMO = "PCG64"
MODULO_SEMILLA = 2**32  # escala de la semilla (para la regla de la semilla de COMPORTAMIENTO)


def validar_numpy(semilla: int) -> None:
    if not 1 <= semilla < MODULO_SEMILLA:
        raise ValueError(f"la semilla debe cumplir 1 ≤ semilla < 2^32; se recibió {semilla}")


class GeneradorNumpy(GeneradorPseudoaleatorio):
    """Envuelve numpy.random.Generator(PCG64(semilla))."""

    def __init__(self, semilla: int) -> None:
        validar_numpy(semilla)
        self._semilla = semilla
        self.reiniciar()

    @property
    def nombre(self) -> str:
        return f"NumPy ({ALGORITMO}, referencia)"

    @property
    def semilla(self) -> int:
        return self._semilla

    @property
    def modulo(self) -> int:
        return MODULO_SEMILLA

    def reiniciar(self) -> None:
        self._generador = np.random.Generator(np.random.PCG64(self._semilla))
        self._indice = 0
        self._u: float | None = None

    def siguiente(self) -> float:
        self._indice += 1
        self._u = float(self._generador.random())
        return self._u

    def estado_interno(self) -> dict[str, Any]:
        return {"metodo": METODO, "algoritmo": ALGORITMO, "indice": self._indice,
                "u": self._u, "degeneracion": None}

    def degenerado(self) -> bool:
        return False
