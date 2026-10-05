"""Pruebas de las rutas de control, las consultas del modo didáctico y el WebSocket (E3)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.protocolo import desempaquetar_cuadro
from app.main import app


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    """Un cliente con su propio bucle de eventos y la simulación vacía al empezar."""
    with TestClient(app) as cliente:
        cliente.post("/api/simulacion/limpiar")
        yield cliente
        cliente.post("/api/simulacion/limpiar")


def configurar(cliente: TestClient, **cambios) -> None:
    cuerpo = {"num_hormigas": 200, **cambios}
    assert cliente.post("/api/simulacion/configurar", json=cuerpo).status_code == 200


def avanzar(cliente: TestClient, cuadros: int) -> None:
    """Ejecuta cuadros directamente en el controlador (sin esperar tiempo real)."""
    controlador = app.state.controlador
    for _ in range(cuadros):
        controlador.ejecutar_cuadro(float("inf"))


# --- Control ------------------------------------------------------------------------------


def test_estado_vacio(cliente: TestClient) -> None:
    datos = cliente.get("/api/simulacion/estado").json()
    assert datos["estado_controlador"] == "vacio"
    assert datos["estadisticas"] is None


@pytest.mark.parametrize("accion", ["iniciar", "pausar", "reiniciar"])
def test_acciones_sin_mundo_dan_409(cliente: TestClient, accion: str) -> None:
    assert cliente.post(f"/api/simulacion/{accion}").status_code == 409


def test_iniciar_pausar_reiniciar_limpiar(cliente: TestClient) -> None:
    configurar(cliente)
    assert cliente.post("/api/simulacion/iniciar").json()["estado_controlador"] == "corriendo"
    assert cliente.post("/api/simulacion/iniciar").status_code == 409
    assert cliente.post("/api/simulacion/pausar").json()["estado_controlador"] == "pausado"
    datos = cliente.post("/api/simulacion/reiniciar").json()
    assert datos == {"estado_controlador": "listo", "pasos_por_segundo": 30, "tick": 0}
    assert cliente.post("/api/simulacion/limpiar").json()["estado_controlador"] == "vacio"
    assert cliente.get("/api/mundo").status_code == 404


def test_velocidad_en_vivo_y_validada(cliente: TestClient) -> None:
    configurar(cliente)
    respuesta = cliente.put("/api/simulacion/velocidad", json={"pasos_por_segundo": 300})
    assert respuesta.json() == {"pasos_por_segundo": 300}
    assert cliente.get("/api/simulacion/estado").json()["pasos_por_segundo"] == 300
    for invalida in (0, 1001):
        respuesta = cliente.put("/api/simulacion/velocidad", json={"pasos_por_segundo": invalida})
        assert respuesta.status_code == 422


def test_estadisticas_en_el_estado(cliente: TestClient) -> None:
    configurar(cliente)
    avanzar(cliente, 20)
    estadisticas = cliente.get("/api/simulacion/estado").json()["estadisticas"]
    assert estadisticas["tick"] == 20
    assert estadisticas["total_hormigas"] == 200
    assert sum(estadisticas["conteo_estados"].values()) == 200
    assert len(estadisticas["alimento_por_fuente"]) == 4


# --- Modo didáctico -----------------------------------------------------------------------


def test_vista_de_hormiga(cliente: TestClient) -> None:
    configurar(cliente)
    avanzar(cliente, 30)
    vista = cliente.get("/api/hormigas/0").json()
    assert vista["id"] == 0 and vista["estado"] != "EN_NIDO"
    numero = vista["ultimo_numero"]
    assert numero["indice"] == vista["ultimo_indice_u"]
    assert numero["u"] == pytest.approx(vista["ultimo_u"])
    assert numero["calculo"]["centrales"]
    assert vista["siguiente_evento"]["descripcion"]
    assert cliente.get("/api/hormigas/200").status_code == 404


def test_bitacora_filtrada_por_hormiga_y_tipo(cliente: TestClient) -> None:
    configurar(cliente)
    avanzar(cliente, 60)
    eventos = cliente.get("/api/eventos", params={"id_hormiga": 3, "limite": 50}).json()["eventos"]
    assert eventos and all(e["id_hormiga"] == 3 for e in eventos)
    salidas = cliente.get("/api/eventos", params={"tipo": "SALIDA_NIDO", "limite": 1000}).json()["eventos"]
    assert salidas and all(e["tipo"] == "SALIDA_NIDO" for e in salidas)
    assert [e["tick"] for e in salidas] == sorted(e["tick"] for e in salidas)
    assert cliente.get("/api/eventos", params={"tipo": "VOLAR"}).status_code == 422


def test_registro_paginado(cliente: TestClient) -> None:
    configurar(cliente)
    avanzar(cliente, 30)
    datos = cliente.get("/api/aleatorio/registro", params={"desde": 1, "limite": 5}).json()
    assert [e["indice"] for e in datos["entradas"]] == [1, 2, 3, 4, 5]
    assert datos["entradas"][0]["proposito"] == "MUNDO"
    recientes = cliente.get("/api/aleatorio/registro", params={"limite": 3}).json()
    assert recientes["entradas"][-1]["indice"] == recientes["total"]


# --- WebSocket ----------------------------------------------------------------------------


def test_websocket_sin_mundo_envia_el_estado(cliente: TestClient) -> None:
    with cliente.websocket_connect("/ws/simulacion") as ws:
        assert ws.receive_json() == {
            "tipo": "control", "estado_controlador": "vacio", "pasos_por_segundo": 30, "tick": 0,
        }


def test_websocket_envia_mundo_estadisticas_y_cuadro(cliente: TestClient) -> None:
    configurar(cliente)
    with cliente.websocket_connect("/ws/simulacion") as ws:
        assert ws.receive_json()["tipo"] == "control"
        mundo = ws.receive_json()
        assert mundo["tipo"] == "mundo" and len(mundo["mundo"]["fuentes"]) == 4
        assert ws.receive_json()["tipo"] == "estadisticas"
        cuadro = desempaquetar_cuadro(ws.receive_bytes())
        assert cuadro["n"] == 200 and cuadro["tick"] == 0


def test_websocket_seleccion(cliente: TestClient) -> None:
    configurar(cliente)
    with cliente.websocket_connect("/ws/simulacion") as ws:
        for _ in range(3):
            ws.receive_json()
        ws.receive_bytes()
        ws.send_json({"tipo": "seleccionar", "id": 5})
        mensaje = ws.receive_json()
        assert mensaje["tipo"] == "seleccion" and mensaje["hormiga"]["id"] == 5
        ws.send_json({"tipo": "seleccionar", "id": 9999})
        assert ws.receive_json()["tipo"] == "error"
        ws.send_text("no es json")
        assert ws.receive_json()["tipo"] == "error"
