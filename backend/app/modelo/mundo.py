"""Mundo.

Concepto de simulación: **sistema** y su **entorno con frontera**. Reúne todas las entidades
y elementos: nido, reina, obreras, fuentes de alimento y rocas, dentro del rectángulo
[0, ancho) × [0, alto).

`campos` está reservado para los campos del entorno (feromonas, etapa E4): las reglas de
comportamiento lo reciben en el contexto aunque hoy esté vacío.
"""

from dataclasses import dataclass, field
from typing import Any

from app.espacial.rejilla import RejillaEspacial
from app.modelo.alimento import FuenteAlimento
from app.modelo.hormigas import Hormigas
from app.modelo.nido import Nido
from app.modelo.obstaculos import Obstaculo
from app.modelo.reina import Reina


@dataclass
class Mundo:
    ancho: float
    alto: float
    nido: Nido
    reina: Reina
    hormigas: Hormigas
    obstaculos: list[Obstaculo]
    fuentes: list[FuenteAlimento]
    rejilla: RejillaEspacial
    campos: dict[str, Any] = field(default_factory=dict)
    # Cuenta cuántas veces cambió la capa estática (p. ej. una fuente se agotó).
    version_estatica: int = 0
    # Datos de la generación por aceptación-rechazo, para mostrarlos en clase.
    generacion: dict[str, int] = field(default_factory=dict)

    def dentro(self, x: float, y: float) -> bool:
        return 0.0 <= x < self.ancho and 0.0 <= y < self.alto

    def capa_estatica(self) -> dict[str, Any]:
        """Lo que no cambia en cada cuadro: dimensiones, nido, reina (zona), rocas y fuentes."""
        return {
            "ancho": self.ancho,
            "alto": self.alto,
            "version": self.version_estatica,
            "nido": {
                "x": self.nido.x, "y": self.nido.y, "radio": self.nido.radio,
                "alimento_almacenado": self.nido.alimento_almacenado,
            },
            "reina": {
                "x": self.reina.x, "y": self.reina.y,
                "radio_influencia": self.reina.radio_influencia,
                "radio_patrulla": self.reina.radio_patrulla,
            },
            "obstaculos": [
                {"id": o.id, "x": o.x, "y": o.y, "radio": o.radio} for o in self.obstaculos
            ],
            "fuentes": [
                {"id": f.id, "x": f.x, "y": f.y, "radio": f.radio,
                 "cantidad": f.cantidad, "cantidad_inicial": f.cantidad_inicial}
                for f in self.fuentes
            ],
            "generacion": dict(self.generacion),
        }
