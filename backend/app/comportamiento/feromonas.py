"""Comportamiento con feromonas (DISENO.md, decisión o).

- Las hormigas que TRANSPORTAN_COMIDA dejan `deposito_feromona` en su celda en cada paso:
  así se marca el camino entre las fuentes y el nido.
- Las que BUSCAN_COMIDA leen tres sensores a `distancia_sensor` delante de ellas: izquierda
  (rumbo + ángulo), frente y derecha (rumbo − ángulo). Si la mayor lectura alcanza el
  umbral y no es la del frente, giran `giro_feromona` grados hacia ese lado; si el frente es
  el mayor, siguen derecho. Empates: gana el frente y, entre los lados, la izquierda.
- Al final del paso el campo se evapora.

Es una regla **determinista**: no consume números pseudoaleatorios. El giro es una
corrección continua del rumbo (como la de volver al nido), no un evento: no se anota en la
bitácora ni cuenta como "cambio de dirección", pero se cuenta aparte (`giros_feromona`).
"""

from typing import Any

import numpy as np

from app.modelo.estados import EstadoHormiga
from app.modelo.feromonas import CampoFeromonas
from app.nucleo.contexto import ContextoPaso

CLAVE_CAMPO = "feromonas"
IZQUIERDA, FRENTE, DERECHA = 0, 1, 2


def campo_de(ctx: ContextoPaso) -> CampoFeromonas | None:
    return ctx.campos.get(CLAVE_CAMPO)


def lecturas_sensores(campo: CampoFeromonas, x: np.ndarray, y: np.ndarray, direccion: np.ndarray,
                      angulo: float, distancia: float) -> np.ndarray:
    """Lecturas (n × 3): izquierda, frente y derecha, para cada hormiga."""
    lecturas = np.empty((np.size(x), 3), dtype=np.float32)
    for columna, desvio in ((IZQUIERDA, angulo), (FRENTE, 0.0), (DERECHA, -angulo)):
        radianes = np.radians(direccion + desvio)
        lecturas[:, columna] = campo.muestrear(x + distancia * np.cos(radianes),
                                               y + distancia * np.sin(radianes))
    return lecturas


def decidir_giro(lecturas: np.ndarray, umbral: float) -> np.ndarray:
    """+1 = gira a la izquierda, −1 = a la derecha, 0 = sigue derecho (vectorizado)."""
    izquierda, frente, derecha = lecturas[:, IZQUIERDA], lecturas[:, FRENTE], lecturas[:, DERECHA]
    maxima = lecturas.max(axis=1)
    gira = (maxima >= umbral) & (frente < maxima)
    return np.where(gira, np.where(izquierda >= derecha, 1, -1), 0).astype(np.int8)


def orientar_por_feromonas(ctx: ContextoPaso) -> None:
    campo = campo_de(ctx)
    if campo is None:
        return
    h, p = ctx.hormigas, ctx.parametros
    buscando = np.flatnonzero(h.estado == EstadoHormiga.BUSCANDO_COMIDA)
    if buscando.size == 0:
        return
    lecturas = lecturas_sensores(campo, h.x[buscando], h.y[buscando], h.dir[buscando],
                                 p.angulo_sensor, p.distancia_sensor)
    giro = decidir_giro(lecturas, p.umbral_feromona)
    giran = giro != 0
    indices = buscando[giran]
    nueva = (h.dir[indices] + giro[giran] * np.float32(p.giro_feromona)) % np.float32(360)
    h.dir[indices] = nueva.astype(np.float32)
    ctx.estadisticas.giros_feromona += int(giran.sum())


def depositar_feromonas(ctx: ContextoPaso) -> None:
    campo = campo_de(ctx)
    if campo is None:
        return
    h = ctx.hormigas
    con_comida = h.estado == EstadoHormiga.TRANSPORTANDO_COMIDA
    campo.depositar(h.x[con_comida], h.y[con_comida], ctx.parametros.deposito_feromona)


def evaporar_feromonas(ctx: ContextoPaso) -> None:
    campo = campo_de(ctx)
    if campo is not None:
        campo.evaporar(ctx.parametros.evaporacion_feromona)


def vista_sensores(campo: CampoFeromonas, parametros: Any, x: float, y: float,
                   direccion: float) -> dict[str, Any]:
    """Lo que "huele" una hormiga y qué haría con eso (para el modo didáctico)."""
    lecturas = lecturas_sensores(campo, np.array([x]), np.array([y]), np.array([direccion]),
                                 parametros.angulo_sensor, parametros.distancia_sensor)
    giro = int(decidir_giro(lecturas, parametros.umbral_feromona)[0])
    return {
        "izquierda": float(lecturas[0, IZQUIERDA]),
        "frente": float(lecturas[0, FRENTE]),
        "derecha": float(lecturas[0, DERECHA]),
        "umbral": parametros.umbral_feromona,
        "giro": {1: "izquierda", -1: "derecha", 0: "ninguno"}[giro],
        "aqui": float(campo.muestrear(np.array([x]), np.array([y]))[0]),
    }
