"""Simulación del hormiguero.

Concepto de simulación: **sistema** y **avance del tiempo**. Es un modelo de tiempo
discreto: cada llamada a `paso()` avanza el reloj `dt` segundos simulados. Dentro de cada
paso ocurren eventos (salir del nido, chocar, encontrar alimento…) que se anotan en la
bitácora con su tiempo, su hormiga y el número pseudoaleatorio que usaron. No es un
simulador de eventos discretos puro: los eventos se detectan dentro de los pasos.

Reproducibilidad: las fases se ejecutan siempre en el mismo orden y, dentro de cada fase,
las hormigas con evento se atienden en orden ascendente de id. Misma semilla y mismos
parámetros ⇒ misma simulación.
"""

import math
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from app import config
from app.aleatorio.fabrica import crear_generador
from app.aleatorio.registro import CAPACIDAD_REGISTRO, EntradaRegistro, RegistroAleatorio
from app.aleatorio.servicio import Flujo, ServicioAleatorio
from app.comportamiento.buscando import detectar_alimento
from app.comportamiento.en_nido import salidas_del_nido
from app.comportamiento.energia import actualizar_energia
from app.comportamiento.feromonas import (
    CLAVE_CAMPO,
    depositar_feromonas,
    evaporar_feromonas,
    orientar_por_feromonas,
    vista_sensores,
)
from app.comportamiento.evitando import terminar_evasiones
from app.comportamiento.movimiento import aplicar_movimiento, proponer_movimiento
from app.comportamiento.regresando import detectar_llegada_nido
from app.comportamiento.reina import mover_reina
from app.comportamiento.siguiendo_reina import (
    detectar_radio_reina,
    orientar_hacia_reina,
    terminar_seguimientos,
)
from app.comportamiento.transportando import orientar_al_nido
from app.config import ParametrosSimulacion
from app.espacial.colisiones import resolver_colisiones
from app.estadisticas.contadores import Estadisticas
from app.estadisticas.series import SeriesEstadisticas
from app.eventos.bitacora import CAPACIDAD_BITACORA, Bitacora, Evento
from app.eventos.prediccion import predecir
from app.modelo.generacion_mundo import generar_mundo
from app.modelo.mundo import Mundo
from app.nucleo.contexto import ContextoPaso


class Simulacion:
    """Una corrida completa: mundo, generadores, bitácora, contadores y reloj."""

    def __init__(
        self,
        parametros: ParametrosSimulacion,
        capacidad_registro: int = CAPACIDAD_REGISTRO,
        capacidad_bitacora: int = CAPACIDAD_BITACORA,
        al_generar_numero: Callable[[EntradaRegistro], None] | None = None,
        al_registrar_evento: Callable[[Evento], None] | None = None,
    ) -> None:
        """`al_generar_numero` y `al_registrar_evento` son avisos opcionales por cada número y
        cada evento (los usa la exportación del registro completo); no alteran la simulación."""
        self.parametros = parametros
        self.dt = config.DT
        self._capacidad_registro = capacidad_registro
        self._capacidad_bitacora = capacidad_bitacora
        self._al_generar_numero = al_generar_numero
        self._al_registrar_evento = al_registrar_evento
        self._construir()

    def _construir(self) -> None:
        p = self.parametros
        self.bitacora = Bitacora(self._capacidad_bitacora, self._al_registrar_evento)
        self.aleatorio = ServicioAleatorio(
            crear_generador(p.configuracion_generador, p.semilla),
            crear_generador(p.configuracion_generador, p.semilla_comportamiento),
            registro=RegistroAleatorio(self._capacidad_registro, self._al_generar_numero),
            bitacora=self.bitacora,
        )
        self.estadisticas = Estadisticas()
        self.tick = 0
        self.mundo: Mundo = generar_mundo(p, self.aleatorio)
        self.estadisticas.actualizar_conteo(self.mundo.hormigas.estado)
        self.series = SeriesEstadisticas()
        self.series.registrar(self.resumen())

    @property
    def tiempo(self) -> float:
        """Tiempo de simulación en segundos simulados."""
        return round(self.tick * self.dt, 10)

    def reiniciar(self) -> None:
        """Vuelve a t = 0 con los mismos parámetros: la corrida se repite idéntica."""
        self._construir()

    def paso(self) -> None:
        """Avanza el reloj un paso `dt` ejecutando las fases en orden fijo (DISENO.md §10.3)."""
        self.tick += 1
        self.aleatorio.fijar_tiempo(self.tick, self.tiempo)
        ctx = ContextoPaso(
            tick=self.tick, tiempo=self.tiempo, dt=self.dt, mundo=self.mundo,
            parametros=self.parametros, aleatorio=self.aleatorio,
            bitacora=self.bitacora, estadisticas=self.estadisticas,
        )
        mover_reina(ctx)                                        # 1
        salidas_del_nido(ctx)                                   # 2
        actualizar_energia(ctx)                                 # 3
        orientar_al_nido(ctx)                                   # 4 rumbos
        orientar_hacia_reina(ctx)
        orientar_por_feromonas(ctx)
        moviles, x_nueva, y_nueva = proponer_movimiento(ctx)    # 5
        bloqueadas = resolver_colisiones(ctx, moviles, x_nueva, y_nueva)  # 6
        aplicar_movimiento(ctx, moviles & ~bloqueadas, x_nueva, y_nueva)  # 7
        depositar_feromonas(ctx)                                # 7b rastro de las que llevan comida
        detectar_alimento(ctx)                                  # 8 eventos espaciales
        detectar_llegada_nido(ctx)
        detectar_radio_reina(ctx)
        terminar_evasiones(ctx)                                 # 9 cuentas regresivas
        terminar_seguimientos(ctx)
        evaporar_feromonas(ctx)                                 # 9b el campo se evapora
        self.estadisticas.actualizar_conteo(self.mundo.hormigas.estado)  # 10
        if self.series.toca_muestra(self.tick):
            self.series.registrar(self.resumen())

    def avanzar(self, pasos: int) -> None:
        for _ in range(pasos):
            self.paso()

    def alimento_total(self) -> int:
        """Fuentes + transportado + depositado (debe ser constante: conservación del recurso)."""
        en_fuentes = sum(f.cantidad for f in self.mundo.fuentes)
        transportado = int(self.mundo.hormigas.carga.sum(dtype="int64"))
        return en_fuentes + transportado + self.mundo.nido.alimento_almacenado

    def resumen(self) -> dict[str, Any]:
        """Estado global para la interfaz y los scripts."""
        datos = self.estadisticas.como_dict()
        datos.update(
            tick=self.tick,
            tiempo=self.tiempo,
            total_hormigas=self.mundo.hormigas.n,
            numeros_generados=self.aleatorio.total_generados,
            resiembras={flujo.value: self.aleatorio.degeneraciones(flujo) for flujo in Flujo},
            alimento_en_nido=self.mundo.nido.alimento_almacenado,
            alimento_por_fuente=[f.cantidad for f in self.mundo.fuentes],
            feromona_total=self.feromonas.total() if self.feromonas is not None else None,
        )
        return datos

    @property
    def feromonas(self):
        """El campo de feromonas, o None si están desactivadas."""
        return self.mundo.campos.get(CLAVE_CAMPO)

    def vista_hormiga(self, id_hormiga: int) -> dict[str, Any]:
        """Todo lo que el modo didáctico muestra de una hormiga (no modifica nada).

        Incluye sus atributos, el último número pseudoaleatorio que usó con su cálculo
        completo, su último evento y la predicción del siguiente, que no consume números.
        """
        datos = self.mundo.hormigas.vista(id_hormiga)
        indice = datos["ultimo_indice_u"]
        entrada = self.aleatorio.registro.ultimo_de(id_hormiga)
        if entrada is None or entrada.indice != indice:  # p. ej. un número sin propósito de hormiga
            entrada = self.aleatorio.registro.buscar(indice) if indice > 0 else None
        datos["ultimo_numero"] = None if entrada is None else asdict(entrada)
        datos["ultimo_numero_fuera_de_bufer"] = indice > 0 and entrada is None
        if math.isnan(datos["ultimo_u"]):
            datos["ultimo_u"] = None
        prediccion = predecir(self.mundo, self.parametros, id_hormiga)
        datos["siguiente_evento"] = {
            "tipo": None if prediccion.tipo is None else prediccion.tipo.name,
            "pasos": prediccion.pasos,
            "descripcion": prediccion.descripcion,
            "aleatorio": prediccion.aleatorio,
        }
        if self.feromonas is not None:
            datos["feromonas"] = vista_sensores(self.feromonas, self.parametros,
                                                datos["x"], datos["y"], datos["dir"])
            if datos["estado"] == "BUSCANDO_COMIDA":
                datos["siguiente_evento"]["descripcion"] += (
                    " Si sus sensores detectan feromona, puede desviarse de esta trayectoria.")
        datos["tick"] = self.tick
        return datos
