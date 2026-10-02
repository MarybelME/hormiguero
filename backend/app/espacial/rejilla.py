"""Rejilla espacial (técnica de implementación, no concepto del modelo).

Divide el mundo en celdas cuadradas y guarda, para cada celda, qué roca o qué fuente la
ocupa (−1 si ninguna). Así, saber si una posición choca con una roca es un acceso directo
a un arreglo, sin recorrer las rocas: O(n) para n hormigas.

Una celda se marca si el círculo la toca. Para eso se compara la distancia del centro de
la celda con `radio + media diagonal de la celda`: todo punto dentro del círculo cae
siempre en una celda marcada (una hormiga nunca queda dentro de una roca).
"""

import math

import numpy as np

SIN_ELEMENTO = -1


class RejillaEspacial:
    def __init__(self, ancho: float, alto: float, tamano_celda: float) -> None:
        self.tamano_celda = tamano_celda
        self.columnas = math.ceil(ancho / tamano_celda)
        self.filas = math.ceil(alto / tamano_celda)
        forma = (self.filas, self.columnas)
        self.mapa_obstaculos = np.full(forma, SIN_ELEMENTO, dtype=np.int16)
        self.mapa_alimento = np.full(forma, SIN_ELEMENTO, dtype=np.int16)

    def _celdas_del_circulo(self, x: float, y: float, radio: float) -> tuple[np.ndarray, np.ndarray]:
        """Filas y columnas de las celdas que toca el círculo."""
        t = self.tamano_celda
        margen = radio + t * math.sqrt(2) / 2
        c0, c1 = max(0, int((x - margen) // t)), min(self.columnas - 1, int((x + margen) // t))
        f0, f1 = max(0, int((y - margen) // t)), min(self.filas - 1, int((y + margen) // t))
        filas, cols = np.mgrid[f0:f1 + 1, c0:c1 + 1]
        centro_x = (cols + 0.5) * t
        centro_y = (filas + 0.5) * t
        dentro = (centro_x - x) ** 2 + (centro_y - y) ** 2 <= margen**2
        return filas[dentro], cols[dentro]

    def marcar_obstaculo(self, id_obstaculo: int, x: float, y: float, radio: float) -> None:
        filas, cols = self._celdas_del_circulo(x, y, radio)
        self.mapa_obstaculos[filas, cols] = id_obstaculo

    def marcar_fuente(self, id_fuente: int, x: float, y: float, radio: float) -> None:
        filas, cols = self._celdas_del_circulo(x, y, radio)
        self.mapa_alimento[filas, cols] = id_fuente

    def borrar_fuente(self, id_fuente: int) -> None:
        """Una fuente agotada deja de existir en el mapa de alimento."""
        self.mapa_alimento[self.mapa_alimento == id_fuente] = SIN_ELEMENTO

    def celdas(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Fila y columna de cada posición, recortadas a la rejilla."""
        col = np.clip((x // self.tamano_celda).astype(np.int32), 0, self.columnas - 1)
        fila = np.clip((y // self.tamano_celda).astype(np.int32), 0, self.filas - 1)
        return fila, col

    def obstaculo_en(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        fila, col = self.celdas(x, y)
        return self.mapa_obstaculos[fila, col]

    def fuente_en(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        fila, col = self.celdas(x, y)
        return self.mapa_alimento[fila, col]
