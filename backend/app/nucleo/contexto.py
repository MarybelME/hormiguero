"""Contexto de un paso de simulación.

Concepto de simulación: **estado del sistema visible para las reglas en un instante**. Todas
las reglas de comportamiento reciben este objeto: el reloj, el mundo, los parámetros, la
fuente de números pseudoaleatorios, la bitácora y los contadores.

`campos` da acceso a los campos del entorno (feromonas en la etapa E4) sin cambiar las
firmas de las reglas cuando se agreguen.
"""

from dataclasses import dataclass
from typing import Any

from app.aleatorio.servicio import ServicioAleatorio
from app.config import ParametrosSimulacion
from app.estadisticas.contadores import Estadisticas
from app.eventos.bitacora import Bitacora
from app.modelo.hormigas import Hormigas
from app.modelo.mundo import Mundo


@dataclass
class ContextoPaso:
    tick: int
    tiempo: float
    dt: float
    mundo: Mundo
    parametros: ParametrosSimulacion
    aleatorio: ServicioAleatorio
    bitacora: Bitacora
    estadisticas: Estadisticas

    @property
    def hormigas(self) -> Hormigas:
        return self.mundo.hormigas

    @property
    def campos(self) -> dict[str, Any]:
        return self.mundo.campos
