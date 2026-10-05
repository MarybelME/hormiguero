"""Generadores congruenciales (lineal y multiplicativo).

Concepto de simulación: **generador de números pseudoaleatorios** por congruencias, el
método más usado en la práctica durante décadas:

    lineal:          x_{i+1} = (a · x_i + c) mod m        u = x_{i+1} / m
    multiplicativo:  x_{i+1} = (a · x_i)     mod m        (el caso c = 0)

Periodo y degeneración. Se exige mcd(a, m) = 1: así la fórmula es una biyección de
[0, m) en sí mismo y la sucesión es un ciclo puro, que vuelve a la semilla antes de repetir
cualquier otro estado. "Degenerar" aquí significa **completar el periodo**: desde ese
número la sucesión se repetiría idéntica. Se detecta en O(1) (el estado vuelve a la
semilla), se informa la longitud del periodo y se re-siembra con la misma regla visible de
cuadrados medios (DISENO.md, decisiones a y r). Con buenos parámetros (teorema de
Hull-Dobell para el lineal; raíz primitiva y m primo para el multiplicativo) el periodo
es enorme; con malos, se ve degenerar en pocos números.
"""

from dataclasses import asdict, dataclass
from math import gcd
from typing import Any

from app.aleatorio.base import (
    PASO_RESIEMBRA,
    Degeneracion,
    GeneradorPseudoaleatorio,
    TipoDegeneracion,
    calcular_resiembra,
)

METODO_LINEAL = "congruencial_lineal"
METODO_MULTIPLICATIVO = "congruencial_multiplicativo"
MODULO_MINIMO = 3  # con menos estados no siempre existe una semilla de re-siembra distinta


@dataclass(frozen=True)
class PasoCongruencial:
    """Cálculo completo de un número: x_i → a·x_i + c → mod m → u."""

    indice: int        # posición en la sucesión de este generador (desde 1)
    previo: int        # x_i
    producto: int      # a · x_i + c (antes de reducir módulo m)
    x: int             # x_{i+1} = producto mod m (antes de una posible re-siembra)
    u: float
    degeneracion: Degeneracion | None


def validar_congruencial(semilla: int, a: int, c: int, m: int) -> None:
    """Lanza ValueError si los parámetros no forman un generador válido."""
    if m < MODULO_MINIMO:
        raise ValueError(f"el módulo m debe ser al menos {MODULO_MINIMO}; se recibió {m}")
    if m % PASO_RESIEMBRA == 0:
        raise ValueError(
            f"m no puede ser múltiplo de {PASO_RESIEMBRA}: la regla de re-siembra "
            f"(semilla + k · {PASO_RESIEMBRA}) mod m daría siempre la misma semilla")
    if not 1 <= a < m:
        raise ValueError(f"el multiplicador debe cumplir 1 ≤ a < m; se recibió a = {a}, m = {m}")
    if not 0 <= c < m:
        raise ValueError(f"el incremento debe cumplir 0 ≤ c < m; se recibió c = {c}, m = {m}")
    if gcd(a, m) != 1:
        raise ValueError(
            f"a y m deben ser primos entre sí (mcd({a}, {m}) = {gcd(a, m)}); si no, el "
            "generador pierde estados y puede caer en un ciclo que no pasa por la semilla")
    if not 1 <= semilla < m:
        raise ValueError(f"la semilla debe cumplir 1 ≤ semilla < m = {m}; se recibió {semilla}")


class GeneradorCongruencial(GeneradorPseudoaleatorio):
    """Congruencial lineal; con c = 0 es el congruencial multiplicativo."""

    def __init__(self, semilla: int, a: int, c: int, m: int) -> None:
        validar_congruencial(semilla, a, c, m)
        self._semilla = semilla
        self._a = a
        self._c = c
        self._m = m
        self.reiniciar()

    # --- Interfaz GeneradorPseudoaleatorio ---------------------------------------------

    @property
    def nombre(self) -> str:
        return "Congruencial lineal"

    @property
    def metodo(self) -> str:
        return METODO_LINEAL

    @property
    def semilla(self) -> int:
        return self._semilla

    @property
    def modulo(self) -> int:
        return self._m

    @property
    def resiembras(self) -> int:
        return self._resiembras

    @property
    def ultimo_paso(self) -> PasoCongruencial | None:
        return self._ultimo

    def reiniciar(self) -> None:
        self._x = self._semilla
        self._inicio_ciclo = self._semilla  # semilla actual: el ciclo se completa al volver a ella
        self._indice_inicio = 0
        self._indice = 0
        self._k = 0
        self._resiembras = 0
        self._ultimo: PasoCongruencial | None = None

    def siguiente(self) -> float:
        return self.siguiente_paso().u

    def estado_interno(self) -> dict[str, Any]:
        datos: dict[str, Any] = {
            "metodo": self.metodo, "estado_actual": self._x,
            "a": self._a, "c": self._c, "m": self._m,
        }
        if self._ultimo is not None:
            datos.update(asdict(self._ultimo))
        return datos

    def degenerado(self) -> bool:
        return self._ultimo is not None and self._ultimo.degeneracion is not None

    # --- Cálculo ------------------------------------------------------------------------

    def siguiente_paso(self) -> PasoCongruencial:
        """Produce un número y devuelve su cálculo completo."""
        previo = self._x
        producto = self._a * previo + self._c
        x = producto % self._m
        self._indice += 1

        degeneracion = None
        if x == self._inicio_ciclo:
            degeneracion = self._degeneracion(x)
            self._resembrar(degeneracion)
        else:
            self._x = x

        self._ultimo = PasoCongruencial(
            indice=self._indice, previo=previo, producto=producto, x=x,
            u=x / self._m, degeneracion=degeneracion,
        )
        return self._ultimo

    def _degeneracion(self, x: int) -> Degeneracion:
        """El estado volvió a la semilla: se completó el periodo."""
        k, semilla_nueva = calcular_resiembra(self._semilla, self._k, self._m, estado_degenerado=x)
        return Degeneracion(TipoDegeneracion.CICLO, x, self._indice - self._indice_inicio, k, semilla_nueva)

    def _resembrar(self, degeneracion: Degeneracion) -> None:
        self._k = degeneracion.numero_resiembra
        self._x = self._inicio_ciclo = degeneracion.semilla_nueva
        self._indice_inicio = self._indice
        self._resiembras += 1


class GeneradorCongruencialMultiplicativo(GeneradorCongruencial):
    """x_{i+1} = (a · x_i) mod m: el congruencial sin incremento (c = 0)."""

    def __init__(self, semilla: int, a: int, m: int) -> None:
        super().__init__(semilla, a, 0, m)

    @property
    def nombre(self) -> str:
        return "Congruencial multiplicativo"

    @property
    def metodo(self) -> str:
        return METODO_MULTIPLICATIVO
