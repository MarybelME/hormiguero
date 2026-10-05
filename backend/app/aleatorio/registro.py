"""Registro de números pseudoaleatorios.

Concepto de simulación: **trazabilidad de los números pseudoaleatorios**. Cada número que
usa el modelo queda anotado con su cálculo, para quién y para qué se usó. En memoria se
guarda un búfer circular (los más recientes); el índice global nunca se reinicia
mientras dure la corrida, así que siempre se sabe cuántos números se han generado.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Any

CAPACIDAD_REGISTRO = 10_000  # entradas que se conservan en memoria para la interfaz


@dataclass(frozen=True)
class EntradaRegistro:
    """Un número pseudoaleatorio usado por el modelo."""

    indice: int          # índice global en la corrida (desde 1)
    flujo: str           # MUNDO o COMPORTAMIENTO
    generador: str       # nombre del método
    proposito: str       # para qué se usó (DIRECCION_SALIDA, SEGUIR_REINA, …)
    id_hormiga: int      # −1 si no corresponde a una hormiga
    tick: int
    tiempo: float
    u: float
    calculo: dict[str, Any] = field(default_factory=dict)  # estado interno del generador


class RegistroAleatorio:
    """Búfer circular de entradas con índice global continuo."""

    def __init__(self, capacidad: int = CAPACIDAD_REGISTRO) -> None:
        self._entradas: deque[EntradaRegistro] = deque(maxlen=capacidad)
        self._total = 0
        # Último número de cada hormiga: aunque salga del búfer, el modo didáctico puede
        # mostrar con qué número tomó su última decisión.
        self._ultimo_por_hormiga: dict[int, EntradaRegistro] = {}

    @property
    def total(self) -> int:
        """Números registrados desde el inicio (incluye los ya descartados del búfer)."""
        return self._total

    @property
    def siguiente_indice(self) -> int:
        return self._total + 1

    @property
    def primer_indice_disponible(self) -> int:
        """Índice de la entrada más vieja que sigue en memoria (total + 1 si está vacío)."""
        return self._total - len(self._entradas) + 1

    def agregar(self, entrada: EntradaRegistro) -> None:
        if entrada.indice != self.siguiente_indice:
            raise ValueError(f"se esperaba el índice {self.siguiente_indice}; llegó {entrada.indice}")
        self._entradas.append(entrada)
        self._total += 1
        if entrada.id_hormiga >= 0:
            self._ultimo_por_hormiga[entrada.id_hormiga] = entrada

    def ultimo_de(self, id_hormiga: int) -> EntradaRegistro | None:
        """El último número que usó esa hormiga (siempre disponible, aunque ya no esté en el búfer)."""
        return self._ultimo_por_hormiga.get(id_hormiga)

    def buscar(self, indice: int) -> EntradaRegistro | None:
        """La entrada con ese índice global, o None si ya salió del búfer (o no existe)."""
        primero = self.primer_indice_disponible
        if not primero <= indice <= self._total:
            return None
        return self._entradas[indice - primero]

    def pagina(self, desde: int, limite: int) -> list[EntradaRegistro]:
        """Entradas con índice ≥ `desde` que sigan en memoria; como máximo `limite`."""
        if limite <= 0:
            return []
        primero = self.primer_indice_disponible
        inicio = max(desde, primero) - primero
        fin = min(inicio + limite, len(self._entradas))
        return [self._entradas[i] for i in range(inicio, fin)]

    def limpiar(self) -> None:
        self._entradas.clear()
        self._total = 0
        self._ultimo_por_hormiga.clear()
