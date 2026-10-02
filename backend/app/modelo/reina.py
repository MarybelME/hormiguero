"""Reina.

Concepto de simulación: **entidad permanente especial**. Hay una sola; patrulla lentamente
alrededor del nido (DISENO.md, decisiones h y l) y atrae a las obreras que entran en su
radio de influencia.
"""

from dataclasses import dataclass

from app.modelo.estados import EstadoReina


@dataclass
class Reina:
    x: float
    y: float
    dir: float                 # grados
    vel: float                 # unidades/s
    radio_influencia: float
    radio_patrulla: float      # zona alrededor del nido de la que no sale
    estado: EstadoReina = EstadoReina.PATRULLANDO
    pasos_para_rumbo: int = 0  # cuenta regresiva hasta el próximo CAMBIO_RUMBO_REINA
