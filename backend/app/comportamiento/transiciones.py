"""Operaciones comunes de las reglas de comportamiento.

Toda regla cambia el estado de una hormiga, pide números y registra eventos a través de
estas funciones, para que:
- cada cambio de estado se valide contra la tabla de `modelo/estados.py`;
- cada número usado quede asociado a la hormiga (`ultimo_u`, `ultimo_indice_u`);
- cada evento quede en la bitácora y como `ultimo_evento` de la hormiga.
"""

import math
from typing import Any

import numpy as np

from app.aleatorio.servicio import Proposito
from app.eventos.bitacora import SIN_HORMIGA, SIN_NUMERO, Evento
from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga, TransicionInvalida, transicion_valida
from app.nucleo.contexto import ContextoPaso


def cambiar_estado(ctx: ContextoPaso, h: int, nuevo: EstadoHormiga) -> None:
    actual = int(ctx.hormigas.estado[h])
    if not transicion_valida(actual, nuevo):
        raise TransicionInvalida(
            f"hormiga {h}: {EstadoHormiga(actual).name} → {nuevo.name} no está permitida"
        )
    ctx.hormigas.estado[h] = nuevo


def pedir_u(ctx: ContextoPaso, proposito: Proposito, h: int) -> tuple[float, int]:
    """Pide un número para la hormiga h y lo anota en sus columnas didácticas."""
    u = ctx.aleatorio.obtener(proposito, h)
    indice = ctx.aleatorio.ultimo_indice
    ctx.hormigas.ultimo_u[h] = u
    ctx.hormigas.ultimo_indice_u[h] = indice
    return u, indice


def nueva_direccion(ctx: ContextoPaso, h: int, grados: float) -> None:
    """Asigna una dirección por un evento y lo cuenta como cambio de dirección."""
    ctx.hormigas.dir[h] = grados
    ctx.estadisticas.cambios_direccion += 1


def registrar_evento(
    ctx: ContextoPaso,
    tipo: TipoEvento,
    h: int = SIN_HORMIGA,
    indice_u: int = SIN_NUMERO,
    **detalle: Any,
) -> None:
    ctx.bitacora.registrar(Evento(ctx.tick, ctx.tiempo, tipo, h, indice_u, detalle))
    if h != SIN_HORMIGA:
        ctx.hormigas.ultimo_evento[h] = tipo
        ctx.hormigas.tick_ultimo_evento[h] = ctx.tick


def rumbo_hacia(x: np.ndarray, y: np.ndarray, destino_x: float, destino_y: float) -> np.ndarray:
    """Dirección en grados [0, 360) desde cada (x, y) hacia el destino (vectorizado)."""
    return (np.degrees(np.arctan2(destino_y - y, destino_x - x)) % 360.0).astype(np.float32)


def rumbo_hacia_punto(x: float, y: float, destino_x: float, destino_y: float) -> float:
    """Versión escalar de `rumbo_hacia`."""
    return math.degrees(math.atan2(destino_y - y, destino_x - x)) % 360.0
