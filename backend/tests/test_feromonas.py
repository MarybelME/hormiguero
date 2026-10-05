"""Campo de feromonas y su comportamiento (RF-70)."""

import asyncio

import numpy as np
import pytest

from app.api.protocolo import (
    TAMANO_ENCABEZADO_FEROMONAS,
    TIPO_FEROMONAS,
    desempaquetar_feromonas,
    empaquetar_feromonas,
)
from app.comportamiento.feromonas import decidir_giro, orientar_por_feromonas
from app.config import ParametrosSimulacion
from app.modelo.feromonas import CampoFeromonas
from app.nucleo.contexto import ContextoPaso
from app.nucleo.simulacion import Simulacion
from app.servicio.controlador import ControladorSimulacion

CON_FEROMONAS = ParametrosSimulacion(num_hormigas=600, salidas_por_paso=10, feromonas_activas=True)


def campo_pequeno() -> CampoFeromonas:
    return CampoFeromonas(ancho=20, alto=10, tamano_celda=5, maxima=50, minima=0.01)  # 4 × 2 celdas


# --- CampoFeromonas ---------------------------------------------------------------------------

def test_depositar_acumula_por_celda_y_satura() -> None:
    campo = campo_pequeno()
    assert (campo.filas, campo.columnas) == (2, 4)
    campo.depositar(np.array([1.0, 2.0, 12.0]), np.array([1.0, 3.0, 7.0]), 4.0)
    assert campo.concentracion[0, 0] == 8.0   # dos hormigas en la misma celda
    assert campo.concentracion[1, 2] == 4.0   # x = 12 → columna 2; y = 7 → fila 1
    campo.depositar(np.array([1.0] * 20), np.array([1.0] * 20), 4.0)
    assert campo.concentracion[0, 0] == 50.0  # saturación en la máxima


def test_depositar_fuera_del_mundo_no_hace_nada() -> None:
    campo = campo_pequeno()
    campo.depositar(np.array([-1.0, 25.0]), np.array([1.0, 1.0]), 4.0)
    assert campo.total() == 0


def test_evaporacion_geometrica() -> None:
    """Sin depósitos, tras k pasos queda c₀ · (1 − ρ)^k."""
    campo = campo_pequeno()
    campo.depositar(np.array([1.0]), np.array([1.0]), 10.0)
    for _ in range(20):
        campo.evaporar(0.1)
    assert campo.concentracion[0, 0] == pytest.approx(10 * 0.9**20, rel=1e-5)


def test_evaporacion_borra_lo_que_queda_bajo_la_minima() -> None:
    campo = campo_pequeno()
    campo.depositar(np.array([1.0]), np.array([1.0]), 0.02)
    campo.evaporar(0.6)  # 0.008 < 0.01
    assert campo.total() == 0


def test_muestrear_y_cuantizar() -> None:
    campo = campo_pequeno()
    campo.depositar(np.array([6.0]), np.array([1.0]), 25.0)
    assert campo.muestrear(np.array([7.0, 100.0, -3.0]), np.array([2.0, 1.0, 1.0])).tolist() == [25.0, 0.0, 0.0]
    cuantizado = campo.cuantizado()
    assert cuantizado.dtype == np.uint8
    assert cuantizado[0, 1] == 128  # 25 / 50 · 255 = 127.5 → 128
    assert cuantizado.sum() == 128


# --- Regla de los sensores ----------------------------------------------------------------------

@pytest.mark.parametrize(
    ("izquierda", "frente", "derecha", "giro"),
    [
        (0.2, 0.1, 0.3, 0),    # nada llega al umbral 0.5
        (1.0, 2.0, 1.5, 0),    # el frente es el mayor
        (3.0, 1.0, 2.0, 1),    # izquierda
        (1.0, 1.0, 4.0, -1),   # derecha
        (2.0, 1.0, 2.0, 1),    # empate entre lados: izquierda
        (2.0, 2.0, 0.0, 0),    # empate con el frente: gana el frente
    ],
)
def test_decision_de_giro(izquierda: float, frente: float, derecha: float, giro: int) -> None:
    lecturas = np.array([[izquierda, frente, derecha]], dtype=np.float32)
    assert decidir_giro(lecturas, umbral=0.5)[0] == giro


def test_seguir_feromonas_no_consume_numeros() -> None:
    simulacion = Simulacion(CON_FEROMONAS)
    simulacion.avanzar(300)
    assert simulacion.estadisticas.giros_feromona > 0
    antes = simulacion.aleatorio.total_generados
    direcciones = simulacion.mundo.hormigas.dir.copy()
    ctx = ContextoPaso(simulacion.tick, simulacion.tiempo, simulacion.dt, simulacion.mundo,
                       simulacion.parametros, simulacion.aleatorio, simulacion.bitacora,
                       simulacion.estadisticas)
    orientar_por_feromonas(ctx)
    assert simulacion.aleatorio.total_generados == antes
    assert not np.array_equal(direcciones, simulacion.mundo.hormigas.dir)  # sí giró alguna


# --- Simulación con feromonas -------------------------------------------------------------------

def test_desactivadas_no_hay_campo() -> None:
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=50))
    assert simulacion.feromonas is None
    assert simulacion.resumen()["feromona_total"] is None


def test_determinismo_con_feromonas() -> None:
    a, b = Simulacion(CON_FEROMONAS), Simulacion(CON_FEROMONAS)
    a.avanzar(400)
    b.avanzar(400)
    for columna in ("x", "y", "dir", "estado", "carga"):
        np.testing.assert_array_equal(getattr(a.mundo.hormigas, columna), getattr(b.mundo.hormigas, columna))
    np.testing.assert_array_equal(a.feromonas.concentracion, b.feromonas.concentracion)
    assert a.feromonas.total() > 0


def test_reiniciar_borra_el_campo() -> None:
    simulacion = Simulacion(CON_FEROMONAS)
    simulacion.avanzar(400)
    simulacion.reiniciar()
    assert simulacion.feromonas.total() == 0


def test_conservacion_del_alimento_con_feromonas() -> None:
    simulacion = Simulacion(CON_FEROMONAS)
    inicial = simulacion.alimento_total()
    for _ in range(500):
        simulacion.paso()
        assert simulacion.alimento_total() == inicial


def test_las_rutas_aceleran_la_recoleccion() -> None:
    """Con la misma semilla, las feromonas llevan más alimento al nido en el mismo tiempo."""
    base = dict(num_hormigas=3000, salidas_por_paso=10)
    sin = Simulacion(ParametrosSimulacion(**base))
    con = Simulacion(ParametrosSimulacion(**base, feromonas_activas=True))
    sin.avanzar(1000)
    con.avanzar(1000)
    assert con.estadisticas.alimento_recolectado > 1.5 * sin.estadisticas.alimento_recolectado
    # El rastro existe y está concentrado en pocas celdas (rutas, no una mancha uniforme)
    ocupadas = (con.feromonas.concentracion > 0).mean()
    assert 0 < ocupadas < 0.15  # ~6 % con esta semilla; una mancha uniforme cubriría casi todo


def test_vista_de_la_hormiga_incluye_sus_sensores() -> None:
    simulacion = Simulacion(CON_FEROMONAS)
    simulacion.avanzar(50)
    vista = simulacion.vista_hormiga(0)
    assert set(vista["feromonas"]) == {"izquierda", "frente", "derecha", "umbral", "giro", "aqui"}


# --- Protocolo y controlador -------------------------------------------------------------------

def test_protocolo_feromonas_byte_a_byte() -> None:
    campo = campo_pequeno()
    campo.depositar(np.array([6.0, 16.0]), np.array([1.0, 8.0]), 50.0)
    datos = empaquetar_feromonas(77, campo)
    assert len(datos) == TAMANO_ENCABEZADO_FEROMONAS + 8 == 28
    assert datos[0] == 1 and datos[1] == TIPO_FEROMONAS
    assert int.from_bytes(datos[2:4], "little") == 4      # columnas
    assert int.from_bytes(datos[4:8], "little") == 77     # tick
    assert int.from_bytes(datos[8:10], "little") == 2     # filas
    assert list(datos[20:]) == [0, 255, 0, 0, 0, 0, 0, 255]  # fila 0, luego fila 1
    leido = desempaquetar_feromonas(datos)
    assert leido["tamano_celda"] == 5.0 and leido["maxima"] == 50.0
    np.testing.assert_array_equal(leido["valores"], campo.cuantizado())


def test_el_controlador_envia_el_campo() -> None:
    async def escenario() -> list:
        controlador = ControladorSimulacion()
        controlador.configurar(CON_FEROMONAS)
        suscripcion = controlador.suscribir()
        suscripcion.pendientes()
        controlador.pasos_por_segundo = 300
        for _ in range(8):  # CUADROS_POR_ESTADISTICA
            controlador.ejecutar_cuadro(presupuesto=10.0)
        return suscripcion.pendientes()

    binarios = [m for m in asyncio.run(escenario()) if isinstance(m, bytes)]
    assert [m[1] for m in binarios] == [TIPO_FEROMONAS, 1]  # campo y luego el cuadro


def test_sin_feromonas_no_se_envia_campo() -> None:
    async def escenario() -> list:
        controlador = ControladorSimulacion()
        controlador.configurar(ParametrosSimulacion(num_hormigas=50))
        return controlador.suscribir().pendientes()

    assert [m[1] for m in asyncio.run(escenario()) if isinstance(m, bytes)] == [1]
