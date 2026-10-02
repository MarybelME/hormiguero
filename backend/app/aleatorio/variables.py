"""Mapeos de números pseudoaleatorios a variables aleatorias.

Concepto de simulación: **variable aleatoria**. El generador sólo produce u ∈ [0, 1)
(uniforme estándar); estas funciones puras la transforman en la variable que necesita
el modelo. Se mantienen separadas de los generadores para poder probarlas y explicarlas solas.
"""

GRADOS_POR_VUELTA = 360.0


def _validar_u(u: float) -> None:
    if not 0.0 <= u < 1.0:
        raise ValueError(f"u debe estar en [0, 1); se recibió {u}")


def angulo(u: float) -> float:
    """Dirección uniforme en [0°, 360°): angulo = u · 360."""
    _validar_u(u)
    return u * GRADOS_POR_VUELTA


def bernoulli(u: float, p: float) -> bool:
    """Ensayo de Bernoulli con probabilidad de éxito p: éxito si u < p."""
    _validar_u(u)
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"p debe estar en [0, 1]; se recibió {p}")
    return u < p


def uniforme(u: float, a: float, b: float) -> float:
    """Uniforme continua en [a, b): x = a + u · (b − a)."""
    _validar_u(u)
    if b < a:
        raise ValueError(f"se requiere a ≤ b; se recibió a={a}, b={b}")
    return a + u * (b - a)
