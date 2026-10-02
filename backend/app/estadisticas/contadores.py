"""Contadores de la simulación.

Concepto de simulación: **variables de estado del sistema** y **medidas de desempeño**.
Los contadores discretos (colisiones, cambios de dirección, alimento…) los incrementan los
eventos; el conteo por estado se recalcula al final de cada paso.

Un "cambio de dirección" es toda dirección nueva asignada por un evento (colisión, borde,
fin de seguimiento, encontrar alimento, energía baja). No cuenta la dirección inicial al
salir del nido ni la corrección continua del rumbo hacia el nido o hacia la reina.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.modelo.estados import EstadoHormiga


def _conteo_vacio() -> np.ndarray:
    return np.zeros(len(EstadoHormiga), dtype=np.int64)


@dataclass
class Estadisticas:
    colisiones: int = 0               # con rocas
    colisiones_borde: int = 0         # con la frontera del mundo
    cambios_direccion: int = 0
    salidas: int = 0
    llegadas_nido: int = 0
    llegadas_sin_alimento: int = 0    # llegaron a una fuente que se agotó en ese mismo paso
    alimento_recolectado: int = 0     # unidades depositadas en el nido
    fuentes_agotadas: int = 0
    decisiones_seguir: int = 0        # entradas al radio de la reina evaluadas
    seguimientos: int = 0             # de ellas, cuántas decidieron seguirla
    conteo_estados: np.ndarray = field(default_factory=_conteo_vacio)

    def actualizar_conteo(self, estados: np.ndarray) -> None:
        self.conteo_estados = np.bincount(estados, minlength=len(EstadoHormiga))

    def como_dict(self) -> dict[str, Any]:
        datos = {nombre: valor for nombre, valor in vars(self).items() if nombre != "conteo_estados"}
        datos["conteo_estados"] = {
            estado.name: int(self.conteo_estados[estado]) for estado in EstadoHormiga
        }
        return datos
