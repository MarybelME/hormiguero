"""Mide cuántos pasos por segundo calcula el núcleo, sin servidor.

Uso (desde la raíz del proyecto):

    python backend/scripts/benchmark.py
    python backend/scripts/benchmark.py --hormigas 5000 --pasos 1000

Primero se ejecuta un calentamiento para que la mayoría de las hormigas haya salido del
nido; luego se cronometran los pasos. La meta del proyecto es 5 000 hormigas a ≥ 30 pasos/s
(un cuadro por paso a 30 cuadros/s).
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import ParametrosSimulacion  # noqa: E402
from app.modelo.estados import EstadoHormiga  # noqa: E402
from app.nucleo.simulacion import Simulacion  # noqa: E402

TAMANOS_POR_DEFECTO = (1000, 5000, 20_000)
SALIDAS_BENCHMARK = 100  # salen rápido para medir con casi todas las hormigas fuera
META_PASOS_POR_SEGUNDO = 30


def medir(num_hormigas: int, pasos: int, calentamiento: int) -> tuple[float, int]:
    parametros = ParametrosSimulacion(num_hormigas=num_hormigas, salidas_por_paso=SALIDAS_BENCHMARK)
    simulacion = Simulacion(parametros)
    simulacion.avanzar(calentamiento)
    inicio = time.perf_counter()
    simulacion.avanzar(pasos)
    segundos = time.perf_counter() - inicio
    fuera = int((simulacion.mundo.hormigas.estado != EstadoHormiga.EN_NIDO).sum())
    return pasos / segundos, fuera


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos correctos también en la consola de Windows
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--hormigas", type=int, nargs="*", default=list(TAMANOS_POR_DEFECTO))
    argumentos.add_argument("--pasos", type=int, default=500)
    argumentos.add_argument("--calentamiento", type=int, default=300)
    opciones = argumentos.parse_args()

    print(f"{'hormigas':>9} | {'fuera del nido':>14} | {'pasos/s':>9} | {'ms/paso':>8} | meta >= {META_PASOS_POR_SEGUNDO}")
    print("-" * 64)
    for n in opciones.hormigas:
        pasos_por_segundo, fuera = medir(n, opciones.pasos, opciones.calentamiento)
        cumple = "sí" if pasos_por_segundo >= META_PASOS_POR_SEGUNDO else "no"
        print(f"{n:>9} | {fuera:>14} | {pasos_por_segundo:>9.1f} | {1000 / pasos_por_segundo:>8.2f} | {cumple}")


if __name__ == "__main__":
    main()
