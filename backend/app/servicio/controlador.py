"""Controlador de la simulación en tiempo real.

Concepto de simulación: **reloj de simulación frente a reloj real**. La simulación avanza en
pasos de `dt` segundos simulados; el controlador decide cuántos pasos ejecutar por cada
segundo real (`pasos_por_segundo`) y, aparte, cuántas fotos (cuadros) enviar al navegador
(como máximo 30 por segundo). A 300 pasos/s se simulan 10 pasos por cada cuadro enviado.
Cambiar la velocidad no cambia el resultado tras N pasos: sólo cuánto tarda en llegar.

Estados del controlador:

    vacio ──configurar──► listo ──iniciar──► corriendo ⇄ pausado
      ▲                     ▲                    │           │
      └──────limpiar────────┴─────reiniciar──────┴───────────┘

Todo se ejecuta en el hilo del bucle de eventos (las rutas que lo usan son `async`), así que
una consulta nunca ve la simulación a medio paso. No importa FastAPI: recibe suscriptores
genéricos que reciben mensajes (bytes para los cuadros, diccionarios para el JSON).
"""

import asyncio
import time
from collections import deque
from enum import Enum
from typing import Any

from app.api.protocolo import empaquetar_cuadro
from app.config import ParametrosSimulacion
from app.nucleo.simulacion import Simulacion

CUADROS_POR_SEGUNDO = 30
CUADROS_POR_ESTADISTICA = 8      # ≈ 4 mensajes de estadísticas por segundo
FRACCION_PRESUPUESTO = 0.8       # parte de cada cuadro que se puede dedicar a calcular pasos
VENTANA_MEDICION = 1.0           # s reales para medir los pasos/s reales
MENSAJES_PENDIENTES_MAX = 256    # mensajes JSON en espera por suscriptor


class EstadoControlador(str, Enum):
    VACIO = "vacio"
    LISTO = "listo"
    CORRIENDO = "corriendo"
    PAUSADO = "pausado"


class AccionInvalida(Exception):
    """La acción no se puede hacer en el estado actual del controlador (HTTP 409)."""


class Suscripcion:
    """Lo que recibe un cliente: mensajes JSON en orden y sólo el cuadro más reciente.

    Si el cliente es lento, los cuadros viejos se descartan (se dibuja el último), pero los
    mensajes JSON (mundo, control, estadísticas, selección) se conservan en orden.
    """

    def __init__(self) -> None:
        self._mensajes: deque[dict[str, Any]] = deque(maxlen=MENSAJES_PENDIENTES_MAX)
        self._cuadro: bytes | None = None
        self._hay_algo = asyncio.Event()
        self.seleccion: int | None = None

    def enviar_mensaje(self, mensaje: dict[str, Any]) -> None:
        self._mensajes.append(mensaje)
        self._hay_algo.set()

    def enviar_cuadro(self, cuadro: bytes) -> None:
        self._cuadro = cuadro
        self._hay_algo.set()

    def pendientes(self) -> list[dict[str, Any] | bytes]:
        """Saca todo lo que está en espera (JSON primero, luego el último cuadro)."""
        salida: list[dict[str, Any] | bytes] = list(self._mensajes)
        self._mensajes.clear()
        if self._cuadro is not None:
            salida.append(self._cuadro)
            self._cuadro = None
        self._hay_algo.clear()
        return salida

    async def siguiente(self) -> list[dict[str, Any] | bytes]:
        """Espera hasta que haya algo que enviar y lo devuelve."""
        await self._hay_algo.wait()
        return self.pendientes()


class MedidorVelocidad:
    """Pasos por segundo reales en la última ventana de tiempo real."""

    def __init__(self) -> None:
        self._muestras: deque[tuple[float, int]] = deque()

    def registrar(self, pasos: int, ahora: float) -> None:
        self._muestras.append((ahora, pasos))
        while self._muestras and ahora - self._muestras[0][0] > VENTANA_MEDICION:
            self._muestras.popleft()

    def pasos_por_segundo(self) -> float:
        if len(self._muestras) < 2:
            return 0.0
        duracion = self._muestras[-1][0] - self._muestras[0][0]
        pasos = sum(p for _, p in list(self._muestras)[1:])
        return pasos / duracion if duracion > 0 else 0.0

    def limpiar(self) -> None:
        self._muestras.clear()


class ControladorSimulacion:
    """Una única simulación compartida por todos los clientes (DISENO.md, decisión m)."""

    def __init__(self) -> None:
        self.simulacion: Simulacion | None = None
        self.estado = EstadoControlador.VACIO
        self.pasos_por_segundo = ParametrosSimulacion().pasos_por_segundo
        self._fraccion_pendiente = 0
        self._cuadros = 0
        self._version_estatica = -1
        self._medidor = MedidorVelocidad()
        self._suscripciones: set[Suscripcion] = set()
        self._tarea: asyncio.Task | None = None

    # --- Suscriptores ---------------------------------------------------------------------

    def suscribir(self) -> Suscripcion:
        """Registra un cliente y le envía el estado actual completo."""
        suscripcion = Suscripcion()
        self._suscripciones.add(suscripcion)
        suscripcion.enviar_mensaje(self._mensaje_control())
        if self.simulacion is not None:
            suscripcion.enviar_mensaje(self._mensaje_mundo())
            suscripcion.enviar_mensaje(self._mensaje_estadisticas())
            suscripcion.enviar_cuadro(self._cuadro())
        return suscripcion

    def desuscribir(self, suscripcion: Suscripcion) -> None:
        self._suscripciones.discard(suscripcion)

    def seleccionar(self, suscripcion: Suscripcion, id_hormiga: int) -> None:
        """La pestaña elige una hormiga; recibe su vista enseguida y luego ~4 veces por segundo."""
        simulacion = self._exigir_simulacion()
        if not 0 <= id_hormiga < simulacion.mundo.hormigas.n:
            raise AccionInvalida(f"No existe la hormiga {id_hormiga}")
        suscripcion.seleccion = id_hormiga
        suscripcion.enviar_mensaje(self._mensaje_seleccion(id_hormiga))

    def deseleccionar(self, suscripcion: Suscripcion) -> None:
        suscripcion.seleccion = None

    def _borrar_selecciones(self) -> None:
        for suscripcion in self._suscripciones:
            if suscripcion.seleccion is not None:
                suscripcion.seleccion = None
                suscripcion.enviar_mensaje({"tipo": "deseleccion"})

    def _difundir(self, mensaje: dict[str, Any]) -> None:
        for suscripcion in self._suscripciones:
            suscripcion.enviar_mensaje(mensaje)

    # --- Mensajes -------------------------------------------------------------------------

    def _cuadro(self) -> bytes:
        s = self.simulacion
        return empaquetar_cuadro(s.tick, s.tiempo, s.mundo)

    def _mensaje_control(self) -> dict[str, Any]:
        return {"tipo": "control", **self.estado_actual()}

    def _mensaje_mundo(self) -> dict[str, Any]:
        s = self.simulacion
        self._version_estatica = s.mundo.version_estatica
        return {
            "tipo": "mundo",
            "mundo": s.mundo.capa_estatica(),
            "semillas": {"MUNDO": s.parametros.semilla, "COMPORTAMIENTO": s.parametros.semilla_comportamiento},
        }

    def _mensaje_estadisticas(self) -> dict[str, Any]:
        return {"tipo": "estadisticas", **self.estadisticas()}

    def _mensaje_seleccion(self, id_hormiga: int) -> dict[str, Any]:
        return {"tipo": "seleccion", "hormiga": self.simulacion.vista_hormiga(id_hormiga)}

    # --- Consultas ------------------------------------------------------------------------

    def estado_actual(self) -> dict[str, Any]:
        return {
            "estado_controlador": self.estado.value,
            "pasos_por_segundo": self.pasos_por_segundo,
            "tick": 0 if self.simulacion is None else self.simulacion.tick,
        }

    def estadisticas(self) -> dict[str, Any]:
        simulacion = self._exigir_simulacion()
        datos = simulacion.resumen()
        datos["p_seguir_reina"] = simulacion.parametros.p_seguir_reina  # para comparar p̂ con p
        datos["pasos_por_segundo_pedidos"] = self.pasos_por_segundo
        datos["pasos_por_segundo_reales"] = round(self._medidor.pasos_por_segundo(), 1)
        return datos

    def _exigir_simulacion(self) -> Simulacion:
        if self.simulacion is None:
            raise AccionInvalida("Todavía no hay un mundo configurado")
        return self.simulacion

    # --- Acciones -------------------------------------------------------------------------

    def configurar(self, parametros: ParametrosSimulacion) -> Simulacion:
        """Crea una corrida nueva en t = 0 (pausada). Puede lanzar ErrorGeneracionMundo."""
        simulacion = Simulacion(parametros)  # si falla, la corrida anterior sigue intacta
        self._detener_bucle()
        self.simulacion = simulacion
        self.pasos_por_segundo = parametros.pasos_por_segundo
        self._reiniciar_reloj_real()
        self._borrar_selecciones()  # la corrida nueva puede tener menos hormigas
        self._cambiar_estado(EstadoControlador.LISTO)
        self._difundir(self._mensaje_mundo())
        self._publicar_todo()
        return simulacion

    def iniciar(self) -> None:
        if self.estado not in (EstadoControlador.LISTO, EstadoControlador.PAUSADO):
            raise AccionInvalida(f"No se puede iniciar en el estado '{self.estado.value}'")
        self._reiniciar_reloj_real()
        self._cambiar_estado(EstadoControlador.CORRIENDO)
        self._tarea = asyncio.get_running_loop().create_task(self._bucle())

    def pausar(self) -> None:
        if self.estado is not EstadoControlador.CORRIENDO:
            raise AccionInvalida(f"No se puede pausar en el estado '{self.estado.value}'")
        self._detener_bucle()
        self._cambiar_estado(EstadoControlador.PAUSADO)
        self._publicar_todo()

    def reiniciar(self) -> None:
        """Vuelve a t = 0 con los mismos parámetros: la corrida se repetirá idéntica."""
        simulacion = self._exigir_simulacion()
        self._detener_bucle()
        simulacion.reiniciar()
        self._reiniciar_reloj_real()
        self._cambiar_estado(EstadoControlador.LISTO)
        self._difundir(self._mensaje_mundo())
        self._publicar_todo()

    def limpiar(self) -> None:
        """Borra mundo, hormigas, registros y estadísticas (los formularios no cambian)."""
        self._detener_bucle()
        self.simulacion = None
        self._borrar_selecciones()
        self._reiniciar_reloj_real()
        self._cambiar_estado(EstadoControlador.VACIO)

    def fijar_velocidad(self, pasos_por_segundo: int) -> None:
        """Cambia la velocidad en vivo; no altera el resultado, sólo el tiempo real."""
        self.pasos_por_segundo = pasos_por_segundo
        self._fraccion_pendiente = 0
        self._difundir(self._mensaje_control())

    def _cambiar_estado(self, nuevo: EstadoControlador) -> None:
        self.estado = nuevo
        self._difundir(self._mensaje_control())

    def _reiniciar_reloj_real(self) -> None:
        self._fraccion_pendiente = 0
        self._cuadros = 0
        self._medidor.limpiar()

    # --- Bucle en tiempo real -------------------------------------------------------------

    def _detener_bucle(self) -> None:
        if self._tarea is not None:
            self._tarea.cancel()
            self._tarea = None

    async def detener(self) -> None:
        """Al apagar el servidor."""
        self._detener_bucle()

    async def _bucle(self) -> None:
        bucle = asyncio.get_running_loop()
        intervalo = 1.0 / CUADROS_POR_SEGUNDO
        proximo = bucle.time()
        while self.estado is EstadoControlador.CORRIENDO:
            try:
                self.ejecutar_cuadro()
            except Exception as error:  # no dejar al cliente creyendo que sigue corriendo
                self._tarea = None
                self._cambiar_estado(EstadoControlador.PAUSADO)
                self._difundir({"tipo": "error", "mensaje": f"La simulación se detuvo: {error}"})
                raise
            proximo += intervalo
            espera = proximo - bucle.time()
            if espera < 0:  # el cálculo se atrasó: no se intenta recuperar el retraso
                proximo = bucle.time()
                espera = 0.0
            await asyncio.sleep(espera)

    def pasos_de_este_cuadro(self) -> int:
        """Pasos que tocan en este cuadro; la fracción sobrante se acumula para el siguiente."""
        # Aritmética entera (en treintavos de paso) para que no se acumule error de redondeo.
        self._fraccion_pendiente += self.pasos_por_segundo
        pasos, self._fraccion_pendiente = divmod(self._fraccion_pendiente, CUADROS_POR_SEGUNDO)
        return pasos

    def ejecutar_cuadro(self, presupuesto: float | None = None) -> int:
        """Ejecuta los pasos de un cuadro y publica lo que corresponda. Devuelve los pasos hechos.

        Si calcular los pasos excede el presupuesto de tiempo real, se cortan: la simulación
        va más lenta de lo pedido (se ve en `pasos_por_segundo_reales`) pero el servidor no
        se congela. Cortar no cambia el resultado: los pasos son los mismos, sólo más tarde.
        """
        simulacion = self._exigir_simulacion()
        if presupuesto is None:
            presupuesto = FRACCION_PRESUPUESTO / CUADROS_POR_SEGUNDO
        pedidos = self.pasos_de_este_cuadro()
        inicio = time.perf_counter()
        hechos = 0
        while hechos < pedidos:
            simulacion.paso()
            hechos += 1
            if time.perf_counter() - inicio > presupuesto:
                break
        if hechos < pedidos:
            self._fraccion_pendiente = 0  # no se acumula el atraso
        self._medidor.registrar(hechos, time.perf_counter())
        self._cuadros += 1
        self._publicar_cuadro(estadisticas=self._cuadros % CUADROS_POR_ESTADISTICA == 0)
        return hechos

    def _publicar_cuadro(self, estadisticas: bool) -> None:
        if self.simulacion.mundo.version_estatica != self._version_estatica:
            self._difundir(self._mensaje_mundo())  # p. ej. se agotó una fuente
        if estadisticas:
            self._difundir(self._mensaje_estadisticas())
            self._publicar_selecciones()
        cuadro = self._cuadro()
        for suscripcion in self._suscripciones:
            suscripcion.enviar_cuadro(cuadro)

    def _publicar_selecciones(self) -> None:
        vistas: dict[int, dict[str, Any]] = {}
        for suscripcion in self._suscripciones:
            if suscripcion.seleccion is None:
                continue
            if suscripcion.seleccion not in vistas:
                vistas[suscripcion.seleccion] = self._mensaje_seleccion(suscripcion.seleccion)
            suscripcion.enviar_mensaje(vistas[suscripcion.seleccion])

    def _publicar_todo(self) -> None:
        """Estadísticas, selecciones y cuadro actuales (al pausar, reiniciar o configurar)."""
        self._publicar_cuadro(estadisticas=True)
