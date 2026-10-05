"""Series de tiempo de las variables de salida.

Concepto de simulación: **variables de salida observadas en el tiempo**. Cada
`PASOS_POR_MUESTRA` pasos se toma una fotografía de las variables de estado del sistema
(cuántas hormigas hay en cada estado, alimento, colisiones, números usados…). Con ellas se
grafica la evolución de una corrida y se distingue el régimen transitorio del estable.
"""

from collections import deque
from collections.abc import Callable
from typing import Any

from app.modelo.estados import EstadoHormiga

PASOS_POR_MUESTRA = 10   # con dt = 0.1 s, una muestra por segundo simulado
MUESTRAS_MAXIMAS = 100_000

# Columna → (encabezado en español, cómo se obtiene del resumen de la simulación)
COLUMNAS: dict[str, tuple[str, Callable[[dict[str, Any]], Any]]] = {
    "tick": ("Paso", lambda r: r["tick"]),
    "tiempo": ("Tiempo (s)", lambda r: r["tiempo"]),
    **{
        f"estado_{estado.name.lower()}": (f"Hormigas {estado.name}",
                                         lambda r, nombre=estado.name: r["conteo_estados"][nombre])
        for estado in EstadoHormiga
    },
    "alimento_en_nido": ("Alimento en el nido", lambda r: r["alimento_en_nido"]),
    "alimento_en_fuentes": ("Alimento en las fuentes", lambda r: sum(r["alimento_por_fuente"])),
    "fuentes_agotadas": ("Fuentes agotadas", lambda r: r["fuentes_agotadas"]),
    "colisiones": ("Colisiones con rocas", lambda r: r["colisiones"]),
    "colisiones_borde": ("Colisiones con el borde", lambda r: r["colisiones_borde"]),
    "cambios_direccion": ("Cambios de dirección", lambda r: r["cambios_direccion"]),
    "giros_feromona": ("Giros por feromona", lambda r: r["giros_feromona"]),
    "feromona_total": ("Feromona total en el campo", lambda r: r["feromona_total"]),
    "decisiones_seguir": ("Decisiones de seguir a la reina", lambda r: r["decisiones_seguir"]),
    "seguimientos": ("La siguieron", lambda r: r["seguimientos"]),
    "numeros_generados": ("Números pseudoaleatorios generados", lambda r: r["numeros_generados"]),
    "resiembras_mundo": ("Re-siembras flujo MUNDO", lambda r: r["resiembras"]["MUNDO"]),
    "resiembras_comportamiento": ("Re-siembras flujo COMPORTAMIENTO",
                                  lambda r: r["resiembras"]["COMPORTAMIENTO"]),
}


class SeriesEstadisticas:
    """Muestras periódicas de las variables de salida (una fila por muestra)."""

    def __init__(self, pasos_por_muestra: int = PASOS_POR_MUESTRA,
                 maximo: int = MUESTRAS_MAXIMAS) -> None:
        self.pasos_por_muestra = pasos_por_muestra
        self._filas: deque[dict[str, Any]] = deque(maxlen=maximo)

    def toca_muestra(self, tick: int) -> bool:
        return tick % self.pasos_por_muestra == 0

    def registrar(self, resumen: dict[str, Any]) -> None:
        self._filas.append({clave: obtener(resumen) for clave, (_, obtener) in COLUMNAS.items()})

    @property
    def filas(self) -> list[dict[str, Any]]:
        return list(self._filas)

    def __len__(self) -> int:
        return len(self._filas)
