"""El modelo funciona con cualquier generador registrado (RF-16)."""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.aleatorio.fabrica import (
    GENERADORES,
    ConfiguracionGenerador,
    crear_generador,
    modulo_generador,
    semilla_derivada,
)
from app.config import ParametrosSimulacion
from app.eventos.tipos import TipoEvento
from app.main import app
from app.nucleo.simulacion import Simulacion

cliente = TestClient(app)
PASOS = 150


@pytest.mark.parametrize("nombre", sorted(GENERADORES))
def test_la_fabrica_crea_cada_generador(nombre: str) -> None:
    configuracion = ConfiguracionGenerador(generador=nombre)
    generador = crear_generador(configuracion, 5735)
    assert generador.modulo == modulo_generador(configuracion)
    assert all(0.0 <= generador.siguiente() < 1.0 for _ in range(100))
    assert generador.estado_interno()["metodo"] == nombre


def test_generador_desconocido() -> None:
    with pytest.raises(ValueError):
        crear_generador(ConfiguracionGenerador(generador="otro"), 1)


def test_semilla_derivada_generaliza_la_regla_k() -> None:
    assert semilla_derivada(5735, 10**4) == 735          # igual que en E2
    assert semilla_derivada(7, 16) == 15                 # (7 + 8) mod 16
    assert semilla_derivada(8, 16) == 1                  # daría 0 → 1
    parametros = ParametrosSimulacion(generador="congruencial_lineal", semilla=5735)
    assert parametros.semilla_comportamiento == 5735 + 2**30


@pytest.mark.parametrize(
    "cambios",
    [
        {"generador": "congruencial_lineal", "congruencial_a": 4},           # mcd(a, m) ≠ 1
        {"generador": "congruencial_lineal", "semilla": 2**31},              # semilla ≥ m
        {"generador": "congruencial_multiplicativo", "multiplicativo_m": 7919},
        {"generador": "cuadrados_medios", "semilla": 10_000},                # sigue valiendo 10^D
    ],
)
def test_parametros_invalidos_del_generador(cambios: dict) -> None:
    with pytest.raises(ValidationError):
        ParametrosSimulacion(**cambios)


def test_cuadrados_medios_ignora_constantes_congruenciales() -> None:
    """Un 'a' inválido para el congruencial no importa si el generador es cuadrados medios."""
    assert ParametrosSimulacion(congruencial_a=4).generador == "cuadrados_medios"


def correr(parametros: ParametrosSimulacion) -> Simulacion:
    simulacion = Simulacion(parametros)
    simulacion.avanzar(PASOS)
    return simulacion


@pytest.mark.parametrize("nombre", sorted(GENERADORES))
def test_determinismo_con_cada_generador(nombre: str) -> None:
    parametros = ParametrosSimulacion(num_hormigas=300, generador=nombre, salidas_por_paso=20)
    a, b = correr(parametros), correr(parametros)
    for columna in ("x", "y", "dir", "estado", "energia", "carga"):
        np.testing.assert_array_equal(getattr(a.mundo.hormigas, columna), getattr(b.mundo.hormigas, columna))
    assert a.aleatorio.registro.total == b.aleatorio.registro.total > 0
    entrada = a.aleatorio.registro.buscar(a.aleatorio.registro.total)
    assert entrada.generador == GENERADORES[nombre].nombre
    assert entrada.calculo["metodo"] == nombre


def test_cambiar_de_generador_cambia_el_mundo() -> None:
    cuadrados = Simulacion(ParametrosSimulacion())
    congruencial = Simulacion(ParametrosSimulacion(generador="congruencial_lineal"))
    assert cuadrados.mundo.capa_estatica()["obstaculos"] != congruencial.mundo.capa_estatica()["obstaculos"]


def test_congruencial_con_periodo_corto_se_resiembra_en_la_corrida() -> None:
    """Un mal congruencial (m = 64) completa su periodo enseguida: se ve en la bitácora."""
    parametros = ParametrosSimulacion(
        num_hormigas=200, num_obstaculos=2, num_fuentes=1, generador="congruencial_lineal",
        semilla=5, congruencial_a=5, congruencial_c=3, congruencial_m=64)
    simulacion = correr(parametros)
    assert simulacion.resumen()["resiembras"]["COMPORTAMIENTO"] > 0
    degeneraciones = simulacion.bitacora.filtrar(10, tipo=TipoEvento.GENERADOR_DEGENERADO)
    assert degeneraciones and degeneraciones[0].detalle["longitud_ciclo"] <= 64


# --- API ----------------------------------------------------------------------------------

def test_vista_previa_congruencial() -> None:
    cuerpo = {"generador": "congruencial_lineal", "semilla": 7, "congruencial_a": 5,
              "congruencial_c": 3, "congruencial_m": 16, "cantidad": 17}
    datos = cliente.post("/api/aleatorio/vista-previa", json=cuerpo).json()
    assert datos["metodo"] == "congruencial_lineal" and datos["modulo"] == 16
    assert [f["x"] for f in datos["filas"][:3]] == [6, 1, 8]
    assert datos["filas"][15]["degeneracion"]["longitud_ciclo"] == 16
    assert datos["filas"][16]["previo"] == 6
    assert datos["resiembras"] == 1


def test_vista_previa_rechaza_congruencial_invalido() -> None:
    cuerpo = {"generador": "congruencial_lineal", "semilla": 1, "congruencial_a": 4, "congruencial_m": 16}
    assert cliente.post("/api/aleatorio/vista-previa", json=cuerpo).status_code == 422


def test_laboratorio_compara_generadores() -> None:
    cuerpo = {
        "generadores": [{"generador": nombre, "semilla": 5735} for nombre in sorted(GENERADORES)],
        "cantidad": 2000, "intervalos": 10, "alfa": 0.05,
    }
    respuesta = cliente.post("/api/aleatorio/pruebas", json=cuerpo)
    assert respuesta.status_code == 200
    resultados = {r["generador"]: r for r in respuesta.json()["resultados"]}
    assert set(resultados) == set(GENERADORES)
    for resultado in resultados.values():
        assert len(resultado["pruebas"]) == 3
        assert sum(resultado["muestra"]["histograma"]) == 2000
    # Cuadrados medios con D = 4 degenera muchas veces en 2000 números; los demás, nunca.
    assert resultados["cuadrados_medios"]["resiembras"] > 0
    assert resultados["numpy"]["resiembras"] == 0
    assert resultados["congruencial_lineal"]["resiembras"] == 0


def test_laboratorio_es_reproducible() -> None:
    cuerpo = {"generadores": [{"generador": "cuadrados_medios", "semilla": 1234}], "cantidad": 500}
    a = cliente.post("/api/aleatorio/pruebas", json=cuerpo).json()
    b = cliente.post("/api/aleatorio/pruebas", json=cuerpo).json()
    assert a == b


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"generadores": []},
        {"generadores": [{"generador": "numpy", "semilla": 1}], "cantidad": 5},
        {"generadores": [{"generador": "numpy", "semilla": 1}], "alfa": 0.2},
        {"generadores": [{"generador": "numpy", "semilla": 1}], "intervalos": 1},
    ],
)
def test_laboratorio_valida_la_solicitud(cuerpo: dict) -> None:
    assert cliente.post("/api/aleatorio/pruebas", json=cuerpo).status_code == 422
