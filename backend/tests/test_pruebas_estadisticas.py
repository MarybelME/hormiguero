"""Pruebas de uniformidad e independencia contra valores de referencia (RF-62)."""

import math

import pytest

from app.aleatorio.congruencial import GeneradorCongruencial
from app.aleatorio.pruebas_estadisticas import (
    chi2_critico,
    chi2_supervivencia,
    contar_corridas,
    ks_critico,
    normal_critico,
    prueba_chi_cuadrada,
    prueba_corridas,
    prueba_kolmogorov_smirnov,
    resumen_muestra,
)


# --- Distribuciones ------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("grados", "critico"),
    # Tabla de χ²_{0.05, gl} de cualquier libro de estadística
    [(1, 3.841), (2, 5.991), (4, 9.488), (9, 16.919), (19, 30.144), (99, 123.225)],
)
def test_chi2_critico_contra_tabla(grados: int, critico: float) -> None:
    assert chi2_critico(0.05, grados) == pytest.approx(critico, abs=1e-3)


def test_chi2_supervivencia_formulas_cerradas() -> None:
    """Con 2 gl, P(X > x) = e^{−x/2}; con 1 gl, P(X > x) = erfc(√(x/2))."""
    for x in (0.1, 1.0, 3.4, 10.0, 40.0):
        assert chi2_supervivencia(x, 2) == pytest.approx(math.exp(-x / 2), rel=1e-10)
        assert chi2_supervivencia(x, 1) == pytest.approx(math.erfc(math.sqrt(x / 2)), rel=1e-9)


def test_criticos_normal_y_ks() -> None:
    assert normal_critico(0.05) == pytest.approx(1.95996, abs=1e-5)
    assert normal_critico(0.01) == pytest.approx(2.57583, abs=1e-5)
    # Tabla de Kolmogórov-Smirnov: D_{0.05} = 0.565 para n = 5; ≈ 1.36/√n para n grande
    assert ks_critico(0.05, 5) == pytest.approx(0.565, abs=1e-3)
    assert ks_critico(0.05, 10_000) == pytest.approx(1.358 / 100, rel=2e-3)


# --- χ² ------------------------------------------------------------------------------------

def muestra_con_frecuencias(observadas: list[int]) -> list[float]:
    """Una muestra con esas frecuencias en k intervalos iguales (el centro de cada intervalo)."""
    k = len(observadas)
    return [(j + 0.5) / k for j, o in enumerate(observadas) for _ in range(o)]


def test_chi_cuadrada_ejemplo_de_texto() -> None:
    """Banks et al., "Discrete-Event System Simulation": n = 100, k = 10,
    O = 8, 8, 10, 9, 12, 8, 10, 14, 10, 11; E = 10.
    X² = (4 + 4 + 0 + 1 + 4 + 4 + 0 + 16 + 0 + 1) / 10 = 3.4 < 16.919 ⇒ no se rechaza.
    """
    observadas = [8, 8, 10, 9, 12, 8, 10, 14, 10, 11]
    resultado = prueba_chi_cuadrada(muestra_con_frecuencias(observadas), intervalos=10)
    assert resultado.estadistico == pytest.approx(3.4)
    assert resultado.detalle["observadas"] == observadas
    assert resultado.valor_critico == pytest.approx(16.919, abs=1e-3)
    # Para gl impar hay fórmula cerrada:
    # Q = erfc(√(x/2)) + √(2x/π)·e^{−x/2}·Σ_{k=1}^{(gl−1)/2} x^{k−1} / (1·3·…·(2k−1)) = 0.946308
    assert resultado.p_valor == pytest.approx(0.946308, abs=1e-6)
    assert not resultado.rechaza


def test_chi_cuadrada_rechaza_una_muestra_concentrada() -> None:
    resultado = prueba_chi_cuadrada([0.05] * 50 + [0.95] * 50, intervalos=10)
    assert resultado.estadistico == pytest.approx(400.0)  # (8·100 + 2·1600) / 10
    assert resultado.rechaza and resultado.p_valor < 1e-6


def test_chi_cuadrada_advierte_frecuencia_esperada_baja() -> None:
    assert "advertencia" in prueba_chi_cuadrada([0.1, 0.5, 0.9] * 4, intervalos=10).detalle


# --- Kolmogórov-Smirnov ---------------------------------------------------------------------

def test_ks_ejemplo_de_texto() -> None:
    """Banks et al.: 0.44, 0.81, 0.14, 0.05, 0.93.

    Ordenados  0.05  0.14  0.44  0.81  0.93
    i/n        0.20  0.40  0.60  0.80  1.00   → i/n − u:     0.15  0.26  0.16  −0.01  0.07
    (i−1)/n    0.00  0.20  0.40  0.60  0.80   → u − (i−1)/n: 0.05 −0.06  0.04   0.21  0.13
    D⁺ = 0.26, D⁻ = 0.21, D = 0.26 < 0.565 ⇒ no se rechaza.
    """
    resultado = prueba_kolmogorov_smirnov([0.44, 0.81, 0.14, 0.05, 0.93])
    assert resultado.detalle["d_mas"] == pytest.approx(0.26)
    assert resultado.detalle["d_menos"] == pytest.approx(0.21)
    assert resultado.estadistico == pytest.approx(0.26)
    assert not resultado.rechaza


def test_ks_rechaza_numeros_en_la_mitad_inferior() -> None:
    resultado = prueba_kolmogorov_smirnov([i / 200 for i in range(100)])  # todos en [0, 0.5)
    assert resultado.estadistico == pytest.approx(0.5, abs=0.01)
    assert resultado.rechaza


# --- Corridas --------------------------------------------------------------------------------

def test_corridas_a_mano() -> None:
    """0.1 ↑ 0.5 ↓ 0.3 ↑ 0.4 ↓ 0.2 ↑ 0.6: signos + − + − +  ⇒ 5 corridas.

    n = 6: E = (2·6 − 1)/3 = 3.6667; V = (16·6 − 29)/90 = 0.7444; Z = (5 − 3.6667)/0.8628 = 1.5454.
    """
    resultado = prueba_corridas([0.1, 0.5, 0.3, 0.4, 0.2, 0.6])
    assert resultado.detalle["corridas"] == 5
    assert resultado.detalle["media_esperada"] == pytest.approx(11 / 3)
    assert resultado.detalle["varianza_esperada"] == pytest.approx(67 / 90)
    assert resultado.estadistico == pytest.approx(1.5454, abs=1e-4)
    assert not resultado.rechaza


def test_corridas_cuenta_empates_como_bajada() -> None:
    assert contar_corridas([0.1, 0.2, 0.3, 0.4]) == 1          # + + +
    assert contar_corridas([0.5, 0.5, 0.5]) == 1               # − − (empates)
    assert contar_corridas([0.1, 0.5, 0.5, 0.7]) == 3          # + − +


def test_corridas_rechaza_una_sucesion_creciente() -> None:
    resultado = prueba_corridas([i / 100 for i in range(100)])
    assert resultado.detalle["corridas"] == 1
    assert resultado.rechaza


# --- Generadores reales ----------------------------------------------------------------------

def test_un_buen_congruencial_pasa_las_tres_pruebas() -> None:
    generador = GeneradorCongruencial(semilla=5735, a=1103515245, c=12345, m=2**31)
    muestra = [generador.siguiente() for _ in range(5000)]
    assert not prueba_chi_cuadrada(muestra).rechaza
    assert not prueba_kolmogorov_smirnov(muestra).rechaza
    assert not prueba_corridas(muestra).rechaza


def test_resumen_de_la_muestra() -> None:
    resumen = resumen_muestra([0.05, 0.15, 0.95, 0.95], intervalos=10)
    assert resumen["histograma"] == [1, 1, 0, 0, 0, 0, 0, 0, 0, 2]
    assert resumen["media"] == pytest.approx(0.525)
    assert resumen["distintos"] == 3
