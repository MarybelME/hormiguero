"""Pruebas del motor de simulación (RF-04, RF-20 a RF-25, RNF-01)."""

import math

import numpy as np
import pytest

from app.aleatorio.variables import angulo
from app.comportamiento.transiciones import cambiar_estado
from app.config import ParametrosSimulacion
from app.eventos.tipos import TipoEvento
from app.modelo.estados import (
    MATRIZ_TRANSICIONES,
    EstadoHormiga,
    TransicionInvalida,
)
from app.nucleo.contexto import ContextoPaso
from app.nucleo.simulacion import Simulacion

E = EstadoHormiga
CAPACIDAD_GRANDE = 5_000_000  # las pruebas revisan eventos y números antiguos


def simular(pasos: int, **cambios) -> Simulacion:
    simulacion = Simulacion(ParametrosSimulacion(**cambios), CAPACIDAD_GRANDE, CAPACIDAD_GRANDE)
    simulacion.avanzar(pasos)
    return simulacion


def eventos(simulacion: Simulacion, tipo: TipoEvento) -> list:
    return [e for e in simulacion.bitacora.ultimos(simulacion.bitacora.total) if e.tipo is tipo]


# --- Reproducibilidad --------------------------------------------------------------------


def test_determinismo() -> None:
    """RNF-01: misma configuración ⇒ arreglos idénticos tras N pasos."""
    a = simular(1500, num_hormigas=1000).mundo.hormigas.copia_columnas()
    b = simular(1500, num_hormigas=1000).mundo.hormigas.copia_columnas()
    for columna, valores in a.items():
        np.testing.assert_array_equal(valores, b[columna], err_msg=columna)


def test_reiniciar_repite_la_corrida() -> None:
    simulacion = simular(500, num_hormigas=500)
    antes = simulacion.mundo.hormigas.copia_columnas()
    simulacion.reiniciar()
    assert simulacion.tick == 0
    simulacion.avanzar(500)
    for columna, valores in simulacion.mundo.hormigas.copia_columnas().items():
        np.testing.assert_array_equal(valores, antes[columna], err_msg=columna)


# --- Invariantes en cada paso ---------------------------------------------------------------


def test_invariantes_en_cada_paso() -> None:
    """Sin hormigas en rocas ni fuera del mundo, alimento conservado, energía en rango,
    transiciones válidas entre pasos (RF-04, RF-21, RF-23, RF-24)."""
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=300, num_obstaculos=30))
    mundo = simulacion.mundo
    h = mundo.hormigas
    rocas = np.array([(o.x, o.y, o.radio) for o in mundo.obstaculos])
    inicial = simulacion.alimento_total()
    energia_max = np.float32(simulacion.parametros.energia_max)

    for _ in range(10_000):
        estado_antes = h.estado.copy()
        simulacion.paso()
        assert simulacion.alimento_total() == inicial
        assert ((h.energia >= 0) & (h.energia <= energia_max)).all()
        afuera = h.estado != E.EN_NIDO
        x, y = h.x[afuera].astype(np.float64), h.y[afuera].astype(np.float64)
        assert ((x >= 0) & (x < mundo.ancho) & (y >= 0) & (y < mundo.alto)).all()
        d2 = (x[:, None] - rocas[:, 0]) ** 2 + (y[:, None] - rocas[:, 1]) ** 2
        assert (d2 >= rocas[:, 2] ** 2).all()
        # Un cambio entre pasos debe estar en la tabla o ser la composición de dos cambios
        # válidos (p. ej. chocar y terminar la evasión de 1 paso en el mismo paso).
        cambio = estado_antes != h.estado
        pares = set(zip(estado_antes[cambio].tolist(), h.estado[cambio].tolist()))
        dos_pasos = MATRIZ_TRANSICIONES.astype(int) @ MATRIZ_TRANSICIONES.astype(int)
        for origen, destino in pares:
            assert MATRIZ_TRANSICIONES[origen, destino] or dos_pasos[origen, destino], (origen, destino)


def test_transicion_invalida_se_rechaza() -> None:
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=5))
    ctx = ContextoPaso(0, 0.0, 0.1, simulacion.mundo, simulacion.parametros, simulacion.aleatorio,
                       simulacion.bitacora, simulacion.estadisticas)
    with pytest.raises(TransicionInvalida):
        cambiar_estado(ctx, 0, E.TRANSPORTANDO_COMIDA)  # EN_NIDO → TRANSPORTANDO no existe


# --- Números pseudoaleatorios y eventos ---------------------------------------------------


def test_direccion_de_salida_es_u_por_360() -> None:
    """RF-20: la dirección al salir es exactamente u · 360 del número registrado."""
    simulacion = simular(1, num_hormigas=20, salidas_por_paso=5)
    salidas = eventos(simulacion, TipoEvento.SALIDA_NIDO)
    assert [e.id_hormiga for e in salidas] == [0, 1, 2, 3, 4]
    for evento in salidas:
        entrada = simulacion.aleatorio.registro.buscar(evento.indice_aleatorio)
        assert entrada.proposito == "DIRECCION_SALIDA" and entrada.id_hormiga == evento.id_hormiga
        assert evento.detalle["direccion"] == angulo(entrada.u)
        assert simulacion.mundo.hormigas.dir[evento.id_hormiga] == np.float32(angulo(entrada.u))


def test_cada_u_de_la_bitacora_esta_en_el_registro() -> None:
    """RF-12: cada número citado por un evento está en el registro con el mismo índice."""
    simulacion = simular(400, num_hormigas=300)
    con_numero = [e for e in simulacion.bitacora.ultimos(10_000) if e.indice_aleatorio > 0 and "u" in e.detalle]
    assert con_numero
    for evento in con_numero:
        entrada = simulacion.aleatorio.registro.buscar(evento.indice_aleatorio)
        assert entrada.u == evento.detalle["u"]


def test_cada_colision_consume_un_numero() -> None:
    simulacion = simular(800, num_hormigas=300)
    colisiones = eventos(simulacion, TipoEvento.COLISION_PREVISTA) + eventos(simulacion, TipoEvento.COLISION_BORDE)
    assert len(colisiones) == simulacion.estadisticas.colisiones + simulacion.estadisticas.colisiones_borde > 0
    propositos = {simulacion.aleatorio.registro.buscar(e.indice_aleatorio).proposito for e in colisiones}
    assert propositos <= {"DIRECCION_COLISION", "DIRECCION_BORDE"}
    assert len({e.indice_aleatorio for e in colisiones}) == len(colisiones)


def test_salidas_a_tasa_constante() -> None:
    simulacion = simular(10, num_hormigas=1000, salidas_por_paso=7)
    assert simulacion.estadisticas.salidas == 70


# --- Reina ----------------------------------------------------------------------------------


def test_con_p_cero_nadie_sigue_a_la_reina() -> None:
    simulacion = simular(1500, num_hormigas=500, p_seguir_reina=0.0)
    assert simulacion.estadisticas.decisiones_seguir > 0
    assert simulacion.estadisticas.seguimientos == 0
    assert not eventos(simulacion, TipoEvento.FIN_SEGUIMIENTO)


def test_con_p_uno_todas_las_que_entran_la_siguen() -> None:
    simulacion = simular(1500, num_hormigas=500, p_seguir_reina=1.0)
    entradas = eventos(simulacion, TipoEvento.ENTRADA_RADIO_REINA)
    assert entradas and all(e.detalle["sigue"] for e in entradas)


def test_proporcion_que_sigue_se_aproxima_a_p() -> None:
    """Con D = 8 (generador menos degenerado) la proporción observada se acerca a p."""
    simulacion = simular(3000, num_hormigas=1000, p_seguir_reina=0.3, digitos=8, semilla=57351234)
    e = simulacion.estadisticas
    assert e.decisiones_seguir > 500
    assert abs(e.seguimientos / e.decisiones_seguir - 0.3) < 0.08


def test_reina_no_sale_de_su_zona() -> None:
    simulacion = Simulacion(ParametrosSimulacion(num_hormigas=10, velocidad_reina=20.0))
    reina, nido = simulacion.mundo.reina, simulacion.mundo.nido
    for _ in range(3000):
        simulacion.paso()
        assert math.dist((reina.x, reina.y), (nido.x, nido.y)) <= reina.radio_patrulla + 1e-9
    assert len(eventos(simulacion, TipoEvento.CAMBIO_RUMBO_REINA)) == 3000 // simulacion.parametros.pasos_rumbo_reina


# --- Alimento y energía ------------------------------------------------------------------


def test_fuente_agotada_no_entrega_alimento() -> None:
    simulacion = simular(4000, num_hormigas=1500, alimento_por_fuente=40, num_fuentes=2)
    agotadas = eventos(simulacion, TipoEvento.FUENTE_AGOTADA)
    assert agotadas
    for evento in agotadas:
        fuente = evento.detalle["fuente"]
        posteriores = [
            e for e in eventos(simulacion, TipoEvento.ENCONTRAR_ALIMENTO)
            if e.detalle["fuente"] == fuente and e.tick > evento.tick
        ]
        assert not posteriores
        assert simulacion.mundo.fuentes[fuente].cantidad == 0


def test_recoleccion_y_deposito() -> None:
    simulacion = simular(3000)
    e = simulacion.estadisticas
    assert e.alimento_recolectado > 0
    assert e.alimento_recolectado == simulacion.mundo.nido.alimento_almacenado
    depositos = eventos(simulacion, TipoEvento.DEPOSITO_ALIMENTO)
    assert all(0 < d.detalle["cantidad"] <= simulacion.parametros.capacidad_carga for d in depositos)


def test_energia_baja_hace_regresar() -> None:
    simulacion = simular(1200, num_hormigas=100, consumo_energia=1.0)
    bajas = eventos(simulacion, TipoEvento.ENERGIA_BAJA)
    assert bajas
    assert all(b.detalle["energia"] < simulacion.parametros.umbral_regreso for b in bajas)
