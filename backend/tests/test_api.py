"""Pruebas de la API REST y del servido del frontend."""

import pytest
from fastapi.testclient import TestClient

from app import __version__
from app.main import app

cliente = TestClient(app)


def test_salud() -> None:
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "version": __version__}


def test_raiz_sirve_el_frontend() -> None:
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert 'id="capa-estatica"' in respuesta.text
    assert 'id="capa-dinamica"' in respuesta.text


def test_vista_previa_semilla_5735() -> None:
    respuesta = cliente.post(
        "/api/aleatorio/vista-previa", json={"semilla": 5735, "digitos": 4, "cantidad": 6}
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert [f["u"] for f in datos["filas"]] == [0.8902, 0.2456, 0.0319, 0.1017, 0.0342, 0.1169]
    primera = datos["filas"][0]
    assert primera["relleno"] == "32890225"
    assert primera["centrales"] == "8902"
    assert primera["angulo"] == pytest.approx(320.472)
    assert datos["resiembras"] == 0


def test_vista_previa_marca_degeneracion_y_resiembra() -> None:
    respuesta = cliente.post("/api/aleatorio/vista-previa", json={"semilla": 6100, "cantidad": 5})
    datos = respuesta.json()
    degeneracion = datos["filas"][3]["degeneracion"]
    assert degeneracion["tipo"] == "CICLO"
    assert degeneracion["longitud_ciclo"] == 4
    assert degeneracion["semilla_nueva"] == (6100 + datos["paso_resiembra"]) % 10_000
    assert datos["filas"][4]["previo"] == degeneracion["semilla_nueva"]
    assert datos["resiembras"] == 1


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"semilla": 0},
        {"semilla": 10_000, "digitos": 4},
        {"semilla": 5735, "digitos": 5},
        {"semilla": 5735, "cantidad": 0},
        {"semilla": 5735, "cantidad": 100_000},
        {"semilla": 5735, "generador": "congruencial"},
    ],
)
def test_vista_previa_rechaza_parametros_invalidos(cuerpo: dict) -> None:
    assert cliente.post("/api/aleatorio/vista-previa", json=cuerpo).status_code == 422


def test_parametros_por_defecto_y_esquema() -> None:
    datos = cliente.get("/api/parametros").json()
    assert datos["valores"]["num_hormigas"] == 2000
    assert datos["esquema"]["properties"]["p_seguir_reina"]["maximum"] == 1.0


def test_configurar_y_consultar_mundo() -> None:
    respuesta = cliente.post("/api/simulacion/configurar", json={"semilla": 5735})
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["semillas"] == {"MUNDO": 5735, "COMPORTAMIENTO": 735}
    assert len(datos["mundo"]["obstaculos"]) == 12 and len(datos["mundo"]["fuentes"]) == 4
    assert cliente.get("/api/mundo").json() == datos


def test_misma_semilla_mismo_mundo_por_la_api() -> None:
    a = cliente.post("/api/simulacion/configurar", json={"semilla": 4321}).json()
    b = cliente.post("/api/simulacion/configurar", json={"semilla": 4321}).json()
    assert a == b


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"num_hormigas": 0},
        {"semilla": 10_000},
        {"p_seguir_reina": 2},
        {"num_obstaculos": 60, "num_fuentes": 20, "radio_patrulla": 300},  # no cabe
    ],
)
def test_configurar_rechaza_parametros_invalidos(cuerpo: dict) -> None:
    assert cliente.post("/api/simulacion/configurar", json=cuerpo).status_code == 422
