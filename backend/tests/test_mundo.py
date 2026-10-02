"""Pruebas de la generación del mundo y de la rejilla (RF-01, RF-02, RF-15)."""

import math

import numpy as np
import pytest

from app.config import ParametrosSimulacion
from app.espacial.rejilla import RejillaEspacial
from app.modelo.generacion_mundo import ErrorGeneracionMundo
from app.nucleo.simulacion import Simulacion


def mundo_de(**cambios):
    return Simulacion(ParametrosSimulacion(**cambios)).mundo


def test_misma_semilla_mismo_mundo() -> None:
    assert mundo_de().capa_estatica() == mundo_de().capa_estatica()


def test_otra_semilla_otro_mundo() -> None:
    assert mundo_de(semilla=1234).capa_estatica()["obstaculos"] != mundo_de().capa_estatica()["obstaculos"]


def test_cambiar_hormigas_no_mueve_las_rocas() -> None:
    """RF-15: el mundo usa su propio flujo de números."""
    a = mundo_de(num_hormigas=100, p_seguir_reina=0.9).capa_estatica()
    b = mundo_de(num_hormigas=5000).capa_estatica()
    assert a["obstaculos"] == b["obstaculos"]
    assert a["fuentes"] == b["fuentes"]


@pytest.mark.parametrize("semilla", [5735, 1, 2500, 6100, 9999])
def test_cantidades_y_sin_solapes(semilla: int) -> None:
    p = ParametrosSimulacion(semilla=semilla, num_obstaculos=30, num_fuentes=10)
    mundo = Simulacion(p).mundo
    assert len(mundo.obstaculos) == 30 and len(mundo.fuentes) == 10
    circulos = [(o.x, o.y, o.radio) for o in mundo.obstaculos] + [(f.x, f.y, f.radio) for f in mundo.fuentes]
    for i, (x1, y1, r1) in enumerate(circulos):
        assert r1 <= x1 <= mundo.ancho - r1 and r1 <= y1 <= mundo.alto - r1
        # Nada dentro de la zona de patrulla (y por lo tanto nada sobre el nido).
        assert math.dist((x1, y1), (mundo.nido.x, mundo.nido.y)) >= p.radio_patrulla + r1
        for x2, y2, r2 in circulos[i + 1:]:
            assert math.dist((x1, y1), (x2, y2)) >= r1 + r2


def test_generacion_registra_aceptacion_rechazo() -> None:
    simulacion = Simulacion(ParametrosSimulacion())
    g = simulacion.mundo.generacion
    assert g["candidatos"] == 12 + 4 + g["rechazados"]
    assert g["numeros_usados"] == 3 * g["candidatos"]  # radio, x, y por candidato
    entradas = simulacion.aleatorio.registro.pagina(1, g["numeros_usados"])
    assert {e.proposito for e in entradas} == {"MUNDO"}


def test_mundo_imposible_falla_con_mensaje() -> None:
    with pytest.raises(ErrorGeneracionMundo):
        mundo_de(num_obstaculos=60, num_fuentes=20, radio_patrulla=300)


def test_rejilla_cubre_todo_el_circulo() -> None:
    rejilla = RejillaEspacial(200, 200, 4)
    rejilla.marcar_obstaculo(0, 100.0, 100.0, 20.0)
    angulos = np.linspace(0, 2 * np.pi, 720)
    for r in (0.0, 10.0, 19.99):
        xs = (100 + r * np.cos(angulos)).astype(np.float32)
        ys = (100 + r * np.sin(angulos)).astype(np.float32)
        assert (rejilla.obstaculo_en(xs, ys) == 0).all()
    assert rejilla.obstaculo_en(np.array([150.0]), np.array([150.0]))[0] == -1


def test_borrar_fuente() -> None:
    rejilla = RejillaEspacial(100, 100, 4)
    rejilla.marcar_fuente(3, 50.0, 50.0, 10.0)
    assert (rejilla.mapa_alimento == 3).any()
    rejilla.borrar_fuente(3)
    assert not (rejilla.mapa_alimento == 3).any()
