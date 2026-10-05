"""Pruebas de los parámetros de la simulación."""

import pytest
from pydantic import ValidationError

from app.config import ParametrosSimulacion, semilla_comportamiento


def test_valores_por_defecto_de_la_especificacion() -> None:
    p = ParametrosSimulacion()
    assert (p.num_hormigas, p.semilla, p.digitos) == (2000, 5735, 4)
    assert (p.num_obstaculos, p.num_fuentes, p.alimento_por_fuente) == (12, 4, 2000)
    assert (p.radio_reina, p.p_seguir_reina) == (80.0, 0.3)


def test_semilla_comportamiento_media_escala() -> None:
    # (5735 + 10⁴/2) mod 10⁴ = 735
    assert semilla_comportamiento(5735, 4) == 735
    assert semilla_comportamiento(1234, 4) == 6234
    assert semilla_comportamiento(5000, 4) == 1  # daría 0 → se usa 1
    assert semilla_comportamiento(123456, 6) == 623456


@pytest.mark.parametrize(
    "cambios",
    [
        {"num_hormigas": 0},
        {"num_hormigas": 20_001},
        {"semilla": 10_000},             # no cabe en D = 4
        {"digitos": 5},
        {"p_seguir_reina": 1.5},
        {"num_obstaculos": 61},
        {"umbral_regreso": 150.0},       # mayor que energia_max
        {"campo_inventado": 1},
    ],
)
def test_parametros_invalidos(cambios: dict) -> None:
    with pytest.raises(ValidationError):
        ParametrosSimulacion(**cambios)


def test_esquema_tiene_unidad_y_rango() -> None:
    propiedades = ParametrosSimulacion.model_json_schema()["properties"]
    radio = propiedades["radio_reina"]
    assert radio["unidad"] == "unidades"
    assert (radio["minimum"], radio["maximum"]) == (0.0, 300.0)
    assert radio["description"]


def test_parametros_demo_generan_un_mundo() -> None:
    from app.config import PARAMETROS_DEMO
    from app.nucleo.simulacion import Simulacion

    simulacion = Simulacion(PARAMETROS_DEMO)
    assert len(simulacion.mundo.obstaculos) == PARAMETROS_DEMO.num_obstaculos
    assert len(simulacion.mundo.fuentes) == PARAMETROS_DEMO.num_fuentes
