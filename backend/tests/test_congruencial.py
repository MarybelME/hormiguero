"""Pruebas de los generadores congruenciales y de NumPy (RF-16)."""

import numpy as np
import pytest

from app.aleatorio.base import PASO_RESIEMBRA, TipoDegeneracion
from app.aleatorio.congruencial import (
    GeneradorCongruencial,
    GeneradorCongruencialMultiplicativo,
    validar_congruencial,
)
from app.aleatorio.numpy_referencia import GeneradorNumpy

# Tabla calculada a mano: x_{i+1} = (5·x_i + 3) mod 16, x0 = 7.
# Cumple Hull-Dobell (c = 3 impar, a − 1 = 4 múltiplo de 4, m = 2^4): periodo completo 16.
#   i  x_i  5·x_i+3  x_{i+1}
#   1   7     38       6
#   2   6     33       1
#   3   1      8       8
#   4   8     43      11
#   5  11     58      10
#   6  10     53       5
#   7   5     28      12
#   8  12     63      15
#   9  15     78      14
#  10  14     73       9
#  11   9     48       0
#  12   0      3       3
#  13   3     18       2
#  14   2     13      13
#  15  13     68       4
#  16   4     23       7   ← vuelve a la semilla: periodo 16
TABLA_LINEAL = [6, 1, 8, 11, 10, 5, 12, 15, 14, 9, 0, 3, 2, 13, 4, 7]
PRODUCTOS_LINEAL = [38, 33, 8, 43, 58, 53, 28, 63, 78, 73, 48, 3, 18, 13, 68, 23]


def test_congruencial_lineal_tabla_a_mano() -> None:
    generador = GeneradorCongruencial(semilla=7, a=5, c=3, m=16)
    pasos = [generador.siguiente_paso() for _ in range(16)]
    assert [p.x for p in pasos] == TABLA_LINEAL
    assert [p.producto for p in pasos] == PRODUCTOS_LINEAL
    assert [p.u for p in pasos] == [x / 16 for x in TABLA_LINEAL]
    assert all(p.degeneracion is None for p in pasos[:15])


def test_congruencial_completa_el_periodo_y_resiembra() -> None:
    generador = GeneradorCongruencial(semilla=7, a=5, c=3, m=16)
    pasos = [generador.siguiente_paso() for _ in range(17)]
    degeneracion = pasos[15].degeneracion
    assert degeneracion.tipo is TipoDegeneracion.CICLO
    assert degeneracion.longitud_ciclo == 16
    # (7 + 1 · 7919) mod 16 = 7926 mod 16 = 6
    assert degeneracion.semilla_nueva == (7 + PASO_RESIEMBRA) % 16 == 6
    assert generador.resiembras == 1
    assert pasos[16].previo == 6


def test_malos_parametros_dan_periodo_corto() -> None:
    """c = 2 (par) viola Hull-Dobell: con m = 16 el periodo es 8, no 16.

    x0 = 1: 7, 5, 11, 9, 15, 13, 3, 1 ← vuelve a la semilla en el número 8.
    """
    generador = GeneradorCongruencial(semilla=1, a=5, c=2, m=16)
    pasos = [generador.siguiente_paso() for _ in range(8)]
    assert [p.x for p in pasos] == [7, 5, 11, 9, 15, 13, 3, 1]
    assert pasos[-1].degeneracion.longitud_ciclo == 8


def test_multiplicativo_tabla_a_mano() -> None:
    """x_{i+1} = 3·x_i mod 7, x0 = 1: 3, 9→2, 6, 18→4, 12→5, 15→1.

    3 es raíz primitiva de 7: periodo completo m − 1 = 6.
    """
    generador = GeneradorCongruencialMultiplicativo(semilla=1, a=3, m=7)
    assert generador.nombre == "Congruencial multiplicativo"
    pasos = [generador.siguiente_paso() for _ in range(6)]
    assert [p.x for p in pasos] == [3, 2, 6, 4, 5, 1]
    assert [p.producto for p in pasos] == [3, 9, 6, 18, 12, 15]
    assert pasos[-1].degeneracion.longitud_ciclo == 6


def test_multiplicativo_periodo_segun_a() -> None:
    """Con m = 11 primo: a = 3 tiene orden 5 (3^5 = 243 ≡ 1), a = 2 es raíz primitiva (periodo 10)."""
    generador = GeneradorCongruencialMultiplicativo(semilla=1, a=3, m=11)
    assert [generador.siguiente_paso().x for _ in range(5)] == [3, 9, 5, 4, 1]
    assert generador.ultimo_paso.degeneracion.longitud_ciclo == 5
    generador = GeneradorCongruencialMultiplicativo(semilla=1, a=2, m=11)
    assert [generador.siguiente_paso().x for _ in range(10)] == [2, 4, 8, 5, 10, 9, 7, 3, 6, 1]
    assert generador.ultimo_paso.degeneracion.longitud_ciclo == 10


def test_multiplicativo_con_m_potencia_de_2() -> None:
    """Con m = 8 y a = 3: 3, 9→1. Periodo 2: un multiplicativo con m = 2^k nunca es de periodo completo."""
    generador = GeneradorCongruencialMultiplicativo(semilla=1, a=3, m=8)
    assert [generador.siguiente_paso().x for _ in range(2)] == [3, 1]
    assert generador.ultimo_paso.degeneracion.longitud_ciclo == 2


def test_park_miller_valor_de_referencia() -> None:
    """Park y Miller (1988): con a = 16807, m = 2^31 − 1 y x0 = 1, x_10000 = 1043618065."""
    generador = GeneradorCongruencialMultiplicativo(semilla=1, a=16807, m=2**31 - 1)
    for _ in range(10_000):
        paso = generador.siguiente_paso()
    assert paso.x == 1043618065
    assert generador.resiembras == 0


def test_reiniciar_repite_la_sucesion_con_resiembras() -> None:
    generador = GeneradorCongruencial(semilla=7, a=5, c=3, m=16)
    primera = [generador.siguiente() for _ in range(50)]
    assert generador.resiembras > 0
    generador.reiniciar()
    assert [generador.siguiente() for _ in range(50)] == primera


def test_estado_interno_describe_el_calculo() -> None:
    generador = GeneradorCongruencial(semilla=7, a=5, c=3, m=16)
    generador.siguiente()
    estado = generador.estado_interno()
    assert estado["metodo"] == "congruencial_lineal"
    assert (estado["a"], estado["c"], estado["m"]) == (5, 3, 16)
    assert (estado["previo"], estado["producto"], estado["x"]) == (7, 38, 6)


@pytest.mark.parametrize(
    ("semilla", "a", "c", "m"),
    [
        (1, 1, 0, 2),      # m muy pequeño
        (1, 5, 3, 7919),   # m múltiplo del paso de re-siembra
        (1, 4, 3, 16),     # mcd(4, 16) ≠ 1
        (16, 5, 3, 16),    # semilla ≥ m
        (0, 5, 3, 16),     # semilla 0
        (1, 5, 16, 16),    # c ≥ m
        (1, 0, 3, 16),     # a = 0
    ],
)
def test_validacion(semilla: int, a: int, c: int, m: int) -> None:
    with pytest.raises(ValueError):
        validar_congruencial(semilla, a, c, m)


def test_numpy_coincide_con_la_referencia() -> None:
    """El envoltorio entrega la misma sucesión que numpy (la prueba sí puede usar numpy.random)."""
    generador = GeneradorNumpy(semilla=5735)
    esperados = np.random.Generator(np.random.PCG64(5735)).random(100)
    assert [generador.siguiente() for _ in range(100)] == esperados.tolist()
    generador.reiniciar()
    assert generador.siguiente() == esperados[0]
    assert not generador.degenerado()
    assert generador.estado_interno()["metodo"] == "numpy"
