"""Movimiento de las obreras (vectorizado, DISENO.md §10.4).

Se calcula primero la posición propuesta de todas las hormigas fuera del nido; después
`espacial/colisiones.py` decide cuáles están bloqueadas, y sólo las demás se mueven.

Convención: 0° = este y los ángulos crecen en sentido antihorario.
"""

import numpy as np

from app.modelo.estados import EstadoHormiga
from app.nucleo.contexto import ContextoPaso


def proponer_movimiento(ctx: ContextoPaso) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve (máscara de móviles, x propuesta, y propuesta)."""
    h = ctx.hormigas
    p = ctx.parametros
    moviles = h.estado != EstadoHormiga.EN_NIDO

    vel = np.where(h.energia <= 0, h.vel * np.float32(p.factor_velocidad_agotada), h.vel)
    # Una seguidora muy cerca de la reina se detiene para no "atravesarla".
    reina = ctx.mundo.reina
    siguiendo = h.estado == EstadoHormiga.SIGUIENDO_REINA
    cerca = (h.x - reina.x) ** 2 + (h.y - reina.y) ** 2 < p.distancia_minima_reina**2
    vel = np.where(siguiendo & cerca, np.float32(0), vel)

    avance = vel * np.float32(ctx.dt)
    radianes = np.radians(h.dir)
    x_nueva = h.x + avance * np.cos(radianes)
    y_nueva = h.y + avance * np.sin(radianes)
    return moviles, x_nueva, y_nueva


def aplicar_movimiento(ctx: ContextoPaso, mover: np.ndarray, x_nueva: np.ndarray, y_nueva: np.ndarray) -> None:
    h = ctx.hormigas
    h.x[mover] = x_nueva[mover]
    h.y[mover] = y_nueva[mover]
