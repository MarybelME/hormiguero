"""Protocolo binario del cuadro de hormigas (DISENO.md §12.2).

Concepto de simulación: **observación del estado del sistema**. Cada cuadro es una foto de
las variables de estado que el navegador necesita para dibujar: posición y estado de cada
hormiga, más el reloj y la posición de la reina. Se envía en binario (9 bytes por hormiga)
porque mandar JSON por hormiga en cada cuadro sería demasiado lento.

Formato versión 1, little-endian:

    desplazamiento  tamaño  tipo        campo
    0               1       uint8       version = 1
    1               1       uint8       tipo_mensaje = 1 (CUADRO)
    2               2       uint16      reservado = 0
    4               4       uint32      tick
    8               4       uint32      n (número de hormigas)
    12              4       float32     tiempo simulado (s)
    16              4       float32     reina_x
    20              4       float32     reina_y
    24              4·n     float32[n]  x  (índice = id)
    24 + 4n         4·n     float32[n]  y
    24 + 8n         n       uint8[n]    estado (códigos EstadoHormiga)
    total: 24 + 9n bytes

`frontend/js/protocolo.js` lee exactamente este formato. Al final del archivo está el
mensaje tipo 2 (campo de feromonas).
"""

import struct

import numpy as np

from app.modelo.feromonas import CampoFeromonas
from app.modelo.mundo import Mundo

VERSION_PROTOCOLO = 1
TIPO_CUADRO = 1
FORMATO_ENCABEZADO = "<BBHIIfff"
TAMANO_ENCABEZADO = struct.calcsize(FORMATO_ENCABEZADO)  # 24 bytes
BYTES_POR_HORMIGA = 9


def tamano_cuadro(n: int) -> int:
    return TAMANO_ENCABEZADO + BYTES_POR_HORMIGA * n


def empaquetar_cuadro(tick: int, tiempo: float, mundo: Mundo) -> bytes:
    """Empaqueta el cuadro actual: encabezado de 24 bytes + x, y, estado."""
    h = mundo.hormigas
    encabezado = struct.pack(
        FORMATO_ENCABEZADO, VERSION_PROTOCOLO, TIPO_CUADRO, 0,
        tick, h.n, tiempo, mundo.reina.x, mundo.reina.y,
    )
    return b"".join((
        encabezado,
        h.x.astype("<f4", copy=False).tobytes(),
        h.y.astype("<f4", copy=False).tobytes(),
        h.estado.astype(np.uint8, copy=False).tobytes(),
    ))


def desempaquetar_cuadro(datos: bytes) -> dict:
    """Inverso de `empaquetar_cuadro` (para pruebas y scripts)."""
    version, tipo, _, tick, n, tiempo, reina_x, reina_y = struct.unpack_from(FORMATO_ENCABEZADO, datos)
    if len(datos) != tamano_cuadro(n):
        raise ValueError(f"el cuadro mide {len(datos)} bytes; se esperaban {tamano_cuadro(n)}")
    inicio_y = TAMANO_ENCABEZADO + 4 * n
    inicio_estado = TAMANO_ENCABEZADO + 8 * n
    return {
        "version": version, "tipo_mensaje": tipo, "tick": tick, "n": n, "tiempo": tiempo,
        "reina_x": reina_x, "reina_y": reina_y,
        "x": np.frombuffer(datos, "<f4", n, TAMANO_ENCABEZADO),
        "y": np.frombuffer(datos, "<f4", n, inicio_y),
        "estado": np.frombuffer(datos, np.uint8, n, inicio_estado),
    }


# --- Mensaje de feromonas (tipo 2) ----------------------------------------------------------
#
# Campo de feromonas cuantizado, unas 4 veces por segundo y sólo si están activas:
#
#     desplazamiento  tamaño  tipo        campo
#     0               1       uint8       version = 1
#     1               1       uint8       tipo_mensaje = 2 (FEROMONAS)
#     2               2       uint16      columnas
#     4               4       uint32      tick
#     8               2       uint16      filas
#     10              2       uint16      reservado = 0
#     12              4       float32     tamano_celda (unidades de longitud)
#     16              4       float32     concentracion_maxima (la que corresponde a 255)
#     20              filas·columnas  uint8  concentración por celda, fila por fila;
#                                            fila 0 = y pequeña (parte baja del mundo)
#     total: 20 + filas·columnas bytes

TIPO_FEROMONAS = 2
FORMATO_FEROMONAS = "<BBHIHHff"
TAMANO_ENCABEZADO_FEROMONAS = struct.calcsize(FORMATO_FEROMONAS)  # 20 bytes


def empaquetar_feromonas(tick: int, campo: CampoFeromonas) -> bytes:
    encabezado = struct.pack(
        FORMATO_FEROMONAS, VERSION_PROTOCOLO, TIPO_FEROMONAS, campo.columnas,
        tick, campo.filas, 0, campo.tamano_celda, float(campo.maxima),
    )
    return encabezado + campo.cuantizado().tobytes()


def desempaquetar_feromonas(datos: bytes) -> dict:
    """Inverso de `empaquetar_feromonas` (para pruebas)."""
    version, tipo, columnas, tick, filas, _, celda, maxima = struct.unpack_from(FORMATO_FEROMONAS, datos)
    if len(datos) != TAMANO_ENCABEZADO_FEROMONAS + filas * columnas:
        raise ValueError(f"el mensaje de feromonas mide {len(datos)} bytes")
    valores = np.frombuffer(datos, np.uint8, filas * columnas, TAMANO_ENCABEZADO_FEROMONAS)
    return {
        "version": version, "tipo_mensaje": tipo, "tick": tick, "filas": filas,
        "columnas": columnas, "tamano_celda": celda, "maxima": maxima,
        "valores": valores.reshape(filas, columnas),
    }
