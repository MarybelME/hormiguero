"""Generación del mundo a partir de la semilla.

Concepto de simulación: **método de aceptación-rechazo**. Para colocar cada roca y cada
fuente se genera un candidato (radio, x, y) con tres números del flujo MUNDO; si se solapa
con algo ya colocado o invade la zona de patrulla de la reina, se rechaza y se genera otro.
Los candidatos rechazados también consumen números y quedan en el registro: en clase se
puede contar cuántos se rechazaron.

Misma semilla ⇒ mismos candidatos ⇒ mismo mundo.
"""

import math

from app import config
from app.aleatorio.servicio import Flujo, Proposito, ServicioAleatorio
from app.aleatorio.variables import uniforme
from app.config import ParametrosSimulacion
from app.espacial.rejilla import RejillaEspacial
from app.modelo.alimento import FuenteAlimento
from app.modelo.estados import EstadoReina
from app.modelo.hormigas import Hormigas
from app.modelo.mundo import Mundo
from app.modelo.nido import Nido
from app.modelo.obstaculos import Obstaculo
from app.modelo.reina import Reina

Circulo = tuple[float, float, float]  # (x, y, radio)


class ErrorGeneracionMundo(ValueError):
    """No caben todos los elementos pedidos tras el máximo de intentos."""


class _Colocador:
    """Aplica aceptación-rechazo y lleva la cuenta de candidatos."""

    def __init__(self, servicio: ServicioAleatorio, nido: Nido, radio_libre: float) -> None:
        self._servicio = servicio
        self._nido = nido
        self._radio_libre = radio_libre
        self.colocados: list[Circulo] = []
        self.candidatos = 0
        self.rechazados = 0

    def _u(self) -> float:
        return self._servicio.obtener(Proposito.MUNDO)

    def _valido(self, x: float, y: float, r: float) -> bool:
        separacion = config.SEPARACION_MINIMA
        if math.dist((x, y), (self._nido.x, self._nido.y)) < self._radio_libre + r + separacion:
            return False
        return all(math.dist((x, y), (cx, cy)) >= r + cr + separacion for cx, cy, cr in self.colocados)

    def colocar(self, radio_min: float, radio_max: float, que: str) -> Circulo:
        for _ in range(config.INTENTOS_POR_ELEMENTO):
            self.candidatos += 1
            r = uniforme(self._u(), radio_min, radio_max)
            x = uniforme(self._u(), r, config.ANCHO_MUNDO - r)
            y = uniforme(self._u(), r, config.ALTO_MUNDO - r)
            if self._valido(x, y, r):
                self.colocados.append((x, y, r))
                return x, y, r
            self.rechazados += 1
        raise ErrorGeneracionMundo(
            f"no se pudo colocar {que} n.º {len(self.colocados) + 1} tras "
            f"{config.INTENTOS_POR_ELEMENTO} intentos; reduzca rocas o fuentes"
        )


def _redondear(valor: float) -> float:
    """Posiciones y radios con 2 decimales: más fáciles de leer en clase."""
    return round(valor, 2)


def generar_mundo(parametros: ParametrosSimulacion, servicio: ServicioAleatorio) -> Mundo:
    """Crea el mundo inicial usando sólo el flujo MUNDO del servicio."""
    numeros_antes = servicio.total_generados
    resiembras_antes = servicio.degeneraciones(Flujo.MUNDO)

    nido = Nido(x=config.ANCHO_MUNDO / 2, y=config.ALTO_MUNDO / 2, radio=config.RADIO_NIDO)
    rejilla = RejillaEspacial(config.ANCHO_MUNDO, config.ALTO_MUNDO, config.TAMANO_CELDA)
    colocador = _Colocador(servicio, nido, radio_libre=parametros.radio_patrulla)

    obstaculos: list[Obstaculo] = []
    for i in range(parametros.num_obstaculos):
        x, y, r = map(_redondear, colocador.colocar(config.RADIO_ROCA_MIN, config.RADIO_ROCA_MAX, "la roca"))
        obstaculos.append(Obstaculo(id=i, x=x, y=y, radio=r))
        rejilla.marcar_obstaculo(i, x, y, r)

    fuentes: list[FuenteAlimento] = []
    for i in range(parametros.num_fuentes):
        x, y, r = map(_redondear, colocador.colocar(config.RADIO_FUENTE_MIN, config.RADIO_FUENTE_MAX, "la fuente"))
        cantidad = parametros.alimento_por_fuente
        fuentes.append(FuenteAlimento(id=i, x=x, y=y, radio=r, cantidad_inicial=cantidad, cantidad=cantidad))
        rejilla.marcar_fuente(i, x, y, r)

    reina = Reina(
        x=nido.x + config.DISTANCIA_REINA_AL_NIDO,
        y=nido.y,
        dir=0.0,
        vel=parametros.velocidad_reina,
        radio_influencia=parametros.radio_reina,
        radio_patrulla=parametros.radio_patrulla,
        estado=EstadoReina.PATRULLANDO,
    )
    hormigas = Hormigas(parametros.num_hormigas, nido, parametros.velocidad_hormiga, parametros.energia_max)

    return Mundo(
        ancho=config.ANCHO_MUNDO,
        alto=config.ALTO_MUNDO,
        nido=nido,
        reina=reina,
        hormigas=hormigas,
        obstaculos=obstaculos,
        fuentes=fuentes,
        rejilla=rejilla,
        generacion={
            "candidatos": colocador.candidatos,
            "rechazados": colocador.rechazados,
            "numeros_usados": servicio.total_generados - numeros_antes,
            "resiembras": servicio.degeneraciones(Flujo.MUNDO) - resiembras_antes,
        },
    )
