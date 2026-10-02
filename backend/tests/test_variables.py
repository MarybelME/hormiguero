"""Pruebas de los mapeos u → variable aleatoria."""

import pytest

from app.aleatorio.variables import angulo, bernoulli, uniforme


def test_angulo() -> None:
    assert angulo(0.0) == 0.0
    assert angulo(0.5) == 180.0
    assert angulo(0.8902) == pytest.approx(320.472)  # primer número de la semilla 5735


def test_bernoulli_exito_si_u_menor_que_p() -> None:
    assert bernoulli(0.29, 0.3) is True
    assert bernoulli(0.3, 0.3) is False  # en el borde u = p no hay éxito
    assert bernoulli(0.0, 0.0) is False  # p = 0: nunca
    assert bernoulli(0.9999, 1.0) is True  # p = 1: siempre


def test_uniforme() -> None:
    assert uniforme(0.0, 10.0, 20.0) == 10.0
    assert uniforme(0.25, 10.0, 20.0) == 12.5


@pytest.mark.parametrize("u", [-0.1, 1.0, 1.5])
def test_u_fuera_de_rango(u: float) -> None:
    with pytest.raises(ValueError):
        angulo(u)


def test_parametros_invalidos() -> None:
    with pytest.raises(ValueError):
        bernoulli(0.5, 1.2)
    with pytest.raises(ValueError):
        uniforme(0.5, 20.0, 10.0)
