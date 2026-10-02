"""Pruebas de la predicción del siguiente evento (DISENO.md §10.9)."""

import numpy as np

from app.config import ParametrosSimulacion
from app.eventos.prediccion import predecir
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.nucleo.simulacion import Simulacion


def test_predecir_no_altera_la_simulacion() -> None:
    """Una corrida con hormigas "seleccionadas" es idéntica a una sin selección."""
    parametros = ParametrosSimulacion(num_hormigas=400)
    sin_seleccion = Simulacion(parametros)
    sin_seleccion.avanzar(600)

    con_seleccion = Simulacion(parametros)
    for _ in range(600):
        con_seleccion.paso()
        if con_seleccion.tick % 50 == 0:
            for id_hormiga in range(0, 400, 7):
                predecir(con_seleccion.mundo, parametros, id_hormiga)

    assert con_seleccion.aleatorio.total_generados == sin_seleccion.aleatorio.total_generados
    a = sin_seleccion.mundo.hormigas.copia_columnas()
    for columna, valores in con_seleccion.mundo.hormigas.copia_columnas().items():
        np.testing.assert_array_equal(valores, a[columna], err_msg=columna)


def test_prediccion_en_el_nido() -> None:
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=10))
    prediccion = predecir(simulacion.mundo, simulacion.parametros, 0)
    assert prediccion.tipo is TipoEvento.SALIDA_NIDO
    assert prediccion.aleatorio


def test_prediccion_de_colision_se_cumple() -> None:
    """Si se predice una colisión en k pasos (sin otros eventos antes), ocurre en ese paso."""
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=200, num_obstaculos=30))
    simulacion.avanzar(200)
    h = simulacion.mundo.hormigas
    verificadas = 0
    for id_hormiga in np.flatnonzero(h.estado == EstadoHormiga.BUSCANDO_COMIDA)[:40].tolist():
        prediccion = predecir(simulacion.mundo, simulacion.parametros, id_hormiga)
        if prediccion.tipo is TipoEvento.COLISION_PREVISTA and prediccion.pasos <= 30:
            copia = Simulacion(simulacion.parametros, capacidad_bitacora=1_000_000)
            copia.avanzar(simulacion.tick)
            tick_esperado = simulacion.tick + prediccion.pasos
            copia.avanzar(prediccion.pasos)
            colisiones = [
                e for e in copia.bitacora.ultimos(copia.bitacora.total)
                if e.id_hormiga == id_hormiga and e.tipo is TipoEvento.COLISION_PREVISTA
            ]
            assert colisiones and colisiones[-1].tick == tick_esperado
            verificadas += 1
            if verificadas == 3:
                break
    assert verificadas > 0
