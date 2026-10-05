"""Pruebas del controlador en tiempo real (RF-31, RF-32, RF-51).

`ejecutar_cuadro()` es síncrono, así que casi todo se prueba sin bucle de eventos; sólo
`iniciar` necesita uno (se usa `asyncio.run`).
"""

import asyncio
import math

import numpy as np
import pytest

from app.api.protocolo import desempaquetar_cuadro
from app.config import ParametrosSimulacion
from app.servicio.controlador import (
    CUADROS_POR_ESTADISTICA,
    AccionInvalida,
    ControladorSimulacion,
    EstadoControlador,
)

SIN_LIMITE = math.inf  # presupuesto de tiempo infinito: siempre se hacen todos los pasos


def controlador_listo(**cambios) -> ControladorSimulacion:
    controlador = ControladorSimulacion()
    controlador.configurar(ParametrosSimulacion(num_hormigas=300, **cambios))
    return controlador


def correr_cuadros(controlador: ControladorSimulacion, cuadros: int) -> None:
    for _ in range(cuadros):
        controlador.ejecutar_cuadro(SIN_LIMITE)


def columnas(controlador: ControladorSimulacion) -> dict[str, np.ndarray]:
    return controlador.simulacion.mundo.hormigas.copia_columnas()


def assert_iguales(a: dict[str, np.ndarray], b: dict[str, np.ndarray]) -> None:
    for columna, valores in a.items():
        np.testing.assert_array_equal(valores, b[columna], err_msg=columna)


# --- Estados del controlador -------------------------------------------------------------


def test_empieza_vacio_y_configurar_lo_deja_listo() -> None:
    controlador = ControladorSimulacion()
    assert controlador.estado is EstadoControlador.VACIO
    controlador.configurar(ParametrosSimulacion(num_hormigas=10))
    assert controlador.estado is EstadoControlador.LISTO
    assert controlador.simulacion.tick == 0


@pytest.mark.parametrize("accion", ["iniciar", "pausar", "reiniciar"])
def test_acciones_invalidas_sin_mundo(accion: str) -> None:
    with pytest.raises(AccionInvalida):
        getattr(ControladorSimulacion(), accion)()


def test_pausar_sin_correr_es_invalido() -> None:
    with pytest.raises(AccionInvalida):
        controlador_listo().pausar()


def test_ciclo_iniciar_pausar_reiniciar_limpiar() -> None:
    async def recorrido() -> list[EstadoControlador]:
        controlador = controlador_listo()
        estados = []
        controlador.iniciar()
        estados.append(controlador.estado)
        with pytest.raises(AccionInvalida):
            controlador.iniciar()  # ya está corriendo
        await asyncio.sleep(0.1)  # deja correr algunos cuadros
        controlador.pausar()
        estados.append(controlador.estado)
        assert controlador.simulacion.tick > 0
        controlador.iniciar()
        controlador.reiniciar()
        estados.append(controlador.estado)
        assert controlador.simulacion.tick == 0
        controlador.limpiar()
        estados.append(controlador.estado)
        assert controlador.simulacion is None
        return estados

    assert asyncio.run(recorrido()) == [
        EstadoControlador.CORRIENDO, EstadoControlador.PAUSADO,
        EstadoControlador.LISTO, EstadoControlador.VACIO,
    ]


def test_configurar_fallido_conserva_la_corrida_anterior() -> None:
    from app.modelo.generacion_mundo import ErrorGeneracionMundo

    controlador = controlador_listo()
    anterior = controlador.simulacion
    with pytest.raises(ErrorGeneracionMundo):
        controlador.configurar(ParametrosSimulacion(num_obstaculos=60, num_fuentes=20, radio_patrulla=300))
    assert controlador.simulacion is anterior


# --- Reloj real frente a reloj de simulación -----------------------------------------------


@pytest.mark.parametrize("pasos_por_segundo, cuadros, esperados", [
    (30, 10, 10), (300, 10, 100), (45, 10, 15), (1, 30, 1), (1000, 3, 100),
])
def test_pasos_por_cuadro_acumulan_la_fraccion(pasos_por_segundo: int, cuadros: int, esperados: int) -> None:
    controlador = controlador_listo()
    controlador.fijar_velocidad(pasos_por_segundo)
    correr_cuadros(controlador, cuadros)
    assert controlador.simulacion.tick == esperados


def test_presupuesto_agotado_corta_los_pasos() -> None:
    controlador = controlador_listo()
    controlador.fijar_velocidad(1000)
    hechos = controlador.ejecutar_cuadro(presupuesto=0.0)
    assert hechos == 1  # al menos un paso por cuadro; el resto se descarta
    assert controlador.simulacion.tick == 1


def test_la_velocidad_no_cambia_el_resultado() -> None:
    """RF-32: a 30, 45 o 300 pasos/s, tras los mismos 300 pasos el estado es idéntico."""
    lento = controlador_listo()
    correr_cuadros(lento, 300)
    medio = controlador_listo()
    medio.fijar_velocidad(45)
    correr_cuadros(medio, 200)
    rapido = controlador_listo()
    rapido.fijar_velocidad(300)
    correr_cuadros(rapido, 30)
    assert lento.simulacion.tick == medio.simulacion.tick == rapido.simulacion.tick == 300
    assert_iguales(columnas(lento), columnas(medio))
    assert_iguales(columnas(lento), columnas(rapido))


def test_cambiar_velocidad_a_mitad_de_corrida() -> None:
    fijo = controlador_listo()
    correr_cuadros(fijo, 200)
    variable = controlador_listo()
    correr_cuadros(variable, 50)       # 50 pasos
    variable.fijar_velocidad(150)
    correr_cuadros(variable, 30)       # 150 pasos
    assert variable.simulacion.tick == 200
    assert_iguales(columnas(fijo), columnas(variable))


def test_reiniciar_reproduce_la_misma_corrida() -> None:
    """RF-31: reiniciar dos veces y correr N pasos da el mismo estado."""
    controlador = controlador_listo()
    correr_cuadros(controlador, 150)
    primera = columnas(controlador)
    numeros = controlador.simulacion.aleatorio.total_generados
    controlador.reiniciar()
    correr_cuadros(controlador, 150)
    assert_iguales(primera, columnas(controlador))
    assert controlador.simulacion.aleatorio.total_generados == numeros


# --- Suscriptores y selección --------------------------------------------------------------


def test_suscripcion_recibe_estado_inicial() -> None:
    controlador = controlador_listo()
    mensajes = controlador.suscribir().pendientes()
    tipos = [m["tipo"] for m in mensajes if isinstance(m, dict)]
    assert tipos == ["control", "mundo", "estadisticas"]
    cuadro = desempaquetar_cuadro(mensajes[-1])
    assert cuadro["n"] == 300 and cuadro["tick"] == 0


def test_suscripcion_conserva_solo_el_ultimo_cuadro() -> None:
    controlador = controlador_listo()
    suscripcion = controlador.suscribir()
    suscripcion.pendientes()
    correr_cuadros(controlador, 5)
    cuadros = [m for m in suscripcion.pendientes() if isinstance(m, bytes)]
    assert len(cuadros) == 1
    assert desempaquetar_cuadro(cuadros[0])["tick"] == 5


def test_estadisticas_cada_pocos_cuadros() -> None:
    controlador = controlador_listo()
    suscripcion = controlador.suscribir()
    suscripcion.pendientes()
    correr_cuadros(controlador, CUADROS_POR_ESTADISTICA * 3)
    estadisticas = [m for m in suscripcion.pendientes() if isinstance(m, dict) and m["tipo"] == "estadisticas"]
    assert len(estadisticas) == 3
    assert estadisticas[-1]["tick"] == CUADROS_POR_ESTADISTICA * 3


def test_seleccion_envia_la_vista_de_la_hormiga() -> None:
    controlador = controlador_listo()
    suscripcion = controlador.suscribir()
    correr_cuadros(controlador, 30)
    suscripcion.pendientes()
    controlador.seleccionar(suscripcion, 3)
    (mensaje,) = suscripcion.pendientes()
    assert mensaje["tipo"] == "seleccion"
    vista = mensaje["hormiga"]
    assert vista["id"] == 3
    assert {"x", "y", "dir", "estado", "ultimo_numero", "siguiente_evento"} <= vista.keys()
    with pytest.raises(AccionInvalida):
        controlador.seleccionar(suscripcion, 300)


def test_la_seleccion_no_cambia_la_simulacion() -> None:
    """RF-51: una corrida con hormiga seleccionada es idéntica a una sin selección."""
    sin_seleccion = controlador_listo()
    correr_cuadros(sin_seleccion, 400)

    con_seleccion = controlador_listo()
    suscripcion = con_seleccion.suscribir()
    con_seleccion.seleccionar(suscripcion, 0)
    otra = con_seleccion.suscribir()
    con_seleccion.seleccionar(otra, 7)
    correr_cuadros(con_seleccion, 400)

    assert_iguales(columnas(sin_seleccion), columnas(con_seleccion))
    assert (sin_seleccion.simulacion.aleatorio.total_generados
            == con_seleccion.simulacion.aleatorio.total_generados)


def test_configurar_borra_las_selecciones() -> None:
    """Una corrida nueva con menos hormigas no debe dejar selecciones a ids inexistentes."""
    controlador = controlador_listo()
    suscripcion = controlador.suscribir()
    controlador.seleccionar(suscripcion, 250)
    suscripcion.pendientes()
    controlador.configurar(ParametrosSimulacion(num_hormigas=10))
    assert suscripcion.seleccion is None
    assert {"tipo": "deseleccion"} in suscripcion.pendientes()
    correr_cuadros(controlador, CUADROS_POR_ESTADISTICA)  # no falla al publicar
