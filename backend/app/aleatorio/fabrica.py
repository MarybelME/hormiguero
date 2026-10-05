"""Fábrica de generadores de números pseudoaleatorios.

Concepto de simulación: **intercambiabilidad del generador** (RF-16). El modelo sólo
conoce la interfaz `GeneradorPseudoaleatorio`; qué método se usa lo decide esta fábrica a
partir de los parámetros. Agregar un generador es escribir su clase y añadir una entrada
a `GENERADORES`: no se toca el modelo.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.aleatorio.base import GeneradorPseudoaleatorio
from app.aleatorio.congruencial import (
    METODO_LINEAL,
    METODO_MULTIPLICATIVO,
    GeneradorCongruencial,
    GeneradorCongruencialMultiplicativo,
    validar_congruencial,
)
from app.aleatorio.cuadrados_medios import GeneradorCuadradosMedios, validar_configuracion
from app.aleatorio.cuadrados_medios import METODO as METODO_CUADRADOS_MEDIOS
from app.aleatorio.numpy_referencia import METODO as METODO_NUMPY
from app.aleatorio.numpy_referencia import MODULO_SEMILLA, GeneradorNumpy, validar_numpy


@dataclass(frozen=True)
class ConfiguracionGenerador:
    """Qué método usar y con qué constantes (la semilla va aparte: cada flujo tiene la suya)."""

    generador: str
    digitos: int = 4
    congruencial_a: int = 1103515245
    congruencial_c: int = 12345
    congruencial_m: int = 2**31
    multiplicativo_a: int = 16807
    multiplicativo_m: int = 2**31 - 1


@dataclass(frozen=True)
class TipoGenerador:
    """Entrada del registro: cómo crearlo, cómo validarlo y cuál es su módulo."""

    nombre: str
    crear: Callable[[ConfiguracionGenerador, int], GeneradorPseudoaleatorio]
    validar: Callable[[ConfiguracionGenerador, int], None]
    modulo: Callable[[ConfiguracionGenerador], int]


GENERADORES: dict[str, TipoGenerador] = {
    METODO_CUADRADOS_MEDIOS: TipoGenerador(
        nombre="Cuadrados medios",
        crear=lambda cfg, s: GeneradorCuadradosMedios(s, cfg.digitos),
        validar=lambda cfg, s: validar_configuracion(s, cfg.digitos),
        modulo=lambda cfg: 10**cfg.digitos,
    ),
    METODO_LINEAL: TipoGenerador(
        nombre="Congruencial lineal",
        crear=lambda cfg, s: GeneradorCongruencial(
            s, cfg.congruencial_a, cfg.congruencial_c, cfg.congruencial_m),
        validar=lambda cfg, s: validar_congruencial(
            s, cfg.congruencial_a, cfg.congruencial_c, cfg.congruencial_m),
        modulo=lambda cfg: cfg.congruencial_m,
    ),
    METODO_MULTIPLICATIVO: TipoGenerador(
        nombre="Congruencial multiplicativo",
        crear=lambda cfg, s: GeneradorCongruencialMultiplicativo(
            s, cfg.multiplicativo_a, cfg.multiplicativo_m),
        validar=lambda cfg, s: validar_congruencial(
            s, cfg.multiplicativo_a, 0, cfg.multiplicativo_m),
        modulo=lambda cfg: cfg.multiplicativo_m,
    ),
    METODO_NUMPY: TipoGenerador(
        nombre="NumPy (PCG64, referencia)",
        crear=lambda cfg, s: GeneradorNumpy(s),
        validar=lambda cfg, s: validar_numpy(s),
        modulo=lambda cfg: MODULO_SEMILLA,
    ),
}


def _tipo(configuracion: ConfiguracionGenerador) -> TipoGenerador:
    try:
        return GENERADORES[configuracion.generador]
    except KeyError:
        raise ValueError(f"generador desconocido: {configuracion.generador}") from None


def crear_generador(configuracion: ConfiguracionGenerador, semilla: int) -> GeneradorPseudoaleatorio:
    return _tipo(configuracion).crear(configuracion, semilla)


def validar_generador(configuracion: ConfiguracionGenerador, semilla: int) -> None:
    """Lanza ValueError si la semilla o las constantes no sirven para ese método."""
    _tipo(configuracion).validar(configuracion, semilla)


def modulo_generador(configuracion: ConfiguracionGenerador) -> int:
    return _tipo(configuracion).modulo(configuracion)


def semilla_derivada(semilla: int, modulo: int) -> int:
    """Semilla del flujo COMPORTAMIENTO (DISENO.md, decisiones k y r): (semilla + m/2) mod m.

    Si da 0 se usa 1. Con cuadrados medios, m = 10^D: 5735 → 735 con D = 4.
    """
    derivada = (semilla + modulo // 2) % modulo
    return derivada if derivada != 0 else 1
