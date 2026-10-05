"""Réplicas por lote (RF-60).

Concepto de simulación: **experimentación con réplicas independientes**. Una sola corrida
es una observación de un sistema aleatorio; para estimar una medida de desempeño se repite
la corrida con semillas distintas (todo lo demás igual) y se resume cada variable de salida
con su media, su desviación estándar y un intervalo de confianza:

    IC = media ± t_{0.975, n−1} · s / √n

Semillas: la réplica i (desde 0) usa `semilla_inicial + i`, dando la vuelta dentro de
[1, m − 1] si hace falta. Con las mismas entradas, el lote completo se repite idéntico.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.config import ParametrosSimulacion
from app.aleatorio.fabrica import modulo_generador
from app.nucleo.simulacion import Simulacion

NIVEL_CONFIANZA = 0.95
# t_{0.975, gl} (tabla de la t de Student, dos colas al 95 %) para gl = 1 … 30
T_975 = [
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
]
# Más allá de 30 gl, valores de tabla en algunos puntos; se usa el del gl tabulado inmediato inferior.
T_975_GRANDE = [(40, 2.021), (60, 2.000), (120, 1.980)]
Z_975 = 1.960


def t_975(grados: int) -> float:
    """Cuantil 0.975 de la t de Student (valor conservador entre puntos de la tabla)."""
    if grados < 1:
        raise ValueError("se necesitan al menos 2 réplicas para un intervalo de confianza")
    if grados <= len(T_975):
        return T_975[grados - 1]
    valor = T_975[-1]
    for limite, t in T_975_GRANDE:
        if grados >= limite:
            valor = t
    return valor if grados < 1000 else Z_975


# Variable de salida → (descripción, cómo se obtiene del resumen final de la corrida)
VARIABLES_SALIDA: dict[str, tuple[str, Callable[[dict[str, Any]], float | None]]] = {
    "alimento_recolectado": ("Alimento depositado en el nido (unidades)", lambda r: r["alimento_recolectado"]),
    "fuentes_agotadas": ("Fuentes agotadas", lambda r: r["fuentes_agotadas"]),
    "colisiones": ("Colisiones (rocas + borde)", lambda r: r["colisiones"] + r["colisiones_borde"]),
    "cambios_direccion": ("Cambios de dirección", lambda r: r["cambios_direccion"]),
    "giros_feromona": ("Giros por feromona", lambda r: r["giros_feromona"]),
    "proporcion_seguir": ("Proporción que siguió a la reina (p̂)",
                          lambda r: r["seguimientos"] / r["decisiones_seguir"] if r["decisiones_seguir"] else None),
    "buscando_al_final": ("Hormigas buscando comida al final", lambda r: r["conteo_estados"]["BUSCANDO_COMIDA"]),
    "numeros_generados": ("Números pseudoaleatorios generados", lambda r: r["numeros_generados"]),
    "resiembras": ("Re-siembras del generador (ambos flujos)",
                   lambda r: r["resiembras"]["MUNDO"] + r["resiembras"]["COMPORTAMIENTO"]),
}


@dataclass(frozen=True)
class ResumenVariable:
    variable: str
    descripcion: str
    n: int                 # réplicas con valor (p̂ no existe si nadie entró al radio de la reina)
    media: float | None
    desviacion: float | None
    ic_inferior: float | None
    ic_superior: float | None
    minimo: float | None
    maximo: float | None


@dataclass
class ResultadoLote:
    parametros: dict[str, Any]
    pasos: int
    semillas: list[int]
    replicas: list[dict[str, Any]] = field(default_factory=list)  # semilla + variables de salida
    resumen: list[ResumenVariable] = field(default_factory=list)


def semillas_del_lote(semilla_inicial: int, replicas: int, modulo: int) -> list[int]:
    """semilla_inicial, semilla_inicial + 1, …, dando la vuelta dentro de [1, m − 1]."""
    return [(semilla_inicial - 1 + i) % (modulo - 1) + 1 for i in range(replicas)]


def correr_replica(parametros: ParametrosSimulacion, pasos: int) -> dict[str, Any]:
    simulacion = Simulacion(parametros)
    simulacion.avanzar(pasos)
    final = simulacion.resumen()
    return {nombre: obtener(final) for nombre, (_, obtener) in VARIABLES_SALIDA.items()}


def resumir(variable: str, valores: list[float | None]) -> ResumenVariable:
    datos = [float(v) for v in valores if v is not None]
    n = len(datos)
    descripcion = VARIABLES_SALIDA[variable][0]
    if n == 0:
        return ResumenVariable(variable, descripcion, 0, None, None, None, None, None, None)
    media = sum(datos) / n
    if n == 1:
        return ResumenVariable(variable, descripcion, 1, media, None, None, None, datos[0], datos[0])
    desviacion = math.sqrt(sum((x - media) ** 2 for x in datos) / (n - 1))
    semiamplitud = t_975(n - 1) * desviacion / math.sqrt(n)
    return ResumenVariable(variable, descripcion, n, media, desviacion,
                           media - semiamplitud, media + semiamplitud, min(datos), max(datos))


def ejecutar_lote(
    parametros: ParametrosSimulacion,
    replicas: int,
    pasos: int,
    semilla_inicial: int | None = None,
    al_terminar_replica: Callable[[int, int], None] | None = None,
    cancelado: Callable[[], bool] | None = None,
) -> ResultadoLote:
    """Corre `replicas` corridas de `pasos` pasos cambiando sólo la semilla.

    `al_terminar_replica(hechas, total)` informa el avance; si `cancelado()` devuelve True,
    el lote se detiene y el resultado sólo incluye las réplicas terminadas.
    """
    inicial = parametros.semilla if semilla_inicial is None else semilla_inicial
    semillas = semillas_del_lote(inicial, replicas, modulo_generador(parametros.configuracion_generador))
    resultado = ResultadoLote(parametros=parametros.model_dump(), pasos=pasos, semillas=semillas)
    base = parametros.model_dump()
    for i, semilla in enumerate(semillas):
        if cancelado is not None and cancelado():
            break
        # Se validan los parámetros de cada réplica (la semilla debe servir al generador).
        parametros_replica = ParametrosSimulacion(**{**base, "semilla": semilla})
        resultado.replicas.append({"semilla": semilla, **correr_replica(parametros_replica, pasos)})
        if al_terminar_replica is not None:
            al_terminar_replica(i + 1, replicas)
    resultado.resumen = [
        resumir(variable, [r[variable] for r in resultado.replicas]) for variable in VARIABLES_SALIDA
    ]
    return resultado
