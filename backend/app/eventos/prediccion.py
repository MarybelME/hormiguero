"""Predicción del siguiente evento de una hormiga (DISENO.md §10.9).

Concepto de simulación: **próximo evento**. En un simulador de eventos discretos el reloj
salta al siguiente evento; aquí el tiempo avanza en pasos fijos, así que el siguiente evento
se **predice**: se avanza una copia local de la hormiga con las reglas deterministas hasta
encontrar el primer evento.

Reglas:
- No consume números pseudoaleatorios ni modifica el mundo (si lo hiciera, seleccionar una
  hormiga cambiaría la simulación).
- Supone que la reina se queda donde está; es una estimación.
- Si el próximo evento depende del azar (seguir a la reina) se informa como posible, con su
  probabilidad.
"""

import math
from dataclasses import dataclass

from app.config import DT, ParametrosSimulacion
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.modelo.mundo import Mundo

HORIZONTE_PREDICCION = 300  # pasos

_E = EstadoHormiga
_VUELVEN_AL_NIDO = (_E.TRANSPORTANDO_COMIDA, _E.REGRESANDO_AL_NIDO)
_VIGILAN_ENERGIA = (_E.BUSCANDO_COMIDA, _E.SIGUIENDO_REINA)


@dataclass(frozen=True)
class Prediccion:
    tipo: TipoEvento | None
    pasos: int | None
    descripcion: str
    aleatorio: bool  # el evento consumirá un número o depende del azar


def _rumbo(x: float, y: float, destino_x: float, destino_y: float) -> float:
    return math.degrees(math.atan2(destino_y - y, destino_x - x)) % 360.0


def _celda(mundo: Mundo, x: float, y: float) -> tuple[int, int]:
    t = mundo.rejilla.tamano_celda
    return int(y // t), int(x // t)


def _en_nido(mundo: Mundo, parametros: ParametrosSimulacion, energia: float) -> Prediccion:
    faltan = math.ceil(max(0.0, parametros.energia_max - energia) / parametros.recuperacion_energia)
    espera = f"en ~{faltan} pasos recupera la energía y " if faltan else ""
    return Prediccion(
        TipoEvento.SALIDA_NIDO, faltan or None,
        f"Está en el nido; {espera}saldrá cuando le toque turno, con dirección u · 360°.", True,
    )


def predecir(mundo: Mundo, parametros: ParametrosSimulacion, id_hormiga: int,
             horizonte: int = HORIZONTE_PREDICCION) -> Prediccion:
    """Primer evento previsto para la hormiga en los próximos `horizonte` pasos."""
    h = mundo.hormigas
    estado = _E(int(h.estado[id_hormiga]))
    energia = float(h.energia[id_hormiga])
    if estado is _E.EN_NIDO:
        return _en_nido(mundo, parametros, energia)

    p = parametros
    x, y = float(h.x[id_hormiga]), float(h.y[id_hormiga])
    direccion = float(h.dir[id_hormiga])
    pasos_restantes = int(h.pasos_restantes[id_hormiga])
    en_radio = bool(h.en_radio_reina[id_hormiga])
    nido, reina = mundo.nido, mundo.reina

    for k in range(1, horizonte + 1):
        energia = max(0.0, energia - p.consumo_energia)
        if estado in _VIGILAN_ENERGIA and energia < p.umbral_regreso:
            return Prediccion(TipoEvento.ENERGIA_BAJA, k,
                              f"Energía baja en ~{k} pasos: regresará al nido.", False)

        if estado in _VUELVEN_AL_NIDO:
            direccion = _rumbo(x, y, nido.x, nido.y)
        elif estado is _E.SIGUIENDO_REINA:
            direccion = _rumbo(x, y, reina.x, reina.y)

        vel = p.velocidad_hormiga * (p.factor_velocidad_agotada if energia <= 0 else 1.0)
        if estado is _E.SIGUIENDO_REINA and math.dist((x, y), (reina.x, reina.y)) < p.distancia_minima_reina:
            vel = 0.0
        nx = x + vel * DT * math.cos(math.radians(direccion))
        ny = y + vel * DT * math.sin(math.radians(direccion))

        if not mundo.dentro(nx, ny):
            return Prediccion(TipoEvento.COLISION_BORDE, k,
                              f"Llegará al borde del mundo en ~{k} pasos; tomará una dirección u · 360°.", True)
        fila, col = _celda(mundo, nx, ny)
        roca = int(mundo.rejilla.mapa_obstaculos[fila, col])
        if roca >= 0:
            return Prediccion(TipoEvento.COLISION_PREVISTA, k,
                              f"Colisión prevista con la roca {roca} en ~{k} pasos; tomará una dirección u · 360°.", True)
        x, y = nx, ny

        if estado is _E.BUSCANDO_COMIDA:
            fila, col = _celda(mundo, x, y)
            fuente = int(mundo.rejilla.mapa_alimento[fila, col])
            if fuente >= 0 and mundo.fuentes[fuente].cantidad > 0:
                return Prediccion(TipoEvento.ENCONTRAR_ALIMENTO, k,
                                  f"Llegará al alimento {fuente} en ~{k} pasos.", False)
        if estado in _VUELVEN_AL_NIDO and nido.contiene(x, y):
            return Prediccion(TipoEvento.LLEGADA_NIDO, k, f"Llegará al nido en ~{k} pasos.", False)
        if estado is not _E.EN_NIDO:
            dentro = math.dist((x, y), (reina.x, reina.y)) <= reina.radio_influencia
            if estado is _E.BUSCANDO_COMIDA and dentro and not en_radio:
                return Prediccion(TipoEvento.ENTRADA_RADIO_REINA, k,
                                  f"Entrará al radio de la reina en ~{k} pasos; "
                                  f"la seguirá con probabilidad p = {p.p_seguir_reina}.", True)
            en_radio = dentro

        if estado in (_E.EVITANDO_OBSTACULO, _E.SIGUIENDO_REINA):
            pasos_restantes -= 1
            if pasos_restantes <= 0:
                if estado is _E.EVITANDO_OBSTACULO:
                    return Prediccion(TipoEvento.FIN_EVASION, k,
                                      f"Terminará de evitar el obstáculo en ~{k} pasos.", False)
                return Prediccion(TipoEvento.FIN_SEGUIMIENTO, k,
                                  f"Dejará de seguir a la reina en ~{k} pasos; tomará una dirección u · 360°.", True)

    return Prediccion(None, None, f"Sin eventos previstos en los próximos {horizonte} pasos.", False)
