"""Pruebas estadísticas de los números pseudoaleatorios (RF-62).

Concepto de simulación: **validación del generador**. Un generador sirve si sus números
"parecen" independientes y uniformes en [0, 1). Se contrasta con tres pruebas clásicas:

- χ² (ji cuadrada) de uniformidad: se divide [0, 1) en k intervalos iguales y se compara la
  frecuencia observada O_i con la esperada E = n/k:  X² = Σ (O_i − E)² / E,  con k − 1 grados
  de libertad. Se rechaza la uniformidad si X² > χ²_{α, k−1}.
- Kolmogórov-Smirnov de uniformidad: compara la distribución empírica con F(u) = u.
  Con los números ordenados u_(1) ≤ … ≤ u_(n):
      D⁺ = max(i/n − u_(i)),  D⁻ = max(u_(i) − (i−1)/n),  D = max(D⁺, D⁻).
  Se rechaza si D > D_α. El valor crítico usa la aproximación de Stephens:
      D_α = λ_α / (√n + 0.12 + 0.11/√n),  con λ_α tal que Q_KS(λ_α) = α.
- Corridas arriba y abajo (independencia): una corrida es una racha de subidas o de bajadas
  consecutivas. Con a corridas en n números, si son independientes:
      E(a) = (2n − 1)/3,  V(a) = (16n − 29)/90,  Z = (a − E(a)) / √V(a) ~ N(0, 1).
  Se rechaza la independencia si |Z| > z_{α/2}. Una diferencia nula cuenta como bajada.

Los valores p se calculan con fórmulas propias (función gamma incompleta y erfc), sin
dependencias externas. Ninguna función de este módulo genera números.
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

ALFA_POR_DEFECTO = 0.05
FRECUENCIA_ESPERADA_MINIMA = 5  # regla práctica de la prueba χ²
_ITERACIONES_MAXIMAS = 500
_TOLERANCIA = 1e-14
_TERMINOS_KS = 100


@dataclass(frozen=True)
class ResultadoPrueba:
    """Resultado de una prueba de hipótesis sobre la muestra."""

    prueba: str
    hipotesis_nula: str
    estadistico: float
    valor_critico: float
    p_valor: float
    alfa: float
    rechaza: bool
    detalle: dict[str, Any] = field(default_factory=dict)


# --- Distribuciones de referencia --------------------------------------------------------

def _gamma_inferior_regularizada(a: float, x: float) -> float:
    """P(a, x) = γ(a, x) / Γ(a), por serie (x < a + 1) o fracción continua (Numerical Recipes)."""
    if x <= 0:
        return 0.0
    log_prefactor = -x + a * math.log(x) - math.lgamma(a)
    if x < a + 1:
        termino = suma = 1.0 / a
        denominador = a
        for _ in range(_ITERACIONES_MAXIMAS):
            denominador += 1
            termino *= x / denominador
            suma += termino
            if abs(termino) < abs(suma) * _TOLERANCIA:
                break
        return suma * math.exp(log_prefactor)
    # Fracción continua de Lentz para Q(a, x) = 1 − P(a, x)
    minimo = 1e-300
    b = x + 1 - a
    c = 1 / minimo
    d = 1 / b
    h = d
    for i in range(1, _ITERACIONES_MAXIMAS):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = minimo if abs(d) < minimo else d
        c = b + an / c
        c = minimo if abs(c) < minimo else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < _TOLERANCIA:
            break
    return 1.0 - math.exp(log_prefactor) * h


def chi2_supervivencia(x: float, grados: int) -> float:
    """P(X > x) para X ~ χ² con `grados` grados de libertad (el valor p)."""
    return 1.0 - _gamma_inferior_regularizada(grados / 2, x / 2)


def _invertir(funcion_decreciente: Callable[[float], float], objetivo: float,
              inferior: float, superior: float) -> float:
    """Bisección: el x en [inferior, superior] donde la función decreciente vale `objetivo`."""
    for _ in range(200):
        medio = (inferior + superior) / 2
        if funcion_decreciente(medio) > objetivo:
            inferior = medio
        else:
            superior = medio
    return (inferior + superior) / 2


def chi2_critico(alfa: float, grados: int) -> float:
    """χ²_{α, gl}: el valor que deja una probabilidad α a la derecha."""
    superior = grados + 20 * math.sqrt(2 * grados) + 50
    return _invertir(lambda x: chi2_supervivencia(x, grados), alfa, 0.0, superior)


def kolmogorov_supervivencia(lam: float) -> float:
    """Q_KS(λ) = 2 Σ_{j≥1} (−1)^{j−1} e^{−2 j² λ²}: P(√n·D > λ) para n grande."""
    if lam < 0.2:
        return 1.0  # la serie converge mal aquí y el valor es 1 en la práctica
    suma = sum((-1) ** (j - 1) * math.exp(-2 * j * j * lam * lam) for j in range(1, _TERMINOS_KS))
    return min(1.0, max(0.0, 2 * suma))


def _factor_stephens(n: int) -> float:
    raiz = math.sqrt(n)
    return raiz + 0.12 + 0.11 / raiz


def ks_critico(alfa: float, n: int) -> float:
    """D_α aproximado (Stephens): λ_α / (√n + 0.12 + 0.11/√n)."""
    lam = _invertir(kolmogorov_supervivencia, alfa, 0.2, 5.0)
    return lam / _factor_stephens(n)


def normal_dos_colas(z: float) -> float:
    """P(|Z| > |z|) para Z ~ N(0, 1)."""
    return math.erfc(abs(z) / math.sqrt(2))


def normal_critico(alfa: float) -> float:
    """z_{α/2}: el valor con P(|Z| > z) = α."""
    return _invertir(normal_dos_colas, alfa, 0.0, 10.0)


# --- Pruebas -----------------------------------------------------------------------------

def _como_arreglo(muestra: Sequence[float]) -> np.ndarray:
    datos = np.asarray(muestra, dtype=np.float64)
    if datos.ndim != 1 or datos.size < 2:
        raise ValueError("la muestra debe tener al menos 2 números")
    return datos


def frecuencias(muestra: Sequence[float], intervalos: int) -> np.ndarray:
    """Cuántos números caen en cada uno de los k intervalos [j/k, (j+1)/k)."""
    datos = _como_arreglo(muestra)
    clase = np.minimum((datos * intervalos).astype(np.int64), intervalos - 1)
    return np.bincount(clase, minlength=intervalos)


def prueba_chi_cuadrada(muestra: Sequence[float], intervalos: int = 10,
                        alfa: float = ALFA_POR_DEFECTO) -> ResultadoPrueba:
    if intervalos < 2:
        raise ValueError("se necesitan al menos 2 intervalos")
    datos = _como_arreglo(muestra)
    observadas = frecuencias(datos, intervalos)
    esperada = datos.size / intervalos
    estadistico = float(((observadas - esperada) ** 2).sum() / esperada)
    grados = intervalos - 1
    critico = chi2_critico(alfa, grados)
    detalle: dict[str, Any] = {
        "intervalos": intervalos, "grados_libertad": grados,
        "frecuencia_esperada": esperada, "observadas": observadas.tolist(),
    }
    if esperada < FRECUENCIA_ESPERADA_MINIMA:
        detalle["advertencia"] = (
            f"la frecuencia esperada n/k = {esperada:.2f} es menor que "
            f"{FRECUENCIA_ESPERADA_MINIMA}: use más números o menos intervalos")
    return ResultadoPrueba(
        prueba="χ² de uniformidad",
        hipotesis_nula="los números son uniformes en [0, 1)",
        estadistico=estadistico, valor_critico=critico,
        p_valor=chi2_supervivencia(estadistico, grados), alfa=alfa,
        rechaza=estadistico > critico, detalle=detalle,
    )


def prueba_kolmogorov_smirnov(muestra: Sequence[float], alfa: float = ALFA_POR_DEFECTO) -> ResultadoPrueba:
    datos = np.sort(_como_arreglo(muestra))
    n = datos.size
    i = np.arange(1, n + 1)
    d_mas = float((i / n - datos).max())
    d_menos = float((datos - (i - 1) / n).max())
    estadistico = max(d_mas, d_menos)
    critico = ks_critico(alfa, n)
    return ResultadoPrueba(
        prueba="Kolmogórov-Smirnov de uniformidad",
        hipotesis_nula="los números siguen la distribución uniforme F(u) = u",
        estadistico=estadistico, valor_critico=critico,
        p_valor=kolmogorov_supervivencia(estadistico * _factor_stephens(n)), alfa=alfa,
        rechaza=estadistico > critico,
        detalle={"n": n, "d_mas": d_mas, "d_menos": d_menos},
    )


def contar_corridas(muestra: Sequence[float]) -> int:
    """Número de corridas arriba y abajo (una diferencia nula cuenta como bajada)."""
    datos = _como_arreglo(muestra)
    sube = np.diff(datos) > 0
    return 1 + int((sube[1:] != sube[:-1]).sum())


def prueba_corridas(muestra: Sequence[float], alfa: float = ALFA_POR_DEFECTO) -> ResultadoPrueba:
    datos = _como_arreglo(muestra)
    n = datos.size
    if n < 3:
        raise ValueError("la prueba de corridas necesita al menos 3 números")
    corridas = contar_corridas(datos)
    media = (2 * n - 1) / 3
    varianza = (16 * n - 29) / 90
    z = (corridas - media) / math.sqrt(varianza)
    critico = normal_critico(alfa)
    return ResultadoPrueba(
        prueba="Corridas arriba y abajo (independencia)",
        hipotesis_nula="los números son independientes",
        estadistico=z, valor_critico=critico,
        p_valor=normal_dos_colas(z), alfa=alfa, rechaza=abs(z) > critico,
        detalle={"n": n, "corridas": corridas, "media_esperada": media, "varianza_esperada": varianza},
    )


def resumen_muestra(muestra: Sequence[float], intervalos: int) -> dict[str, Any]:
    """Media y varianza (esperadas 1/2 y 1/12 para la uniforme) e histograma."""
    datos = _como_arreglo(muestra)
    return {
        "n": int(datos.size),
        "media": float(datos.mean()),
        "varianza": float(datos.var(ddof=1)),
        "media_esperada": 0.5,
        "varianza_esperada": 1 / 12,
        "histograma": frecuencias(datos, intervalos).tolist(),
        "distintos": int(np.unique(datos).size),
    }
