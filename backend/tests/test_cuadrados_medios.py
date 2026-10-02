"""Pruebas del generador de cuadrados medios (RF-10, RF-11, RF-13, RF-14)."""

import pytest

from app.aleatorio.cuadrados_medios import (
    PASO_RESIEMBRA,
    GeneradorCuadradosMedios,
    TipoDegeneracion,
)

# Tabla calculada a mano (DISENO.md §10.1), semilla 5735, D = 4:
#
#  i | xᵢ   | xᵢ²        | relleno (8) | centrales | uᵢ
#  1 | 5735 | 32 890 225 | 32 8902 25  | 8902      | 0.8902
#  2 | 8902 | 79 245 604 | 79 2456 04  | 2456      | 0.2456
#  3 | 2456 |  6 031 936 | 06 0319 36  | 0319      | 0.0319
#  4 | 0319 |    101 761 | 00 1017 61  | 1017      | 0.1017
#  5 | 1017 |  1 034 289 | 01 0342 89  | 0342      | 0.0342
#  6 | 0342 |    116 964 | 00 1169 64  | 1169      | 0.1169
TABLA_5735 = [
    (5735, 32890225, "32890225", "8902", 0.8902),
    (8902, 79245604, "79245604", "2456", 0.2456),
    (2456, 6031936, "06031936", "0319", 0.0319),
    (319, 101761, "00101761", "1017", 0.1017),
    (1017, 1034289, "01034289", "0342", 0.0342),
    (342, 116964, "00116964", "1169", 0.1169),
]


def test_tabla_semilla_5735_calculada_a_mano() -> None:
    generador = GeneradorCuadradosMedios(semilla=5735, digitos=4)
    for i, (previo, cuadrado, relleno, centrales, u) in enumerate(TABLA_5735, start=1):
        paso = generador.siguiente_paso()
        assert paso.indice == i
        assert paso.previo == previo
        assert paso.cuadrado == cuadrado
        assert paso.relleno == relleno
        assert paso.centrales == centrales
        assert paso.u == pytest.approx(u)
        assert paso.degeneracion is None


def test_siguiente_devuelve_u_en_intervalo() -> None:
    generador = GeneradorCuadradosMedios(semilla=5735)
    for _ in range(500):
        assert 0.0 <= generador.siguiente() < 1.0


def test_seis_digitos() -> None:
    # 123456² = 15 241 383 936 → relleno a 12 dígitos 015 241383 936 → centrales 241383
    paso = GeneradorCuadradosMedios(semilla=123456, digitos=6).siguiente_paso()
    assert paso.relleno == "015241383936"
    assert paso.centrales == "241383"
    assert paso.u == pytest.approx(0.241383)


def test_ocho_digitos() -> None:
    # 12345678² = 152 415 765 279 684 → relleno a 16: 0152 41576527 9684 → 41576527
    paso = GeneradorCuadradosMedios(semilla=12345678, digitos=8).siguiente_paso()
    assert paso.relleno == "0152415765279684"
    assert paso.centrales == "41576527"


def test_semilla_1_cae_en_cero() -> None:
    # 1² = 00000001 → centrales 0000
    generador = GeneradorCuadradosMedios(semilla=1)
    paso = generador.siguiente_paso()
    assert paso.x == 0 and paso.u == 0.0
    assert paso.degeneracion is not None
    assert paso.degeneracion.tipo is TipoDegeneracion.CERO
    assert generador.degenerado()


@pytest.mark.parametrize("semilla", [2500, 3792])
def test_puntos_fijos_ciclo_de_longitud_1(semilla: int) -> None:
    # 2500² = 06 2500 00 ; 3792² = 14 3792 64
    paso = GeneradorCuadradosMedios(semilla=semilla).siguiente_paso()
    assert paso.x == semilla
    assert paso.degeneracion is not None
    assert paso.degeneracion.tipo is TipoDegeneracion.CICLO
    assert paso.degeneracion.longitud_ciclo == 1


def test_semilla_6100_ciclo_de_longitud_4() -> None:
    # 6100 → 2100 → 4100 → 8100 → 6100
    generador = GeneradorCuadradosMedios(semilla=6100)
    estados = [generador.siguiente_paso() for _ in range(4)]
    assert [p.x for p in estados] == [2100, 4100, 8100, 6100]
    assert all(p.degeneracion is None for p in estados[:3])
    degeneracion = estados[3].degeneracion
    assert degeneracion is not None
    assert degeneracion.tipo is TipoDegeneracion.CICLO
    assert degeneracion.longitud_ciclo == 4


def test_regla_de_resiembra_visible() -> None:
    # Semilla 1: degenera en el primer número; k = 1 → (1 + 7919) mod 10⁴ = 7920
    generador = GeneradorCuadradosMedios(semilla=1)
    degeneracion = generador.siguiente_paso().degeneracion
    assert degeneracion is not None
    assert degeneracion.numero_resiembra == 1
    assert degeneracion.semilla_nueva == (1 + PASO_RESIEMBRA) % 10_000 == 7920
    assert generador.resiembras == 1
    # El número siguiente parte de la semilla nueva: 7920² = 62 7264 00
    assert generador.siguiente_paso().previo == 7920


def test_resiembras_sucesivas_usan_k_creciente() -> None:
    generador = GeneradorCuadradosMedios(semilla=2500)
    ks = [p.degeneracion.numero_resiembra for p in (generador.siguiente_paso() for _ in range(300))
          if p.degeneracion is not None]
    assert len(ks) >= 2
    assert ks == sorted(ks) and len(set(ks)) == len(ks)
    assert generador.resiembras == len(ks)


def test_resiembra_salta_k_si_da_cero() -> None:
    # Semilla 2081: con k = 1, (2081 + 7919) mod 10⁴ = 0 → se usa k = 2 → 7919
    generador = GeneradorCuadradosMedios(semilla=2081)
    paso = None
    while paso is None or paso.degeneracion is None:
        paso = generador.siguiente_paso()
    assert paso.degeneracion.numero_resiembra >= 2
    assert paso.degeneracion.semilla_nueva != 0


def test_resiembra_determinista() -> None:
    a = GeneradorCuadradosMedios(semilla=5735)
    b = GeneradorCuadradosMedios(semilla=5735)
    pasos_a = [a.siguiente_paso() for _ in range(1000)]
    pasos_b = [b.siguiente_paso() for _ in range(1000)]
    assert pasos_a == pasos_b
    assert a.resiembras == b.resiembras > 0


def test_reiniciar_reproduce_la_secuencia() -> None:
    generador = GeneradorCuadradosMedios(semilla=5735)
    primera = [generador.siguiente() for _ in range(200)]
    generador.reiniciar()
    assert [generador.siguiente() for _ in range(200)] == primera
    assert generador.resiembras > 0


def test_estado_interno_muestra_el_calculo() -> None:
    generador = GeneradorCuadradosMedios(semilla=5735)
    generador.siguiente()
    estado = generador.estado_interno()
    assert estado["previo"] == 5735
    assert estado["relleno"] == "32890225"
    assert estado["centrales"] == "8902"
    assert estado["degeneracion"] is None


@pytest.mark.parametrize(
    ("semilla", "digitos"),
    [(0, 4), (10_000, 4), (-5, 4), (5735, 5), (5735, 2)],
)
def test_configuracion_invalida(semilla: int, digitos: int) -> None:
    with pytest.raises(ValueError):
        GeneradorCuadradosMedios(semilla=semilla, digitos=digitos)
