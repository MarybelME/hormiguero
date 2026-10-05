"""Laboratorio de generadores: comparar métodos con las mismas pruebas.

Concepto de simulación: **experimentación con generadores**. Cada generador produce una
muestra con su propia semilla (la sucesión es exactamente la que usaría el modelo, re-siembras
incluidas) y se somete a las pruebas de uniformidad e independencia. Usa generadores
temporales: no toca ninguna simulación.
"""

from dataclasses import asdict
from typing import Any

from app.aleatorio.fabrica import GENERADORES, ConfiguracionGenerador, crear_generador
from app.aleatorio.pruebas_estadisticas import (
    prueba_chi_cuadrada,
    prueba_corridas,
    prueba_kolmogorov_smirnov,
    resumen_muestra,
)


def evaluar_generador(configuracion: ConfiguracionGenerador, semilla: int, cantidad: int,
                      intervalos: int, alfa: float) -> dict[str, Any]:
    """Genera `cantidad` números y devuelve su resumen y las tres pruebas."""
    generador = crear_generador(configuracion, semilla)
    muestra = [generador.siguiente() for _ in range(cantidad)]
    pruebas = [
        prueba_chi_cuadrada(muestra, intervalos, alfa),
        prueba_kolmogorov_smirnov(muestra, alfa),
        prueba_corridas(muestra, alfa),
    ]
    return {
        "generador": configuracion.generador,
        "nombre": GENERADORES[configuracion.generador].nombre,
        "semilla": semilla,
        "modulo": generador.modulo,
        "resiembras": generador.resiembras,
        "muestra": resumen_muestra(muestra, intervalos),
        "primeros": muestra[:10],
        "pruebas": [asdict(prueba) for prueba in pruebas],
    }
