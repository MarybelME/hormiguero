"""Pruebas del protocolo binario del cuadro (DISENO.md §12.2)."""

import struct

import numpy as np
import pytest

from app.api.protocolo import (
    TAMANO_ENCABEZADO,
    desempaquetar_cuadro,
    empaquetar_cuadro,
    tamano_cuadro,
)
from app.config import ParametrosSimulacion
from app.nucleo.simulacion import Simulacion


@pytest.fixture(scope="module")
def simulacion() -> Simulacion:
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=50))
    simulacion.avanzar(40)
    return simulacion


def test_encabezado_mide_24_bytes() -> None:
    assert TAMANO_ENCABEZADO == 24
    assert tamano_cuadro(5000) == 24 + 9 * 5000


def test_cuadro_byte_a_byte(simulacion: Simulacion) -> None:
    """Cada campo está en el desplazamiento y con el tipo que documenta la tabla."""
    mundo, h = simulacion.mundo, simulacion.mundo.hormigas
    n = h.n
    datos = empaquetar_cuadro(simulacion.tick, simulacion.tiempo, mundo)

    assert len(datos) == 24 + 9 * n
    assert datos[0] == 1                                       # version
    assert datos[1] == 1                                       # tipo_mensaje = CUADRO
    assert datos[2:4] == b"\x00\x00"                           # reservado
    assert struct.unpack("<I", datos[4:8])[0] == simulacion.tick
    assert struct.unpack("<I", datos[8:12])[0] == n
    assert struct.unpack("<f", datos[12:16])[0] == pytest.approx(simulacion.tiempo)
    assert struct.unpack("<f", datos[16:20])[0] == pytest.approx(mundo.reina.x)
    assert struct.unpack("<f", datos[20:24])[0] == pytest.approx(mundo.reina.y)
    for i in (0, n // 2, n - 1):
        assert struct.unpack_from("<f", datos, 24 + 4 * i)[0] == h.x[i]
        assert struct.unpack_from("<f", datos, 24 + 4 * n + 4 * i)[0] == h.y[i]
        assert datos[24 + 8 * n + i] == h.estado[i]


def test_ida_y_vuelta(simulacion: Simulacion) -> None:
    h = simulacion.mundo.hormigas
    cuadro = desempaquetar_cuadro(empaquetar_cuadro(simulacion.tick, simulacion.tiempo, simulacion.mundo))
    assert cuadro["tick"] == simulacion.tick and cuadro["n"] == h.n
    np.testing.assert_array_equal(cuadro["x"], h.x)
    np.testing.assert_array_equal(cuadro["y"], h.y)
    np.testing.assert_array_equal(cuadro["estado"], h.estado)


def test_rechaza_tamano_incorrecto(simulacion: Simulacion) -> None:
    datos = empaquetar_cuadro(simulacion.tick, simulacion.tiempo, simulacion.mundo)
    with pytest.raises(ValueError):
        desempaquetar_cuadro(datos[:-1])
