"""Campo de feromonas.

Concepto de simulación: **variable de estado del entorno (campo)**. A diferencia de los
atributos de una hormiga, la feromona es una cantidad repartida en el espacio: una rejilla
2D donde cada celda guarda su concentración. Cambia por tres procesos:

- depositar: cada hormiga que lleva comida suma `deposito` en su celda (un rastro);
- evaporar:  en cada paso toda celda pierde una fracción ρ:  c ← c · (1 − ρ).
  Sin depósitos, tras k pasos queda c₀ · (1 − ρ)^k (decaimiento geométrico);
- muestrear: las hormigas que buscan leen la concentración en puntos delante de ellas.

Todo es determinista (no usa números pseudoaleatorios): con la misma semilla las rutas se
forman igual. La celda es más grande que la de la rejilla espacial porque el rastro es una
propiedad "gruesa" del terreno y así el navegador recibe pocas celdas.
"""

import math

import numpy as np


class CampoFeromonas:
    """Concentración de feromona por celda (fila 0 = parte baja del mundo, y pequeña)."""

    def __init__(self, ancho: float, alto: float, tamano_celda: float,
                 maxima: float, minima: float) -> None:
        self.tamano_celda = tamano_celda
        self.columnas = math.ceil(ancho / tamano_celda)
        self.filas = math.ceil(alto / tamano_celda)
        self.maxima = np.float32(maxima)
        self.minima = np.float32(minima)
        self.concentracion = np.zeros((self.filas, self.columnas), dtype=np.float32)

    def _celdas(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Fila, columna y si la posición cae dentro del campo."""
        col = np.floor(np.asarray(x) / self.tamano_celda).astype(np.int64)
        fila = np.floor(np.asarray(y) / self.tamano_celda).astype(np.int64)
        dentro = (col >= 0) & (col < self.columnas) & (fila >= 0) & (fila < self.filas)
        return fila, col, dentro

    def depositar(self, x: np.ndarray, y: np.ndarray, cantidad: float) -> None:
        """Suma `cantidad` en la celda de cada posición (varias en la misma celda se acumulan)."""
        fila, col, dentro = self._celdas(x, y)
        np.add.at(self.concentracion, (fila[dentro], col[dentro]), np.float32(cantidad))
        np.minimum(self.concentracion, self.maxima, out=self.concentracion)

    def evaporar(self, tasa: float) -> None:
        """c ← c · (1 − ρ); lo que queda por debajo de la mínima se vuelve 0."""
        self.concentracion *= np.float32(1.0 - tasa)
        self.concentracion[self.concentracion < self.minima] = 0

    def muestrear(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Concentración en cada posición (0 fuera del mundo)."""
        fila, col, dentro = self._celdas(x, y)
        valores = np.zeros(np.shape(fila), dtype=np.float32)
        valores[dentro] = self.concentracion[fila[dentro], col[dentro]]
        return valores

    def total(self) -> float:
        return float(self.concentracion.sum(dtype=np.float64))

    def cuantizado(self) -> np.ndarray:
        """Concentración en 0–255 (uint8) relativa a la máxima, para enviarla al navegador."""
        escala = np.float32(255) / self.maxima
        return np.minimum(np.rint(self.concentracion * escala), 255).astype(np.uint8)

    def limpiar(self) -> None:
        self.concentracion.fill(0)
