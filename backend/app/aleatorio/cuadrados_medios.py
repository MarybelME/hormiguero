"""Generador de cuadrados medios (von Neumann).

Concepto de simulación: **generador de números pseudoaleatorios**. Es el método histórico
más sencillo y también uno de los peores: degenera rápido (cae en 0 o en ciclos cortos).
Esa degeneración es contenido de clase, por eso aquí se **detecta, se registra y se
corrige de forma visible**, nunca en silencio.

Algoritmo (D dígitos, D par):
    cuadrado  = x · x
    relleno   = cuadrado con ceros a la izquierda hasta 2D dígitos
    centrales = los D dígitos del centro de `relleno`
    x         = entero(centrales)
    u         = x / 10^D

Política ante la degeneración (DISENO.md, decisión a): el número degenerado se entrega
y se marca; luego se re-siembra con

    nueva_semilla = (semilla_original + k · PASO_RESIEMBRA) mod 10^D

donde k es el número de re-siembra. Si el resultado es 0 o el mismo estado que degeneró,
se pasa a k + 1. Tras re-sembrar empieza una sucesión nueva, así que se olvidan los
estados vistos.
"""

from dataclasses import asdict, dataclass
from typing import Any

from app.aleatorio.base import (
    PASO_RESIEMBRA,
    Degeneracion,
    GeneradorPseudoaleatorio,
    TipoDegeneracion,
    calcular_resiembra,
)

__all__ = [
    "DIGITOS_PERMITIDOS", "DIGITOS_POR_DEFECTO", "PASO_RESIEMBRA", "Degeneracion",
    "GeneradorCuadradosMedios", "PasoCuadradosMedios", "TipoDegeneracion",
    "calcular_centrales", "validar_configuracion",
]

METODO = "cuadrados_medios"
DIGITOS_PERMITIDOS = (4, 6, 8)
DIGITOS_POR_DEFECTO = 4


@dataclass(frozen=True)
class PasoCuadradosMedios:
    """Cálculo completo de un número, tal como se muestra en la tabla didáctica."""

    indice: int        # posición en la sucesión de este generador (desde 1)
    previo: int        # x antes del cálculo
    cuadrado: int
    relleno: str
    centrales: str
    x: int             # nuevo estado (antes de una posible re-siembra)
    u: float
    degeneracion: Degeneracion | None


def validar_configuracion(semilla: int, digitos: int) -> None:
    """Lanza ValueError si la semilla o la cantidad de dígitos no son válidas."""
    if digitos not in DIGITOS_PERMITIDOS:
        raise ValueError(f"digitos debe ser uno de {DIGITOS_PERMITIDOS}; se recibió {digitos}")
    if not 1 <= semilla < 10**digitos:
        raise ValueError(f"la semilla debe cumplir 1 ≤ semilla < 10^{digitos}; se recibió {semilla}")


def calcular_centrales(x: int, digitos: int) -> tuple[int, str, str]:
    """Un paso del método sin estado: devuelve (cuadrado, relleno, centrales)."""
    cuadrado = x * x
    relleno = str(cuadrado).zfill(2 * digitos)
    inicio = digitos // 2
    return cuadrado, relleno, relleno[inicio:inicio + digitos]


class GeneradorCuadradosMedios(GeneradorPseudoaleatorio):
    """Cuadrados medios con detección de degeneración y re-siembra visible."""

    def __init__(self, semilla: int, digitos: int = DIGITOS_POR_DEFECTO) -> None:
        validar_configuracion(semilla, digitos)
        self._semilla = semilla
        self._digitos = digitos
        self._modulo = 10**digitos
        self.reiniciar()

    # --- Interfaz GeneradorPseudoaleatorio ---------------------------------------------

    @property
    def nombre(self) -> str:
        return "Cuadrados medios"

    @property
    def semilla(self) -> int:
        return self._semilla

    @property
    def digitos(self) -> int:
        return self._digitos

    @property
    def modulo(self) -> int:
        """10^D: los estados posibles van de 0 a 10^D − 1."""
        return self._modulo

    @property
    def resiembras(self) -> int:
        """Cuántas veces se ha re-sembrado desde el inicio."""
        return self._resiembras

    @property
    def ultimo_paso(self) -> PasoCuadradosMedios | None:
        return self._ultimo

    def reiniciar(self) -> None:
        self._x = self._semilla
        self._indice = 0
        self._k = 0
        self._resiembras = 0
        self._vistos: dict[int, int] = {self._semilla: 0}  # estado → índice donde apareció
        self._ultimo: PasoCuadradosMedios | None = None

    def siguiente(self) -> float:
        return self.siguiente_paso().u

    def estado_interno(self) -> dict[str, Any]:
        datos: dict[str, Any] = {"metodo": METODO, "estado_actual": self._x, "digitos": self._digitos}
        if self._ultimo is not None:
            datos.update(asdict(self._ultimo))
        return datos

    def degenerado(self) -> bool:
        return self._ultimo is not None and self._ultimo.degeneracion is not None

    # --- Cálculo ------------------------------------------------------------------------

    def siguiente_paso(self) -> PasoCuadradosMedios:
        """Produce un número y devuelve su cálculo completo."""
        previo = self._x
        cuadrado, relleno, centrales = calcular_centrales(previo, self._digitos)
        x = int(centrales)
        self._indice += 1

        degeneracion = self._detectar(x)
        if degeneracion is None:
            self._vistos[x] = self._indice
            self._x = x
        else:
            self._resembrar(degeneracion)

        self._ultimo = PasoCuadradosMedios(
            indice=self._indice,
            previo=previo,
            cuadrado=cuadrado,
            relleno=relleno,
            centrales=centrales,
            x=x,
            u=x / self._modulo,
            degeneracion=degeneracion,
        )
        return self._ultimo

    def _detectar(self, x: int) -> Degeneracion | None:
        """Devuelve la degeneración que revela el nuevo estado x, o None si no hay."""
        if x == 0:
            tipo, longitud = TipoDegeneracion.CERO, None
        elif x in self._vistos:
            tipo, longitud = TipoDegeneracion.CICLO, self._indice - self._vistos[x]
        else:
            return None
        k, semilla_nueva = self._calcular_resiembra(estado_degenerado=x)
        return Degeneracion(tipo, x, longitud, k, semilla_nueva)

    def _calcular_resiembra(self, estado_degenerado: int) -> tuple[int, int]:
        """Aplica la regla (semilla + k · PASO_RESIEMBRA) mod 10^D con el siguiente k válido."""
        return calcular_resiembra(self._semilla, self._k, self._modulo, estado_degenerado)

    def _resembrar(self, degeneracion: Degeneracion) -> None:
        self._k = degeneracion.numero_resiembra
        semilla_nueva = degeneracion.semilla_nueva
        self._x = semilla_nueva
        self._resiembras += 1
        self._vistos = {semilla_nueva: self._indice}
