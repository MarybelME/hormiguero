"""Exportación a CSV (RF-61) y réplicas por lote (RF-60)."""

import csv
import io
import math
import time
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from app.config import ParametrosSimulacion
from app.estadisticas.exportar import (
    BOM,
    ENCABEZADOS_REGISTRO,
    escribir_lote,
    escribir_series,
    exportar_corrida,
    formatear,
)
from app.estadisticas.replicas import (
    VARIABLES_SALIDA,
    ejecutar_lote,
    resumir,
    semillas_del_lote,
    t_975,
)
from app.estadisticas.series import COLUMNAS, PASOS_POR_MUESTRA
from app.main import app
from app.nucleo.simulacion import Simulacion

PARAMETROS = ParametrosSimulacion(num_hormigas=300, salidas_por_paso=20)
PASOS = 120


def leer_csv(texto: str) -> list[list[str]]:
    assert texto.startswith(BOM)
    return list(csv.reader(io.StringIO(texto[len(BOM):]), delimiter=";"))


def a_numero(texto: str) -> float:
    return float(texto.replace(",", "."))


def exportar(parametros: ParametrosSimulacion, pasos: int, que: str) -> list[list[str]]:
    destino = io.StringIO(newline="")
    exportar_corrida(parametros, pasos, que, destino)
    return leer_csv(destino.getvalue())


# --- Formato ----------------------------------------------------------------------------------

def test_formato_para_excel_en_espanol() -> None:
    assert formatear(0.8902) == "0,8902"
    assert formatear(1 / 3) == "0,333333333333"
    assert formatear(12) == "12"
    assert formatear(None) == ""
    assert formatear(True) == "sí"


# --- Re-ejecución de la corrida ---------------------------------------------------------------

def test_registro_completo_coincide_con_la_corrida_en_vivo() -> None:
    """El CSV re-ejecutado tiene todos los números, y los que siguen en el búfer son idénticos."""
    vivo = Simulacion(PARAMETROS, capacidad_registro=500)
    vivo.avanzar(PASOS)
    filas = exportar(PARAMETROS, PASOS, "registro")
    assert filas[0] == ENCABEZADOS_REGISTRO
    datos = filas[1:]
    assert len(datos) == vivo.aleatorio.registro.total > 500  # más de lo que cabe en el búfer
    assert [int(f[0]) for f in datos] == list(range(1, len(datos) + 1))
    for entrada in vivo.aleatorio.registro.pagina(1, 10_000):
        fila = datos[entrada.indice - 1]
        assert fila[3] == entrada.proposito
        assert a_numero(fila[10]) == pytest.approx(entrada.u, rel=1e-11)
        assert int(fila[5]) == entrada.tick


def test_bitacora_completa_coincide_con_la_corrida_en_vivo() -> None:
    vivo = Simulacion(PARAMETROS, capacidad_bitacora=100)
    vivo.avanzar(PASOS)
    datos = exportar(PARAMETROS, PASOS, "bitacora")[1:]
    assert len(datos) == vivo.bitacora.total > 100
    ultimos = vivo.bitacora.ultimos(100)
    for fila, evento in zip(datos[-100:], ultimos, strict=True):
        assert fila[2] == evento.tipo.name
        assert int(fila[0]) == evento.tick


def test_exportar_rechaza_otro_contenido() -> None:
    with pytest.raises(ValueError):
        exportar_corrida(PARAMETROS, 1, "hormigas", io.StringIO())


def test_el_registro_muestra_el_calculo_de_cada_metodo() -> None:
    lineal = ParametrosSimulacion(num_hormigas=50, generador="congruencial_lineal")
    fila = exportar(lineal, 1, "registro")[1]
    assert fila[2] == "Congruencial lineal"
    assert "mod 2147483648" in fila[8]
    fila = exportar(PARAMETROS, 1, "registro")[1]
    assert fila[8].startswith("x² = ") and "centrales" in fila[8]


# --- Series -------------------------------------------------------------------------------------

def test_series_una_muestra_cada_segundo_simulado() -> None:
    simulacion = Simulacion(PARAMETROS)
    simulacion.avanzar(PASOS)
    filas = simulacion.series.filas
    assert [f["tick"] for f in filas] == list(range(0, PASOS + 1, PASOS_POR_MUESTRA))
    ultima = filas[-1]
    assert ultima["numeros_generados"] == simulacion.aleatorio.total_generados
    estados = [ultima[c] for c in COLUMNAS if c.startswith("estado_")]
    assert sum(estados) == PARAMETROS.num_hormigas


def test_csv_de_series() -> None:
    simulacion = Simulacion(PARAMETROS)
    simulacion.avanzar(30)
    destino = io.StringIO(newline="")
    assert escribir_series(destino, simulacion.series.filas) == 4
    filas = leer_csv(destino.getvalue())
    assert filas[0][:2] == ["Paso", "Tiempo (s)"]
    assert [f[0] for f in filas[1:]] == ["0", "10", "20", "30"]
    assert filas[2][1] == "1"  # 10 pasos · 0.1 s


# --- Réplicas -------------------------------------------------------------------------------------

def test_semillas_consecutivas_dan_la_vuelta() -> None:
    assert semillas_del_lote(5735, 3, 10_000) == [5735, 5736, 5737]
    assert semillas_del_lote(9998, 3, 10_000) == [9998, 9999, 1]


def test_t_de_student_contra_tabla() -> None:
    assert t_975(1) == 12.706
    assert t_975(4) == 2.776
    assert t_975(29) == 2.045
    assert t_975(35) == 2.042   # conservador: el de 30 gl
    assert t_975(5000) == 1.960


def test_intervalo_de_confianza_a_mano() -> None:
    """x = 1, 2, 3, 4, 5: media 3; s = √(10/4) = 1.5811; IC = 3 ± 2.776 · 1.5811 / √5 = 3 ± 2.776 · 0.70711 = 3 ± 1.96293."""
    r = resumir("alimento_recolectado", [1, 2, 3, 4, 5])
    assert r.media == 3
    assert r.desviacion == pytest.approx(math.sqrt(2.5))
    assert r.ic_inferior == pytest.approx(3 - 1.96293, abs=1e-5)
    assert r.ic_superior == pytest.approx(3 + 1.96293, abs=1e-5)
    assert (r.minimo, r.maximo) == (1, 5)


def test_resumen_ignora_replicas_sin_valor() -> None:
    r = resumir("proporcion_seguir", [None, 0.5, None])
    assert r.n == 1 and r.media == 0.5 and r.ic_inferior is None
    assert resumir("proporcion_seguir", [None, None]).media is None


def test_el_mismo_lote_dos_veces_da_lo_mismo() -> None:
    """Criterio de RF-60."""
    a = ejecutar_lote(PARAMETROS, replicas=3, pasos=80)
    b = ejecutar_lote(PARAMETROS, replicas=3, pasos=80)
    assert asdict(a) == asdict(b)
    assert a.semillas == [5735, 5736, 5737]
    assert len(a.replicas) == 3 and set(a.replicas[0]) == {"semilla", *VARIABLES_SALIDA}
    # Las réplicas son distintas entre sí (semillas distintas)
    assert len({r["numeros_generados"] for r in a.replicas}) > 1


def test_lote_cancelado_y_avance() -> None:
    avance = []
    resultado = ejecutar_lote(PARAMETROS, replicas=5, pasos=10,
                              al_terminar_replica=lambda h, t: avance.append((h, t)),
                              cancelado=lambda: len(avance) >= 2)
    assert avance == [(1, 5), (2, 5)]
    assert len(resultado.replicas) == 2


def test_csv_del_lote() -> None:
    destino = io.StringIO(newline="")
    escribir_lote(destino, ejecutar_lote(PARAMETROS, replicas=2, pasos=20))
    filas = leer_csv(destino.getvalue())
    assert filas[0][:2] == ["Réplica", "Semilla"]
    assert [f[1] for f in filas[1:3]] == ["5735", "5736"]
    assert filas[3] == []
    assert filas[5][0] == "Variable"
    assert len(filas) == 6 + len(VARIABLES_SALIDA)


# --- API --------------------------------------------------------------------------------------------

@pytest.fixture
def cliente():
    with TestClient(app) as c:
        c.post("/api/simulacion/limpiar")
        yield c
        c.post("/api/simulacion/limpiar")


def esperar_lote(cliente: TestClient, estados=("terminado", "cancelado", "error")) -> dict:
    for _ in range(600):
        datos = cliente.get("/api/experimentos").json()
        if datos["estado"] in estados:
            return datos
        time.sleep(0.05)
    raise AssertionError("el lote no terminó")


def test_exportar_sin_corrida(cliente: TestClient) -> None:
    assert cliente.get("/api/exportar/registro.csv").status_code == 404
    assert cliente.get("/api/exportar/otra.csv").status_code == 422


def test_exportar_por_la_api(cliente: TestClient) -> None:
    cliente.post("/api/simulacion/configurar", json={"num_hormigas": 200})
    for que, encabezado in (("registro", "Índice"), ("bitacora", "Paso"), ("series", "Paso")):
        respuesta = cliente.get(f"/api/exportar/{que}.csv")
        assert respuesta.status_code == 200
        assert respuesta.headers["content-type"].startswith("text/csv")
        assert f"{que}_semilla5735_paso0.csv" in respuesta.headers["content-disposition"]
        filas = leer_csv(respuesta.content.decode("utf-8"))
        assert filas[0][0] == encabezado
    # En t = 0 el registro tiene los números con que se generó el mundo
    filas = leer_csv(cliente.get("/api/exportar/registro.csv").content.decode("utf-8"))
    assert {f[3] for f in filas[1:]} == {"MUNDO"}


def test_lote_por_la_api(cliente: TestClient) -> None:
    cuerpo = {"parametros": {"num_hormigas": 100}, "replicas": 3, "pasos": 30}
    assert cliente.post("/api/experimentos", json=cuerpo).status_code == 200
    datos = esperar_lote(cliente)
    assert datos["estado"] == "terminado" and datos["hechas"] == 3
    assert [r["semilla"] for r in datos["resultado"]["replicas"]] == [5735, 5736, 5737]
    respuesta = cliente.get("/api/experimentos/resultado.csv")
    assert respuesta.status_code == 200
    assert leer_csv(respuesta.content.decode("utf-8"))[0][0] == "Réplica"
    # Mismo lote por la API y directamente: idéntico
    directo = ejecutar_lote(ParametrosSimulacion(num_hormigas=100), replicas=3, pasos=30)
    assert datos["resultado"]["replicas"] == directo.replicas


def test_lote_un_solo_a_la_vez_y_cancelable(cliente: TestClient) -> None:
    grande = {"parametros": {"num_hormigas": 1000}, "replicas": 30, "pasos": 5000}
    assert cliente.post("/api/experimentos", json=grande).status_code == 200
    assert cliente.post("/api/experimentos", json=grande).status_code == 409
    assert cliente.post("/api/experimentos/cancelar").status_code == 200
    datos = esperar_lote(cliente)
    assert datos["estado"] == "cancelado" and datos["hechas"] < 30
    assert cliente.post("/api/experimentos/cancelar").status_code == 409


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"parametros": {}, "replicas": 1},
        {"parametros": {}, "replicas": 31},
        {"parametros": {}, "pasos": 5001},
        {"parametros": {"num_hormigas": 20_000}, "replicas": 30, "pasos": 5000},  # demasiado trabajo
        {"parametros": {"p_seguir_reina": 2}},
    ],
)
def test_lote_valida_la_solicitud(cliente: TestClient, cuerpo: dict) -> None:
    assert cliente.post("/api/experimentos", json=cuerpo).status_code == 422


def test_informe_de_generadores_en_csv(cliente: TestClient) -> None:
    cuerpo = {"generadores": [{"generador": "cuadrados_medios", "semilla": 5735},
                              {"generador": "numpy", "semilla": 5735}], "cantidad": 500}
    respuesta = cliente.post("/api/aleatorio/pruebas.csv", json=cuerpo)
    filas = leer_csv(respuesta.content.decode("utf-8"))
    assert filas[0] == ["", "Cuadrados medios", "NumPy (PCG64, referencia)"]
    titulos = [f[0] for f in filas]
    assert "Re-siembras (degeneraciones)" in titulos
    assert any(t.startswith("Frecuencia en [0;") for t in titulos)
