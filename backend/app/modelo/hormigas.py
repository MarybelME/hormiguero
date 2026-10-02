"""Colección de hormigas obreras.

Concepto de simulación: **entidades temporales y móviles** con sus **atributos** (variables
de estado). Para manejar miles de hormigas no hay un objeto por hormiga: cada atributo es
una columna NumPy (estructura de arreglos) y la hormiga `id` es la fila `id` de todas las
columnas. `vista(id)` reúne una fila para mostrarla en el modo didáctico.
"""

from typing import Any

import numpy as np

from app.eventos.tipos import TipoEvento
from app.modelo.estados import EstadoHormiga
from app.modelo.nido import Nido


class Hormigas:
    """Atributos de las `n` obreras como arreglos paralelos (DISENO.md §5)."""

    def __init__(self, n: int, nido: Nido, velocidad: float, energia_max: float) -> None:
        self.n = n
        self.id = np.arange(n, dtype=np.int32)
        self.x = np.full(n, nido.x, dtype=np.float32)
        self.y = np.full(n, nido.y, dtype=np.float32)
        self.dir = np.zeros(n, dtype=np.float32)          # grados, 0° = este, antihorario
        self.vel = np.full(n, velocidad, dtype=np.float32)
        self.energia = np.full(n, energia_max, dtype=np.float32)
        self.estado = np.full(n, EstadoHormiga.EN_NIDO, dtype=np.uint8)
        self.carga = np.zeros(n, dtype=np.uint8)
        # Columnas de apoyo para la máquina de estados y el modo didáctico.
        self.estado_previo = np.full(n, EstadoHormiga.EN_NIDO, dtype=np.uint8)
        self.pasos_restantes = np.zeros(n, dtype=np.int16)
        self.en_radio_reina = np.zeros(n, dtype=np.bool_)
        self.ultimo_u = np.full(n, np.nan, dtype=np.float32)
        self.ultimo_indice_u = np.full(n, -1, dtype=np.int32)
        self.ultimo_evento = np.full(n, TipoEvento.NINGUNO, dtype=np.uint8)
        self.tick_ultimo_evento = np.zeros(n, dtype=np.uint32)

    COLUMNAS = (
        "id", "x", "y", "dir", "vel", "energia", "estado", "carga", "estado_previo",
        "pasos_restantes", "en_radio_reina", "ultimo_u", "ultimo_indice_u", "ultimo_evento",
        "tick_ultimo_evento",
    )

    def vista(self, id_hormiga: int) -> dict[str, Any]:
        """Atributos de una hormiga como diccionario legible (para el modo didáctico)."""
        if not 0 <= id_hormiga < self.n:
            raise IndexError(f"no existe la hormiga {id_hormiga}")
        datos = {columna: getattr(self, columna)[id_hormiga].item() for columna in self.COLUMNAS}
        datos["estado"] = EstadoHormiga(datos["estado"]).name
        datos["estado_previo"] = EstadoHormiga(datos["estado_previo"]).name
        datos["ultimo_evento"] = TipoEvento(datos["ultimo_evento"]).name
        return datos

    def copia_columnas(self) -> dict[str, np.ndarray]:
        """Copia de todas las columnas (para comparar corridas en las pruebas)."""
        return {columna: getattr(self, columna).copy() for columna in self.COLUMNAS}
